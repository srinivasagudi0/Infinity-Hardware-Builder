# Jarvis Hardware Builder

Jarvis Hardware Builder is a hardware planning assistant that helps you design structured hardware projects. It provides a CLI, a Streamlit UI, persistent project memory, revision history, file attachments, and exportable plans.

---

## Features

- Generate hardware plans from structured inputs  
- Ask follow-up questions using saved project context  
- Store projects in SQLite with revisions, tags, and attachments  
- Export plans as JSON, Markdown, and PDF  
- Local fallback plan generator when no OpenAI API key is available  
- Clean Streamlit UI for better workflow  

---

## Project Structure

```
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

---

## Requirements

- Python 3.9+
- OpenAI API key (optional)

Default model: `gpt-4o`

---

## Installation

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

---

## Configuration

Set your OpenAI API key:

```bash
export OPENAI_API_KEY="your_api_key_here"
```

Optional environment variables:

```bash
OPENAI_MODEL=gpt-4o
MEMORY_DB_PATH=memory.db
PROJECT_FILES_DIR=project_files
EXPORT_DIR=exports
```

---

## Usage

### CLI

```bash
python main.py
```

### Streamlit UI

```bash
streamlit run streamlit_ui.py
```

---

## How It Works

1. Enter project details (requirements, budget, goals)  
2. The agent generates:
   - Bill of Materials (BOM)
   - Wiring plan
   - Safety checks
   - Cost estimate  
3. The project is saved with revision history  
4. You can ask follow-ups, update the project, or export results  

If no API key is provided, a local fallback generator is used.

---

## Data Model

SQLite tables:

- projects  
- project_revisions  
- follow_ups  
- attachments  
- project_tags  

Each project includes inputs, generated plans, history, revisions, and file metadata.

---

## Testing

```bash
python test_memory.py
python test_agent_contract.py
```

---

## Notes

- Uses modern OpenAI SDK when available  
- Falls back to a local generator if AI is unavailable  
