# Jarvis Hardware Builder

Jarvis Hardware Builder is a hardware planning assistant with a CLI, a Streamlit UI, structured project memory, revision history, file attachments, and exportable project plans. I plan to add moore in future if possible.

## Features

- Builds hardware plans from structured project inputs
- Ask follow-up questions against saved project context
- Save projects in SQLite with revisions, tags, and attachments
- Export projects as JSON, Markdown, and PDF
- Fall back to a local plan generator when no OpenAI API key is available
- A good UI for easier workflow and asthetics.

## Project Structure

```text
.
├── agent.py
├── exporter.py
├── main.py
├── memory_db.py
├── streamlit_ui.py
├── test_agent_contract.py
├── test_memory.py
└── requirements.txt
```

## Requirements

- Python 3.9+
- `OPENAI_API_KEY` if you want model-backed responses. FYI the default model is set to `gpt-4o`.

## Installation

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Configuration

Required for AI responses:

```bash
export OPENAI_API_KEY="your_api_key_here"
```

Optional environment variables:

- `OPENAI_MODEL`: defaults to `gpt-4o`
- `MEMORY_DB_PATH`: defaults to `memory.db`
- `PROJECT_FILES_DIR`: defaults to `project_files`
- `EXPORT_DIR`: defaults to `exports`

## Run

CLI:

```bash
python main.py
```

Streamlit:

```bash
streamlit run streamlit_ui.py
```

## Data Model

SQLite stores project state in these tables:

- `projects`
- `project_revisions`
- `follow_ups`
- `attachments`
- `project_tags`

Saved project records include:

- Project profile and structured inputs
- Structured artifacts such as BOM, wiring plan, safety checks, and estimated cost to make everything work in one space.
- Plan text easy to understand and great for beginner and experts
- Follow-up history
- Revision snapshots
- Uploaded file metadata

## Testing

Run:

```bash
python test_memory.py
python test_agent_contract.py
```

The tests cover persistence, revision history, attachment storage, exports, legacy migration, and the agent contract.

## Notes

- The OpenAI client uses the modern SDK when available and falls back to the older compatibility path otherwise.
- When AI output is unavailable or invalid, the app generates a local structured fallback plan instead of failing.

Thanks for reading the README! ✌️
