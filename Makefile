.PHONY: help install test lint clean run server ui view-db verify-graph create-dummies migrate-up migrate-down migrate-status

# Default target
help:
	@echo "Available targets:"
	@echo "  make install          - Install dependencies"
	@echo "  make test            - Run tests"
	@echo "  make lint            - Run code linter"
	@echo "  make run             - Run CLI application"
	@echo "  make server          - Run API server"
        @echo "  make ui              - Run Streamlit UI"
	@echo "  make view-db         - View database contents"
	@echo "  make verify-graph    - Verify LangGraph workflow"
	@echo "  make create-dummies  - Create dummy resume files"
	@echo "  make migrate-up      - Apply pending database migrations"
	@echo "  make migrate-down    - Rollback last database migration"
	@echo "  make migrate-status  - Show migration status"
	@echo "  make clean           - Remove cache files"

# Install dependencies
install:
	@echo "Installing dependencies..."
	./venv/bin/python -m pip install -r requirements.txt
	./venv/bin/python -m pip install flake8 black


# Run tests
test: verify-graph
	@echo "✓ All tests passed!"

# Lint code
lint:
	@echo "Running flake8..."
	./venv/bin/flake8 src/ scripts/ main.py --max-line-length=120 --exclude=venv,__pycache__,.git
	@echo "Running black check..."
	./venv/bin/black --check src/ scripts/ main.py

# Format code
format:
	@echo "Formatting code with black..."
	./venv/bin/black src/ scripts/ main.py

# Run CLI application
run:
	@echo "Usage: make run ROLE='Backend Engineer' SENIORITY='Senior' STACK='Python, Django'"
	@if [ -z "$(ROLE)" ] || [ -z "$(SENIORITY)" ] || [ -z "$(STACK)" ]; then \
		echo "Error: Please provide ROLE, SENIORITY, and STACK variables"; \
		exit 1; \
	fi
	./venv/bin/python main.py --role "$(ROLE)" --seniority "$(SENIORITY)" --tech_stack "$(STACK)"

# Run API server
server:
	@echo "Starting API server on http://localhost:8000"
	./venv/bin/python main.py --server

# Run Streamlit UI
ui:
        @echo "Starting Streamlit UI..."
        ./venv/bin/streamlit run streamlit_app.py

# View database contents
view-db:
	@echo "Viewing database contents..."
	./venv/bin/python scripts/view_db.py

# Verify LangGraph workflow
verify-graph:
	@echo "Verifying LangGraph workflow..."
	./venv/bin/python scripts/verify_graph.py

# Create dummy resume files
create-dummies:
	@echo "Creating dummy resume files..."
	./venv/bin/python scripts/create_dummies.py

# Database migrations
migrate-up:
	@echo "Applying database migrations..."
	./venv/bin/python migrations/migrate.py up

migrate-down:
	@echo "Rolling back last migration..."
	./venv/bin/python migrations/migrate.py down

migrate-status:
	@echo "Checking migration status..."
	./venv/bin/python migrations/migrate.py status

# Clean cache files
clean:
	@echo "Cleaning cache files..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name ".DS_Store" -delete
	@echo "✓ Cache files cleaned"
