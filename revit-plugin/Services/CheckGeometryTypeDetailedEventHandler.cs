using Autodesk.Revit.DB;
using Autodesk.Revit.UI;
using RevitMCPSDK.API.Interfaces;
using System;
using System.Collections.Generic;
using System.Linq;
using System.Security.Cryptography;
using System.Text;
using System.Threading;

namespace RevitMCPCommandSet.Services
{
    /// <summary>
    /// Event handler for detailed geometry grading per Autodesk criterion
    /// </summary>
    public class CheckGeometryTypeDetailedEventHandler : IExternalEventHandler, IWaitableExternalEventHandler
    {
        private string _elementId;
        public object Result { get; private set; }
        public bool TaskCompleted { get; private set; }
        private readonly ManualResetEvent _resetEvent = new ManualResetEvent(false);

        public void SetElementId(string elementId)
        {
            _elementId = elementId;
            TaskCompleted = false;
            _resetEvent.Reset();
        }

        public bool WaitForCompletion(int timeoutMilliseconds = 10000)
        {
            return _resetEvent.WaitOne(timeoutMilliseconds);
        }

        public void Execute(UIApplication app)
        {
            try
            {
                var doc = app.ActiveUIDocument.Document;

                // Parse element ID
                if (!long.TryParse(_elementId, out long elementIdLong))
                {
                    throw new ArgumentException($"Invalid element ID: {_elementId}");
                }

                ElementId elementId = new ElementId(elementIdLong);
                Element element = doc.GetElement(elementId);

                if (element == null)
                {
                    throw new Exception($"Element with ID {_elementId} not found");
                }

                // Get family information
                string familyName = "N/A";
                string familyTypeName = "N/A";
                
                if (element is FamilyInstance familyInstance)
                {
                    familyName = familyInstance.Symbol?.Family?.Name ?? "Unknown";
                    familyTypeName = familyInstance.Symbol?.Name ?? "Unknown";
                }
                else if (element is ElementType elementType)
                {
                    familyName = elementType.FamilyName ?? "System Family";
                    familyTypeName = elementType.Name;
                }

                // Get geometry
                Options geometryOptions = new Options
                {
                    DetailLevel = ViewDetailLevel.Fine,
                    IncludeNonVisibleObjects = false
                };

                GeometryElement geometryElement = element.get_Geometry(geometryOptions);

                if (geometryElement == null)
                {
                    Result = new
                    {
                        elementId = _elementId,
                        elementName = element.Name,
                        hasGeometry = false,
                        message = "No geometry found for this element"
                    };
                }
                else
                {
                    // Analyze geometry
                    var analysis = AnalyzeGeometry(geometryElement);
                    
                    // Calculate detailed grades for each criterion
                    var detailedGrades = CalculateDetailedGrades(analysis);
                    
                    // Calculate overall grade
                    var overallGrade = CalculateOverallGrade(detailedGrades);

                    // Get Revit file information
                    string revitFileName = doc.Title;
                    string gradeDateTime = DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss");
                    
                    // Generate unique family hash
                    string familyHash = GenerateFamilyHash(familyName, familyTypeName, analysis);

                    Result = new
                    {
                        elementId = _elementId,
                        elementUniqueId = element.UniqueId,
                        elementName = element.Name,
                        elementCategory = element.Category?.Name ?? "Unknown",
                        familyName = familyName,
                        familyTypeName = familyTypeName,
                        familyHash = familyHash,
                        revitFileName = revitFileName,
                        gradeDateTime = gradeDateTime,
                        
                        // Overall metrics
                        solidCount = analysis.SolidCount,
                        meshCount = analysis.MeshCount,
                        totalFaces = analysis.TotalFaces,
                        totalEdges = analysis.TotalEdges,
                        geometryInstanceCount = analysis.GeometryInstanceCount,
                        
                        // Detailed grades per criterion
                        criteriaGrades = new
                        {
                            geometryType = detailedGrades.GeometryTypeGrade,
                            faceCount = detailedGrades.FaceCountGrade,
                            nesting = detailedGrades.NestingGrade
                        },
                        
                        // Overall grade
                        overallGrade = overallGrade.Grade,
                        overallScore = overallGrade.Score,
                        overallAnalysis = overallGrade.Analysis,
                        
                        // Recommendations
                        recommendations = overallGrade.Recommendations
                    };
                }

                TaskCompleted = true;
            }
            catch (Exception ex)
            {
                Result = new
                {
                    error = true,
                    message = ex.Message
                };
                TaskCompleted = true;
            }
            finally
            {
                _resetEvent.Set();
            }
        }

