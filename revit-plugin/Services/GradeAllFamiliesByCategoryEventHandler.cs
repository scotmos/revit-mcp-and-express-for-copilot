using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading;
using Autodesk.Revit.DB;
using Autodesk.Revit.UI;
using Newtonsoft.Json.Linq;
using System.IO;
using RevitMCPSDK.API.Interfaces;

namespace RevitMCPCommandSet.Services
{
    /// <summary>
    /// Grades all family instances in the Revit project by category and exports results to CSV format.
    /// Supports filtering by category, batch processing, and both quick/detailed grading modes.
    /// </summary>
    public class GradeAllFamiliesByCategoryEventHandler : IExternalEventHandler, IWaitableExternalEventHandler
    {
        private JObject _parameters;
        private readonly object _lockObject = new object();
        private readonly ManualResetEvent _resetEvent = new ManualResetEvent(false);

        public object Result { get; private set; }
        public bool TaskCompleted { get; private set; }

        public string GetName() => "GradeAllFamiliesByCategoryEventHandler";

        public void SetParameters(string category, string gradeType, bool includeTypes, string outputPath)
        {
            _parameters = new JObject
            {
                ["category"] = category,
                ["gradeType"] = gradeType,
                ["includeTypes"] = includeTypes,
                ["outputPath"] = outputPath
            };
            TaskCompleted = false;
            _resetEvent.Reset();
        }

        public bool WaitForCompletion(int timeoutMilliseconds = 300000)
        {
            return _resetEvent.WaitOne(timeoutMilliseconds);
        }

        public void Execute(UIApplication app)
        {
            try
            {
                var doc = app.ActiveUIDocument.Document;
                
                // Parse parameters
                string categoryFilter = _parameters["category"]?.ToString() ?? "All";
                string gradeType = _parameters["gradeType"]?.ToString() ?? "detailed";
                bool includeTypes = _parameters["includeTypes"]?.ToObject<bool>() ?? true;
                string outputPath = _parameters["outputPath"]?.ToString();

                // Collect all family instances
                var familyInstances = CollectFamilyInstances(doc, categoryFilter);

                if (familyInstances.Count == 0)
                {
                    var noInstancesResult = new JObject
                    {
                        ["success"] = false,
                        ["error"] = $"No family instances found for category: {categoryFilter}",
                        ["totalElements"] = 0
                    };
                    Result = noInstancesResult;
                    TaskCompleted = true;
                    _resetEvent.Set();
                    return;
                }

                // Grade each family instance
                var gradedResults = GradeFamilyInstances(doc, familyInstances, gradeType);

                // Generate CSV
                string csvContent = GenerateCSV(gradedResults, gradeType);

                // Save to file if path provided
                string savedPath = null;
                if (!string.IsNullOrEmpty(outputPath))
                {
                    try
                    {
                        File.WriteAllText(outputPath, csvContent);
                        savedPath = outputPath;
                    }
                    catch (Exception ex)
                    {
                        // Fall back to temp file
                        savedPath = SaveToTempFile(csvContent, doc.Title);
                    }
                }
                else
                {
                    // Auto-generate temp file
                    savedPath = SaveToTempFile(csvContent, doc.Title);
                }

                // Calculate summary statistics
                var stats = CalculateStatistics(gradedResults);

                var result = new JObject
                {
                    ["success"] = true,
                    ["totalElements"] = gradedResults.Count,
                    ["categories"] = new JArray(stats["categories"]),
                    ["gradeDistribution"] = stats["gradeDistribution"],
                    ["avgScore"] = stats["avgScore"],
                    ["csvFilePath"] = savedPath,
                    ["csvContent"] = csvContent,
                    ["revitFileName"] = doc.Title,
                    ["timestamp"] = DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss"),
                    ["summaryStats"] = stats
                };

                Result = result;
                TaskCompleted = true;
                _resetEvent.Set();
            }
            catch (Exception ex)
            {
                var errorResult = new JObject
                {
                    ["success"] = false,
                    ["error"] = ex.Message,
                    ["stackTrace"] = ex.StackTrace
                };

                Result = errorResult;
                TaskCompleted = true;
                _resetEvent.Set();
            }
        }

        /// <summary>
        /// Collects all family instances from the document, optionally filtered by category
        /// </summary>
        private List<FamilyInstance> CollectFamilyInstances(Document doc, string categoryFilter)
        {
            var collector = new FilteredElementCollector(doc)
                .OfClass(typeof(FamilyInstance))
                .WhereElementIsNotElementType()
                .Cast<FamilyInstance>();

            if (categoryFilter != "All" && !string.IsNullOrEmpty(categoryFilter))
            {
                collector = collector.Where(fi => 
                    fi.Category != null && 
                    fi.Category.Name.Equals(categoryFilter, StringComparison.OrdinalIgnoreCase));
            }

            return collector.ToList();
        }

