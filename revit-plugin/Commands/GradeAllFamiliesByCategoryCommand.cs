using Autodesk.Revit.UI;
using Newtonsoft.Json.Linq;
using RevitMCPSDK.API.Base;
using RevitMCPCommandSet.Services;
using System;

namespace RevitMCPCommandSet.Commands
{
    /// <summary>
    /// Command to grade all family instances by category and export to CSV
    /// </summary>
    public class GradeAllFamiliesByCategoryCommand : ExternalEventCommandBase
    {
        private GradeAllFamiliesByCategoryEventHandler _handler => (GradeAllFamiliesByCategoryEventHandler)Handler;

        /// <summary>
        /// Command name
        /// </summary>
        public override string CommandName => "grade_all_families_by_category";

        /// <summary>
        /// Constructor
        /// </summary>
        /// <param name="uiApp">Revit UIApplication</param>
        public GradeAllFamiliesByCategoryCommand(UIApplication uiApp)
            : base(new GradeAllFamiliesByCategoryEventHandler(), uiApp)
        {
        }

        public override object Execute(JObject parameters, string requestId)
        {
            try
            {
                // Parse parameters with defaults
                string category = parameters["category"]?.ToString() ?? "All";
                string gradeType = parameters["gradeType"]?.ToString() ?? "detailed";
                bool includeTypes = parameters["includeTypes"]?.ToObject<bool>() ?? true;
                string outputPath = parameters["outputPath"]?.ToString() ?? "";

                // Set parameters on handler
                _handler.SetParameters(category, gradeType, includeTypes, outputPath);

                // Trigger external event and wait for completion (5 minutes timeout for bulk operations)
                if (RaiseAndWaitForCompletion(300000))
                {
                    return _handler.Result;
                }
                else
                {
                    throw new TimeoutException("Bulk grading operation timed out after 5 minutes");
                }
            }
            catch (Exception ex)
            {
                return new
                {
                    success = false,
                    error = ex.Message,
                    stackTrace = ex.StackTrace
                };
            }
        }
    }
}
