# Adding Bulk Family Grading to Copilot Studio

## 🎉 New Feature: `grade_all_families_by_category`

This powerful tool performs batch geometry analysis on all families in your Revit project, providing performance grades and exporting detailed CSV reports.

### What It Does:

- **Analyzes all family instances** in the open Revit project by category
- **Grades performance** using Autodesk criteria (A, B, C, D, F)
- **Exports to CSV** with 17 detailed columns or 5 quick columns
- **Provides statistics**: grade distribution, average scores, recommendations
- **Identifies issues**: imported SAT/ACIS, meshes, high face counts, nested families

### Test Results (SnowdonTowers):
- ✅ Successfully graded **142 door instances**
- ✅ Average score: **96.4/100**
- ✅ Grade distribution: Mostly A/B grades, 10 D grades, 0 failures
- ✅ CSV generated: `RevitFamilyGrades_[ProjectName]_[Timestamp].csv`

---

## Step 1: Update Your HTTP Wrapper

### Option A: Using the Decoupled Approach (Recommended)

Since we discovered the HTTP wrapper has subprocess issues, use the Node server directly:

1. **Start the MCP Server** (in one terminal):
```powershell
cd C:\Users\ScottM\source\repos\MCP\revit-mcp
node build\index.js
```

2. **Expose with ngrok** (in another terminal):
```powershell
# Option 1: Expose the stdio server via HTTP wrapper
cd C:\Users\ScottM\source\repos\MCP\mcp-wrapper-http
python http_wrapper.py --port 5000 node C:\Users\ScottM\source\repos\MCP\revit-mcp\build\index.js

# Then in another terminal:
ngrok http 5000
```

### Option B: Use the REST API Directly

Test the command via REST:
```powershell
$body = @{
    category = "Doors"
    gradeType = "detailed"
    includeTypes = $true
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:5000/api/tools/grade_all_families_by_category" `
    -Method POST `
    -Body $body `
    -ContentType "application/json"
```

---

## Step 2: Add Action to Copilot Studio Custom Connector

### Navigate to Copilot Studio:
1. Go to https://copilotstudio.microsoft.com
2. Find your Revit MCP connector
3. Click **Edit** → **Actions**

### Add New Action:

**Action Name**: `GradeAllFamiliesByCategory`

**Display Name**: Grade All Families By Category

**Description**: 
```
Perform batch geometry analysis on all family instances in the Revit project by category. 
Analyzes performance using Autodesk criteria and exports detailed CSV report with grades, 
recommendations, and statistics. Use this to identify problematic families that need 
optimization (imported SAT/ACIS, meshes, high face counts).
```

**Operation ID**: `grade_all_families_by_category`

**Request**:
- **Method**: `POST`
- **URL**: `/api/tools/grade_all_families_by_category`
- **Content-Type**: `application/json`

**Request Body Schema**:
```json
{
  "type": "object",
  "properties": {
    "category": {
      "type": "string",
      "description": "Category to filter (e.g., 'Doors', 'Windows', 'Furniture', 'Plumbing Fixtures'). Use 'All' for all categories. Case-insensitive.",
      "default": "All"
    },
    "gradeType": {
      "type": "string",
      "enum": ["quick", "detailed"],
      "description": "Grading detail level. 'detailed' provides individual criterion grades (17 columns). 'quick' provides overall grade only (5 columns).",
      "default": "detailed"
    },
    "includeTypes": {
      "type": "boolean",
      "description": "Include all family type instances (true) or only unique families (false).",
      "default": true
    },
    "outputPath": {
      "type": "string",
      "description": "Optional custom output path (e.g., 'C:\\Projects\\grades.csv'). If not provided, saves to temp folder with auto-generated name.",
      "x-ms-summary": "Output Path (Optional)"
    }
  },
  "required": []
}
```

**Response Schema**:
```json
{
  "type": "object",
  "properties": {
    "success": {
      "type": "boolean",
      "description": "Whether the operation succeeded"
    },
    "data": {
      "type": "object",
      "properties": {
        "totalElements": {
          "type": "integer",
          "description": "Total number of family instances graded"
        },
        "csvFilePath": {
          "type": "string",
          "description": "Full path to the generated CSV file"
        },
        "avgScore": {
          "type": "number",
          "description": "Average score across all instances (0-100)"
        },
        "gradeDistribution": {
          "type": "object",
          "description": "Count of each grade (A, B, C, D, F, ERROR)",
          "properties": {
            "A": { "type": "integer" },
            "B": { "type": "integer" },
            "C": { "type": "integer" },
            "D": { "type": "integer" },
            "F": { "type": "integer" },
            "ERROR": { "type": "integer" }
          }
        },
        "categories": {
          "type": "array",
          "items": { "type": "string" },
          "description": "List of categories analyzed"
        },
        "timestamp": {
          "type": "string",
          "description": "When the analysis was performed"
        },
        "revitFileName": {
          "type": "string",
          "description": "Name of the Revit file analyzed"
        }
      }
    },
    "error": {
      "type": "string",
      "description": "Error message if operation failed"
    }
  }
}
```

---

## Step 3: Add to Your Copilot

### Create a Topic:

**Topic Name**: "Grade Families"

**Trigger Phrases**:
- "grade all families"
- "analyze family geometry"
- "check family performance"
- "grade doors"
- "grade windows"
- "family quality report"
- "export family grades"

### Add Question Node:

**Variable**: `CategoryFilter`

**Question**: "Which category would you like to grade? (e.g., Doors, Windows, Furniture, or 'All' for everything)"

**User Response Type**: Text

### Add Action Node:

**Action**: `GradeAllFamiliesByCategory`

**Inputs**:
- `category`: `{CategoryFilter}` (or use "All" as default)
- `gradeType`: "detailed"
- `includeTypes`: true

### Add Message Node (Success):

```
✅ Successfully graded {x.data.totalElements} family instances!

