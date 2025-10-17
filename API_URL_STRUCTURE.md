# API URL Structure - v2.1.0

## ✅ **Reorganized for Clarity** (October 17, 2025)

The API has been reorganized so that synchronous and asynchronous endpoints have **equal URL lengths** and **parallel structure**. This makes them easier to discover and understand.

---

## 📊 **URL Comparison**

### **Before (v2.0) - Confusing Hierarchy**
```
POST /api/grade-families          ← Sync endpoint (short URL)
POST /api/grade-families/async    ← Async looked "buried" under sync
```
❌ **Problem**: Async endpoint appeared subordinate to sync
❌ **Problem**: Different URL depths implied hierarchy that doesn't exist

### **After (v2.1.0) - Equal Hierarchy** ✅
```
POST /api/grade-families-sync     ← Synchronous grading
POST /api/grade-families-async    ← Asynchronous grading (RECOMMENDED)
```
✅ **Benefit**: Both endpoints are peers at the same level
✅ **Benefit**: Clear naming makes purpose obvious
✅ **Benefit**: Async is not "hidden" - it's a first-class endpoint

---

## 🎯 **Complete API Structure**

### **Health & Info**
```
GET  /health                      - Server health check
GET  /api/info                    - Server information and documentation
```

### **Grading Endpoints** (Choose One)
```
POST /api/grade-families-sync     - Synchronous (fast, may timeout)
POST /api/grade-families-async    - Asynchronous (safe, recommended)
```

### **Async Job Management**
```
GET    /api/jobs/:jobId           - Get job status and results
GET    /api/jobs                  - List all jobs
DELETE /api/jobs/:jobId           - Delete completed job
```

### **Legacy Compatibility**
```
POST /api/tools/grade_all_families_by_category    - Flask-compatible endpoint
```

---

## 📋 **Endpoint Details**

### **POST /api/grade-families-sync**

**Purpose**: Synchronous family grading  
**Use When**: Small projects (<50 families), fast operations  
**Warning**: ⚠️ Will timeout after 240 seconds in Power Platform

**Request:**
```json
{
  "category": "Doors",
  "gradeType": "quick",
  "includeTypes": true,
  "outputPath": ""
}
```

**Response (immediate):**
```json
{
  "success": true,
  "totalElements": 142,
  "avgScore": 96.4,
  "csvFilePath": "C:\\Users\\...\\RevitFamilyGrades.csv",
  "gradeDistribution": { "A": 132, "B": 0, "C": 0, "D": 10, "F": 0, "ERROR": 0 },
  "duration": 781
}
```

**Pros:**
- ✅ Immediate results
- ✅ Simpler workflow (one request)
- ✅ Lower latency for small jobs

**Cons:**
- ❌ Timeout risk for large projects
- ❌ Not suitable for Power Platform with large datasets

---

### **POST /api/grade-families-async** ⭐ **RECOMMENDED**

**Purpose**: Asynchronous family grading  
**Use When**: Large projects, Power Platform integrations, uncertain project size  
**Guarantee**: ✅ Never times out

**Request:**
```json
{
  "category": "All",
  "gradeType": "detailed",
  "includeTypes": true,
  "outputPath": ""
}
```

**Response (immediate, <10ms):**
```json
{
  "success": true,
  "jobId": "a34750eba629fa17ebd0e2b1bb02d1f2",
  "status": "pending",
  "message": "Job created successfully. Use GET /api/jobs/{jobId} to check status.",
  "pollUrl": "/api/jobs/a34750eba629fa17ebd0e2b1bb02d1f2"
}
```

**Then poll:** `GET /api/jobs/a34750eba629fa17ebd0e2b1bb02d1f2`

**When completed:**
```json
{
  "success": true,
  "jobId": "a34750eba629fa17ebd0e2b1bb02d1f2",
  "status": "completed",
  "result": {
    "success": true,
    "totalElements": 142,
    "avgScore": 96.4,
    "csvFilePath": "C:\\Users\\...\\RevitFamilyGrades.csv",
    "gradeDistribution": { "A": 132, "B": 0, "C": 0, "D": 10, "F": 0, "ERROR": 0 }
  },
  "createdAt": "2025-10-17T17:08:17.628Z",
  "completedAt": "2025-10-17T17:08:18.411Z",
  "duration": 781
}
```

**Pros:**
- ✅ Never times out (Power Platform safe)
- ✅ Suitable for projects of any size
- ✅ Job status tracking
- ✅ Recommended for production

**Cons:**
- ⚠️ Requires polling loop (adds ~10 seconds overhead)
- ⚠️ Slightly more complex workflow

---

## 🔄 **Migration Guide**

### **If you're using the OLD URLs:**

**Old Code (will still work but deprecated):**
```javascript
// Sync
fetch('/api/grade-families', { ... })

// Async
fetch('/api/grade-families/async', { ... })
```

**New Code (recommended):**
```javascript
// Sync
fetch('/api/grade-families-sync', { ... })

// Async
fetch('/api/grade-families-async', { ... })
```

### **OpenAPI Spec Changes:**

**Old operation IDs:**
- `gradeFamilies` (sync)
- `startAsyncGrading` (async)

**New operation IDs:**
- `gradeFamiliesSync` (sync)
- `gradeFamiliesAsync` (async)

**Action**: Re-import `revit-mcp-openapi.json` into Power Apps Custom Connector

---

## 💡 **Best Practices**

### **Choose the Right Endpoint:**

| Scenario | Recommended Endpoint |
|----------|---------------------|
| Small project (<50 families) | Either (sync is faster) |
| Large project (>50 families) | `/api/grade-families-async` |
| Power Platform integration | `/api/grade-families-async` |
| Unknown project size | `/api/grade-families-async` |
| Development/testing | Either |
| Production | `/api/grade-families-async` |

### **Default Recommendation:**
**Always use `/api/grade-families-async` unless you have a specific reason not to.**

The ~10 second polling overhead is negligible compared to the risk of a 240-second timeout failure.

---

## 📊 **URL Length Comparison**

```
/api/grade-families-sync     (24 characters)
/api/grade-families-async    (25 characters)
```

✅ **Nearly equal lengths** - visually balanced
✅ **Parallel structure** - easy to remember
✅ **Self-documenting** - purpose is clear from name

---

## 🚀 **Next Steps**

1. **Re-import OpenAPI spec** into Power Apps Custom Connector
2. **Update Copilot Studio actions** to use new operation IDs
3. **Test both endpoints** to verify functionality
4. **Update any existing flows** to use new URLs (optional - old URLs still work)

---

## 📝 **Summary**

- ✅ URLs reorganized for equal hierarchy
- ✅ Async endpoint no longer "buried" under sync
- ✅ Clearer naming convention
- ✅ Both endpoints are first-class citizens
- ✅ Backward compatible (legacy endpoints still work)
- ✅ Committed to GitHub and ready to use

**Version**: 2.1.0  
**Updated**: October 17, 2025