        private GeometryAnalysis AnalyzeGeometry(GeometryElement geometryElement)
        {
            var analysis = new GeometryAnalysis();
            var details = new List<string>();

            foreach (GeometryObject geomObj in geometryElement)
            {
                if (geomObj is Solid solid)
                {
                    if (solid.Faces.Size > 0 && solid.Volume > 0.0001)
                    {
                        analysis.SolidCount++;
                        analysis.TotalFaces += solid.Faces.Size;
                        analysis.TotalEdges += solid.Edges.Size;
                        
                        // Detect import source based on solid characteristics
                        if (IsLikelyImportedSAT(solid))
                        {
                            analysis.ImportedSATSolids++;
                            analysis.HasComplexBRep = true;
                            if (!analysis.DetectedSources.Contains("SAT/ACIS Import"))
                                analysis.DetectedSources.Add("SAT/ACIS Import");
                        }
                        else
                        {
                            analysis.NativeRevitSolids++;
                            if (!analysis.DetectedSources.Contains("Native Revit"))
                                analysis.DetectedSources.Add("Native Revit");
                        }
                    }
                }
                else if (geomObj is Mesh mesh)
                {
                    analysis.MeshCount++;
                    analysis.ImportedMeshes++;
                    analysis.TotalFaces += mesh.NumTriangles;
                    
                    // Meshes are typically from STL, OBJ, SketchUp, or other imports
                    if (!analysis.DetectedSources.Contains("Mesh Import (STL/OBJ/SketchUp)"))
                        analysis.DetectedSources.Add("Mesh Import (STL/OBJ/SketchUp)");
                }
                else if (geomObj is GeometryInstance geometryInstance)
                {
                    analysis.GeometryInstanceCount++;
                    var instanceGeometry = geometryInstance.GetInstanceGeometry();
                    if (instanceGeometry != null)
                    {
                        var instanceAnalysis = AnalyzeGeometry(instanceGeometry);
                        analysis.SolidCount += instanceAnalysis.SolidCount;
                        analysis.MeshCount += instanceAnalysis.MeshCount;
                        analysis.TotalFaces += instanceAnalysis.TotalFaces;
                        analysis.TotalEdges += instanceAnalysis.TotalEdges;
                        analysis.NativeRevitSolids += instanceAnalysis.NativeRevitSolids;
                        analysis.ImportedSATSolids += instanceAnalysis.ImportedSATSolids;
                        analysis.ImportedMeshes += instanceAnalysis.ImportedMeshes;
                        analysis.HasComplexBRep = analysis.HasComplexBRep || instanceAnalysis.HasComplexBRep;
                        
                        // Merge detected sources
                        foreach (var source in instanceAnalysis.DetectedSources)
                        {
                            if (!analysis.DetectedSources.Contains(source))
                                analysis.DetectedSources.Add(source);
                        }
                    }
                }
            }

            analysis.HasSolids = analysis.SolidCount > 0;
            analysis.HasMeshes = analysis.MeshCount > 0;

            return analysis;
        }
        
