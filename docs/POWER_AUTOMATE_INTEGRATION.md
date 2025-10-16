# Power Automate Integration for Bulk Family Grading

## Why Power Automate?

Copilot Studio has a **~30 second timeout** via Azure API Management. Detailed family grading takes **30-60 seconds** for 100+ elements, causing timeout errors.

**Power Automate Benefits**:
- ✅ **No timeout limits** (configure up to 5+ minutes)
- ✅ **Async processing** (trigger and check status later)
- ✅ **Scheduled runs** (daily/weekly quality reports)
- ✅ **Better error handling** (retry logic, exponential backoff)
- ✅ **Email/Teams notifications** (send results when complete)
- ✅ **SharePoint integration** (auto-upload CSV reports)

---

## Flow Design Options

### Option 1: Manual Trigger Flow (Interactive)

**Use Case**: On-demand grading initiated by user

**Flow Steps**:

1. **Trigger**: Manual button / Power Apps button
   
2. **Initialize Variables**:
   - `Category` (string): User input (Doors, Windows, Furniture, All)
   - `GradeType` (string): detailed or quick
   - `IncludeTypes` (boolean): true

3. **HTTP Action** - Call Revit MCP Connector:
   ```
   Method: POST
   URI: https://YOUR_NGROK_URL/api/tools/grade_all_families_by_category
   Headers:
     Content-Type: application/json
   Body:
   {
     "category": "@{variables('Category')}",
     "gradeType": "@{variables('GradeType')}",
     "includeTypes": @{variables('IncludeTypes')}
   }
   Timeout: PT5M (5 minutes)
   ```

4. **Parse JSON** - Parse the response:
   ```json
   {
     "type": "object",
     "properties": {
       "success": {"type": "boolean"},
       "totalElements": {"type": "integer"},
       "avgScore": {"type": "number"},
       "csvFilePath": {"type": "string"},
       "gradeDistribution": {
         "type": "object",
         "properties": {
           "A": {"type": "integer"},
           "B": {"type": "integer"},
           "C": {"type": "integer"},
           "D": {"type": "integer"},
           "F": {"type": "integer"},
           "ERROR": {"type": "integer"}
         }
       },
       "categories": {"type": "array"},
       "timestamp": {"type": "string"},
       "revitFileName": {"type": "string"}
     }
   }
   ```

5. **Condition** - Check if success:
   ```
   @{body('Parse_JSON')?['success']} is equal to true
   ```

6a. **If YES** - Send success email:
   ```
   To: [Your email]
   Subject: ✅ Revit Family Grading Complete - @{body('Parse_JSON')?['revitFileName']}
   
   Body:
   Successfully graded @{body('Parse_JSON')?['totalElements']} family instances!
   
   📊 Results Summary:
   ━━━━━━━━━━━━━━━━━━━━━━
   📈 Average Score: @{body('Parse_JSON')?['avgScore']}/100
   
   🏆 Grade Distribution:
     A (Excellent): @{body('Parse_JSON')?['gradeDistribution']?['A']}
     B (Good): @{body('Parse_JSON')?['gradeDistribution']?['B']}
     C (Fair): @{body('Parse_JSON')?['gradeDistribution']?['C']}
     D (Poor): @{body('Parse_JSON')?['gradeDistribution']?['D']}
     F (Failed): @{body('Parse_JSON')?['gradeDistribution']?['F']}
     ⚠️ Errors: @{body('Parse_JSON')?['gradeDistribution']?['ERROR']}
   
   📁 CSV Report:
   @{body('Parse_JSON')?['csvFilePath']}
   
   📂 Categories: @{body('Parse_JSON')?['categories']}
   ⏰ Timestamp: @{body('Parse_JSON')?['timestamp']}
   ```

6b. **If NO** - Send error email:
   ```
   Subject: ❌ Revit Family Grading Failed
   Body:
   Error occurred during family grading.
   
   Details: @{body('HTTP')}
   
   Please check:
   1. Revit is running with document open
   2. MCP switch is ON
   3. Category name is correct
   4. Server logs for details
   ```

---

### Option 2: Scheduled Flow (Automated Reports)

**Use Case**: Daily quality reports, weekly summaries

**Flow Steps**:

