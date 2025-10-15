using Autodesk.Revit.UI;
using Newtonsoft.Json.Linq;
using RevitMCPSDK.API.Base;
using RevitMCPCommandSet.Services;
using System;

namespace RevitMCPCommandSet.Commands
{
    /// <summary>
    /// Command to check family geometry with detailed grading per Autodesk criterion
    /// </summary>
    public class CheckGeometryTypeDetailedCommand : ExternalEventCommandBase
    {
        private CheckGeometryTypeDetailedEventHandler _handler => (CheckGeometryTypeDetailedEventHandler)Handler;

        /// <summary>
        /// Command name
        /// </summary>
        public override string CommandName => "check_geometry_type_detailed";

        /// <summary>
        /// Constructor
        /// </summary>
        /// <param name="uiApp">Revit UIApplication</param>
        public CheckGeometryTypeDetailedCommand(UIApplication uiApp)
            : base(new CheckGeometryTypeDetailedEventHandler(), uiApp)
        {
        }

        public override object Execute(JObject parameters, string requestId)
        {
            try
            {
                // Parse element ID parameter
                string elementIdStr = parameters["elementId"]?.ToString();
                if (string.IsNullOrEmpty(elementIdStr))
                {
                    throw new ArgumentNullException(nameof(elementIdStr), "Element ID is required");
                }

                // Set parameters
                _handler.SetElementId(elementIdStr);

                // Trigger external event and wait for completion
                if (RaiseAndWaitForCompletion(10000))
                {
                    return _handler.Result;
                }
                else
                {
                    throw new TimeoutException("Command execution timed out");
                }
            }
            catch (Exception ex)
            {
                return new
                {
                    error = true,
                    message = ex.Message
                };
            }
        }
    }
}