        /// <summary>
        /// Detects if a solid is likely imported from SAT/ACIS (AutoCAD, Inventor, SolidWorks, STEP)
        /// Based on surface complexity and NURBS characteristics
        /// </summary>
        private bool IsLikelyImportedSAT(Solid solid)
        {
            int nurbsSurfaceCount = 0;
            int cylindricalSurfaceCount = 0;
            int conicalSurfaceCount = 0;
            int planarSurfaceCount = 0;
            int complexSurfaceCount = 0;
            
            foreach (Face face in solid.Faces)
            {
                if (face is HermiteFace || face is RuledFace)
                {
                    // NURBS or complex ruled surfaces - typical of SAT imports
                    nurbsSurfaceCount++;
                    complexSurfaceCount++;
                }
                else if (face is CylindricalFace)
                {
                    cylindricalSurfaceCount++;
                }
                else if (face is ConicalFace)
                {
                    conicalSurfaceCount++;
                }
                else if (face is PlanarFace)
                {
                    planarSurfaceCount++;
                }
                else
                {
                    // Other complex surface types
                    complexSurfaceCount++;
                }
            }
            
            int totalFaces = solid.Faces.Size;
            
            // Heuristics for SAT detection:
            // 1. High ratio of NURBS/complex surfaces (>30%)
            // 2. Very high face count for simple shapes (likely over-tessellated)
            // 3. Mix of surface types uncommon in native Revit modeling
            
            double complexRatio = totalFaces > 0 ? (double)complexSurfaceCount / totalFaces : 0;
            double nurbsRatio = totalFaces > 0 ? (double)nurbsSurfaceCount / totalFaces : 0;
            
            // Native Revit typically uses simple extrusions, sweeps, blends
            // SAT imports have higher surface complexity
            bool hasHighNURBSContent = nurbsRatio > 0.3;
            bool hasHighComplexity = complexRatio > 0.4;
            bool hasUnusuallyHighFaceCount = totalFaces > 200 && (planarSurfaceCount + cylindricalSurfaceCount) < totalFaces * 0.5;
            
            return hasHighNURBSContent || hasHighComplexity || hasUnusuallyHighFaceCount;
        }

        private DetailedCriteriaGrades CalculateDetailedGrades(GeometryAnalysis analysis)
        {
            var grades = new DetailedCriteriaGrades();

            // Grade 1: Geometry Type (Solid vs Mesh)
            grades.GeometryTypeGrade = GradeGeometryType(analysis);
            
            // Grade 2: Face Count
            grades.FaceCountGrade = GradeFaceCount(analysis);
            
            // Grade 3: Nesting
            grades.NestingGrade = GradeNesting(analysis);
            
            // Grade 4: Import Source Quality
            grades.ImportSourceGrade = GradeImportSource(analysis);

            return grades;
        }

        private CriterionGrade GradeGeometryType(GeometryAnalysis analysis)
        {
            string grade;
            int score;
            string assessment;
            var issues = new List<string>();
            var recommendations = new List<string>();

            if (!analysis.HasMeshes && analysis.HasSolids)
            {
                grade = "A";
                score = 100;
                assessment = "Excellent - Native Revit solid geometry (optimal)";
                issues.Add("Uses native Revit solid geometry - best for performance");
            }
            else if (analysis.HasMeshes && analysis.HasSolids)
            {
                grade = "C";
                score = 70;
                assessment = "Mixed - Contains both solids and meshes";
                issues.Add($"Contains {analysis.MeshCount} mesh(es) and {analysis.SolidCount} solid(s)");
                recommendations.Add("Convert mesh geometry to native Revit solids where possible");
            }
            else if (analysis.HasMeshes && !analysis.HasSolids)
            {
                grade = "D";
                score = 60;
                assessment = "Poor - Only mesh geometry (imported/non-native)";
                issues.Add($"Contains only {analysis.MeshCount} mesh object(s) - no native solids");
                recommendations.Add("URGENT: Convert all mesh geometry to native Revit solid geometry");
                recommendations.Add("Avoid importing from SketchUp, Rhino, or other mesh-based tools");
            }
            else
            {
                grade = "F";
                score = 0;
                assessment = "No valid geometry found";
                issues.Add("No solids or meshes detected");
            }

            return new CriterionGrade
            {
                CriterionName = "Geometry Type",
                Grade = grade,
                Score = score,
                Assessment = assessment,
                AutodeskGuideline = "Autodesk recommends native Revit solid geometry over imported meshes",
                Issues = issues,
                Recommendations = recommendations
            };
        }

