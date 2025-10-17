# Async vs Sync: When to Use Each Endpoint

## 🚨 Power Platform Timeout Limitation

**Power Platform has a HARD 240-second (4 minute) timeout for Custom Connectors, Copilot Studio, and Power Automate HTTP actions.**

This timeout:
- ❌ **Cannot be extended** in any Power Platform product
- ❌ **Cannot be configured** in Custom Connector settings
- ❌ **Cannot be bypassed** with retries or error handling
- ✅ **Can be worked around** using the async job pattern

---

## 📊 Decision Matrix: Sync vs Async

### Use **SYNCHRONOUS** Endpoints (`POST /api/grade-families`)

✅ **When:**
- Small projects (<50 families in target category)
- Specific categories (Doors, Windows, Furniture)
- Quick grading mode (`gradeType: "quick"`)
- Expected completion time <3 minutes
- Testing/development with small models
- Direct API calls outside Power Platform

✅ **Advantages:**
- Immediate results (no polling needed)
- Simpler code/flow
- Lower latency for small jobs
- Single HTTP request

❌ **Risk:**
- Will timeout if processing takes >240 seconds
- Power Platform will show error: "The connector has timed out after 240000 seconds"

---

### Use **ASYNCHRONOUS** Endpoints (`POST /api/grade-families/async`)

✅ **When:**
- Large projects (>50 families)
- Category = "All" (analyzes entire project)
- Detailed grading mode (`gradeType: "detailed"`)
- Uncertain project size
- **ANY Power Platform integration** (safest choice)
- Production/user-facing scenarios

✅ **Advantages:**
- **Never times out** (client only waits for polling interval)
- Can process jobs of any duration
- Power Platform friendly
- Job status tracking and history

❌ **Tradeoff:**
- Requires polling loop (slightly more complex)
- Adds latency from polling intervals (5-10 seconds)
- Needs multiple HTTP requests

---

## 🎯 Recommendation for Power Platform

### **Default to ASYNC for ALL Power Platform integrations**

Why? Because:
1. You don't know how large the user's Revit project will be
2. You don't know what category they'll select
3. A timeout produces a bad user experience
4. Async has minimal downside (just polling delay)

### Exception: Use SYNC only if you have:
- Fixed, known-small dataset
- Hard requirement for <5 second response
- Complete control over input parameters

---

## 💡 How Copilot Agent Will Choose

**The Copilot agent will NOT automatically choose between sync/async.**

You need to configure this in your Power Platform integration:

### Option 1: **Always Use Async** (Recommended)
```
Create a single action in Copilot Studio that:
1. Calls POST /api/grade-families/async
2. Polls GET /api/jobs/{jobId} until completed
3. Returns results to user

This works for all scenarios.
```

### Option 2: **Expose Both, Let User Choose**
```
Create two actions:
- "Grade Families (Fast)" → Uses sync endpoint
- "Grade Families (Safe)" → Uses async endpoint

User documentation explains when to use each.
```

### Option 3: **Smart Flow with Parameter**
```
Add a parameter like "useAsync" (boolean):
- If true: Use async pattern
- If false: Use sync pattern

User can override based on their needs.
```

### Option 4: **Heuristic-Based Decision** (Advanced)
```
In Power Automate, use a condition:
IF category = "All" OR gradeType = "detailed":
    Use async pattern
ELSE:
    Use sync pattern

This adds complexity but optimizes for speed when safe.
```

---

## 🔄 Async Pattern Implementation

### Step-by-Step Flow (Power Automate Example)

