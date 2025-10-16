import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";
import { withRevitConnection } from "../utils/ConnectionManager.js";

export function registerGradeAllFamiliesByCategoryTool(server: McpServer) {
  server.tool(
    "grade_all_families_by_category",
    `Grade all family instances in the open Revit project by category and export results to CSV format.
  
This tool performs batch geometry analysis on all families in the project, providing performance grades based on Autodesk criteria. Ideal for:
- Project-wide geometry quality assessment
- Identifying problematic families across categories
- Bulk data export for analysis in Excel/Power BI
- Category-by-category performance comparison
- Finding families that need optimization (imported SAT, high face count, meshes)

The tool generates a CSV file with detailed grading results including:
- Individual criterion grades (Geometry Type, Face Count, Import Source, Nesting)
- Overall weighted grade (A-F)
- Performance metrics (face count, solid/mesh breakdown)
- Import source detection (Native Revit, SAT/ACIS, Mesh imports)
- Family hash for tracking across documents
- Recommendations for each family

CSV includes summary statistics:
- Grade distribution (count of A, B, C, D, F grades)
- Average scores by category
- Top issues and recommendations
- Import source breakdown`,
    {
      category: z
        .string()
        .optional()
        .describe('Category to filter (e.g., "Railings", "Furniture", "Plumbing Fixtures"). Use "All" or omit for all categories. Case-insensitive.'),
      gradeType: z
        .enum(["quick", "detailed"])
        .optional()
        .default("detailed")
        .describe('Grading detail level. "detailed" (default) provides individual criterion grades. "quick" provides overall grade only.'),
      includeTypes: z
        .boolean()
        .optional()
        .default(true)
        .describe("Include all family type instances (true) or only unique families (false). Default: true"),
      outputPath: z
        .string()
        .optional()
        .describe('Optional custom output path (e.g., "C:\\\\Projects\\\\grades.csv"). If not provided, saves to temp folder with auto-generated name.')
    },
    async (args, extra) => {
      const params = {
        category: args.category || "All",
        gradeType: args.gradeType || "detailed",
        includeTypes: args.includeTypes !== undefined ? args.includeTypes : true,
        outputPath: args.outputPath || ""
      };

      console.log(`📊 Grading all families (Category: ${params.category}, Type: ${params.gradeType})...`);

      try {
        const response = await withRevitConnection(async (revitClient) => {
          return await revitClient.sendCommand(
            "grade_all_families_by_category",
            params
          );
        });

        // Debug: log the actual response
        console.error("Response from Revit:", JSON.stringify(response, null, 2));

        if (response.success && response.data) {
          const data = response.data;
          
          return {
            content: [
              {
                type: "text",
                text: `✅ Successfully graded ${data.totalElements} family instances

📁 CSV File Saved: ${data.csvFilePath}

📊 Summary Statistics:
- Average Score: ${data.avgScore}/100
- Grade Distribution:
${formatGradeDistribution(data.gradeDistribution)}

📂 Categories Analyzed: ${data.categories.length}
${formatCategories(data.categories)}

${formatImportSourceBreakdown(data.summaryStats.importSourceBreakdown)}

🔝 Top Issues:
${formatTopIssues(data.summaryStats.topIssues)}

💡 Next Steps:
1. Open CSV in Excel: ${data.csvFilePath}
2. Filter by grade (F, D) to find problematic families
3. Sort by OverallScore to prioritize improvements
4. Review DetectedSources column to identify imports
5. Use Recommendations to guide optimization

📋 Revit File: ${data.revitFileName}
⏰ Analysis completed: ${data.timestamp}`
              }
            ]
          };
        } else {
          return {
            content: [
              {
                type: "text",
                text: `❌ Failed to grade families: ${response.error || "Unknown error"}`
              }
            ],
            isError: true
          };
        }
      } catch (error) {
        return {
          content: [
            {
              type: "text",
              text: `❌ Error: ${error instanceof Error ? error.message : String(error)}`
            }
          ],
          isError: true
        };
      }
    }
  );
}

// Helper functions for formatting output

function formatGradeDistribution(dist: any): string {
  const grades = ['A', 'B', 'C', 'D', 'F'];
  return grades.map(grade => `  ${grade}: ${dist[grade] || 0}`).join('\n');
}

function formatCategories(categories: any[]): string {
  if (!categories || categories.length === 0) {
    return "  No categories found";
  }
  
  return categories
    .sort((a, b) => b.avgScore - a.avgScore)
    .slice(0, 10)  // Top 10 categories
    .map(cat => `  • ${cat.name}: ${cat.count} families, avg ${cat.avgScore}/100`)
    .join('\n');
}

function formatImportSourceBreakdown(breakdown: any): string {
  if (!breakdown || Object.keys(breakdown).length === 0) {
    return "";
  }
  
  return `🔍 Import Source Breakdown:
  • Native Revit: ${breakdown.nativeRevit || 0} families
  • SAT/ACIS Imports: ${breakdown.satImports || 0} families (from AutoCAD/Inventor/SolidWorks/STEP)
  • Mesh Imports: ${breakdown.meshImports || 0} families (from STL/OBJ/SketchUp)
`;
}

function formatTopIssues(issues: any[]): string {
  if (!issues || issues.length === 0) {
    return "  No major issues found";
  }
  
  return issues
    .slice(0, 5)
    .map((issue, idx) => `  ${idx + 1}. ${issue.recommendation} (${issue.count} families)`)
    .join('\n');
}