        private CriterionGrade GradeFaceCount(GeometryAnalysis analysis)
        {
            string grade;
            int score;
            string assessment;
            var issues = new List<string>();
            var recommendations = new List<string>();
            string guideline;

            if (analysis.TotalFaces > 100000)
            {
                grade = "F";
                score = 0;
                assessment = "CRITICAL - Extreme face count will cause severe performance issues";
                guideline = "Autodesk MAXIMUM: Keep families under 100,000 faces";
                issues.Add($"Face count ({analysis.TotalFaces:N0}) far exceeds Autodesk's maximum threshold");
                recommendations.Add("URGENT: Drastically simplify geometry or split into multiple families");
                recommendations.Add("Use detail levels to hide faces in distant views");
                recommendations.Add("Consider using symbolic 2D representations");
            }
            else if (analysis.TotalFaces > 50000)
            {
                grade = "D";
                score = 40;
                assessment = "Very Poor - High face count causes significant performance degradation";
                guideline = "Autodesk WARNING: 50,000+ faces cause significant performance issues";
                issues.Add($"Face count ({analysis.TotalFaces:N0}) exceeds 50,000 - major performance impact");
                recommendations.Add("Simplify curved surfaces and remove unnecessary detail");
                recommendations.Add("Use coarser resolution for non-critical views");
            }
            else if (analysis.TotalFaces > 20000)
            {
                grade = "C";
                score = 65;
                assessment = "Fair - Exceeds Autodesk's recommended threshold";
                guideline = "Autodesk RECOMMENDED MAX: Keep families under 20,000 faces";
                issues.Add($"Face count ({analysis.TotalFaces:N0}) exceeds Autodesk's 20,000 face recommendation");
                recommendations.Add("Consider simplifying geometry where possible");
                recommendations.Add("May impact performance when many instances are placed");
            }
            else if (analysis.TotalFaces > 5000)
            {
                grade = "B";
                score = 85;
                assessment = "Good - Acceptable face count, monitor performance";
                guideline = "Autodesk STANDARD: 5,000-20,000 faces is acceptable for most families";
                issues.Add($"Face count ({analysis.TotalFaces:N0}) is within acceptable range");
                recommendations.Add("Monitor performance if using many instances in large projects");
            }
            else if (analysis.TotalFaces > 1000)
            {
                grade = "A";
                score = 95;
                assessment = "Very Good - Low face count, good performance";
                guideline = "Autodesk BEST PRACTICE: Keep families under 5,000 faces for optimal performance";
                issues.Add($"Face count ({analysis.TotalFaces:N0}) is well-optimized");
            }
            else
            {
                grade = "A";
                score = 100;
                assessment = "Excellent - Very low face count, optimal performance";
                guideline = "Autodesk OPTIMAL: Simple families under 1,000 faces perform best";
                issues.Add($"Face count ({analysis.TotalFaces:N0}) is excellent - simple geometry");
            }

            return new CriterionGrade
            {
                CriterionName = "Face Count",
                Grade = grade,
                Score = score,
                Assessment = assessment,
                AutodeskGuideline = guideline,
                Issues = issues,
                Recommendations = recommendations
            };
        }

