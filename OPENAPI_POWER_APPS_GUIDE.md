# OpenAPI Specification for Revit MCP - Power Apps Custom Connector Guide

## Overview

The `revit-mcp-openapi.json` file is a complete OpenAPI 3.0.1 specification for the Revit MCP Express Server. Use this to automatically create a Custom Connector in Power Apps/Power Automate with all actions pre-configured.

## Quick Start

### 1. Import into Power Apps

1. **Open Power Apps** (https://make.powerapps.com)

2. **Go to Custom Connectors**
   - In the left menu: `Data` → `Custom Connectors`
   - Or direct: `Dataverse` → `Custom Connectors`

3. **Create New Custom Connector**
   - Click `+ New custom connector` → `Import an OpenAPI file`
   - Name: `Revit MCP API`
   - Upload: `revit-mcp-openapi.json`
   - Click `Import`

4. **Update Server URL**
   - On the `General` tab
   - Update Host: `your-ngrok-url.ngrok-free.app` (without https://)
   - Or use your permanent domain

5. **Configure Security** (Optional)
   - On the `Security` tab
   - For development: `No authentication`
   - For production: Choose `API Key` or `OAuth 2.0`

6. **Review Actions**
   - On the `Definition` tab
   - You should see all actions:
     - Health Check
     - Grade Families
     - Grade Families (Legacy)
     - Get Server Information

7. **Test**
   - On the `Test` tab
   - Create a connection
   - Test `healthCheck` operation
   - Test `gradeFamilies` with sample data

8. **Create**
   - Click `Create connector` (top right)
   - Connector is now available in Power Apps and Power Automate!

### 2. Use in Power Automate

1. **Create New Flow**
   - Go to Power Automate
   - Create new cloud flow

2. **Add Revit MCP Action**
   - Add new step
   - Search for "Revit MCP API"
   - Select action: `Grade Families`

3. **Configure Action**
   - category: `Doors` (or dynamic from previous step)
   - gradeType: `quick` or `detailed`
   - includeTypes: `true` or `false`

4. **Process Results**
   - Add condition: `success` equals `true`
   - Parse JSON to extract:
     - `totalElements`
     - `avgScore`
     - `csvFilePath`
     - `gradeDistribution`

5. **Take Actions**
   - Send email with results
   - Save to SharePoint
   - Update Excel
   - Create Teams message
   - Etc.

### 3. Use in Power Apps

1. **Add Data Source**
   - In your Power App
   - Add data → Connectors → `Revit MCP API`
   - Create connection

2. **Call Action from Button**
   ```power-fx
   Set(
       gradingResult,
       RevitMCPAPI.gradeFamilies({
           category: "Doors",
           gradeType: "quick",
           includeTypes: true
       })
   )
   ```

3. **Display Results**
   ```power-fx
   // Show total elements
   Label1.Text = gradingResult.totalElements

   // Show average score
   Label2.Text = gradingResult.avgScore

   // Show CSV path
   Label3.Text = gradingResult.csvFilePath

   // Check success
   If(gradingResult.success,
       Notify("Grading completed successfully!", NotificationType.Success),
       Notify("Error: " & gradingResult.error, NotificationType.Error)
   )
   ```

## OpenAPI File Details

### Endpoints Included

1. **GET /health**
   - Operation ID: `healthCheck`
   - Purpose: Verify server is running
   - Parameters: None
   - Returns: Server status and version

2. **POST /api/grade-families**
   - Operation ID: `gradeFamilies`
   - Purpose: Grade Revit families by category
   - Parameters: category, gradeType, includeTypes, outputPath
   - Returns: Complete grading results with CSV path

3. **POST /api/tools/grade_all_families_by_category**
   - Operation ID: `gradeFamiliesLegacy`
   - Purpose: Backward compatibility with Flask
   - Parameters: Same as grade-families
   - Returns: Same as grade-families

4. **GET /api/info**
   - Operation ID: `getServerInfo`
   - Purpose: Get API information and examples
   - Parameters: None
   - Returns: Server details and documentation

### Schema Definitions

#### GradingRequest
```json
{
  "category": "string (default: All)",
  "gradeType": "quick|detailed (default: detailed)",
  "includeTypes": "boolean (default: true)",
  "outputPath": "string (optional)"
}
```

#### GradingResult
```json
{
  "success": "boolean",
  "totalElements": "integer",
  "avgScore": "float",
  "csvFilePath": "string",
  "gradeDistribution": {
    "A": "integer",
    "B": "integer",
    "C": "integer",
    "D": "integer",
    "F": "integer",
    "ERROR": "integer"
  },
  "categories": "array",
  "timestamp": "string",
  "revitFileName": "string",
  "duration": "integer (ms)",
  "summaryStats": "object"
}
```

#### Error
```json
{
  "success": false,
  "error": "string (error message)",
  "duration": "integer (ms)"
}
```

## Customization

### Update Server URL

Before importing, edit `revit-mcp-openapi.json`:

```json
"servers": [
  {
    "url": "https://YOUR-NGROK-URL.ngrok-free.app",
    "description": "Your ngrok Tunnel"
  }
]
```

### Add Authentication

If you add API key authentication to your Express server, update the OpenAPI file:

```json
"components": {
  "securitySchemes": {
    "ApiKeyAuth": {
      "type": "apiKey",
      "in": "header",
      "name": "X-API-Key"
    }
  }
},
"security": [
  {
    "ApiKeyAuth": []
  }
]
```

Then in Power Apps Custom Connector:
- Security tab → Authentication type: `API Key`
- Parameter label: `X-API-Key`
- Parameter name: `X-API-Key`
- Parameter location: `Header`

### Add Rate Limiting Info

Add to the info section:

```json
"x-ratelimit": {
  "requests": 100,
  "period": "minute"
}
```

## Power Automate Flow Examples

### Example 1: Daily Grading Report

**Trigger**: Recurrence (daily at 8 AM)

**Actions**:
1. `Revit MCP API - Grade Families`
   - category: `All`
   - gradeType: `detailed`
   - includeTypes: `true`

2. `Condition` - Check if `success` equals `true`

3. **If Yes**:
   - `Send an email (V2)`
     - To: `project-team@company.com`
     - Subject: `Daily Revit Family Grading Report`
     - Body:
       ```
       Grading completed for @{body('Grade_Families')?['revitFileName']}
       
       Total Elements: @{body('Grade_Families')?['totalElements']}
       Average Score: @{body('Grade_Families')?['avgScore']}/100
       
       Grade Distribution:
       A: @{body('Grade_Families')?['gradeDistribution']?['A']}
       B: @{body('Grade_Families')?['gradeDistribution']?['B']}
       C: @{body('Grade_Families')?['gradeDistribution']?['C']}
       D: @{body('Grade_Families')?['gradeDistribution']?['D']}
       F: @{body('Grade_Families')?['gradeDistribution']?['F']}
       
       CSV Report: @{body('Grade_Families')?['csvFilePath']}
       ```

4. **If No**:
   - `Send an email (V2)`
     - Subject: `ERROR: Revit Grading Failed`
     - Body: `@{body('Grade_Families')?['error']}`

### Example 2: On-Demand Grading with Teams

**Trigger**: `When a new message is posted in Teams`

**Condition**: Message contains "grade" or "quality check"

**Actions**:
1. `Compose` - Extract category from message
   - Input: `@{triggerBody()?['body']?['plainText']}`

2. `Revit MCP API - Grade Families`
   - category: `@{outputs('Compose')}`
   - gradeType: `quick`
   - includeTypes: `true`

3. `Post message in a chat or channel`
   - Channel: Same as trigger
   - Message:
     ```
     ✅ Grading complete!
     📊 Elements: @{body('Grade_Families')?['totalElements']}
     ⭐ Avg Score: @{body('Grade_Families')?['avgScore']}/100
     📁 CSV: @{body('Grade_Families')?['csvFilePath']}
     ```

### Example 3: Quality Gate Check

**Trigger**: Manual trigger

**Actions**:
1. `Revit MCP API - Grade Families`
   - category: `All`
   - gradeType: `detailed`
   - includeTypes: `true`

2. `Condition` - `avgScore` is less than `80`

3. **If Yes** (Quality Gate Failed):
   - Create SharePoint item in "Quality Issues" list
   - Send notification to BIM Manager
   - Create Planner task for remediation

4. **If No** (Quality Gate Passed):
   - Update project status to "Ready for Review"
   - Send success notification

## Power Apps Canvas App Example

### Simple Grading App

1. **Screen Layout**:
   - Dropdown: Category selector (Doors, Windows, Walls, All)
   - Toggle: Grade Type (Quick/Detailed)
   - Button: "Run Grading"
   - Label: Status message
   - Gallery: Results display

2. **OnSelect for Button**:
```power-fx
Set(varLoading, true);
Set(
    varResult,
    RevitMCPAPI.gradeFamilies({
        category: Dropdown1.Selected.Value,
        gradeType: If(Toggle1.Value, "detailed", "quick"),
        includeTypes: true
    })
);
Set(varLoading, false);

If(
    varResult.success,
    Set(varMessage, "✅ Graded " & varResult.totalElements & " elements. Avg Score: " & varResult.avgScore),
    Set(varMessage, "❌ Error: " & varResult.error)
)
```

3. **Results Gallery**:
```power-fx
// Items property
Table(
    {Category: "Total Elements", Value: Text(varResult.totalElements)},
    {Category: "Average Score", Value: Text(varResult.avgScore) & "/100"},
    {Category: "Grade A", Value: Text(varResult.gradeDistribution.A)},
    {Category: "Grade B", Value: Text(varResult.gradeDistribution.B)},
    {Category: "Grade C", Value: Text(varResult.gradeDistribution.C)},
    {Category: "Grade D", Value: Text(varResult.gradeDistribution.D)},
    {Category: "Grade F", Value: Text(varResult.gradeDistribution.F)},
    {Category: "CSV Path", Value: varResult.csvFilePath}
)
```

## Troubleshooting

### Import Fails

**Error**: "Unable to parse OpenAPI file"
- **Solution**: Validate JSON at https://editor.swagger.io
- Check for syntax errors
- Ensure file is UTF-8 encoded

### Connection Test Fails

**Error**: "Unable to connect to server"
- **Solution**: 
  1. Verify ngrok is running: `ngrok http 3000`
  2. Update Host in connector to match ngrok URL
  3. Test health endpoint: `curl https://your-url.ngrok-free.app/health`
  4. Check Express server is running

### Actions Not Appearing

**Error**: No actions listed after import
- **Solution**:
  1. Check OpenAPI file has `paths` defined
  2. Each path must have `operationId`
  3. Re-import the file
  4. Refresh Custom Connectors page

### Authentication Errors

**Error**: "401 Unauthorized"
- **Solution**:
  1. If using API key, configure in Security tab
  2. Test with Postman first
  3. Verify credentials are correct
  4. Check CORS settings on Express server

### Response Parsing Errors

**Error**: "Unable to parse response"
- **Solution**:
  1. Check response matches schema in OpenAPI file
  2. Test endpoint with Postman
  3. Verify Content-Type is `application/json`
  4. Update schema if needed

## Advanced Usage

### Dynamic Category Selection

In Power Automate, create a dropdown from Revit categories:

1. Add `Initialize variable` - `categoriesList`
   - Type: Array
   - Value: `["All", "Doors", "Windows", "Walls", "Floors", "Roofs", "Columns", "Beams"]`

2. Use in flow:
   - Add input: Dropdown
   - Options: `@variables('categoriesList')`

### Batch Processing Multiple Projects

1. Get list of Revit files from SharePoint
2. For each file:
   - Open in Revit (external process)
   - Call Grade Families
   - Save results to Excel
   - Move to "Processed" folder

### Integration with Power BI

1. Grade families via Power Automate
2. Parse results and save to SQL/SharePoint
3. Connect Power BI to data source
4. Create dashboards:
   - Quality trends over time
   - Grade distribution by category
   - Top issues by family
   - Import source breakdown

## Version History

### v2.0.1 (2025-10-17)
- Initial OpenAPI specification
- Includes all Express server endpoints
- Full schema definitions
- Ready for Power Apps import

## Next Steps

1. Import OpenAPI file to Power Apps
2. Test all actions
3. Create your first Power Automate flow
4. Build Power Apps canvas app
5. Share with team

## Support

- **Documentation**: See `EXPRESS_SERVER_COMPLETE.md`
- **Repository**: https://github.com/scotmos/revit-mcp-and-express-for-copilot
- **Issues**: Create GitHub issue

---

**Ready to automate your Revit workflows with Power Platform! 🚀**
