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
    /// Event handler to check if family geometry is mesh or solid
    /// </summary>
    public class CheckGeometryTypeEventHandler : IExternalEventHandler, IWaitableExternalEventHandler
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

                // Get geometry options
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
                        elementCategory = element.Category?.Name ?? "Unknown",
                        hasGeometry = false,
                        message = "No geometry found for this element"
                    };
                }
                else
                {
                    // Analyze geometry
                    var analysis = AnalyzeGeometry(geometryElement);
                    
                    // Calculate performance report card
                    var reportCard = CalculatePerformanceGrade(analysis);

                    // Get Revit file information
                    string revitFileName = doc.Title;
                    string gradeDateTime = DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss");
                    
                    // Generate unique family hash (for tracking across documents)
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
                        hasGeometry = true,
                        hasSolids = analysis.HasSolids,
                        hasMeshes = analysis.HasMeshes,
                        solidCount = analysis.SolidCount,
                        meshCount = analysis.MeshCount,
                        geometryInstanceCount = analysis.GeometryInstanceCount,
                        totalFaces = analysis.TotalFaces,
                        totalEdges = analysis.TotalEdges,
                        geometryTypes = analysis.GeometryTypes,
                        details = analysis.Details,
                        performanceGrade = reportCard.Grade,
                        performanceScore = reportCard.Score,
                        performanceAnalysis = reportCard.Analysis,
                        recommendations = reportCard.Recommendations
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
                        details.Add($"Solid: {solid.Faces.Size} faces, {solid.Edges.Size} edges, Volume: {solid.Volume:F2} cubic feet");
                    }
                }
                else if (geomObj is Mesh mesh)
                {
                    analysis.MeshCount++;
                    analysis.TotalFaces += mesh.NumTriangles;
                    details.Add($"Mesh: {mesh.NumTriangles} triangles, {mesh.Vertices.Count} vertices");
                }
                else if (geomObj is GeometryInstance geometryInstance)
                {
                    analysis.GeometryInstanceCount++;
                    // Recursively analyze geometry instances
                    var instanceGeometry = geometryInstance.GetInstanceGeometry();
                    if (instanceGeometry != null)
                    {
                        var instanceAnalysis = AnalyzeGeometry(instanceGeometry);
                        analysis.SolidCount += instanceAnalysis.SolidCount;
                        analysis.MeshCount += instanceAnalysis.MeshCount;
                        analysis.TotalFaces += instanceAnalysis.TotalFaces;
                        analysis.TotalEdges += instanceAnalysis.TotalEdges;
                        details.AddRange(instanceAnalysis.Details.Select(d => $"  Instance: {d}"));
                    }
                }
                else
                {
                    string typeName = geomObj.GetType().Name;
                    if (!analysis.GeometryTypes.Contains(typeName))
                    {
                        analysis.GeometryTypes.Add(typeName);
                    }
                    details.Add($"Other geometry type: {typeName}");
                }
            }

            analysis.HasSolids = analysis.SolidCount > 0;
            analysis.HasMeshes = analysis.MeshCount > 0;
            analysis.Details = details;

            return analysis;
        }

        private PerformanceReportCard CalculatePerformanceGrade(GeometryAnalysis analysis)
        {
            int score = 100; // Start with perfect score
            var issues = new List<string>();
            var recommendations = new List<string>();

            // Autodesk Criteria: Face Count (Primary Performance Factor)
            // Based on Autodesk's guidelines for family performance
            if (analysis.TotalFaces > 100000)
            {
                score -= 50;
                issues.Add($"CRITICAL: Face count ({analysis.TotalFaces:N0}) exceeds 100,000 - Severe performance impact");
                recommendations.Add("URGENT: Simplify geometry drastically or use detail levels to reduce visible faces");
                recommendations.Add("Consider using symbolic lines or 2D representations in plan/elevation views");
            }
            else if (analysis.TotalFaces > 50000)
            {
                score -= 35;
                issues.Add($"Very high face count ({analysis.TotalFaces:N0}) exceeds 50,000 - Significant performance issues");
                recommendations.Add("Reduce face count by simplifying curved surfaces and removing unnecessary detail");
                recommendations.Add("Use coarser detail level for non-close-up views");
            }
            else if (analysis.TotalFaces > 20000)
            {
                score -= 25;
                issues.Add($"High face count ({analysis.TotalFaces:N0}) exceeds 20,000 - Moderate performance impact");
                recommendations.Add("Consider simplifying geometry where possible");
                recommendations.Add("Autodesk recommends keeping families under 20,000 faces");
            }
            else if (analysis.TotalFaces > 5000)
            {
                score -= 15;
                issues.Add($"Elevated face count ({analysis.TotalFaces:N0}) - May impact performance in large projects");
                recommendations.Add("Monitor performance if using many instances of this family");
            }
            else if (analysis.TotalFaces > 1000)
            {
                score -= 5;
                issues.Add($"Face count ({analysis.TotalFaces:N0}) is acceptable but consider optimization");
            }

            // Autodesk Criteria: Mesh vs Solid (Meshes are slower to regenerate)
            if (analysis.HasMeshes)
            {
                score -= 20 * analysis.MeshCount;
                issues.Add($"Contains {analysis.MeshCount} mesh object(s) - Imported/mesh geometry is slower than native Revit solids");
                recommendations.Add("Convert imported meshes to native Revit solid geometry when possible");
                recommendations.Add("Avoid importing complex geometry from SketchUp, Rhino, or other mesh-based tools");
            }

            // Autodesk Criteria: Nested Families (Each level adds overhead)
            if (analysis.GeometryInstanceCount > 10)
            {
                score -= 15;
                issues.Add($"Excessive nested instances ({analysis.GeometryInstanceCount}) - Deep nesting impacts performance");
                recommendations.Add("Autodesk recommends keeping nesting to 3 levels or less");
                recommendations.Add("Flatten nested families where possible");
            }
            else if (analysis.GeometryInstanceCount > 3)
            {
                score -= 8;
                issues.Add($"Multiple nested instances ({analysis.GeometryInstanceCount}) - Moderate nesting overhead");
                recommendations.Add("Review nesting structure for optimization opportunities");
            }

            // Bonus: Optimized Geometry (Autodesk Best Practice)
            if (analysis.HasSolids && !analysis.HasMeshes && analysis.TotalFaces < 1000)
            {
                score += 10;
                issues.Add("Well-optimized: Native Revit solid geometry with low face count");
            }

            // Ensure score is within 0-100 range
            score = Math.Max(0, Math.Min(100, score));

            // Determine letter grade
            string grade;
            if (score >= 90) grade = "A";
            else if (score >= 80) grade = "B";
            else if (score >= 70) grade = "C";
            else if (score >= 60) grade = "D";
            else grade = "F";

            string analysis_summary;
            if (score >= 90)
                analysis_summary = "Excellent - This geometry is well-optimized and easy for Revit to process";
            else if (score >= 80)
                analysis_summary = "Good - Minor optimization opportunities exist";
            else if (score >= 70)
                analysis_summary = "Fair - Some performance concerns, consider optimization";
            else if (score >= 60)
                analysis_summary = "Poor - Geometry will impact performance, optimization recommended";
            else
                analysis_summary = "Critical - This geometry is very complex and will significantly impact Revit performance";

            return new PerformanceReportCard
            {
                Grade = grade,
                Score = score,
                Analysis = analysis_summary,
                Issues = issues,
                Recommendations = recommendations
            };
        }

        public string GetName()
        {
            return "CheckGeometryTypeEventHandler";
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

        private class PerformanceReportCard
        {
            public string Grade { get; set; }
            public int Score { get; set; }
            public string Analysis { get; set; }
            public List<string> Issues { get; set; }
            public List<string> Recommendations { get; set; }
        }

        private class GeometryAnalysis
        {
            public bool HasSolids { get; set; }
            public bool HasMeshes { get; set; }
            public int SolidCount { get; set; }
            public int MeshCount { get; set; }
            public int GeometryInstanceCount { get; set; }
            public int TotalFaces { get; set; }
            public int TotalEdges { get; set; }
            public List<string> GeometryTypes { get; set; } = new List<string>();
            public List<string> Details { get; set; } = new List<string>();
        }
    }
}