        private CriterionGrade GradeNesting(GeometryAnalysis analysis)
        {
            string grade;
            int score;
            string assessment;
            var issues = new List<string>();
            var recommendations = new List<string>();

            if (analysis.GeometryInstanceCount == 0)
            {
                grade = "A";
                score = 100;
                assessment = "Excellent - No nesting, direct geometry";
                issues.Add("No nested geometry instances - optimal");
            }
            else if (analysis.GeometryInstanceCount <= 3)
            {
                grade = "A";
                score = 95;
                assessment = "Excellent - Minimal nesting within Autodesk guidelines";
                issues.Add($"{analysis.GeometryInstanceCount} nested instance(s) - within recommended limit");
            }
            else if (analysis.GeometryInstanceCount <= 10)
            {
                grade = "B";
                score = 80;
                assessment = "Good - Moderate nesting, minor performance overhead";
                issues.Add($"{analysis.GeometryInstanceCount} nested instances - moderate overhead");
                recommendations.Add("Review nesting structure for optimization opportunities");
            }
            else
            {
                grade = "D";
                score = 50;
                assessment = "Poor - Excessive nesting impacts performance";
                issues.Add($"{analysis.GeometryInstanceCount} nested instances - excessive nesting");
                recommendations.Add("Autodesk recommends keeping nesting to 3 levels or less");
                recommendations.Add("Flatten nested families where possible to improve performance");
            }

            return new CriterionGrade
            {
                CriterionName = "Nesting Depth",
                Grade = grade,
                Score = score,
                Assessment = assessment,
                AutodeskGuideline = "Autodesk recommends maximum 2-3 levels of nested families",
                Issues = issues,
                Recommendations = recommendations
            };
        }

        private CriterionGrade GradeImportSource(GeometryAnalysis analysis)
        {
            string grade;
            int score;
            string assessment;
            var issues = new List<string>();
            var recommendations = new List<string>();
            
            int totalGeometry = analysis.NativeRevitSolids + analysis.ImportedSATSolids + analysis.ImportedMeshes;
            double nativePercentage = totalGeometry > 0 ? (double)analysis.NativeRevitSolids / totalGeometry * 100 : 0;
            double satPercentage = totalGeometry > 0 ? (double)analysis.ImportedSATSolids / totalGeometry * 100 : 0;
            double meshPercentage = totalGeometry > 0 ? (double)analysis.ImportedMeshes / totalGeometry * 100 : 0;
            
            // Build detected sources summary
            string detectedSourcesSummary = analysis.DetectedSources.Count > 0 
                ? string.Join(", ", analysis.DetectedSources) 
                : "Unknown";

            if (analysis.NativeRevitSolids > 0 && analysis.ImportedSATSolids == 0 && analysis.ImportedMeshes == 0)
            {
                // 100% Native Revit - Best case
                grade = "A";
                score = 100;
                assessment = "Excellent - 100% native Revit geometry (optimal)";
                issues.Add($"All geometry created with native Revit modeling tools");
                issues.Add($"Detected sources: {detectedSourcesSummary}");
            }
            else if (analysis.NativeRevitSolids > 0 && analysis.ImportedSATSolids > 0 && analysis.ImportedMeshes == 0)
            {
                // Mix of Native and SAT - Good but not optimal
                grade = "B";
                score = 80;
                assessment = $"Good - Mixed native Revit ({nativePercentage:F0}%) and SAT/ACIS imports ({satPercentage:F0}%)";
                issues.Add($"Contains {analysis.ImportedSATSolids} SAT/ACIS imported solid(s) and {analysis.NativeRevitSolids} native solid(s)");
                issues.Add($"Detected sources: {detectedSourcesSummary}");
                recommendations.Add("Consider recreating SAT geometry using native Revit families for better parametric control");
                recommendations.Add("SAT imports from AutoCAD/Inventor/SolidWorks cannot be edited parametrically");
            }
            else if (analysis.ImportedSATSolids > 0 && analysis.NativeRevitSolids == 0 && analysis.ImportedMeshes == 0)
            {
                // 100% SAT import - Fair
                grade = "C";
                score = 70;
                assessment = "Fair - 100% SAT/ACIS imported geometry (limited editability)";
                issues.Add($"All geometry imported from SAT/ACIS files (AutoCAD 3D, Inventor, SolidWorks, STEP)");
                issues.Add($"Detected sources: {detectedSourcesSummary}");
                issues.Add("Imported SAT geometry cannot be edited parametrically in Revit");
                recommendations.Add("RECOMMENDED: Recreate geometry using native Revit families");
                recommendations.Add("SAT files add file size and cannot adapt to parameter changes");
            }
            else if (analysis.ImportedMeshes > 0 && analysis.NativeRevitSolids > 0)
            {
                // Mix with meshes - Poor
                grade = "D";
                score = 60;
                assessment = $"Poor - Contains mesh imports ({meshPercentage:F0}%) from STL/OBJ/SketchUp";
                issues.Add($"Contains {analysis.ImportedMeshes} mesh object(s) - typically from STL, OBJ, or SketchUp");
                issues.Add($"Native Revit: {nativePercentage:F0}%, Meshes: {meshPercentage:F0}%, SAT: {satPercentage:F0}%");
                issues.Add($"Detected sources: {detectedSourcesSummary}");
                recommendations.Add("URGENT: Replace mesh geometry with native Revit solids or SAT imports");
                recommendations.Add("Meshes cause poor performance and cannot be edited");
                recommendations.Add("Avoid importing from SketchUp, Rhino (as mesh), or 3D scans");
            }
            else if (analysis.ImportedMeshes > 0 && analysis.NativeRevitSolids == 0)
            {
                // 100% Mesh - Critical
                grade = "F";
                score = 40;
                assessment = "Critical - 100% mesh geometry (STL/OBJ/SketchUp import)";
                issues.Add($"All geometry is mesh-based - likely imported from STL, OBJ, SketchUp, or 3D scans");
                issues.Add($"Detected sources: {detectedSourcesSummary}");
                issues.Add("Mesh geometry causes severe performance issues in Revit");
                issues.Add("Cannot be edited, dimensioned, or used for fabrication");
                recommendations.Add("CRITICAL: Rebuild family using native Revit modeling tools");
                recommendations.Add("If organic shapes are needed, use SAT/ACIS from SolidWorks/Rhino instead of meshes");
                recommendations.Add("Consider using Revit's adaptive components for complex forms");
            }
            else
            {
                // Unknown or no geometry
                grade = "C";
                score = 70;
                assessment = "Unknown import source - unable to determine origin";
                issues.Add($"Geometry source could not be definitively determined");
                issues.Add($"Detected sources: {detectedSourcesSummary}");
                recommendations.Add("Review family creation method for optimization opportunities");
            }
            
            string guideline = "Autodesk recommends native Revit modeling over imported geometry. " +
                             "Import priority: Native Revit (best) > SAT/ACIS solids (good) > Meshes (avoid). " +
                             "SAT sources: AutoCAD 3D, Inventor, SolidWorks, STEP files. " +
                             "Mesh sources: STL, OBJ, SketchUp, Rhino (as mesh), 3D scans.";

            return new CriterionGrade
            {
                CriterionName = "Import Source Quality",
                Grade = grade,
                Score = score,
                Assessment = assessment,
                AutodeskGuideline = guideline,
                Issues = issues,
                Recommendations = recommendations
            };
        }

