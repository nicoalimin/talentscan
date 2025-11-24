# TODO

This document tracks planned improvements and known issues for the TalentScan resume screening application.

## High Priority

### 1. ~~Fix `make ui-watch` in iTerm~~ ✅
**Issue**: The `make ui-watch` command doesn't work properly in iTerm terminal.

**Solution**: Recreate the virtual environment to resolve the issue.

**Steps to Fix**:
```bash
# Remove old venv
rm -rf venv

# Create new venv
python3 -m venv venv

# Activate and install dependencies
source venv/bin/activate
pip install -r requirements.txt
```

**Status**: � Completed

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

### 3. ~~Rename "Capture" in Screen Tool~~ ✅
**Issue**: Screen feature is incorrectly named - what does "Capture" even mean?

**Details**:
- `screen_candidates_tool_with_capture` was confusing
- The "capture" referred to capturing results for later use, but this was not clear to users
- Renamed to `screen_candidates_tool` for better clarity

**Files Updated**:
- `src/graph.py` (tool definition and all references)
- System prompts that mention the tool

**Status**: � Completed

---

### 4. Upgrade Orchestrator to Reasoning Model
**Issue**: The orchestrator agent should use a reasoning model and pipe the thinking process back to the user.

**Details**:
- Current agent uses `gemini-2.0-flash-exp` which doesn't expose reasoning steps
- Should upgrade to a reasoning model (e.g., `gemini-2.0-flash-thinking-exp` or similar)
- Display the model's internal reasoning/thinking process in the Chainlit UI
- This will help users understand why the agent made certain decisions

**Implementation**:
- Update model in `src/graph.py` to use a reasoning-capable model
- Capture and display thinking tokens/steps in the UI
- May need to create additional `cl.Step` instances for reasoning phases
- Consider streaming the thinking process as it happens

**Benefits**:
- Transparency in agent decision-making
- Better debugging when agent makes unexpected choices
- Improved user trust and understanding

**Files to Modify**:
- `src/graph.py` - Update model configuration
- `src/app.py` - Add reasoning step display logic

**Status**: 🔴 Not Started

---

## Medium Priority

### 5. Dockerize the Application
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

### 6. Google Drive Native Integration
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

### 7. Handle Out-of-Sync Resumes
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
