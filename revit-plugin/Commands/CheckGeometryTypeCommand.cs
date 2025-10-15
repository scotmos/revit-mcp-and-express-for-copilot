using Autodesk.Revit.UI;
using Newtonsoft.Json.Linq;
using RevitMCPSDK.API.Base;
using RevitMCPCommandSet.Services;
using System;

namespace RevitMCPCommandSet.Commands
{
    /// <summary>
    /// Command to check if a family instance's geometry is mesh or solid
    /// </summary>
    public class CheckGeometryTypeCommand : ExternalEventCommandBase
    {
        private CheckGeometryTypeEventHandler _handler => (CheckGeometryTypeEventHandler)Handler;

        /// <summary>
        /// Command name
        /// </summary>
        public override string CommandName => "check_geometry_type";

        /// <summary>
        /// Constructor
        /// </summary>
        /// <param name="uiApp">Revit UIApplication</param>
        public CheckGeometryTypeCommand(UIApplication uiApp)
            : base(new CheckGeometryTypeEventHandler(), uiApp)
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
                    throw new TimeoutException("Check geometry type operation timed out");
                }
            }
            catch (Exception ex)
            {
                throw new Exception($"Failed to check geometry type: {ex.Message}");
            }
        }
    }
}