        private OverallGrade CalculateOverallGrade(DetailedCriteriaGrades criteriaGrades)
        {
            // Weight the criteria (Autodesk priorities)
            // Face Count: 30% (critical for performance)
            // Geometry Type: 30% (solids vs meshes)
            // Import Source: 25% (native vs imported)
            // Nesting: 15% (important but less critical)
            
            double weightedScore = 
                (criteriaGrades.FaceCountGrade.Score * 0.30) +
                (criteriaGrades.GeometryTypeGrade.Score * 0.30) +
                (criteriaGrades.ImportSourceGrade.Score * 0.25) +
                (criteriaGrades.NestingGrade.Score * 0.15);

            int finalScore = (int)Math.Round(weightedScore);

            string grade;
            string analysis;
            
            if (finalScore >= 90)
            {
                grade = "A";
                analysis = "Excellent - Well-optimized family following Autodesk best practices";
            }
            else if (finalScore >= 80)
            {
                grade = "B";
                analysis = "Good - Minor optimization opportunities exist";
            }
            else if (finalScore >= 70)
            {
                grade = "C";
                analysis = "Fair - Some performance concerns, optimization recommended";
            }
            else if (finalScore >= 60)
            {
                grade = "D";
                analysis = "Poor - Geometry will impact performance, optimization needed";
            }
            else
            {
                grade = "F";
                analysis = "Critical - Significant performance issues, immediate action required";
            }

            // Collect all recommendations
            var allRecommendations = new List<string>();
            allRecommendations.AddRange(criteriaGrades.GeometryTypeGrade.Recommendations);
            allRecommendations.AddRange(criteriaGrades.FaceCountGrade.Recommendations);
            allRecommendations.AddRange(criteriaGrades.ImportSourceGrade.Recommendations);
            allRecommendations.AddRange(criteriaGrades.NestingGrade.Recommendations);

            return new OverallGrade
            {
                Grade = grade,
                Score = finalScore,
                Analysis = analysis,
                Recommendations = allRecommendations.Distinct().ToList()
            };
        }