1. **Trigger**: Recurrence
   ```
   Frequency: Daily
   Time: 9:00 AM
   Time zone: (UTC-08:00) Pacific Time (US & Canada)
   ```

2. **Initialize Variables**:
   - `Category`: "All" (grade everything)
   - `GradeType`: "detailed"
   - `IncludeTypes`: true

3. **HTTP Action** - Same as Option 1 (with 5-minute timeout)

4. **Parse JSON** - Same schema

5. **Condition** - Check success

6a. **If YES** - Upload to SharePoint:
   
   **Create File** (SharePoint):
   ```
   Site: [Your SharePoint site]
   Folder: /Shared Documents/Revit Quality Reports
   File Name: RevitFamilyReport_@{formatDateTime(utcNow(), 'yyyyMMdd_HHmmss')}.csv
   File Content: [Read from csvFilePath using File System connector]
   ```
   
   **Send Teams Message**:
   ```
   Channel: Revit Quality
   Message:
   📊 **Daily Revit Family Quality Report**
   
   ✅ Graded @{body('Parse_JSON')?['totalElements']} instances
   📈 Average Score: @{body('Parse_JSON')?['avgScore']}/100
   
   Grade Summary:
   - A: @{body('Parse_JSON')?['gradeDistribution']?['A']}
   - D: @{body('Parse_JSON')?['gradeDistribution']?['D']}
   - F: @{body('Parse_JSON')?['gradeDistribution']?['F']}
   
   📁 [View Report](link to SharePoint file)
   ```

6b. **If NO** - Send error notification

---

### Option 3: Power Apps Integration (User-Friendly UI)

**Use Case**: Give team members easy access via mobile/desktop app

**Power Apps Design**:

1. **Input Screen**:
   - Dropdown: Select Category (Doors, Windows, Furniture, All)
   - Toggle: Detailed vs Quick
   - Toggle: Include Types
   - Button: "Start Grading"

2. **On Button Click**:
   ```powerapp
   Set(varGrading, true);
   Set(varResult, 
     [Your Power Automate flow name].Run(
       Dropdown1.Selected.Value,
       Toggle1.Value ? "detailed" : "quick",
       Toggle2.Value
     )
   );
   Set(varGrading, false);
   ```

3. **Results Screen**:
   - Display totalElements, avgScore
   - Chart: Grade distribution (pie chart or bar chart)
   - Button: "Open CSV" (launches file from path)
   - Button: "Grade Another"

---

## Implementation Steps

### Step 1: Create Custom Connector (if not done)

Follow `DEPLOYMENT_GUIDE.md` Copilot Studio Configuration section.

### Step 2: Create Power Automate Flow

1. Go to: https://make.powerautomate.com
2. Click **+ Create** → **Automated cloud flow**
3. Name: "Revit Family Grading - Manual"
4. Trigger: **Manually trigger a flow**
5. Add **Input**:
   - `Category` (Text, default: "All")
   - `GradeType` (Choice: detailed, quick)
   - `IncludeTypes` (Yes/No, default: Yes)

### Step 3: Add HTTP Action

1. Click **+ New step**
2. Search for your custom connector: "Revit MCP Tools"
3. Select action: `GradeAllFamiliesByCategory`
4. Set inputs:
   ```
   category: @{triggerBody()['text']}
   gradeType: @{triggerBody()['choice']}
   includeTypes: @{triggerBody()['boolean']}
   ```
5. **Advanced Settings** → Set timeout:
   ```
   Timeout: PT5M  (5 minutes)
   Retry Policy: Exponential Interval
   Retry Count: 2
   ```

### Step 4: Parse Response

1. Add **Parse JSON** action
2. Content: `@{body('GradeAllFamiliesByCategory')}`
3. Use schema from Option 1 above

### Step 5: Add Conditional Logic

Follow Option 1 or Option 2 flow design.

### Step 6: Test

1. Click **Test** → **Manually**
2. Enter inputs:
   - Category: "Furniture"
   - GradeType: "quick"
   - IncludeTypes: Yes
3. Click **Run flow**
4. Should complete in ~10 seconds for quick mode

**Test Detailed Mode**:
- Category: "Doors"
- GradeType: "detailed"
- Should complete in 30-60 seconds (no timeout!)

---

## Error Handling Best Practices

### Retry Logic

