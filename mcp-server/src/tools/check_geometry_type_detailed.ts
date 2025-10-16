import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";
import { withRevitConnection } from "../utils/ConnectionManager.js";

export function registerCheckGeometryTypeDetailedTool(server: McpServer) {
  server.tool(
    "check_geometry_type_detailed",
    "Check family geometry with detailed grading per Autodesk criterion. Returns individual grades for Geometry Type (Solid vs Mesh), Face Count, and Nesting Depth, plus an overall weighted grade.",
    {
      elementId: z.string().describe("The element ID to check"),
    },
    async ({ elementId }) => {
      return await withRevitConnection(async (revitClient) => {
        const params = {
          elementId: elementId.toString(),
        };

        return await revitClient.sendCommand("check_geometry_type_detailed", params);
      });
    }
  );
}