        public string GetName()
        {
            return "CheckGeometryTypeDetailedEventHandler";
        }

        /// <summary>
        /// Public method to execute grading without external event (for internal batch processing)
        /// </summary>
        public Newtonsoft.Json.Linq.JObject ExecuteInternal(Document doc, Newtonsoft.Json.Linq.JObject parameters)
        {
            try
            {
                string elementId = parameters["elementId"]?.ToString();
                
                if (!long.TryParse(elementId, out long elementIdLong))
                {
                    return new Newtonsoft.Json.Linq.JObject
                    {
                        ["success"] = false,
                        ["error"] = $"Invalid element ID: {elementId}"
                    };
                }

                ElementId elId = new ElementId(elementIdLong);
                Element element = doc.GetElement(elId);

                if (element == null)
                {
                    return new Newtonsoft.Json.Linq.JObject
                    {
                        ["success"] = false,
                        ["error"] = $"Element not found: {elementId}"
                    };
                }

                // Get geometry options
                var options = new Options
                {
                    ComputeReferences = true,
                    DetailLevel = ViewDetailLevel.Fine,
                    IncludeNonVisibleObjects = false
                };

                var geometryElement = element.get_Geometry(options);

                if (geometryElement == null)
                {
                    return new Newtonsoft.Json.Linq.JObject
                    {
                        ["success"] = false,
                        ["error"] = $"No geometry found for element: {elementId}"
                    };
                }

                // Analyze geometry
                var analysis = AnalyzeGeometry(geometryElement);

                // Calculate detailed grades
                var criteriaGrades = CalculateDetailedGrades(analysis);

                // Calculate overall grade
                var overallGrade = CalculateOverallGrade(criteriaGrades);

                // Get family information
                string familyName = "Unknown";
                string familyTypeName = "Unknown";
                string familyHash = null;

                if (element is FamilyInstance fi && fi.Symbol != null)
                {
                    familyName = fi.Symbol.FamilyName;
                    familyTypeName = fi.Symbol.Name;
                    
                    // Calculate family hash
                    familyHash = GenerateFamilyHash(familyName, familyTypeName, analysis);
                }

                // Build result - include DetectedSources in import source grade
                var importSourceGrade = CriterionGradeToJObject(criteriaGrades.ImportSourceGrade);
                if (analysis.DetectedSources != null && analysis.DetectedSources.Any())
                {
                    importSourceGrade["DetectedSources"] = new Newtonsoft.Json.Linq.JArray(analysis.DetectedSources);
                }

                var result = new Newtonsoft.Json.Linq.JObject
                {
                    ["success"] = true,
                    ["elementId"] = elementId,
                    ["elementUniqueId"] = element.UniqueId,
                    ["elementName"] = element.Name,
                    ["elementCategory"] = element.Category?.Name ?? "Unknown",
                    ["familyName"] = familyName,
                    ["familyTypeName"] = familyTypeName,
                    ["familyHash"] = familyHash,
                    ["revitFileName"] = doc.Title,
                    ["gradeDateTime"] = DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss"),
                    
                    ["solidCount"] = analysis.SolidCount,
                    ["meshCount"] = analysis.MeshCount,
                    ["totalFaces"] = analysis.TotalFaces,
                    ["totalEdges"] = analysis.TotalEdges,
                    ["geometryInstanceCount"] = analysis.GeometryInstanceCount,
                    
                    ["criteriaGrades"] = new Newtonsoft.Json.Linq.JObject
                    {
                        ["geometryType"] = CriterionGradeToJObject(criteriaGrades.GeometryTypeGrade),
                        ["faceCount"] = CriterionGradeToJObject(criteriaGrades.FaceCountGrade),
                        ["importSource"] = importSourceGrade,
                        ["nesting"] = CriterionGradeToJObject(criteriaGrades.NestingGrade)
                    },
                    
                    ["overallGrade"] = overallGrade.Grade,
                    ["overallScore"] = overallGrade.Score,
                    ["overallAnalysis"] = overallGrade.Analysis,
                    ["recommendations"] = new Newtonsoft.Json.Linq.JArray(overallGrade.Recommendations)
                };

                return result;
            }
            catch (Exception ex)
            {
                return new Newtonsoft.Json.Linq.JObject
                {
                    ["success"] = false,
                    ["error"] = ex.Message,
                    ["stackTrace"] = ex.StackTrace
                };
            }
        }