```json
{
  "retryPolicy": {
    "type": "exponential",
    "count": 3,
    "interval": "PT10S",
    "maximumInterval": "PT1M"
  }
}
```

### Timeout Handling

```
Configure HTTP action:
Timeout: PT5M (5 minutes)

Add Scope action around HTTP call
Add Parallel Branch:
  - Branch A: HTTP action
  - Branch B: Delay for 4m 30s → Terminate with timeout message
  
Whichever completes first wins
```

### Error Notifications

```powerautomate
Add "Configure run after" on error email action:
- Run after: HTTP action has failed OR timed out

Include in email:
- Error details: @{body('HTTP')}
- Flow run URL: @{workflow()?['run']?['id']}
- Timestamp: @{utcNow()}
```

---

## Monitoring and Logging

### Application Insights Integration

```powerautomate
After HTTP action, add:
HTTP POST to Application Insights:
{
  "name": "RevitFamilyGrading",
  "properties": {
    "category": "@{triggerBody()?['category']}",
    "gradeType": "@{triggerBody()?['gradeType']}",
    "totalElements": "@{body('Parse_JSON')?['totalElements']}",
    "avgScore": "@{body('Parse_JSON')?['avgScore']}",
    "duration": "@{actions('HTTP')?['duration']}"
  }
}
```

### Flow Analytics

Power Automate automatically tracks:
- Run count
- Success rate
- Average duration
- Failure reasons

View at: https://make.powerautomate.com → Analytics

---

## Example Flows (Copy-Paste Templates)

### Quick Start Template (JSON)

```json
{
  "definition": {
    "$schema": "https://schema.management.azure.com/schemas/2016-06-01/workflowdefinition.json#",
    "triggers": {
      "manual": {
        "type": "Request",
        "kind": "Button",
        "inputs": {
          "schema": {
            "type": "object",
            "properties": {
              "category": {
                "type": "string",
                "default": "All"
              },
              "gradeType": {
                "type": "string",
                "enum": ["quick", "detailed"],
                "default": "detailed"
              }
            }
          }
        }
      }
    },
    "actions": {
      "GradeAllFamilies": {
        "type": "OpenApiConnection",
        "inputs": {
          "host": {
            "connectionName": "shared_revitmcptools",
            "operationId": "GradeAllFamiliesByCategory"
          },
          "parameters": {
            "category": "@{triggerBody()['category']}",
            "gradeType": "@{triggerBody()['gradeType']}",
            "includeTypes": true
          }
        }
      },
      "Send_email": {
        "runAfter": {
          "GradeAllFamilies": ["Succeeded"]
        },
        "type": "ApiConnection",
        "inputs": {
          "host": {
            "connectionName": "shared_office365"
          },
          "method": "post",
          "path": "/v2/Mail",
          "body": {
            "To": "your.email@company.com",
            "Subject": "Revit Grading Complete",
            "Body": "Graded @{body('GradeAllFamilies')?['totalElements']} elements. Avg: @{body('GradeAllFamilies')?['avgScore']}"
          }
        }
      }
    }
  }
}
```

---

## FAQs

**Q: Can I use this with Copilot Studio directly?**

A: For quick mode (< 10 sec), yes! For detailed mode, use Power Automate to avoid timeouts.

**Q: How do I handle large projects (1000+ elements)?**

A: Grade by category instead of "All". Example: Run separate flows for Doors, Windows, Furniture.

**Q: Can I schedule grading for multiple projects?**

A: Yes, but you'll need to:
1. Open different Revit project in each run
2. Use Revit API to open/close projects programmatically
3. Or run separate flows with manual Revit project switching

**Q: What if ngrok URL changes?**

A: Update the custom connector host in Power Platform, flows will automatically use new URL.

**Q: Can I run flows in parallel?**

A: No, the Revit MCP server handles one request at a time (socket limitation).

---

## Summary

Power Automate solves the Copilot Studio timeout issue by:
1. ✅ Allowing 5+ minute operations
2. ✅ Providing async processing
3. ✅ Enabling better error handling
4. ✅ Supporting scheduled runs
5. ✅ Integrating with email/Teams/SharePoint

**Next Steps**:
1. Create manual trigger flow for testing
2. Test with quick mode (should work immediately)
3. Test with detailed mode (should complete without timeout)
4. Set up scheduled flow for daily reports
5. Optional: Build Power App for team access