📊 Results Summary:
━━━━━━━━━━━━━━━━━━━━━━
📈 Average Score: {x.data.avgScore}/100

🏆 Grade Distribution:
  A (Excellent): {x.data.gradeDistribution.A}
  B (Good): {x.data.gradeDistribution.B}
  C (Fair): {x.data.gradeDistribution.C}
  D (Poor): {x.data.gradeDistribution.D}
  F (Failed): {x.data.gradeDistribution.F}
  ⚠️ Errors: {x.data.gradeDistribution.ERROR}

📁 CSV Report Saved:
{x.data.csvFilePath}

📂 Categories Analyzed: {x.data.categories}

💡 Next Steps:
1. Open the CSV in Excel
2. Filter by grade (F, D) to find problematic families
3. Review the Recommendations column
4. Check DetectedSources for imported SAT/ACIS files
5. Sort by OverallScore to prioritize improvements

Would you like me to grade another category?
```

### Add Message Node (Error):

```
❌ Failed to grade families: {x.error}

Please make sure:
- Revit is running with a project open
- The MCP switch is turned ON
- The category name is correct (e.g., "Doors", "Windows", "Furniture")

Try again or ask for help!
```

---

## Step 4: Example Conversations

### Example 1: Grade Specific Category

**User**: "Grade all doors"

**Copilot**: "I'll analyze all door families in your Revit project..."

*[Calls action with category="Doors"]*

**Copilot**: "✅ Successfully graded 142 family instances! Average Score: 96.4/100..."

---

### Example 2: Grade Everything

**User**: "Analyze all family geometry in the project"

**Copilot**: "Which category would you like to grade?"

**User**: "All"

**Copilot**: "I'll analyze ALL family instances in your Revit project. This may take a few minutes..."

*[Calls action with category="All"]*

**Copilot**: "✅ Successfully graded 1,247 family instances across 15 categories!..."

---

### Example 3: Quick Grading

**User**: "I need a quick family performance check"

**Copilot**: "Which category?"

**User**: "Windows"

*[Calls action with category="Windows", gradeType="quick"]*

**Copilot**: Shows simplified results with 5-column CSV

---

## Step 5: Advanced Features

### Add Follow-up Questions:

After showing results, ask:
- "Would you like to grade another category?"
- "Should I export a report for the failing families?"
- "Would you like recommendations for the D and F graded families?"

### Integration with Other Tools:

Combine with existing actions:
```
1. Grade all doors → Get list of F-graded families
2. Call get_selected_elements on those IDs
3. Call operate_element to highlight them in red
4. User can now see problematic families in Revit
```

### Scheduled Analysis:

Set up Power Automate flow:
```
Trigger: Daily at 9 AM
Action: Call grade_all_families_by_category with category="All"
Action: Email CSV report to team
```

---

## CSV File Schema

### Detailed Mode (17 columns):
1. **ElementId** - Revit element ID
2. **Category** - Element category
3. **FamilyName** - Family name
4. **TypeName** - Family type name
5. **OverallGrade** - Letter grade (A-F)
6. **OverallScore** - Numeric score (0-100)
7. **GeometryTypeGrade** - Grade for geometry type criterion
8. **FaceCountGrade** - Grade for face count criterion
9. **ImportSourceGrade** - Grade for import source criterion
10. **NestingGrade** - Grade for nesting level criterion
11. **TotalFaces** - Total face count
12. **SolidCount** - Number of solids
13. **MeshCount** - Number of meshes
14. **DetectedSources** - Import sources detected (Native, SAT, ACIS, Mesh, Mixed)
15. **NestingLevel** - Family nesting depth
16. **FamilyHash** - Unique identifier for tracking
17. **Recommendations** - Comma-separated improvement suggestions

### Quick Mode (5 columns):
1. **ElementId**
2. **FamilyName**
3. **TypeName**
4. **OverallGrade**
5. **OverallScore**

---

## Testing Checklist

- [ ] Revit 2024 running with SnowdonTowers open
- [ ] MCP switch turned ON (port 8080 listening)
- [ ] Node MCP server running (`node build\index.js`)
- [ ] HTTP wrapper or ngrok exposing server
- [ ] Custom connector created in Copilot Studio
- [ ] Action added with correct schema
- [ ] Topic created with trigger phrases
- [ ] Test with "grade all doors"
- [ ] Verify CSV file is created
- [ ] Check grade distribution makes sense
- [ ] Test error handling (MCP switch OFF, invalid category)

---

## Troubleshooting

### "Command not found" error
- Check that `grade_all_families_by_category` is in commandRegistry.json
- Verify DLL is deployed (259,584 bytes)
- Restart Revit after updating registry

### "Cannot read properties of undefined"
- The command returned null/undefined
- Check Revit logs: `C:\Users\ScottM\AppData\Roaming\Autodesk\Revit\Addins\2024\revit_mcp_plugin\Logs\`
- Verify MCP switch is ON

### Slow response
- Large projects may take 2-5 minutes for "All" categories
- Use specific categories for faster results
- Try "quick" mode instead of "detailed"

### CSV not found
- Check temp folder: `C:\Users\ScottM\AppData\Local\Temp\`
- Look for: `RevitFamilyGrades_*.csv`
- Verify write permissions

---

## Summary

You now have a powerful bulk family grading feature integrated into Copilot Studio! Users can:

✅ Ask to "grade all doors" in natural language
✅ Get instant performance analysis
✅ Receive detailed CSV reports
✅ Identify problematic families automatically
✅ Get recommendations for improvements

This turns Copilot into a Revit family quality assurance tool! 🚀