        /// <summary>
        /// Converts CriterionGrade to JObject
        /// </summary>
        private Newtonsoft.Json.Linq.JObject CriterionGradeToJObject(CriterionGrade grade)
        {
            return new Newtonsoft.Json.Linq.JObject
            {
                ["CriterionName"] = grade.CriterionName,
                ["Grade"] = grade.Grade,
                ["Score"] = grade.Score,
                ["Assessment"] = grade.Assessment,
                ["AutodeskGuideline"] = grade.AutodeskGuideline,
                ["Issues"] = new Newtonsoft.Json.Linq.JArray(grade.Issues),
                ["Recommendations"] = new Newtonsoft.Json.Linq.JArray(grade.Recommendations)
            };
        }

        // Supporting classes
        private class GeometryAnalysis
        {
            public bool HasSolids { get; set; }
            public bool HasMeshes { get; set; }
            public int SolidCount { get; set; }
            public int MeshCount { get; set; }
            public int GeometryInstanceCount { get; set; }
            public int TotalFaces { get; set; }
            public int TotalEdges { get; set; }
            
            // Import source tracking
            public int NativeRevitSolids { get; set; }
            public int ImportedSATSolids { get; set; }
            public int ImportedMeshes { get; set; }
            public List<string> DetectedSources { get; set; } = new List<string>();
            public bool HasComplexBRep { get; set; } // Indicator of SAT/ACIS import
        }

        private string GenerateFamilyHash(string familyName, string typeName, GeometryAnalysis analysis)
        {
            // Create a unique hash based on family identity and geometry fingerprint
            // This hash will be the same for the same family across different documents
            string fingerprint = $"{familyName}|{typeName}|{analysis.TotalFaces}|{analysis.SolidCount}|{analysis.MeshCount}";
            
            using (MD5 md5 = MD5.Create())
            {
                byte[] inputBytes = Encoding.UTF8.GetBytes(fingerprint);
                byte[] hashBytes = md5.ComputeHash(inputBytes);
                
                // Convert to hex string (first 16 chars for readability)
                StringBuilder sb = new StringBuilder();
                for (int i = 0; i < Math.Min(8, hashBytes.Length); i++)
                {
                    sb.Append(hashBytes[i].ToString("x2"));
                }
                return sb.ToString();
            }
        }

        private class DetailedCriteriaGrades
        {
            public CriterionGrade GeometryTypeGrade { get; set; }
            public CriterionGrade FaceCountGrade { get; set; }
            public CriterionGrade NestingGrade { get; set; }
            public CriterionGrade ImportSourceGrade { get; set; }
        }

        private class CriterionGrade
        {
            public string CriterionName { get; set; }
            public string Grade { get; set; }
            public int Score { get; set; }
            public string Assessment { get; set; }
            public string AutodeskGuideline { get; set; }
            public List<string> Issues { get; set; }
            public List<string> Recommendations { get; set; }
        }

        private class OverallGrade
        {
            public string Grade { get; set; }
            public int Score { get; set; }
            public string Analysis { get; set; }
            public List<string> Recommendations { get; set; }
        }
    }
}
