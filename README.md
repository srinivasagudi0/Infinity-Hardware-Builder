# Jarvis Hardware Builder

Jarvis Hardware Builder is a lightweight AI assistant for planning hardware projects. It helps you describe a build, get step-by-step suggestions, ask follow-up questions, and keep project history in a local SQLite database so you can resume work later.

The project includes:

- A CLI workflow for quick interactive use in the terminal
- A Streamlit app for a simple browser-based interface
- Local project memory with saved follow-up history
- Automatic generation of a plain-text project plan file

## What It Does

You provide:

- A project name
- The components you want to use
- The purpose of the build
- Any special requirements or constraints

The app then:

- Generates an initial hardware build recommendation with practical steps
- Stores the project and responses in SQLite
- Lets you continue the conversation with follow-up questions
- Reuses prior context so later answers stay tied to the same project
- Writes a final plan file named like `<project_name>_plan.txt`

## Project Structure

```text
.
├── agent.py          # OpenAI client wrapper and prompt helpers
├── main.py           # CLI entry point
├── memory_db.py      # SQLite persistence layer
├── streamlit_ui.py   # Streamlit web UI
├── test_memory.py    # Basic persistence tests
├── requirements.txt  # Python dependencies
└── README.md
```

## Requirements

- Python 3.9+
- An OpenAI API key

## Installation

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Configuration

Set your OpenAI API key before running the app:

```bash
export OPENAI_API_KEY="your_api_key_here"
```

Optional environment variables:

- `MEMORY_DB_PATH`: overrides the default SQLite file path (`memory.db`)

Example:

```bash
export MEMORY_DB_PATH="data/hardware_builder.db"
```

## Run The CLI App

```bash
python main.py
```

The CLI will:

1. Show saved projects if they exist
2. Let you resume a project or start a new one
3. Generate an initial suggestion
4. Accept follow-up questions until you type `exit`
5. Save a plan file at the end of the session

## Run The Streamlit App

```bash
streamlit run streamlit_ui.py
```

The Streamlit UI lets you:

- Create a new hardware project
- Reopen saved projects
- Review the initial suggestion
- Ask follow-up questions from the browser

## Data Storage

Project data is stored locally in SQLite.

- Default database: `memory.db`
- Saved data includes project inputs, initial responses, follow-up questions, follow-up answers, and timestamps

Two tables are used:

- `projects`
- `follow_ups`

## Testing

Run the included persistence test with:

```bash
python test_memory.py
```

This verifies that:

- Projects can be saved and reloaded
- Follow-up questions persist correctly
- Context can be rebuilt from stored history
- Duplicate project detection works

## Notes

- The OpenAI model is currently hardcoded in [agent.py](/Users/srinivasagudi/Desktop/Jarvis-Hardware-Builder/agent.py) as `gpt-4o`.
- The code supports both the modern `openai` SDK interface and an older compatibility path.
- The generated project plan is saved as a plain text file in the repository root.

## Typical Workflow

1. Start the CLI or Streamlit app
2. Describe the hardware project you want to build
3. Review the generated plan and recommendations
4. Ask follow-up questions about parts, wiring, cost, power, tools, or assembly
5. Resume the same project later from saved history

## Future Improvements

- Configurable model selection through environment variables
- Better validation for missing or invalid user input
- Export formats such as Markdown or PDF
- More structured hardware bill-of-materials output
- Automated tests for the CLI and Streamlit flows

## License

View MIT License in [LICENSE](LICENSE) file.
