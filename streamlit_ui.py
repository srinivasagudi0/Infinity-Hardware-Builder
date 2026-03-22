import csv
import io
import os
from pathlib import Path

import streamlit as st

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

TEMPLATE_DESCRIPTIONS = {
    "custom": "Best for open-ended projects where the parts or goals are still moving.",
    "robot": "Good for motion, sensors, control loops, and actuator safety.",
    "home automation": "Good for relays, controllers, power switching, and remote control.",
    "sensor node": "Good for telemetry, battery life, and compact monitoring builds.",
    "weather station": "Good for outdoor sensing, enclosure planning, and long-term data collection.",
}

DIFFICULTY_BADGES = {
    "beginner": "🟢 Beginner",
    "intermediate": "🟡 Intermediate",
    "advanced": "🔴 Advanced",
}


def make_blank_project_profile():
    return {
        "name": "",
        "purpose": "",
        "skill_level": "beginner",
        "budget_mode": "mid",
        "template_type": "custom",
        "status": "draft",
        "tags": [],
    }


def make_blank_project_inputs():
    return {
        "components": "",
        "constraints": "",
        "specific_requirements": "",
        "clarification_answers": {},
    }


def reset_the_draft_workspace():
    st.session_state.selected_project_id = None
    st.session_state.draft_profile = make_blank_project_profile()
    st.session_state.draft_inputs = make_blank_project_inputs()


def set_up_streamlit_page_state():
    st.session_state.setdefault("selected_project_id", None)
    st.session_state.setdefault("draft_profile", make_blank_project_profile())
    st.session_state.setdefault("draft_inputs", make_blank_project_inputs())
    st.session_state.setdefault("dark_mode_on", True)


