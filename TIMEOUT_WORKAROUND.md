# Power Platform Timeout Workaround

## The Problem

**Power Platform Custom Connector Timeout**: 240 seconds (4 minutes) - HARD LIMIT
- Cannot be extended in Copilot Studio
- Cannot be extended in Power Apps
- Cannot be extended in Power Automate custom connectors
- This is a Microsoft platform limitation

**Your Express Server Timeout**: 600 seconds (10 minutes)
- Server can handle long operations
- But Power Platform times out first

## Error Message
```
The connector 'grade families' has timed out after 240000 seconds.
Error Code: ConnectorTimeoutError
```

## Immediate Solutions

### Solution 1: Use Quick Mode (Fastest)
In your Copilot Studio action inputs, set:
```json
{
  "category": "Doors",
  "gradeType": "quick",    ← Change from "detailed" to "quick"
  "includeTypes": true
}
```

**Quick mode** completes much faster:
- Small projects (<500 elements): ~5-30 seconds
- Medium projects (500-2000 elements): ~30-120 seconds  
- Large projects (2000+ elements): ~2-4 minutes

This should work within the 4-minute limit for most projects.

### Solution 2: Grade Specific Categories (Faster)
Instead of grading "All" categories, grade one category at a time:
- Doors only: Faster
- Windows only: Faster
- All categories: Slower (may timeout)

Example - Multiple actions:
1. Grade Doors (quick mode)
2. Grade Windows (quick mode)
3. Grade Walls (quick mode)

Each completes within timeout.

### Solution 3: Use Power Automate HTTP Action (240s limit still applies)
Power Automate's built-in HTTP action has the same 240-second timeout, so this won't help.

### Solution 4: Test Locally First
Before calling from Copilot, test the grading time:
```powershell
# Time the request
$start = Get-Date
$body = '{"category":"All","gradeType":"detailed","includeTypes":true}'
Invoke-RestMethod -Uri "http://localhost:3000/api/grade-families" `
    -Method POST -Body $body -ContentType "application/json"
$duration = (Get-Date) - $start
Write-Host "Duration: $($duration.TotalSeconds) seconds"
```

If > 240 seconds locally, it will definitely timeout from Power Platform.

## Advanced Solution: Async Pattern (Requires Code Changes)

To handle operations > 4 minutes, implement async pattern:

### How It Works
1. **Start Job**: POST `/api/grade-families/start` → Returns `jobId`
2. **Check Status**: GET `/api/grade-families/status/{jobId}` → Returns status
3. **Get Results**: GET `/api/grade-families/results/{jobId}` → Returns results

### Benefits
- Initial request returns immediately (< 1 second)
- Power Platform doesn't timeout
- Poll for completion at your own pace
- Can handle operations of any length

### Implementation Needed
This requires modifying the Express server to:
1. Accept requests and return job IDs immediately
2. Run grading in background
3. Store results in memory or database
4. Provide status/results endpoints

**Do you want me to implement this?** It's about 2-3 hours of work.

## Current Workarounds Summary

| Solution | Effort | Effectiveness | Notes |
|----------|--------|---------------|-------|
| Use "quick" mode | None | ⭐⭐⭐ High | Works for most projects |
| Grade by category | Low | ⭐⭐ Medium | Split into multiple calls |
| Test locally first | Low | ⭐⭐ Medium | Helps predict timeout |
| Implement async | High | ⭐⭐⭐ High | Best long-term solution |

## Recommended Approach

**For now:**
1. ✅ Use `"gradeType": "quick"` in Copilot Studio
2. ✅ Grade specific categories instead of "All"
3. ✅ Test locally to verify timing

**For future:**
- If you consistently hit timeout, implement async pattern
- Or use "quick" mode permanently (it's usually sufficient)

## Testing Quick Mode

Update your Copilot Studio action input mapping:
1. Go to action settings
2. Change gradeType default from "detailed" to "quick"
3. Or in system instructions: "Always use quick mode for grading"

Test from Copilot:
```
You: "Grade all doors"
Copilot: [Calls action with gradeType: "quick"]
Copilot: "Graded 142 doors in 45 seconds, average score 96/100"
```

Should complete well within 240 seconds!

## Why Quick Mode is Usually Sufficient

**Quick Mode**:
- ✅ Checks face count, solid count
- ✅ Detects import sources (SAT, mesh)
- ✅ Calculates quality score
- ✅ Generates CSV with recommendations
- ✅ ~80% faster than detailed mode

**Detailed Mode Additions**:
- Additional geometry analysis
- More detailed recommendations
- Slightly more accurate scoring
- But takes much longer

For most use cases, **quick mode provides all the information you need**.

## Current Status

Your Express server is:
- ✅ Running and healthy
- ✅ Capable of 10-minute operations
- ⚠️ But limited by Power Platform's 4-minute timeout

**Next step**: Update Copilot Studio to use "quick" mode and test again.

---

**Need async implementation? Let me know and I'll build it!**