```yaml
1. Initialize Variables:
   - jobId (string)
   - status (string) = "pending"
   - maxAttempts (integer) = 60  # 10 minutes max
   - attempts (integer) = 0

2. HTTP Request - Start Job:
   POST /api/grade-families/async
   Body: {
     "category": "@{triggerBody()?['category']}",
     "gradeType": "detailed",
     "includeTypes": true
   }
   → Set jobId = @{body('HTTP')?['jobId']}

3. Do Until Loop (condition: status = "completed" OR status = "failed" OR attempts > maxAttempts):
   
   a. Delay: 10 seconds
   
   b. HTTP Request - Check Status:
      GET /api/jobs/@{variables('jobId')}
      → Set status = @{body('HTTP_2')?['status']}
   
   c. Increment attempts: @{add(variables('attempts'), 1)}

4. Condition - Check Final Status:
   IF status = "completed":
      → Parse and return body('HTTP_2')?['result']
   ELSE:
      → Return error message
```

### Key Implementation Notes

1. **Polling Interval**: 5-10 seconds is optimal
   - Too fast: Wastes server resources
   - Too slow: Poor user experience

2. **Max Attempts**: Set reasonable limit (60 = 10 minutes)
   - Prevents infinite loops
   - Allows time for large projects

3. **Status Handling**:
   - `pending`: Keep polling
   - `processing`: Keep polling
   - `completed`: Extract results from `.result` property
   - `failed`: Show error from `.error` property

4. **Error Handling**:
   - Network errors: Retry with backoff
   - 404 on job: Server restarted, job lost
   - 500 errors: Show user, don't retry

---

## 📈 Performance Comparison

| Scenario | Sync Endpoint | Async Endpoint |
|----------|---------------|----------------|
| **10 Doors, Quick** | ⚡ 300ms total | 🐢 ~10s total (polling overhead) |
| **50 Doors, Quick** | ⚡ 800ms total | 🐢 ~11s total |
| **142 Doors, Quick** | ⚡ 781ms total | 🐢 ~11s total |
| **All Categories, Detailed** | ⚠️ ~180s (risk timeout) | ✅ ~190s total (safe) |
| **Large Project (>1000)** | ❌ TIMEOUT (>240s) | ✅ Works (no timeout) |

**Key Insight**: Async adds ~10 seconds overhead but eliminates timeout risk.

---

## 🛠️ Testing Your Integration

### Test Sync Endpoint (Direct)
```powershell
$body = @{ category = "Doors"; gradeType = "quick"; includeTypes = $true } | ConvertTo-Json
Invoke-RestMethod -Uri "http://localhost:3000/api/grade-families" -Method POST -Body $body -ContentType "application/json"
```

### Test Async Endpoint (With Polling)
```powershell
# Start job
$body = @{ category = "All"; gradeType = "detailed"; includeTypes = $true } | ConvertTo-Json
$job = Invoke-RestMethod -Uri "http://localhost:3000/api/grade-families/async" -Method POST -Body $body -ContentType "application/json"

Write-Host "Job ID: $($job.jobId)"

# Poll for results
do {
    Start-Sleep -Seconds 5
    $status = Invoke-RestMethod -Uri "http://localhost:3000/api/jobs/$($job.jobId)"
    Write-Host "Status: $($status.status)"
} while ($status.status -ne "completed" -and $status.status -ne "failed")

# Show results
$status.result | ConvertTo-Json -Depth 10
```

---

## 📝 Summary

| Aspect | Recommendation |
|--------|----------------|
| **Default Choice** | Async (safer) |
| **Power Platform** | Always async |
| **Small Projects** | Sync acceptable (if <3 min guaranteed) |
| **Large Projects** | Must use async |
| **Production** | Async |
| **Development/Testing** | Either (sync is faster) |

**Bottom Line**: When in doubt, use async. The 10-second polling overhead is worth the guarantee that your integration won't timeout.

---

## 🔗 Related Documentation

- [EXPRESS_SERVER_COMPLETE.md](./EXPRESS_SERVER_COMPLETE.md) - Server implementation details
- [OPENAPI_POWER_APPS_GUIDE.md](./OPENAPI_POWER_APPS_GUIDE.md) - Power Platform setup
- [README_COMPLETE.md](./README_COMPLETE.md) - Complete solution overview
- [revit-mcp-openapi.json](./revit-mcp-openapi.json) - OpenAPI specification with both endpoints
