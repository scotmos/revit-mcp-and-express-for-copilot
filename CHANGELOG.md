# Changelog

All notable changes to the Revit MCP Express Server project will be documented in this file.

## [2.3.0] - 2025-10-17

### Added
- **Category Normalization**: Automatic handling of category name variations
  - Supports singular/plural forms (window/windows, door/doors, wall/walls, etc.)
  - Case-insensitive matching
  - Maps common variations to correct Revit category names
- **Enhanced Logging**: Request logging shows category normalization and processing details
- **Summary Results by Default**: GET /api/jobs/{jobId} now returns compact summary results by default
  - Avoids Copilot Studio "AsyncResponsePayloadTooLarge" errors
  - Use ?full=true query parameter for complete results (debugging only)

### Changed
- **Breaking**: GET /api/jobs/{jobId} response structure simplified
  - Default response is now summary format (totalElements, avgScore, gradeDistribution, csvFilePath, etc.)
  - Full nested result object only returned with ?full=true
  - Note field added to indicate response type
- **Improved**: Express server logging now shows category normalization steps

### Fixed
- **Category Filtering**: Categories now work correctly with async endpoints
  - "window" → "Windows", "door" → "Doors", "wall" → "Walls", etc.
  - Copilot Studio can now filter by specific categories reliably
- **Payload Size Limit**: Resolved Copilot Studio payload size errors
  - Summary response reduced from ~100KB to ~1-2KB
  - No longer requires query parameter configuration in Power Apps

### Technical Details

#### Category Normalization Map
```javascript
{
  'window': 'Windows', 'windows': 'Windows',
  'door': 'Doors', 'doors': 'Doors',
  'wall': 'Walls', 'walls': 'Walls',
  'floor': 'Floors', 'floors': 'Floors',
  'ceiling': 'Ceilings', 'ceilings': 'Ceilings',
  'roof': 'Roofs', 'roofs': 'Roofs',
  'all': 'All'
}
```

#### Summary Response Format
```json
{
  "success": true,
  "jobId": "abc123...",
  "status": "completed",
  "totalElements": 142,
  "avgScore": 96.4,
  "gradeDistribution": { "A": 132, "B": 8, "C": 2, "D": 0, "F": 0 },
  "csvFilePath": "C:\\Users\\...\\RevitFamilyGrades_....csv",
  "revitFileName": "SnowdonTowers.rvt",
  "timestamp": "2025-10-17 12:34:56",
  "duration": 781,
  "note": "Summary results (default). Use ?full=true for complete details."
}
```

### Migration Guide

**For Power Apps Custom Connectors:**
- Remove any `summary` query parameter configurations
- Default behavior now returns summary results automatically
- No action needed for existing connectors

**For Copilot Studio:**
- Async grading workflow now works without payload size errors
- Category filtering works with natural language ("grade windows", "grade doors")
- No changes needed to existing topics

**For Direct API Users:**
- Add `?full=true` to GET /api/jobs/{jobId} if you need complete results
- Default response is now compact summary format

---

## [2.2.0] - 2025-10-17 (Earlier)

### Added
- Query parameter support for summary mode (later replaced by default behavior)
- OpenAPI documentation for summary parameter

### Changed
- URL structure reorganized for equal hierarchy
  - `/api/grade-families` → `/api/grade-families-sync`
  - `/api/grade-families/async` → `/api/grade-families-async`

---

## [2.1.0] - 2025-10-17 (Earlier)

### Added
- **Async Job Pattern**: Full implementation to avoid Power Platform 240-second timeout
  - POST /api/grade-families-async - Create async job
  - GET /api/jobs/{jobId} - Poll for results
  - GET /api/jobs - List all jobs
  - DELETE /api/jobs/{jobId} - Cleanup
- In-memory job storage with Map()
- Background job processing with setImmediate()
- Job status tracking (PENDING → PROCESSING → COMPLETED/FAILED)
- Unique job IDs using crypto.randomBytes(16)

### Changed
- Server version updated to 2.1.0
- OpenAPI specification updated to v2.1.0

---

## [2.0.0] - 2025-10-16 (Initial Release)

### Added
- Express.js HTTP server for Revit MCP integration
- Synchronous family grading endpoint
- OpenAPI 3.0.1 specification
- ngrok tunnel support for public access
- Health check endpoint
- CORS support for Power Platform
- Comprehensive error handling
- CSV export functionality
