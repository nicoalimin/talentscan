# TalentScan - Resume Screening Agent

An AI-powered resume screening agent built with LangChain, LangGraph, and Google Gemini.

## Features

- 📄 **Resume Processing**: Extracts structured data from PDF and DOCX resumes using Google Gemini VLM
- 🎯 **Smart Screening**: Ranks candidates based on role, seniority, and tech stack requirements
- 💾 **SQLite Database**: Stores candidate profiles with deduplication
- 🌐 **Multiple Interfaces**:
  - CLI for batch processing
  - FastAPI REST API
  - Chainlit chat UI
- 🔄 **LangGraph Workflow**: Orchestrates processing and screening with state management

## Quick Start

### Prerequisites

- Python 3.12+
- Google API Key (for Gemini)
- Google Drive service account credentials (for optional Drive sync)

### Installation

```bash
# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # On macOS/Linux

# Install dependencies
make install
```

### Set Environment Variable

You can set the Google API key in two ways:

**Option 1: Using .env file (Recommended)**
```bash
# Copy the example file
cp .env.example .env

# Edit .env and add your API key
# GOOGLE_API_KEY=your-google-api-key-here
```

**Option 2: Export as environment variable**
```bash
export GOOGLE_API_KEY='your-google-api-key'
```

### Google Drive Credentials (optional)

To automatically fetch resumes from a Google Drive folder, provide a service account credential using one of these options:

```bash
# As a JSON string
export GOOGLE_DRIVE_CREDENTIALS='{"type": "service_account", ... }'

# Or path to the JSON file
export GOOGLE_DRIVE_CREDENTIALS_PATH=/path/to/credentials.json
```

Get your API key from: https://makersuite.google.com/app/apikey

## Usage

### Using Makefile (Recommended)

```bash
# View all available commands
make help

# Run tests
make test

# Run linter
make lint

# View database contents
make view-db

# Run API server
make server

# Run Chainlit UI
make ui

# Clean cache files
make clean
```

### CLI

```bash
python main.py \
  --role "Backend Engineer" \
  --seniority "Senior" \
  --tech_stack "Python, Django, AWS"
```

To fetch resumes from a Google Drive folder before processing, pass the folder ID:

```bash
python main.py \
  --drive_folder_id "your-drive-folder-id" \
  --role "Backend Engineer" \
  --seniority "Senior" \
  --tech_stack "Python, Django, AWS"
```

### API Server

```bash
# Start server
python main.py --server

# Or use make
make server
```

API will be available at `http://localhost:8000`

Endpoints:
- `GET /` - Health check
- `POST /screen` - Screen candidates
- `POST /process` - Process resumes from directory
- `GET /candidates` - List all candidates

### Chainlit UI

```bash
chainlit run chainlit_app.py

# Or use make
make ui
```

## Project Structure

```
talentscan/
├── src/                  # Core application code
│   ├── agent.py         # Candidate screening logic
│   ├── api.py           # FastAPI REST endpoints
│   ├── database.py      # SQLite operations
│   ├── graph.py         # LangGraph workflow
│   └── processor.py     # Resume extraction
├── scripts/             # Utility scripts
│   ├── create_dummies.py
│   ├── verify_graph.py
│   └── view_db.py
├── chainlit_app.py      # Chainlit UI entrypoint
├── main.py              # CLI entry point
├── Makefile             # Development automation
└── requirements.txt     # Dependencies
```

## Development

### Running Tests

```bash
make test
```

### Linting

```bash
# Check code
make lint

# Auto-format code
make format
```

### Creating Test Data

```bash
make create-dummies
```

## License

MIT
