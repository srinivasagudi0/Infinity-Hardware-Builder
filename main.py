import os

from agent import (
    BUDGET_LEVELS,
    PROJECT_TEMPLATES,
    SKILL_LEVELS,
    STATUSES,
    answer_follow_up_like_a_human_mentor,
    build_full_project_plan,
    make_clarification_questions_for_project,
)
from exporter import export_project_in_every_format
from memory_db import MemoryDB


DB_PATH = os.getenv("MEMORY_DB_PATH", "memory.db")
db = MemoryDB(DB_PATH)


def check_environment_before_starting():
    if "OPENAI_API_KEY" not in os.environ:
        print("OPENAI_API_KEY not set. Running with local structured fallback mode.")
    else:
        print("OpenAI API key found. AI generation enabled.")
    print()
    return True


def choose_saved_project_session():
    all_projects = db.get_all_saved_projects()
    if not all_projects:
        return None
    print("Saved projects:")
    for index, project in enumerate(all_projects, 1):
        profile = project["project_profile"]
        print(
            f"[{index}] {project['project_name']} | {profile.get('template_type')} | "
            f"{profile.get('status')} | rev {project.get('revision_number', 1)}"
        )
    while True:
        choice = input("Choose a project number or type 'new': ").strip().lower()
        if choice == "new":
            return None
        if choice.isdigit():
            index = int(choice) - 1
            if 0 <= index < len(all_projects):
                return all_projects[index]["id"]
        print("Invalid choice.")


def ask_user_to_pick_an_option(prompt, options, default):
    print(f"{prompt} ({'/'.join(options)})")
    value = input(f"Default [{default}]: ").strip().lower()
    return value if value in options else default


def collect_project_details_from_user(existing=None):
    existing = existing or {}
    profile = dict(existing.get("project_profile", {}))
    inputs_json = dict(existing.get("inputs_json", {}))
    profile["name"] = input(f"Project name [{profile.get('name', '')}]: ").strip() or profile.get("name", "")
    profile["purpose"] = input(f"Purpose [{profile.get('purpose', '')}]: ").strip() or profile.get("purpose", "")
    profile["template_type"] = ask_user_to_pick_an_option("Template", PROJECT_TEMPLATES, profile.get("template_type", "custom"))
    profile["skill_level"] = ask_user_to_pick_an_option("Skill level", SKILL_LEVELS, profile.get("skill_level", "beginner"))
    profile["budget_mode"] = ask_user_to_pick_an_option("Budget mode", BUDGET_LEVELS, profile.get("budget_mode", "mid"))
    profile["status"] = ask_user_to_pick_an_option("Status", STATUSES, profile.get("status", "planned"))
    tags = input(f"Tags comma separated [{', '.join(profile.get('tags', []))}]: ").strip()
    profile["tags"] = [item.strip() for item in tags.split(",") if item.strip()] if tags else profile.get("tags", [])

    inputs_json["components"] = (
        input(f"Components [{inputs_json.get('components', '')}]: ").strip() or inputs_json.get("components", "")
    )
    inputs_json["specific_requirements"] = (
        input(f"Specific requirements [{inputs_json.get('specific_requirements', '')}]: ").strip()
        or inputs_json.get("specific_requirements", "")
    )
    inputs_json["constraints"] = (
        input(f"Constraints [{inputs_json.get('constraints', '')}]: ").strip() or inputs_json.get("constraints", "")
    )
    inputs_json["clarification_answers"] = inputs_json.get("clarification_answers", {})

    questions = make_clarification_questions_for_project(profile, inputs_json)
    for question in questions:
        answer = input(f"{question} ").strip()
        if answer:
            inputs_json["clarification_answers"][question] = answer
    return profile, inputs_json


def create_or_update_project_record(project_id=None):
    existing = db.get_project_by_id(project_id) if project_id else None
    profile, inputs_json = collect_project_details_from_user(existing)
    payload = build_full_project_plan(profile, inputs_json, attachments=existing["attachments"] if existing else [])
    if project_id:
        db.save_project_as_new_revision(
            project_id,
            payload["project_profile"],
            payload["inputs_json"],
            payload["artifacts_json"],
            payload["narrative_plan"],
            change_summary="CLI revision update",
        )
        return project_id
    return db.create_new_project_record(
        payload["project_profile"],
        payload["inputs_json"],
        payload["artifacts_json"],
        payload["narrative_plan"],
        change_summary="CLI initial creation",
    )


def show_project_summary_on_cli(project):
    profile = project["project_profile"]
    artifacts = project["artifacts_json"]
    print(f"\n=== {project['project_name']} ===")
    print(
        f"Template: {profile.get('template_type')} | Skill: {profile.get('skill_level')} | "
        f"Budget: {profile.get('budget_mode')} | Status: {profile.get('status')}"
    )
    print(f"Components: {project['inputs_json'].get('components', '')}")
    print(f"Requirements: {project['inputs_json'].get('specific_requirements', '')}")
    print("\nNarrative plan:")
    print(project.get("narrative_plan", ""))
    print("\nBOM:")
    for item in artifacts.get("bom", []):
        print(
            f"- {item.get('name')}: qty {item.get('quantity', 1)} | "
            f"${item.get('total_cost_estimate', 0)}"
        )
    print("\nSuggested follow-ups:")
    for item in artifacts.get("suggested_follow_ups", []):
        print(f"- {item}")


def keep_chatting_about_the_project(project_id):
    while True:
        question = input("\nAsk a follow-up question, type 'export', 'edit', or 'exit': ").strip()
        if question.lower() == "exit":
            break
        if question.lower() == "edit":
            create_or_update_project_record(project_id)
            show_project_summary_on_cli(db.get_project_by_id(project_id))
            continue
        if question.lower() == "export":
            exports = export_project_in_every_format(db.get_project_by_id(project_id))
            for export_type, path in exports.items():
                print(f"{export_type}: {path}")
            continue

        project = db.get_project_by_id(project_id)
        answer = answer_follow_up_like_a_human_mentor(question, db.build_full_project_context_for_ai(project_id), project["artifacts_json"])
        db.save_follow_up_answer(project_id, question, answer)
        print(answer)


def run_the_cli_app():
    print("Welcome to Hardware Builder V2")
    print("Streamlit is the primary UI, but this CLI supports planning, revisions, follow-ups, and exports.\n")
    project_id = choose_saved_project_session()
    if project_id is None:
        project_id = create_or_update_project_record()
    else:
        selected = input("Type 'edit' to create a new revision, or press Enter to continue: ").strip().lower()
        if selected == "edit":
            create_or_update_project_record(project_id)
    show_project_summary_on_cli(db.get_project_by_id(project_id))
    keep_chatting_about_the_project(project_id)


if __name__ == "__main__":
    try:
        check_environment_before_starting()
        run_the_cli_app()
    except KeyboardInterrupt:
        print("\nProgram interrupted. Goodbye!")
