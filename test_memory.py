import os
import shutil

from agent import build_full_project_plan
from exporter import export_project_in_every_format
from memory_db import MemoryDB


def run_all_memory_database_tests(db_path="test_memory.db", files_dir="test_project_files"):
    if os.path.exists(db_path):
        os.remove(db_path)
    if os.path.exists(files_dir):
        shutil.rmtree(files_dir)

    db = MemoryDB(db_path, project_files_dir=files_dir)

    project_profile = {
        "name": "Smart Light",
        "purpose": "Home automation",
        "skill_level": "beginner",
        "budget_mode": "mid",
        "template_type": "home automation",
        "status": "planned",
        "tags": ["lighting", "wifi"],
    }
    inputs_json = {
        "components": "Arduino, LED strip, relay module",
        "constraints": "Must fit in a wall box",
        "specific_requirements": "Wifi controlled, mobile app",
        "clarification_answers": {"Need offline fallback?": "Yes"},
    }

    payload = build_full_project_plan(project_profile, inputs_json)
    project_id = db.create_new_project_record(
        payload["project_profile"],
        payload["inputs_json"],
        payload["artifacts_json"],
        payload["narrative_plan"],
    )
    assert isinstance(project_id, int) and project_id > 0

    db.save_follow_up_answer(project_id, "Can I use Raspberry Pi?", "Yes, but it is likely overpowered for a simple switch.")
    attachment_id = db.save_uploaded_file_for_project(
        project_id,
        "datasheet.txt",
        b"relay coil current: 70mA",
        "text/plain",
        note="Relay datasheet excerpt",
    )
    assert attachment_id > 0

    project = db.get_project_by_id(project_id)
    assert project is not None
    assert project["project_profile"]["template_type"] == "home automation"
    assert "bom" in project["artifacts_json"]
    assert len(project["attachments"]) == 1
    assert project["tags"] == ["lighting", "wifi"]

    results = db.search_projects_with_filters(query="Smart", status="planned", template_type="home automation", tag="wifi")
    assert len(results) == 1

    db.save_project_as_new_revision(
        project_id,
        {**project["project_profile"], "status": "in progress"},
        {**project["inputs_json"], "constraints": "Indoor only"},
        {"estimated_cost": {"total": 88.5}},
        project["narrative_plan"] + "\n\nRevision note: moved to enclosure planning.",
        change_summary="Moved to enclosure planning",
    )
    updated = db.get_project_by_id(project_id)
    assert updated["revision_number"] == 2
    assert updated["project_profile"]["status"] == "in progress"
    assert len(updated["revision_history"]) == 2
    assert updated["artifacts_json"]["estimated_cost"]["total"] == 88.5
    assert updated["artifacts_json"]["estimated_cost"]["currency"] == "USD"
    assert "notes" in updated["artifacts_json"]["estimated_cost"]

    context = db.build_full_project_context_for_ai(project_id)
    assert "Project Name: Smart Light" in context
    assert "Bill of Materials:" in context
    assert "Follow-up History:" in context

    exports = export_project_in_every_format(updated)
    for path in exports.values():
        assert os.path.exists(path)

    duplicate = db.find_exact_matching_project(
        "Smart Light",
        "Arduino, LED strip, relay module",
        "Home automation",
        "Wifi controlled, mobile app",
    )
    assert duplicate is not None
    assert duplicate["id"] == project_id

    legacy_db = MemoryDB("test_legacy.db", project_files_dir="test_legacy_files")
    legacy_id = legacy_db.save_legacy_project_record(
        project_name="Legacy Project",
        components="Arduino, Sensor",
        project_purpose="Learning",
        specific_requirements="Simple demo",
        response="Legacy free-form answer",
    )
    migrated = legacy_db.get_project_by_id(legacy_id)
    assert migrated["artifacts_json"]["bom"]
    assert migrated["narrative_plan"] == "Legacy free-form answer"

    print("All V2 memory tests passed.")


if __name__ == "__main__":
    run_all_memory_database_tests()
