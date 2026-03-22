import json
import os

import agent
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

    original_openai = agent.OpenAI
    original_api_key = os.environ.get("OPENAI_API_KEY")

    class RaisingCompletions:
        @staticmethod
        def create(*args, **kwargs):
            raise RuntimeError("forced OpenAI failure")

    class RaisingChat:
        completions = RaisingCompletions()

    class FakeOpenAI:
        def __init__(self, api_key):
            self.api_key = api_key
            self.chat = RaisingChat()

    try:
        os.environ["OPENAI_API_KEY"] = "fake-key"
        agent.OpenAI = FakeOpenAI
        fallback_payload = build_full_project_plan(project_profile, inputs_json)
        assert fallback_payload["artifacts_json"]["bom"]
        assert isinstance(fallback_payload["artifacts_json"]["resources"], list)
        assert fallback_payload["narrative_plan"]
    finally:
        agent.OpenAI = original_openai
        if original_api_key is None:
            os.environ.pop("OPENAI_API_KEY", None)
        else:
            os.environ["OPENAI_API_KEY"] = original_api_key

    original_helper = agent.ask_openai_for_chat_response
    try:
        agent.ask_openai_for_chat_response = lambda messages, model=None: json.dumps(
            {
                "artifacts_json": {
                    "bom": [],
                    "resources": None,
                    "estimated_cost": {"total": 12.5},
                },
                "narrative_plan": "AI plan",
            }
        )
        sanitized_payload = build_full_project_plan(
            project_profile,
            inputs_json,
            attachments=[{"original_name": "notes.txt"}],
        )
        assert isinstance(sanitized_payload["artifacts_json"]["resources"], list)
        assert len(sanitized_payload["artifacts_json"]["resources"]) == 1
        assert sanitized_payload["artifacts_json"]["resources"][0]["title"] == "Attached project files"
        assert sanitized_payload["artifacts_json"]["estimated_cost"]["currency"] == "USD"
    finally:
        agent.ask_openai_for_chat_response = original_helper

    print("All agent contract tests passed.")


if __name__ == "__main__":
    run_all_agent_contract_tests()
