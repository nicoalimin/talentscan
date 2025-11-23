# TODO

This document tracks planned improvements and known issues for the TalentScan resume screening application.

## High Priority

### 1. Fix `make ui-watch` in iTerm
**Issue**: The `make ui-watch` command doesn't work properly in iTerm terminal.

**Details**: 
- Command may not be running correctly in iTerm environment
- Need to investigate terminal compatibility issues
- Consider alternative commands or shell configurations

**Status**: 🔴 Not Started

---

### 2. Orchestrator Tool Selection Logic
**Issue**: The orchestrator doesn't know to call the screen candidates tool if there are no candidates pre-populated yet.

**Details**:
- Agent should intelligently detect when candidate database is empty
- Should automatically call `process_resumes_tool` before attempting to screen
- Need to improve agent's decision-making logic in `src/graph.py`

**Suggested Solution**:
- Add a check in the screening tool to return a helpful message if no candidates exist
- Update system prompt to guide the agent to process resumes first
- Consider adding a "smart screening" tool that handles both steps

**Status**: 🔴 Not Started

---

### 3. Rename "Capture" in Screen Tool
**Issue**: Screen feature is incorrectly named - what does "Capture" even mean?

**Details**:
- `screen_candidates_tool_with_capture` is confusing
- The "capture" refers to capturing results for later use, but this is not clear to users
- Should be renamed to something more intuitive

**Suggested Names**:
- `screen_candidates_tool`
- `search_candidates_tool`
- `filter_candidates_tool`

**Files to Update**:
- `src/graph.py` (tool definition and references)
- System prompts that mention the tool

**Status**: 🔴 Not Started

---

## Medium Priority

### 4. Dockerize the Application
**Issue**: Application is not containerized, making deployment and environment consistency difficult.

**Details**:
- Create `Dockerfile` for the application
- Create `docker-compose.yml` for easy local development
- Include all dependencies (Python, SQLite, etc.)
- Document Docker setup in README

**Requirements**:
- Multi-stage build for optimization
- Volume mounts for database persistence
- Environment variable configuration
- Health checks

**Status**: 🔴 Not Started

---

### 5. Google Drive Native Integration
**Issue**: No native integration with Google Drive for resume storage.

**Details**:
- Users should be able to connect their Google Drive
- Automatically sync resumes from a specific folder
- Process new resumes as they're added
- Update existing candidate profiles when resumes are modified

**Implementation Considerations**:
- Use Google Drive API
- OAuth2 authentication flow
- Webhook/polling for file changes
- Store Drive file IDs in database for tracking

**Files to Create/Modify**:
- `src/gdrive.py` - Google Drive integration
- `src/database.py` - Add `drive_file_id` column
- Environment variables for Google Drive credentials

**Status**: 🔴 Not Started

---

### 6. Handle Out-of-Sync Resumes
**Issue**: No capability for resumes that are not in sync anymore (deleted, moved, or outdated).

**Details**:
- Need an `is_active` flag on the database
- Mark candidates as inactive when their resume is no longer available
- Provide UI to show active vs inactive candidates
- Allow reactivation if resume becomes available again

**Database Changes**:
```sql
ALTER TABLE candidates ADD COLUMN is_active BOOLEAN DEFAULT 1;
ALTER TABLE candidates ADD COLUMN last_synced_at TIMESTAMP;
```

**Implementation**:
- Add migration for new columns
- Update `process_resumes` to check file existence
- Mark missing files as `is_active = 0`
- Filter inactive candidates from search results by default
- Add option to include inactive candidates in searches

**Files to Modify**:
- `migrations/` - New migration file
- `src/database.py` - Update schema and queries
- `src/processor.py` - Add sync checking logic
- `src/agent.py` - Filter inactive candidates

**Status**: 🔴 Not Started

---

## Status Legend
- 🔴 Not Started
- 🟡 In Progress
- 🟢 Completed
- 🔵 Blocked

---

## Contributing
When working on a TODO item:
1. Update the status to 🟡 In Progress
2. Create a feature branch: `feature/todo-<number>-<short-description>`
3. Update this file with any additional findings or changes to the plan
4. Mark as 🟢 Completed when done and merged
