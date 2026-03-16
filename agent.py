import json
import os
from copy import deepcopy

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    load_dotenv = None

try:
    from openai import OpenAI
except ImportError:  # Backward compatibility for openai<1.0
    OpenAI = None
    import openai


if load_dotenv is not None:
    load_dotenv()


DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")
PROJECT_TEMPLATES = ["custom", "robot", "home automation", "sensor node", "weather station"]
SKILL_LEVELS = ["beginner", "intermediate", "advanced"]
BUDGET_LEVELS = ["low", "mid", "premium"]
STATUSES = ["draft", "planned", "in progress", "tested", "archived"]

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


def ask_openai_for_chat_response(messages, model=DEFAULT_MODEL):
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None

    if OpenAI is not None:
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(model=model, messages=messages)
        return response.choices[0].message.content

    openai.api_key = api_key
    response = openai.ChatCompletion.create(model=model, messages=messages)
    return response["choices"][0]["message"]["content"]


def make_clarification_questions_for_project(project_profile, inputs_json):
    questions = []
    if len((inputs_json.get("components") or "").split(",")) < 2:
        questions.append("What controller, sensors, or actuators do you already have in mind?")
    if not (inputs_json.get("constraints") or "").strip():
        questions.append("Are there power, size, portability, or connectivity constraints?")
    if not (inputs_json.get("specific_requirements") or "").strip():
        questions.append("What outcome matters most: learning, reliability, low cost, or speed?")
    if project_profile.get("template_type") == "custom":
        questions.append("Should this project prioritize prototyping speed or long-term robustness?")
    return questions[:3]


def break_components_into_list(components_text):
    components = [item.strip() for item in (components_text or "").split(",") if item.strip()]
    return components or ["Microcontroller", "Power supply", "Mounting hardware"]


def guess_unit_cost_for_component(name, budget_mode):
    base = {
        "arduino": 18,
        "raspberry": 55,
        "sensor": 8,
        "motor": 14,
        "battery": 22,
        "relay": 6,
        "display": 15,
        "camera": 30,
    }
    lowered = name.lower()
    amount = 10
    for key, value in base.items():
        if key in lowered:
            amount = value
            break
    multiplier = {"low": 0.8, "mid": 1.0, "premium": 1.35}.get(budget_mode, 1.0)
    return round(amount * multiplier, 2)


def build_local_artifacts_when_ai_is_unavailable(project_profile, inputs_json):
    components = break_components_into_list(inputs_json.get("components", ""))
    budget_mode = project_profile.get("budget_mode", "mid")
    bom = []
    total = 0.0
    for component in components:
        unit_cost = guess_unit_cost_for_component(component, budget_mode)
        item_total = round(unit_cost, 2)
        total += item_total
        bom.append(
            {
                "name": component,
                "quantity": 1,
                "unit_cost_estimate": unit_cost,
                "total_cost_estimate": item_total,
                "purchase_link": "",
                "source_note": "AI-estimated local fallback cost.",
            }
        )

    template = project_profile.get("template_type", "custom")
    purpose = project_profile.get("purpose", "")
    requirements = inputs_json.get("specific_requirements", "")

    wiring_plan = [
        {
            "from": components[0],
            "to": component,
            "signal": "GPIO / data",
            "notes": f"Confirm voltage compatibility before connecting {component}.",
        }
        for component in components[1:]
    ]
    power_checks = [
        {
            "title": "System power budget",
            "details": "Verify the controller regulator can supply every peripheral or add a dedicated power rail.",
            "status": "warning",
        }
    ]
    safety_warnings = [
        "Validate current draw before powering motors, relays, or heating elements.",
        "Do not connect 5V outputs directly into 3.3V-only inputs without level shifting.",
    ]
    tools = ["Breadboard", "Jumper wires", "USB cable", "Multimeter"]
    build_steps = [
        f"Review the {template} requirements and confirm the goal: {purpose or 'general prototyping'}.",
        "Lay out the controller, power path, and peripherals before wiring anything.",
        "Wire one component at a time and test each connection before adding the next part.",
        "Load a minimal firmware sketch or script to verify communication with each module.",
        "Integrate the full workflow and test against the main success criteria.",
    ]
    testing_checklist = [
        "Power-on smoke test passes without overheating.",
        "Each sensor or actuator responds independently.",
        "The final workflow matches the intended project purpose.",
        "The build remains stable for at least 15 minutes of continuous operation.",
    ]
    suggested_follow_ups = [
        "Can you optimize this bill of materials for a tighter budget?",
        "Can you turn the wiring plan into a pin-by-pin checklist?",
        "What are the main risks or failure points in this design?",
    ]
    resources = [
        {"title": "Controller datasheet", "url": "", "notes": "Review voltage and current limits."},
        {"title": "Project assembly checklist", "url": "", "notes": "Use during final integration."},
    ]
    compatibility_notes = [
        f"Template selected: {template}. Keep component selection aligned with {purpose or 'the core goal'}.",
        f"Specific requirements to preserve: {requirements or 'No extra constraints provided yet.'}",
    ]
    return {
        "bom": bom,
        "wiring_plan": wiring_plan,
        "power_checks": power_checks,
        "safety_warnings": safety_warnings,
        "tools": tools,
        "build_steps": build_steps,
        "testing_checklist": testing_checklist,
        "suggested_follow_ups": suggested_follow_ups,
        "resources": resources,
        "compatibility_notes": compatibility_notes,
        "estimated_cost": {
            "currency": "USD",
            "total": round(total, 2),
            "notes": "Estimated locally without live retailer pricing.",
        },
    }