def paint_the_page_with_better_colors_and_layout():
    page_is_dark = st.session_state.get("dark_mode_on", False)
    if page_is_dark:
        style_block = """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;700&family=IBM+Plex+Sans:wght@400;500;600&display=swap');
        :root {
            --jarvis-bg: #0b0f14;
            --jarvis-bg-soft: #10161d;
            --jarvis-panel: rgba(21, 27, 35, 0.95);
            --jarvis-panel-strong: rgba(17, 22, 29, 0.98);
            --jarvis-ink: #e6edf3;
            --jarvis-soft-ink: #9aabb8;
            --jarvis-accent: #4fd1c5;
            --jarvis-accent-warm: #ff8f5a;
            --jarvis-line: rgba(230, 237, 243, 0.10);
            --jarvis-shadow: 0 18px 40px rgba(0, 0, 0, 0.34);
        }
        .stApp {
            background:
                radial-gradient(circle at top right, rgba(79, 209, 197, 0.10), transparent 24%),
                radial-gradient(circle at top left, rgba(255, 143, 90, 0.08), transparent 20%),
                linear-gradient(180deg, #0b0f14 0%, #10161d 100%);
            color: var(--jarvis-ink);
            font-family: 'IBM Plex Sans', sans-serif;
        }
        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #10161d 0%, #0b0f14 100%);
            border-right: 1px solid rgba(255,255,255,0.06);
            min-width: 220px !important;
            max-width: 220px !important;
        }
        </style>
        """
    else:
        style_block = """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;700&family=IBM+Plex+Sans:wght@400;500;600&display=swap');
        :root {
            --jarvis-bg: #eef2f1;
            --jarvis-bg-soft: #f6f3ee;
            --jarvis-panel: rgba(255, 255, 255, 0.92);
            --jarvis-panel-strong: rgba(255, 252, 248, 0.98);
            --jarvis-ink: #16232b;
            --jarvis-soft-ink: #51636d;
            --jarvis-accent: #1f6a70;
            --jarvis-accent-warm: #bf5a2a;
            --jarvis-line: rgba(22, 35, 43, 0.10);
            --jarvis-shadow: 0 20px 44px rgba(22, 35, 43, 0.10);
        }
        .stApp {
            background:
                radial-gradient(circle at top left, rgba(31, 106, 112, 0.10), transparent 24%),
                radial-gradient(circle at top right, rgba(191, 90, 42, 0.10), transparent 28%),
                linear-gradient(180deg, #eef2f1 0%, #f8f6f2 46%, #f1ece5 100%);
            color: var(--jarvis-ink);
            font-family: 'IBM Plex Sans', sans-serif;
        }
        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #16232b 0%, #1d3340 100%);
            border-right: 1px solid rgba(255,255,255,0.06);
            min-width: 220px !important;
            max-width: 220px !important;
        }
        </style>
        """

    st.markdown(
        style_block
        + """
        <style>
        .stApp, .stApp p, .stApp li, .stApp label, .stApp span, .stApp div, .stMarkdown, .stMarkdown * {
            color: var(--jarvis-ink);
        }
        [data-testid="stSidebar"] * {
            color: #eef3f7 !important;
        }
        h1, h2, h3, .jarvis-title {
            font-family: 'Space Grotesk', sans-serif !important;
            color: var(--jarvis-ink);
            letter-spacing: -0.035em;
        }
        h1 { font-size: 40px !important; line-height: 1.04; }
        h2 { font-size: 28px !important; line-height: 1.12; }
        h3 { font-size: 20px !important; line-height: 1.2; }
        .jarvis-hero {
            background:
                radial-gradient(circle at top right, rgba(79, 209, 197, 0.08), transparent 22%),
                linear-gradient(135deg, var(--jarvis-panel-strong), var(--jarvis-panel));
            border: 1px solid var(--jarvis-line);
            border-radius: 30px;
            padding: 1.4rem 1.5rem;
            box-shadow: var(--jarvis-shadow);
            animation: jarvisFadeUp 420ms ease-out;
        }
        .jarvis-kicker {
            text-transform: uppercase;
            letter-spacing: 0.14em;
            font-size: 13px;
            font-weight: 700;
            color: var(--jarvis-accent) !important;
        }
        .jarvis-subtitle {
            color: var(--jarvis-soft-ink) !important;
            font-size: 16px;
            margin-top: 0.35rem;
        }
        .jarvis-main-builder {
            background: linear-gradient(180deg, var(--jarvis-panel-strong), var(--jarvis-panel));
            border: 1px solid var(--jarvis-line);
            border-radius: 28px;
            padding: 1.25rem;
            box-shadow: 0 30px 70px rgba(0,0,0,0.10);
            animation: jarvisFadeUp 460ms ease-out;
        }
        .jarvis-preview-panel {
            background: linear-gradient(180deg, var(--jarvis-panel-strong), var(--jarvis-panel));
            border: 1px solid var(--jarvis-line);
            border-radius: 28px;
            padding: 1.15rem;
            box-shadow: var(--jarvis-shadow);
            animation: jarvisFadeUp 500ms ease-out;
        }
        .jarvis-stat-pill {
            display: flex;
            align-items: center;
            gap: 0.6rem;
            background: var(--jarvis-panel-strong);
            border: 1px solid var(--jarvis-line);
            border-radius: 999px;
            padding: 0.75rem 0.95rem;
            box-shadow: 0 10px 24px rgba(0,0,0,0.06);
            transition: transform 180ms ease, box-shadow 180ms ease;
            animation: jarvisPopIn 480ms ease-out;
        }
        .jarvis-stat-pill:hover, .jarvis-lift-card:hover {
            transform: translateY(-3px);
            box-shadow: 0 14px 30px rgba(0,0,0,0.12);
        }
        .jarvis-stat-icon {
            font-size: 1.05rem;
        }
        .jarvis-stat-value {
            font-weight: 700;
            font-size: 15px;
        }
        .jarvis-stat-note {
            color: var(--jarvis-soft-ink) !important;
            font-size: 13px;
        }
        .jarvis-chip-row {
            display: flex;
            flex-wrap: wrap;
            gap: 0.45rem;
            margin-top: 0.65rem;
        }
        .jarvis-chip {
            background: rgba(79, 209, 197, 0.10);
            color: var(--jarvis-accent) !important;
            border: 1px solid rgba(79, 209, 197, 0.22);
            border-radius: 999px;
            padding: 0.30rem 0.72rem;
            font-size: 13px;
            font-weight: 600;
        }
        .jarvis-section-box, .jarvis-lift-card {
            background: var(--jarvis-panel);
            border: 1px solid var(--jarvis-line);
            border-radius: 20px;
            padding: 0.95rem 1rem;
            box-shadow: 0 10px 22px rgba(0,0,0,0.05);
            transition: transform 180ms ease, box-shadow 180ms ease;
        }
        .jarvis-helper-box {
            background: linear-gradient(135deg, rgba(79, 209, 197, 0.10), rgba(255, 143, 90, 0.10));
            border-left: 4px solid var(--jarvis-accent-warm);
            border-radius: 18px;
            padding: 0.9rem 1rem;
            margin-bottom: 1rem;
        }
        .jarvis-progress-shell {
            width: 100%;
            height: 10px;
            border-radius: 999px;
            background: rgba(128, 128, 128, 0.16);
            overflow: hidden;
            margin: 0.55rem 0 0.35rem 0;
        }
        .jarvis-progress-fill {
            height: 100%;
            border-radius: 999px;
            background: linear-gradient(90deg, var(--jarvis-accent), var(--jarvis-accent-warm));
            transition: width 260ms ease;
        }
        .jarvis-empty-preview {
            display: flex;
            align-items: center;
            justify-content: center;
            min-height: 330px;
            text-align: center;
            border: 1px dashed var(--jarvis-line);
            border-radius: 24px;
            background: rgba(255,255,255,0.05);
        }
        .stButton > button, .stDownloadButton > button {
            border-radius: 999px;
            padding: 0.62rem 1rem;
            font-weight: 700;
            border: 1px solid var(--jarvis-line);
            background: linear-gradient(180deg, var(--jarvis-panel-strong), var(--jarvis-panel));
            color: var(--jarvis-ink);
            transition: transform 160ms ease, box-shadow 160ms ease, filter 160ms ease;
        }
        .stButton > button:hover, .stDownloadButton > button:hover {
            transform: translateY(-2px);
            box-shadow: 0 12px 28px rgba(0,0,0,0.14);
            filter: saturate(1.05);
        }
        .stButton > button[kind="primary"] {
            background: linear-gradient(180deg, var(--jarvis-accent-warm), #9e461f);
            color: white;
            border: none;
            box-shadow: 0 12px 24px rgba(191, 90, 42, 0.28);
        }
        .stTextInput input,
        .stTextArea textarea,
        .stSelectbox div[data-baseweb="select"] > div {
            background: var(--jarvis-panel-strong) !important;
            color: var(--jarvis-ink) !important;
            border: 1px solid var(--jarvis-line) !important;
        }
        .stTabs [data-baseweb="tab-list"] { gap: 0.5rem; }
        .stTabs [data-baseweb="tab"] {
            border-radius: 999px;
            border: 1px solid var(--jarvis-line);
            background: var(--jarvis-panel);
            color: var(--jarvis-ink) !important;
            font-weight: 600;
            padding: 0.44rem 0.88rem;
            height: auto;
        }
        .stTabs [aria-selected="true"] {
            background: rgba(79, 209, 197, 0.14) !important;
            color: var(--jarvis-accent) !important;
        }
        [data-testid="stExpander"] {
            background: var(--jarvis-panel);
            border: 1px solid var(--jarvis-line);
            border-radius: 18px;
        }
        [data-testid="stExpander"] summary, [data-testid="stExpander"] summary * {
            color: var(--jarvis-ink) !important;
        }
        .block-container {
            padding-top: 1.1rem;
            padding-bottom: 1.2rem;
            max-width: 1380px;
        }
        @keyframes jarvisFadeUp {
            from { opacity: 0; transform: translateY(8px); }
            to { opacity: 1; transform: translateY(0); }
        }
        @keyframes jarvisPopIn {
            from { opacity: 0; transform: scale(0.985) translateY(4px); }
            to { opacity: 1; transform: scale(1) translateY(0); }
        }
        @media (max-width: 900px) {
            [data-testid="stSidebar"] {
                min-width: 220px !important;
                max-width: 220px !important;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def show_main_header_section():
    st.markdown(
        """
        <div class="jarvis-hero">
            <div class="jarvis-kicker">Jarvis Hardware Builder</div>
            <h1>Describe your build. Get a full hardware plan.</h1>
            <p class="jarvis-subtitle">
                AI generates wiring guidance, parts lists, safety notes, budget estimates,
                and step-by-step instructions from a simple project brief.
            </p>
            <div class="jarvis-chip-row">
                <span class="jarvis-chip">🧹 Clear text</span>
                <span class="jarvis-chip">⚡ Quick builder</span>
                <span class="jarvis-chip">💾 Saved revisions</span>
                <span class="jarvis-chip">🎞 Animated panels</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def load_selected_project_into_the_draft(project):
    st.session_state.selected_project_id = project["id"]
    st.session_state.draft_profile = dict(project["project_profile"])
    st.session_state.draft_inputs = dict(project["inputs_json"])


def make_sidebar_project_label(project):
    profile = project["project_profile"]
    return f"{project['project_name']} | {profile.get('template_type')} | rev {project.get('revision_number', 1)}"


def show_sidebar_project_shelf():
    st.sidebar.markdown("## Project Shelf")
    st.sidebar.caption("Keep the left side compact. Open a project or start fresh.")
    #st.session_state.dark_mode_on = st.sidebar.toggle("Dark mode", value=st.session_state.get("dark_mode_on", False))

    search_text = st.sidebar.text_input("Search")
    status_filter = st.sidebar.selectbox("Status", ["All"] + STATUSES)
    template_filter = st.sidebar.selectbox("Template", ["All"] + PROJECT_TEMPLATES)
    all_tags = sorted({tag for project in db.get_all_saved_projects() for tag in project.get("tags", [])})
    tag_filter = st.sidebar.selectbox("Tag", ["All"] + all_tags)

    visible_projects = db.search_projects_with_filters(
        query=search_text,
        status=None if status_filter == "All" else status_filter,
        template_type=None if template_filter == "All" else template_filter,
        tag=None if tag_filter == "All" else tag_filter,
    )

    st.sidebar.caption(f"{len(visible_projects)} project(s)")
    for project in visible_projects[:12]:
        if st.sidebar.button(make_sidebar_project_label(project), key=f"open_project_{project['id']}", use_container_width=True):
            load_selected_project_into_the_draft(project)
            st.rerun()

    if st.sidebar.button("New blank draft", use_container_width=True):
        reset_the_draft_workspace()
        st.rerun()


def count_build_completeness():
    profile = st.session_state.draft_profile
    inputs_json = st.session_state.draft_inputs
    checks = [
        bool(profile.get("name", "").strip()),
        bool(profile.get("purpose", "").strip()),
        bool(inputs_json.get("components", "").strip()),
        bool(inputs_json.get("specific_requirements", "").strip()),
        bool(inputs_json.get("constraints", "").strip()),
    ]
    return int(sum(checks) / len(checks) * 100)


def show_small_stat_pills():
    all_projects = db.get_all_saved_projects()
    selected_project = db.get_project_by_id(st.session_state.selected_project_id) if st.session_state.selected_project_id else None
    selected_artifacts = selected_project["artifacts_json"] if selected_project else {}
    stat_columns = st.columns(4)
    stat_items = [
        ("📁", f"{len(all_projects)} Projects", "Saved locally"),
        ("🧠", f"{sum(len(project.get('revision_history', [])) for project in all_projects)} Revisions", "Snapshots"),
        ("🧾", f"{len(selected_artifacts.get('bom', [])) if selected_project else 0} BOM", "Current build"),
        ("💰", f"${selected_artifacts.get('estimated_cost', {}).get('total', 0) if selected_project else 0} Cost", "Estimate"),
    ]
    for column, (icon, value, note) in zip(stat_columns, stat_items):
        column.markdown(
            f"""
            <div class="jarvis-stat-pill">
                <div class="jarvis-stat-icon">{icon}</div>
                <div>
                    <div class="jarvis-stat-value">{value}</div>
                    <div class="jarvis-stat-note">{note}</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def show_current_draft_snapshot():
    profile = st.session_state.draft_profile
    inputs_json = st.session_state.draft_inputs
    difficulty_badge = DIFFICULTY_BADGES.get(profile.get("skill_level", "beginner"), "🟢 Beginner")
    tags = profile.get("tags", [])[:3]
    chips = [difficulty_badge, profile.get("budget_mode", "mid").title(), profile.get("template_type", "custom").title()]
    chips.extend(tag for tag in tags if tag)
    chip_markup = "".join(f'<span class="jarvis-chip">{chip}</span>' for chip in chips)
    st.markdown(
        f"""
        <div class="jarvis-section-box jarvis-lift-card" style="margin-top:1rem;">
            <div style="font-size:13px; letter-spacing:.12em; text-transform:uppercase; color:var(--jarvis-soft-ink); font-weight:700;">
                Current Draft
            </div>
            <h3 style="margin:0.35rem 0 0.3rem 0;">{profile.get('name') or 'Unnamed project'}</h3>
            <div style="color:var(--jarvis-soft-ink); font-size:16px;">{profile.get('purpose') or 'No goal added yet.'}</div>
            <div class="jarvis-chip-row">{chip_markup}</div>
            <div style="margin-top:0.8rem; color:var(--jarvis-soft-ink); font-size:15px;">
                Components: {inputs_json.get('components') or 'Not added yet'}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def draft_is_ready_to_build():
    profile = st.session_state.draft_profile
    inputs_json = st.session_state.draft_inputs
    return bool(profile.get("name", "").strip() and profile.get("purpose", "").strip() and inputs_json.get("components", "").strip())


def save_the_current_draft(uploaded_files):
    project_profile = dict(st.session_state.draft_profile)
    project_inputs = dict(st.session_state.draft_inputs)
    selected_project_id = st.session_state.selected_project_id
    existing_project = db.get_project_by_id(selected_project_id) if selected_project_id else None

    plan_payload = build_full_project_plan(
        project_profile,
        project_inputs,
        attachments=existing_project["attachments"] if existing_project else [],
    )

    if selected_project_id:
        db.save_project_as_new_revision(
            selected_project_id,
            plan_payload["project_profile"],
            plan_payload["inputs_json"],
            plan_payload["artifacts_json"],
            plan_payload["narrative_plan"],
            change_summary="Streamlit quick builder revision",
        )
        saved_project_id = selected_project_id
    else:
        saved_project_id = db.create_new_project_record(
            plan_payload["project_profile"],
            plan_payload["inputs_json"],
            plan_payload["artifacts_json"],
            plan_payload["narrative_plan"],
            change_summary="Streamlit quick builder creation",
        )

    for uploaded_file in uploaded_files or []:
        db.save_uploaded_file_for_project(
            saved_project_id,
            uploaded_file.name,
            uploaded_file.getvalue(),
            uploaded_file.type or "",
            note="Uploaded from the quick builder workspace.",
        )

    load_selected_project_into_the_draft(db.get_project_by_id(saved_project_id))
    st.success("Project saved.")
    st.rerun()


def show_build_progress_indicator():
    completion_value = count_build_completeness()
    profile = st.session_state.draft_profile
    inputs_json = st.session_state.draft_inputs
    goal_done = "✓" if profile.get("purpose", "").strip() else "☐"
    parts_done = "✓" if inputs_json.get("components", "").strip() else "☐"
    budget_done = "✓" if profile.get("budget_mode", "").strip() else "☐"
    st.markdown(
        f"""
        <div class="jarvis-section-box" style="margin-bottom:1rem;">
            <div style="font-weight:700;">Build completeness</div>
            <div class="jarvis-progress-shell"><div class="jarvis-progress-fill" style="width:{completion_value}%;"></div></div>
            <div style="color:var(--jarvis-soft-ink); font-size:14px;">{completion_value}% ready</div>
            <div class="jarvis-chip-row">
                <span class="jarvis-chip">Goal {goal_done}</span>
                <span class="jarvis-chip">Parts {parts_done}</span>
                <span class="jarvis-chip">Budget {budget_done}</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def show_main_builder_panel():
    profile = st.session_state.draft_profile
    inputs_json = st.session_state.draft_inputs

    st.markdown('<div class="jarvis-main-builder">', unsafe_allow_html=True)
    st.markdown("## Quick Builder")
    st.markdown(
        """
        <div class="jarvis-helper-box">
            Start here: name the build, describe what it should do, and list the parts you already know.
            Then press <strong>⚡ Generate Build Plan</strong>.
        </div>
        """,
        unsafe_allow_html=True,
    )
    show_build_progress_indicator()

    name_column, template_column = st.columns([1.45, 1])
    profile["name"] = name_column.text_input("Project name", value=profile.get("name", ""), placeholder="Apple Sensor Tracker")
    profile["template_type"] = template_column.selectbox(
        "Template",
        PROJECT_TEMPLATES,
        index=PROJECT_TEMPLATES.index(profile.get("template_type", "custom")),
    )

    profile["purpose"] = st.text_area(
        "Project goal",
        value=profile.get("purpose", ""),
        height=100,
        placeholder="Track humidity and temperature and display it on screen",
    )
    inputs_json["components"] = st.text_area(
        "Parts you have",
        value=inputs_json.get("components", ""),
        height=130,
        placeholder="ESP32\nBME280\nOLED display",
    )

    difficulty_column, budget_column = st.columns(2)
    profile["skill_level"] = difficulty_column.selectbox(
        "Difficulty",
        SKILL_LEVELS,
        index=SKILL_LEVELS.index(profile.get("skill_level", "beginner")),
        format_func=lambda value: DIFFICULTY_BADGES.get(value, value.title()),
    )
    profile["budget_mode"] = budget_column.select_slider("Estimated budget", options=BUDGET_LEVELS, value=profile.get("budget_mode", "mid"))

    with st.expander("More project details"):
        profile["status"] = st.selectbox("Status", STATUSES, index=STATUSES.index(profile.get("status", "draft")))
        tag_text = st.text_input("Tags", value=", ".join(profile.get("tags", [])), placeholder="tracker, esp32, sensing")
        profile["tags"] = [tag.strip().lower() for tag in tag_text.split(",") if tag.strip()]
        inputs_json["specific_requirements"] = st.text_area(
            "Specific requirements",
            value=inputs_json.get("specific_requirements", ""),
            height=90,
            placeholder="Low power, easy to read outdoors, budget under $80",
        )
        inputs_json["constraints"] = st.text_area(
            "Constraints",
            value=inputs_json.get("constraints", ""),
            height=90,
            placeholder="3.3V logic only, must fit in a small enclosure",
        )

    clarification_questions = make_clarification_questions_for_project(profile, inputs_json)
    clarification_answers = dict(inputs_json.get("clarification_answers", {}))
    for question in clarification_questions:
        clarification_answers[question] = st.text_input(question, value=clarification_answers.get(question, ""), key=f"clarify_{question}")
    inputs_json["clarification_answers"] = clarification_answers

    uploaded_files = st.file_uploader("Optional files", accept_multiple_files=True)
    show_current_draft_snapshot()

    button_columns = st.columns([1.3, 1, 1])
    build_label = "⚡ Generate Build Plan" if not st.session_state.selected_project_id else "⚡ Save New Revision"
    if button_columns[0].button(build_label, type="primary", disabled=not draft_is_ready_to_build(), use_container_width=True):
        save_the_current_draft(uploaded_files)
    if button_columns[1].button("💾 Save Draft", use_container_width=True, disabled=True):
        st.info("Draft values are already kept in the page state until you refresh.")
    if button_columns[2].button("🧹 Clear", use_container_width=True):
        reset_the_draft_workspace()
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)


def make_bom_csv_text(project):
    output = io.StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=["name", "quantity", "unit_cost_estimate", "total_cost_estimate", "purchase_link", "source_note"],
    )
    writer.writeheader()
    for item in project["artifacts_json"].get("bom", []):
        writer.writerow(item)
    return output.getvalue()


def get_export_cache_marker(project):
    return f"{project.get('revision_number', 1)}::{project.get('updated_at', '')}"


def ensure_export_paths(project):
    export_key = f"ready_exports_{project['id']}"
    marker_key = f"ready_exports_marker_{project['id']}"
    current_marker = get_export_cache_marker(project)
    if st.session_state.get(marker_key) != current_marker or export_key not in st.session_state:
        st.session_state[export_key] = export_project_in_every_format(project)
        st.session_state[marker_key] = current_marker
    return st.session_state[export_key]


def show_preview_panel_when_no_project_exists():
    st.markdown(
        """
        <div class="jarvis-preview-panel jarvis-empty-preview">
            <div>
                <h2 style="margin-bottom:0.5rem;">Build Plan Preview</h2>
                <div style="color:var(--jarvis-soft-ink); font-size:16px; max-width:28rem;">
                    Parts, wiring, safety notes, steps, and cost will appear here as soon as you generate the first plan.
                </div>
                <div class="jarvis-chip-row" style="justify-content:center;">
                    <span class="jarvis-chip">Parts</span>
                    <span class="jarvis-chip">Wiring</span>
                    <span class="jarvis-chip">Safety</span>
                    <span class="jarvis-chip">Steps</span>
                    <span class="jarvis-chip">Cost</span>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def show_live_preview_summary(project):
    profile = project["project_profile"]
    artifacts = project["artifacts_json"]
    st.markdown(
        f"""
        <div class="jarvis-preview-panel">
            <div style="font-size:13px; letter-spacing:.12em; text-transform:uppercase; color:var(--jarvis-soft-ink); font-weight:700;">
                Build Plan Preview
            </div>
            <h2 style="margin:0.35rem 0 0.3rem 0;">{project['project_name']}</h2>
            <div style="color:var(--jarvis-soft-ink); font-size:16px;">{profile.get('purpose') or 'No goal stored.'}</div>
            <div class="jarvis-chip-row">
                <span class="jarvis-chip">{DIFFICULTY_BADGES.get(profile.get('skill_level', 'beginner'), '🟢 Beginner')}</span>
                <span class="jarvis-chip">{profile.get('budget_mode', 'mid').title()}</span>
                <span class="jarvis-chip">{profile.get('template_type', 'custom').title()}</span>
                <span class="jarvis-chip">💰 ${artifacts.get('estimated_cost', {}).get('total', 0)}</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def show_preview_sections(project):
    artifacts = project["artifacts_json"]
    section_columns = st.columns(2)
    preview_groups = [
        ("🧾 Parts", [item.get("name", "Part") for item in artifacts.get("bom", [])[:5]] or ["No parts yet"]),
        ("🔌 Wiring", [f"{item.get('from', 'Source')} -> {item.get('to', 'Target')}" for item in artifacts.get("wiring_plan", [])[:4]] or ["No wiring plan yet"]),
        ("🛟 Safety", artifacts.get("safety_warnings", [])[:4] or ["No safety notes yet"]),
        ("🪜 Steps", artifacts.get("build_steps", [])[:4] or ["No build steps yet"]),
    ]
    for column, (title, values) in zip(section_columns * 2, preview_groups):
        column.markdown(
            f"""
            <div class="jarvis-section-box jarvis-lift-card" style="margin-bottom:0.9rem;">
                <div style="font-weight:700; margin-bottom:0.55rem;">{title}</div>
                <div style="color:var(--jarvis-soft-ink); font-size:15px;">{'<br>'.join(f'• {value}' for value in values)}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def show_export_buttons(project):
    st.info("Download the current saved revision as PDF, Markdown, or CSV here. If you just saved a new revision, click Refresh exports first.")

    try:
        export_paths = ensure_export_paths(project)
    except Exception as exc:
        st.error(f"Could not generate exports: {exc}")
        return

    export_columns = st.columns(4)
    if export_columns[0].button("Refresh exports", key=f"refresh_exports_{project['id']}", use_container_width=True):
        try:
            st.session_state[f"ready_exports_{project['id']}"] = export_project_in_every_format(project)
            st.session_state[f"ready_exports_marker_{project['id']}"] = get_export_cache_marker(project)
            st.rerun()
        except Exception as exc:
            st.error(f"Could not refresh exports: {exc}")
            return

    with open(export_paths["pdf"], "rb") as file_handle:
        export_columns[1].download_button("PDF", data=file_handle.read(), file_name=export_paths["pdf"].name, mime="application/pdf", use_container_width=True)
    with open(export_paths["markdown"], "rb") as file_handle:
        export_columns[2].download_button("Markdown", data=file_handle.read(), file_name=export_paths["markdown"].name, mime="text/markdown", use_container_width=True)
    export_columns[3].download_button("BOM CSV", data=make_bom_csv_text(project), file_name=f"{project['project_name']}_bom.csv", mime="text/csv", use_container_width=True)


def show_follow_up_tab(project):
    with st.form(f"follow_up_form_{project['id']}"):
        follow_up_question = st.text_input("Ask a follow-up question", placeholder="How should I power this safely?")
        ask_button_pressed = st.form_submit_button("Get answer")

    if ask_button_pressed and follow_up_question.strip():
        follow_up_answer = answer_follow_up_like_a_human_mentor(
            follow_up_question,
            db.build_full_project_context_for_ai(project["id"]),
            project["artifacts_json"],
        )
        db.save_follow_up_answer(project["id"], follow_up_question, follow_up_answer)
        st.success(follow_up_answer)
        st.rerun()

    history = db.get_follow_up_history(project["id"])
    for item in history:
        st.markdown(
            f"""
            <div class="jarvis-section-box jarvis-lift-card" style="margin-bottom:0.85rem;">
                <div style="font-size:13px; color:var(--jarvis-soft-ink); text-transform:uppercase; letter-spacing:.12em;">Question</div>
                <div style="font-weight:700; margin-bottom:0.65rem;">{item['question']}</div>
                <div style="font-size:13px; color:var(--jarvis-soft-ink); text-transform:uppercase; letter-spacing:.12em;">Answer</div>
                <div style="color:var(--jarvis-soft-ink);">{item['response']}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def show_live_build_preview_panel(project):
    show_live_preview_summary(project)
    show_export_buttons(project)
    preview_tabs = st.tabs(["Preview", "Narrative", "Follow-ups"])
    with preview_tabs[0]:
        show_preview_sections(project)
    with preview_tabs[1]:
        st.markdown('<div class="jarvis-section-box">', unsafe_allow_html=True)
        st.markdown(project.get("narrative_plan", ""))
        st.markdown("</div>", unsafe_allow_html=True)
    with preview_tabs[2]:
        show_follow_up_tab(project)


def run_streamlit_app():
    st.set_page_config(page_title="Jarvis Hardware Builder V2", layout="wide")
    set_up_streamlit_page_state()
    show_sidebar_project_shelf()
    paint_the_page_with_better_colors_and_layout()

    show_main_header_section()

    builder_shell_left, builder_shell_center, builder_shell_right = st.columns([0.08, 1.15, 0.08])
    with builder_shell_center:
        show_main_builder_panel()

    st.write("")
    show_small_stat_pills()
    st.write("")

    selected_project_id = st.session_state.selected_project_id
    if selected_project_id:
        project = db.get_project_by_id(selected_project_id)
        if project:
            show_live_build_preview_panel(project)
        else:
            show_preview_panel_when_no_project_exists()
    else:
        show_preview_panel_when_no_project_exists()


if __name__ == "__main__":
    run_streamlit_app()