        /// <summary>
        /// Grades each family instance using the detailed grading logic
        /// </summary>
        private List<GradedFamilyResult> GradeFamilyInstances(Document doc, List<FamilyInstance> instances, string gradeType)
        {
            var results = new List<GradedFamilyResult>();
            var detailedHandler = new CheckGeometryTypeDetailedEventHandler();

            foreach (var instance in instances)
            {
                try
                {
                    // Create parameters for detailed grading
                    var gradeParams = new JObject
                    {
                        ["elementId"] = instance.Id.ToString()
                    };

                    // Call detailed grading handler
                    var gradeResult = detailedHandler.ExecuteInternal(doc, gradeParams);

                    if (gradeResult["success"]?.ToObject<bool>() == true)
                    {
                        var result = new GradedFamilyResult
                        {
                            ElementId = instance.Id.ToString(),
                            ElementUniqueId = gradeResult["elementUniqueId"]?.ToString(),
                            Category = instance.Category?.Name ?? "Unknown",
                            FamilyName = gradeResult["familyName"]?.ToString() ?? "Unknown",
                            TypeName = gradeResult["familyTypeName"]?.ToString() ?? "Unknown",
                            FamilyHash = gradeResult["familyHash"]?.ToString(),
                            
                            // Overall grades
                            OverallGrade = gradeResult["overallGrade"]?.ToString(),
                            OverallScore = gradeResult["overallScore"]?.ToObject<int>() ?? 0,
                            
                            // Geometry metrics
                            TotalFaces = gradeResult["totalFaces"]?.ToObject<int>() ?? 0,
                            SolidCount = gradeResult["solidCount"]?.ToObject<int>() ?? 0,
                            MeshCount = gradeResult["meshCount"]?.ToObject<int>() ?? 0,
                            
                            // Criterion grades
                            CriteriaGrades = gradeResult["criteriaGrades"] as JObject,
                            
                            // Recommendations
                            Recommendations = gradeResult["recommendations"]?.ToObject<List<string>>() ?? new List<string>()
                        };

                        // Extract individual criterion grades if detailed
                        if (result.CriteriaGrades != null)
                        {
                            result.GeometryTypeGrade = result.CriteriaGrades["geometryType"]?["Grade"]?.ToString();
                            result.FaceCountGrade = result.CriteriaGrades["faceCount"]?["Grade"]?.ToString();
                            result.ImportSourceGrade = result.CriteriaGrades["importSource"]?["Grade"]?.ToString();
                            result.NestingGrade = result.CriteriaGrades["nesting"]?["Grade"]?.ToString();
                            
                            // Extract detected sources
                            var detectedSourcesArray = result.CriteriaGrades["importSource"]?["DetectedSources"] as JArray;
                            if (detectedSourcesArray != null)
                            {
                                result.DetectedSources = string.Join("; ", detectedSourcesArray.Select(s => s.ToString()));
                            }
                        }

                        results.Add(result);
                    }
                }
                catch (Exception ex)
                {
                    // Log error but continue processing other elements
                    results.Add(new GradedFamilyResult
                    {
                        ElementId = instance.Id.ToString(),
                        Category = instance.Category?.Name ?? "Unknown",
                        FamilyName = instance.Symbol?.FamilyName ?? "Unknown",
                        TypeName = instance.Symbol?.Name ?? "Unknown",
                        OverallGrade = "ERROR",
                        OverallScore = 0,
                        Recommendations = new List<string> { $"Grading failed: {ex.Message}" }
                    });
                }
            }

            return results;
        }

        /// <summary>
        /// Generates CSV content from graded results
        /// </summary>
        private string GenerateCSV(List<GradedFamilyResult> results, string gradeType)
        {
            var csv = new StringBuilder();

            // Header row
            if (gradeType == "detailed")
            {
                csv.AppendLine("Category,FamilyName,TypeName,ElementId,UniqueId,GeometryTypeGrade,FaceCountGrade,ImportSourceGrade,NestingGrade,OverallGrade,OverallScore,TotalFaces,SolidCount,MeshCount,DetectedSources,FamilyHash,TopRecommendation");
            }
            else
            {
                csv.AppendLine("Category,FamilyName,TypeName,ElementId,UniqueId,OverallGrade,OverallScore,TotalFaces,SolidCount,MeshCount,FamilyHash,TopRecommendation");
            }

            // Data rows
            foreach (var result in results)
            {
                if (gradeType == "detailed")
                {
                    csv.AppendLine(string.Format("{0},{1},{2},{3},{4},{5},{6},{7},{8},{9},{10},{11},{12},{13},\"{14}\",{15},\"{16}\"",
                        EscapeCSV(result.Category),
                        EscapeCSV(result.FamilyName),
                        EscapeCSV(result.TypeName),
                        result.ElementId,
                        result.ElementUniqueId,
                        result.GeometryTypeGrade ?? "N/A",
                        result.FaceCountGrade ?? "N/A",
                        result.ImportSourceGrade ?? "N/A",
                        result.NestingGrade ?? "N/A",
                        result.OverallGrade,
                        result.OverallScore,
                        result.TotalFaces,
                        result.SolidCount,
                        result.MeshCount,
                        EscapeCSV(result.DetectedSources ?? "Unknown"),
                        result.FamilyHash ?? "N/A",
                        EscapeCSV(result.Recommendations.FirstOrDefault() ?? "No recommendations")
                    ));
                }
                else
                {
                    csv.AppendLine(string.Format("{0},{1},{2},{3},{4},{5},{6},{7},{8},{9},{10},\"{11}\"",
                        EscapeCSV(result.Category),
                        EscapeCSV(result.FamilyName),
                        EscapeCSV(result.TypeName),
                        result.ElementId,
                        result.ElementUniqueId,
                        result.OverallGrade,
                        result.OverallScore,
                        result.TotalFaces,
                        result.SolidCount,
                        result.MeshCount,
                        result.FamilyHash ?? "N/A",
                        EscapeCSV(result.Recommendations.FirstOrDefault() ?? "No recommendations")
                    ));
                }
            }

            return csv.ToString();
        }