def write_local_narrative_plan(project_profile, inputs_json, artifacts):
    lines = [
        f"# {project_profile.get('name', 'Hardware Project')}",
        "",
        f"Template: {project_profile.get('template_type', 'custom')}",
        f"Purpose: {project_profile.get('purpose', '')}",
        f"Skill level: {project_profile.get('skill_level', 'beginner')}",
        f"Budget mode: {project_profile.get('budget_mode', 'mid')}",
        "",
        "## Summary",
        f"Build a system around {inputs_json.get('components', 'your selected hardware')} and satisfy: {inputs_json.get('specific_requirements', 'the stated project goals')}.",
        "",
        "## Build Steps",
    ]
    for step in artifacts.get("build_steps", []):
        lines.append(f"- {step}")
    lines.append("")
    lines.append("## Safety")
    for warning in artifacts.get("safety_warnings", []):
        lines.append(f"- {warning}")
    lines.append("")
    lines.append("## Validation")
    for item in artifacts.get("testing_checklist", []):
        lines.append(f"- {item}")
    return "\n".join(lines)


def generate_structured_plan_with_ai(project_profile, inputs_json):
    instructions = (
        "You are a hardware planning assistant. Return strict JSON only. "
        "The JSON must contain keys: artifacts_json, narrative_plan. "
        "artifacts_json must include bom, wiring_plan, power_checks, safety_warnings, tools, build_steps, "
        "testing_checklist, suggested_follow_ups, resources, compatibility_notes, estimated_cost. "
        "Use concise but practical entries. BOM items must include name, quantity, unit_cost_estimate, "
        "total_cost_estimate, purchase_link, source_note."
    )
    messages = [
        {"role": "system", "content": instructions},
        {
            "role": "user",
            "content": json.dumps({"project_profile": project_profile, "inputs_json": inputs_json}, ensure_ascii=True),
        },
    ]
    raw = ask_openai_for_chat_response(messages)
    if not raw:
        return None
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return None
    if not isinstance(parsed, dict):
        return None
    artifacts = parsed.get("artifacts_json")
    narrative = parsed.get("narrative_plan")
    if not isinstance(artifacts, dict) or not isinstance(narrative, str):
        return None
    normalized = deepcopy(DEFAULT_ARTIFACTS)
    normalized.update(artifacts)
    return {"artifacts_json": normalized, "narrative_plan": narrative}


def build_full_project_plan(project_profile, inputs_json, attachments=None):
    project_profile = dict(project_profile or {})
    inputs_json = dict(inputs_json or {})
    clarifications = make_clarification_questions_for_project(project_profile, inputs_json)
    ai_payload = generate_structured_plan_with_ai(project_profile, inputs_json)
    if ai_payload is None:
        artifacts = build_local_artifacts_when_ai_is_unavailable(project_profile, inputs_json)
        narrative = write_local_narrative_plan(project_profile, inputs_json, artifacts)
    else:
        artifacts = ai_payload["artifacts_json"]
        narrative = ai_payload["narrative_plan"]

    if attachments:
        artifacts["resources"].append(
            {
                "title": "Attached project files",
                "url": "",
                "notes": ", ".join(item.get("original_name", "attachment") for item in attachments[:5]),
            }
        )
    return {
        "project_profile": project_profile,
        "inputs_json": inputs_json,
        "artifacts_json": artifacts,
        "narrative_plan": narrative,
        "clarification_questions": clarifications,
    }


