import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";
import { withRevitConnection } from "../utils/ConnectionManager.js";

export function registerCheckGeometryTypeTool(server: McpServer) {
  server.tool(
    "check_geometry_type",
    "Check if a family instance's geometry is mesh or solid. Returns detailed information about the geometry including solid count, mesh count, faces, edges, and geometry types.",
    {
      elementId: z
        .string()
        .describe("The ElementId of the family instance to check"),
    },
    async (args, extra) => {
      const params = {
        elementId: args.elementId,
      };

      try {
        const response = await withRevitConnection(async (revitClient) => {
          return await revitClient.sendCommand("check_geometry_type", params);
        });

        return {
          content: [
            {
              type: "text",
              text: JSON.stringify(response, null, 2),
            },
          ],
        };
      } catch (error) {
        return {
          content: [
            {
              type: "text",
              text: `Error checking geometry type: ${error instanceof Error ? error.message : String(error)}`,
            },
          ],
          isError: true,
        };
      }
    }
  );
}