        /// <summary>
        /// Escapes CSV special characters
        /// </summary>
        private string EscapeCSV(string value)
        {
            if (string.IsNullOrEmpty(value))
                return "";

            if (value.Contains(",") || value.Contains("\"") || value.Contains("\n"))
            {
                return value.Replace("\"", "\"\"");
            }

            return value;
        }

        /// <summary>
        /// Saves CSV content to temporary file
        /// </summary>
        private string SaveToTempFile(string csvContent, string projectName)
        {
            string tempPath = Path.GetTempPath();
            string timestamp = DateTime.Now.ToString("yyyyMMdd_HHmmss");
            string fileName = $"RevitFamilyGrades_{SanitizeFileName(projectName)}_{timestamp}.csv";
            string fullPath = Path.Combine(tempPath, fileName);

            File.WriteAllText(fullPath, csvContent);
            return fullPath;
        }

        /// <summary>
        /// Sanitizes filename by removing invalid characters
        /// </summary>
        private string SanitizeFileName(string fileName)
        {
            var invalid = Path.GetInvalidFileNameChars();
            return string.Join("_", fileName.Split(invalid, StringSplitOptions.RemoveEmptyEntries));
        }

        /// <summary>
        /// Calculates summary statistics from graded results
        /// </summary>
        private JObject CalculateStatistics(List<GradedFamilyResult> results)
        {
            var stats = new JObject();

            // Categories
            var categories = results.GroupBy(r => r.Category)
                .Select(g => new JObject
                {
                    ["name"] = g.Key,
                    ["count"] = g.Count(),
                    ["avgScore"] = Math.Round(g.Average(r => r.OverallScore), 1)
                })
                .ToList();
            stats["categories"] = new JArray(categories);

            // Grade distribution
            var gradeDistribution = new JObject();
            foreach (var grade in new[] { "A", "B", "C", "D", "F" })
            {
                gradeDistribution[grade] = results.Count(r => r.OverallGrade == grade);
            }
            gradeDistribution["ERROR"] = results.Count(r => r.OverallGrade == "ERROR");
            stats["gradeDistribution"] = gradeDistribution;

            // Average score
            stats["avgScore"] = Math.Round(results.Where(r => r.OverallGrade != "ERROR")
                .Average(r => (double)r.OverallScore), 1);

            // Top issues
            var allRecommendations = results.SelectMany(r => r.Recommendations)
                .GroupBy(rec => rec)
                .OrderByDescending(g => g.Count())
                .Take(5)
                .Select(g => new JObject
                {
                    ["recommendation"] = g.Key,
                    ["count"] = g.Count()
                })
                .ToList();
            stats["topIssues"] = new JArray(allRecommendations);

            // Import source breakdown (if available)
            var importSourceStats = new JObject();
            var resultsWithImportData = results.Where(r => !string.IsNullOrEmpty(r.DetectedSources)).ToList();
            if (resultsWithImportData.Any())
            {
                importSourceStats["nativeRevit"] = resultsWithImportData.Count(r => r.DetectedSources.Contains("Native Revit"));
                importSourceStats["satImports"] = resultsWithImportData.Count(r => r.DetectedSources.Contains("SAT/ACIS"));
                importSourceStats["meshImports"] = resultsWithImportData.Count(r => r.DetectedSources.Contains("Mesh Import"));
            }
            stats["importSourceBreakdown"] = importSourceStats;

            return stats;
        }
    }

    /// <summary>
    /// Data class to hold graded family results
    /// </summary>
    internal class GradedFamilyResult
    {
        public string ElementId { get; set; }
        public string ElementUniqueId { get; set; }
        public string Category { get; set; }
        public string FamilyName { get; set; }
        public string TypeName { get; set; }
        public string FamilyHash { get; set; }
        
        public string OverallGrade { get; set; }
        public int OverallScore { get; set; }
        
        public int TotalFaces { get; set; }
        public int SolidCount { get; set; }
        public int MeshCount { get; set; }
        
        // Individual criterion grades
        public string GeometryTypeGrade { get; set; }
        public string FaceCountGrade { get; set; }
        public string ImportSourceGrade { get; set; }
        public string NestingGrade { get; set; }
        
        public string DetectedSources { get; set; }
        
        public JObject CriteriaGrades { get; set; }
        public List<string> Recommendations { get; set; }
    }
}