def answer_follow_up_like_a_human_mentor(question, project_context, artifacts_json=None):
    instructions = (
        "You are a practical hardware mentor. Answer the follow-up question with direct, implementation-oriented guidance. "
        "Keep the answer concise but actionable. Mention safety or compatibility risks when relevant."
    )
    messages = [
        {
            "role": "system",
            "content": instructions
            + "\nProject context:\n"
            + project_context
            + "\nStructured artifacts:\n"
            + json.dumps(artifacts_json or {}, ensure_ascii=True),
        },
        {"role": "user", "content": question},
    ]
    raw = ask_openai_for_chat_response(messages)
    if raw:
        return raw

    hints = []
    question_lower = question.lower()
    if "power" in question_lower or "voltage" in question_lower:
        hints.append("Check the controller logic voltage and total current draw before adding peripherals.")
    if "cost" in question_lower or "budget" in question_lower:
        hints.append("Reduce cost by replacing premium modules with breakout boards and reusing a single controller.")
    if "wire" in question_lower or "pin" in question_lower:
        hints.append("Wire one module at a time and validate the pin map against the controller datasheet.")
    if not hints:
        hints.append("Start with the existing BOM and build steps, then validate the highest-risk subsystem first.")
    return " ".join(hints)


def turn_project_into_markdown_text(project):
    profile = project["project_profile"]
    inputs_json = project["inputs_json"]
    artifacts = project["artifacts_json"]
    lines = [
        f"# {profile.get('name', project.get('project_name', 'Hardware Project'))}",
        "",
        f"- Template: {profile.get('template_type', 'custom')}",
        f"- Purpose: {profile.get('purpose', '')}",
        f"- Skill level: {profile.get('skill_level', 'beginner')}",
        f"- Budget mode: {profile.get('budget_mode', 'mid')}",
        f"- Status: {profile.get('status', 'draft')}",
        f"- Tags: {', '.join(project.get('tags', [])) or 'None'}",
        "",
        "## Inputs",
        f"- Components: {inputs_json.get('components', '')}",
        f"- Requirements: {inputs_json.get('specific_requirements', '')}",
        f"- Constraints: {inputs_json.get('constraints', '')}",
        "",
        "## Narrative Plan",
        project.get("narrative_plan", ""),
        "",
        "## Bill of Materials",
    ]
    for item in artifacts.get("bom", []):
        lines.append(
            f"- {item.get('name', 'Item')}: qty {item.get('quantity', 1)}, "
            f"unit ${item.get('unit_cost_estimate', 0)}, total ${item.get('total_cost_estimate', 0)}"
        )
    lines.extend(["", "## Wiring Plan"])
    for wire in artifacts.get("wiring_plan", []):
        lines.append(
            f"- {wire.get('from', 'Source')} -> {wire.get('to', 'Target')} "
            f"({wire.get('signal', 'signal')}): {wire.get('notes', '')}"
        )
    lines.extend(["", "## Safety Warnings"])
    for item in artifacts.get("safety_warnings", []):
        lines.append(f"- {item}")
    lines.extend(["", "## Build Steps"])
    for step in artifacts.get("build_steps", []):
        lines.append(f"- {step}")
    lines.extend(["", "## Testing Checklist"])
    for item in artifacts.get("testing_checklist", []):
        lines.append(f"- {item}")
    return "\n".join(lines)


def write_initial_instruction_text(project_name, components, project_purpose, specific_requirements):
    payload = build_full_project_plan(
        {
            "name": project_name,
            "purpose": project_purpose,
            "skill_level": "beginner",
            "budget_mode": "mid",
            "template_type": "custom",
            "status": "planned",
            "tags": [],
        },
        {
            "components": components,
            "constraints": "",
            "specific_requirements": specific_requirements,
            "clarification_answers": {},
        },
    )
    return payload["narrative_plan"]


def answer_following_questions_in_plain_words(following_question, context_data=""):
    return answer_follow_up_like_a_human_mentor(following_question, context_data, {})


def save_project_plan_text_file(project_name, conversation_data=""):
    safe_name = "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in project_name).strip("_")
    if not safe_name:
        safe_name = "project"
    file_name = f"{safe_name}_plan.txt"
    with open(file_name, "w", encoding="utf-8") as file_handle:
        file_handle.write(conversation_data)
    print(f"Plan saved to {file_name}")
