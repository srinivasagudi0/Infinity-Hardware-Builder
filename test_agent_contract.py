from agent import (
    answer_follow_up_like_a_human_mentor,
    build_full_project_plan,
    make_clarification_questions_for_project,
)


def run_all_agent_contract_tests():
    project_profile = {
        "name": "Weather Monitor",
        "purpose": "Outdoor sensing",
        "skill_level": "intermediate",
        "budget_mode": "low",
        "template_type": "weather station",
        "status": "planned",
        "tags": ["weather"],
    }
    inputs_json = {
        "components": "ESP32, BME280, solar battery charger",
        "constraints": "Outdoor enclosure, battery powered",
        "specific_requirements": "Should publish readings over Wi-Fi",
        "clarification_answers": {},
    }

    questions = make_clarification_questions_for_project(project_profile, inputs_json)
    assert isinstance(questions, list)

    payload = build_full_project_plan(project_profile, inputs_json)
    assert "artifacts_json" in payload
    assert "narrative_plan" in payload
    assert payload["artifacts_json"]["bom"]
    assert payload["artifacts_json"]["power_checks"]
    assert payload["artifacts_json"]["safety_warnings"]

    answer = answer_follow_up_like_a_human_mentor(
        "How should I handle the battery power budget?",
        "Project context here",
        payload["artifacts_json"],
    )
    assert "current" in answer.lower() or "power" in answer.lower() or "voltage" in answer.lower()

    print("All agent contract tests passed.")


if __name__ == "__main__":
    run_all_agent_contract_tests()
