import json
import os
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path


DEFAULT_ARTIFACTS = {
    "bom": [],
    "wiring_plan": [],
    "power_checks": [],
    "safety_warnings": [],
    "tools": [],
    "build_steps": [],
    "testing_checklist": [],
    "suggested_follow_ups": [],
    "resources": [],
    "compatibility_notes": [],
    "estimated_cost": {"currency": "USD", "total": 0.0, "notes": ""},
}

DEFAULT_PROFILE = {
    "name": "",
    "purpose": "",
    "skill_level": "beginner",
    "budget_mode": "mid",
    "template_type": "custom",
    "status": "draft",
    "tags": [],
}


class MemoryDB:
    def __init__(self, db_name="memory.db", project_files_dir=None):
        self.db_name = db_name
        self.project_files_dir = Path(project_files_dir or os.getenv("PROJECT_FILES_DIR", "project_files"))
        self.project_files_dir.mkdir(parents=True, exist_ok=True)
        self.set_up_database_tables()

    def open_database_connection_for_memory(self):
        conn = sqlite3.connect(self.db_name)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def set_up_database_tables(self):
        with self.open_database_connection_for_memory() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS projects (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_name TEXT NOT NULL,
                    components TEXT,
                    project_purpose TEXT,
                    specific_requirements TEXT,
                    response TEXT,
                    timestamp DATETIME NOT NULL,
                    project_profile TEXT NOT NULL DEFAULT '{}',
                    inputs_json TEXT NOT NULL DEFAULT '{}',
                    artifacts_json TEXT NOT NULL DEFAULT '{}',
                    narrative_plan TEXT NOT NULL DEFAULT '',
                    revision_number INTEGER NOT NULL DEFAULT 1,
                    parent_revision_id INTEGER,
                    updated_at DATETIME NOT NULL DEFAULT '',
                    status TEXT NOT NULL DEFAULT 'draft',
                    template_type TEXT NOT NULL DEFAULT 'custom'
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS follow_ups (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER NOT NULL,
                    question TEXT NOT NULL,
                    response TEXT,
                    timestamp DATETIME NOT NULL,
                    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS project_revisions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER NOT NULL,
                    revision_number INTEGER NOT NULL,
                    parent_revision_id INTEGER,
                    project_profile TEXT NOT NULL,
                    inputs_json TEXT NOT NULL,
                    artifacts_json TEXT NOT NULL,
                    narrative_plan TEXT NOT NULL,
                    change_summary TEXT NOT NULL DEFAULT '',
                    created_at DATETIME NOT NULL,
                    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS attachments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER NOT NULL,
                    revision_id INTEGER,
                    original_name TEXT NOT NULL,
                    stored_path TEXT NOT NULL,
                    mime_type TEXT,
                    note TEXT NOT NULL DEFAULT '',
                    uploaded_at DATETIME NOT NULL,
                    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
                    FOREIGN KEY (revision_id) REFERENCES project_revisions(id) ON DELETE SET NULL
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS project_tags (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER NOT NULL,
                    tag TEXT NOT NULL,
                    UNIQUE(project_id, tag),
                    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
                )
                """
            )
            self.add_missing_v2_columns_to_old_projects(cursor)

    def add_missing_v2_columns_to_old_projects(self, cursor):
        cursor.execute("PRAGMA table_info(projects)")
        columns = {row["name"] for row in cursor.fetchall()}
        desired_columns = {
            "project_profile": "TEXT NOT NULL DEFAULT '{}'",
            "inputs_json": "TEXT NOT NULL DEFAULT '{}'",
            "artifacts_json": "TEXT NOT NULL DEFAULT '{}'",
            "narrative_plan": "TEXT NOT NULL DEFAULT ''",
            "revision_number": "INTEGER NOT NULL DEFAULT 1",
            "parent_revision_id": "INTEGER",
            "updated_at": "DATETIME NOT NULL DEFAULT ''",
            "status": "TEXT NOT NULL DEFAULT 'draft'",
            "template_type": "TEXT NOT NULL DEFAULT 'custom'",
        }
        for column, definition in desired_columns.items():
            if column not in columns:
                cursor.execute(f"ALTER TABLE projects ADD COLUMN {column} {definition}")

    def get_time_right_now(self):
        return datetime.now().isoformat()

    def turn_saved_json_into_python_data(self, raw_value, default):
        if not raw_value:
            return json.loads(json.dumps(default))
        try:
            loaded = json.loads(raw_value)
        except (TypeError, json.JSONDecodeError):
            return json.loads(json.dumps(default))
        if isinstance(default, dict) and not isinstance(loaded, dict):
            return json.loads(json.dumps(default))
        if isinstance(default, list) and not isinstance(loaded, list):
            return json.loads(json.dumps(default))
        return loaded

    def turn_python_data_into_json_text(self, value):
        return json.dumps(value, ensure_ascii=True, sort_keys=True)

    def make_project_row_ready_for_app(self, row):
        if not row:
            return None

        project = dict(row)
        profile = self.turn_saved_json_into_python_data(project.get("project_profile"), DEFAULT_PROFILE)
        inputs_json = self.turn_saved_json_into_python_data(project.get("inputs_json"), {})
        artifacts_json = self.turn_saved_json_into_python_data(project.get("artifacts_json"), DEFAULT_ARTIFACTS)

        if not any(artifacts_json.values()) and project.get("response"):
            artifacts_json = self.build_old_style_artifacts_for_project(project)

        profile.setdefault("name", project.get("project_name") or "")
        profile.setdefault("purpose", project.get("project_purpose") or "")
        profile.setdefault("skill_level", "beginner")
        profile.setdefault("budget_mode", "mid")
        profile.setdefault("template_type", project.get("template_type") or "custom")
        profile.setdefault("status", project.get("status") or "draft")
        profile["tags"] = self.get_project_tags(project["id"])

        if not inputs_json:
            inputs_json = self.build_old_style_inputs_for_project(project)

        project["project_profile"] = profile
        project["inputs_json"] = inputs_json
        project["artifacts_json"] = artifacts_json
        project["narrative_plan"] = project.get("narrative_plan") or project.get("response") or ""
        project["response"] = project.get("response") or project["narrative_plan"]
        project["tags"] = profile["tags"]
        project["attachments"] = self.get_saved_attachments(project["id"])
        project["revision_history"] = self.get_revision_history_for_project(project["id"])
        return project

    def build_old_style_inputs_for_project(self, project):
        return {
            "components": project.get("components", ""),
            "constraints": "",
            "specific_requirements": project.get("specific_requirements", ""),
            "clarification_answers": {},
        }

    def build_old_style_artifacts_for_project(self, project):
        response = project.get("response") or ""
        components = [item.strip() for item in (project.get("components") or "").split(",") if item.strip()]
        bom = [
            {
                "name": component,
                "quantity": 1,
                "unit_cost_estimate": 0.0,
                "total_cost_estimate": 0.0,
                "purchase_link": "",
                "source_note": "Migrated from V1 free-form components list.",
            }
            for component in components
        ]
        return {
            **json.loads(json.dumps(DEFAULT_ARTIFACTS)),
            "bom": bom,
            "build_steps": [line.strip("- ").strip() for line in response.splitlines() if line.strip()][:8],
            "compatibility_notes": ["Legacy project imported from V1 free-form plan."],
            "suggested_follow_ups": [
                "Do you want a more detailed wiring guide?",
                "Should I optimize the plan for budget or reliability?",
            ],
            "resources": [],
            "estimated_cost": {"currency": "USD", "total": 0.0, "notes": "No pricing data stored in V1."},
        }

    def get_project_files_folder(self, project_id):
        path = self.project_files_dir / f"project_{project_id}"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def create_new_project_record(self, project_profile, inputs_json, artifacts_json, narrative_plan, change_summary="Initial plan"):
        timestamp = self.get_time_right_now()
        profile = {**DEFAULT_PROFILE, **(project_profile or {})}
        inputs_payload = inputs_json or {}
        artifacts_payload = {**json.loads(json.dumps(DEFAULT_ARTIFACTS)), **(artifacts_json or {})}
        with self.open_database_connection_for_memory() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO projects (
                    project_name, components, project_purpose, specific_requirements, response, timestamp,
                    project_profile, inputs_json, artifacts_json, narrative_plan, revision_number,
                    parent_revision_id, updated_at, status, template_type
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    profile.get("name", ""),
                    inputs_payload.get("components", ""),
                    profile.get("purpose", ""),
                    inputs_payload.get("specific_requirements", ""),
                    narrative_plan,
                    timestamp,
                    self.turn_python_data_into_json_text(profile),
                    self.turn_python_data_into_json_text(inputs_payload),
                    self.turn_python_data_into_json_text(artifacts_payload),
                    narrative_plan,
                    1,
                    None,
                    timestamp,
                    profile.get("status", "draft"),
                    profile.get("template_type", "custom"),
                ),
            )
            project_id = cursor.lastrowid
        self.replace_project_tags(project_id, profile.get("tags", []))
        self.save_revision_snapshot_record(project_id, 1, None, profile, inputs_payload, artifacts_payload, narrative_plan, change_summary)
        return project_id

    def save_project_as_new_revision(self, project_id, project_profile, inputs_json, artifacts_json, narrative_plan, change_summary="Updated project"):
        current = self.get_project_by_id(project_id)
        if not current:
            raise ValueError(f"Project {project_id} not found.")
        new_revision = current["revision_number"] + 1
        timestamp = self.get_time_right_now()
        profile = {**current["project_profile"], **(project_profile or {})}
        inputs_payload = {**current["inputs_json"], **(inputs_json or {})}
        artifacts_payload = json.loads(json.dumps(DEFAULT_ARTIFACTS))
        artifacts_payload.update(current["artifacts_json"])
        if artifacts_json:
            artifacts_payload.update(artifacts_json)
        with self.open_database_connection_for_memory() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE projects
                SET project_name = ?, components = ?, project_purpose = ?, specific_requirements = ?, response = ?,
                    project_profile = ?, inputs_json = ?, artifacts_json = ?, narrative_plan = ?, revision_number = ?,
                    parent_revision_id = ?, updated_at = ?, status = ?, template_type = ?
                WHERE id = ?
                """,
                (
                    profile.get("name", ""),
                    inputs_payload.get("components", ""),
                    profile.get("purpose", ""),
                    inputs_payload.get("specific_requirements", ""),
                    narrative_plan,
                    self.turn_python_data_into_json_text(profile),
                    self.turn_python_data_into_json_text(inputs_payload),
                    self.turn_python_data_into_json_text(artifacts_payload),
                    narrative_plan,
                    new_revision,
                    current["revision_history"][-1]["id"] if current["revision_history"] else None,
                    timestamp,
                    profile.get("status", "draft"),
                    profile.get("template_type", "custom"),
                    project_id,
                ),
            )
        self.replace_project_tags(project_id, profile.get("tags", []))
        self.save_revision_snapshot_record(
            project_id,
            new_revision,
            current["revision_history"][-1]["id"] if current["revision_history"] else None,
            profile,
            inputs_payload,
            artifacts_payload,
            narrative_plan,
            change_summary,
        )
        return new_revision

    def save_revision_snapshot_record(self, project_id, revision_number, parent_revision_id, profile, inputs_json, artifacts_json, narrative_plan, change_summary):
        with self.open_database_connection_for_memory() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO project_revisions (
                    project_id, revision_number, parent_revision_id, project_profile, inputs_json,
                    artifacts_json, narrative_plan, change_summary, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    project_id,
                    revision_number,
                    parent_revision_id,
                    self.turn_python_data_into_json_text(profile),
                    self.turn_python_data_into_json_text(inputs_json),
                    self.turn_python_data_into_json_text(artifacts_json),
                    narrative_plan,
                    change_summary,
                    self.get_time_right_now(),
                ),
            )
            return cursor.lastrowid

    def save_legacy_project_record(self, project_name, components, project_purpose, specific_requirements, response):
        project_profile = {
            "name": project_name,
            "purpose": project_purpose,
            "skill_level": "beginner",
            "budget_mode": "mid",
            "template_type": "custom",
            "status": "planned",
            "tags": [],
        }
        inputs_json = {
            "components": components,
            "constraints": "",
            "specific_requirements": specific_requirements,
            "clarification_answers": {},
        }
        artifacts_json = self.build_old_style_artifacts_for_project(
            {
                "components": components,
                "response": response,
            }
        )
        return self.create_new_project_record(project_profile, inputs_json, artifacts_json, response)

    def get_project_by_id(self, project_id):
        with self.open_database_connection_for_memory() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM projects WHERE id = ?", (project_id,))
            return self.make_project_row_ready_for_app(cursor.fetchone())

    def get_all_saved_projects(self):
        with self.open_database_connection_for_memory() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM projects ORDER BY updated_at DESC, id DESC")
            return [self.make_project_row_ready_for_app(row) for row in cursor.fetchall()]

    def search_projects_with_filters(self, query="", status=None, template_type=None, tag=None):
        projects = self.get_all_saved_projects()
        query = (query or "").strip().lower()
        filtered = []
        for project in projects:
            if query:
                haystack = " ".join(
                    [
                        project.get("project_name", ""),
                        project["project_profile"].get("purpose", ""),
                        project["inputs_json"].get("components", ""),
                        project["inputs_json"].get("specific_requirements", ""),
                    ]
                ).lower()
                if query not in haystack:
                    continue
            if status and project["project_profile"].get("status") != status:
                continue
            if template_type and project["project_profile"].get("template_type") != template_type:
                continue
            if tag and tag not in project.get("tags", []):
                continue
            filtered.append(project)
        return filtered

    def find_exact_matching_project(self, project_name, components, project_purpose, specific_requirements):
        matches = self.search_projects_with_filters(query=project_name)
        for project in matches:
            if (
                project.get("project_name") == project_name
                and project["inputs_json"].get("components") == components
                and project["project_profile"].get("purpose") == project_purpose
                and project["inputs_json"].get("specific_requirements") == specific_requirements
            ):
                return project
        return None

    def save_follow_up_answer(self, project_id, question, response):
        with self.open_database_connection_for_memory() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO follow_ups (project_id, question, response, timestamp)
                VALUES (?, ?, ?, ?)
                """,
                (project_id, question, response, self.get_time_right_now()),
            )

    def get_follow_up_history(self, project_id):
        with self.open_database_connection_for_memory() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM follow_ups WHERE project_id = ? ORDER BY id ASC", (project_id,))
            return [dict(row) for row in cursor.fetchall()]

    def save_uploaded_file_for_project(self, project_id, original_name, content, mime_type="", note="", revision_id=None):
        project_dir = self.get_project_files_folder(project_id)
        safe_name = "".join(ch if ch.isalnum() or ch in ("-", "_", ".") else "_" for ch in original_name).strip("._")
        safe_name = safe_name or "attachment"
        stored_name = f"{datetime.now().strftime('%Y%m%d%H%M%S%f')}_{safe_name}"
        stored_path = project_dir / stored_name
        with open(stored_path, "wb") as file_handle:
            file_handle.write(content)
        with self.open_database_connection_for_memory() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO attachments (project_id, revision_id, original_name, stored_path, mime_type, note, uploaded_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (project_id, revision_id, original_name, str(stored_path), mime_type, note, self.get_time_right_now()),
            )
            return cursor.lastrowid

    def get_saved_attachments(self, project_id):
        with self.open_database_connection_for_memory() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM attachments WHERE project_id = ? ORDER BY uploaded_at DESC", (project_id,))
            return [dict(row) for row in cursor.fetchall()]

    def replace_project_tags(self, project_id, tags):
        cleaned_tags = sorted({tag.strip().lower() for tag in tags if tag and tag.strip()})
        with self.open_database_connection_for_memory() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM project_tags WHERE project_id = ?", (project_id,))
            for tag in cleaned_tags:
                cursor.execute("INSERT OR IGNORE INTO project_tags (project_id, tag) VALUES (?, ?)", (project_id, tag))

    def get_project_tags(self, project_id):
        with self.open_database_connection_for_memory() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT tag FROM project_tags WHERE project_id = ? ORDER BY tag ASC", (project_id,))
            return [row["tag"] for row in cursor.fetchall()]

    def get_revision_history_for_project(self, project_id):
        with self.open_database_connection_for_memory() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM project_revisions WHERE project_id = ? ORDER BY revision_number ASC",
                (project_id,),
            )
            revisions = []
            for row in cursor.fetchall():
                revision = dict(row)
                revision["project_profile"] = self.turn_saved_json_into_python_data(revision.get("project_profile"), DEFAULT_PROFILE)
                revision["inputs_json"] = self.turn_saved_json_into_python_data(revision.get("inputs_json"), {})
                revision["artifacts_json"] = self.turn_saved_json_into_python_data(revision.get("artifacts_json"), DEFAULT_ARTIFACTS)
                revisions.append(revision)
            return revisions

    def build_full_project_context_for_ai(self, project_id):
        project = self.get_project_by_id(project_id)
        if not project:
            return ""
        lines = [
            f"Project Name: {project['project_name']}",
            f"Template: {project['project_profile'].get('template_type', 'custom')}",
            f"Purpose: {project['project_profile'].get('purpose', '')}",
            f"Skill Level: {project['project_profile'].get('skill_level', 'beginner')}",
            f"Budget Mode: {project['project_profile'].get('budget_mode', 'mid')}",
            f"Status: {project['project_profile'].get('status', 'draft')}",
            f"Components: {project['inputs_json'].get('components', '')}",
            f"Specific Requirements: {project['inputs_json'].get('specific_requirements', '')}",
            f"Constraints: {project['inputs_json'].get('constraints', '')}",
            f"Narrative Plan: {project.get('narrative_plan', '')}",
        ]

        bom = project["artifacts_json"].get("bom", [])
        if bom:
            lines.append("Bill of Materials:")
            for item in bom:
                lines.append(f"- {item.get('name', 'Unknown')}: qty {item.get('quantity', 1)}")

        for section in ("compatibility_notes", "power_checks", "safety_warnings"):
            values = project["artifacts_json"].get(section, [])
            if values:
                lines.append(section.replace("_", " ").title() + ":")
                for value in values:
                    if isinstance(value, dict):
                        lines.append(f"- {value.get('title', value.get('component', 'Item'))}: {value.get('details', value)}")
                    else:
                        lines.append(f"- {value}")

        follow_ups = self.get_follow_up_history(project_id)
        if follow_ups:
            lines.append("Follow-up History:")
            for item in follow_ups:
                lines.append(f"Q: {item['question']}")
                lines.append(f"A: {item['response']}")
        return "\n".join(lines)

    def count_saved_projects(self):
        with self.open_database_connection_for_memory() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM projects")
            return cursor.fetchone()[0]

    def get_most_recent_project(self):
        projects = self.get_all_saved_projects()
        return projects[0] if projects else None

    def delete_everything_for_tests(self):
        with self.open_database_connection_for_memory() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM attachments")
            cursor.execute("DELETE FROM project_tags")
            cursor.execute("DELETE FROM follow_ups")
            cursor.execute("DELETE FROM project_revisions")
            cursor.execute("DELETE FROM projects")
        if self.project_files_dir.exists():
            for child in self.project_files_dir.iterdir():
                if child.is_dir():
                    shutil.rmtree(child, ignore_errors=True)
