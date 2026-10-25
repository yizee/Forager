"""Shared pattern for agents that answer in JSON and are checked in code.

The agent gets one short request per turn; larger context goes in through the
input builder on the first turn. Every answer is parsed and checked by Python.
On failure the agent gets the exact problems and one more turn to fix them.
"""

import json
import re


def parse_json(text: str) -> dict:
    """Extract the JSON object from a model answer, tolerating code fences."""
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip())
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("No JSON object found in the answer.")
    return json.loads(text[start:end + 1])


def json_agent_factory(name: str, instructions: str):
    def create(model):
        from agents import Agent
        return Agent(name=name, model=model, instructions=instructions, tools=[])
    return create


def run_plain(agent, messages, run_config=None):
    from agents import Runner
    return Runner.run_sync(agent, messages, max_turns=3, run_config=run_config)


def context_input(label: str, context: str):
    """Input builder that sends context once, as the first message of the history.

    session.run accepts at most 6,000 characters, so long context cannot be the
    user message itself.
    """
    def build(history, user_input, files):
        if not history and context:
            history = [{"role": "user", "content": f"{label} (JSON):\n{context}"}]
        return history + [{"role": "user", "content": user_input}]
    return build


def ask_json(session, request: str, check, *, max_repairs=1) -> dict:
    """Run request on session, parse JSON and check it; repair up to max_repairs times.

    check(data) returns a list of problems. Returns {"data", "errors", "attempts",
    "turns"}; data is None if no answer parsed, errors is empty on success.
    """
    turns, data, errors = [], None, []
    for _ in range(max_repairs + 1):
        result = session.run(request)
        turns.append(result.to_dict())
        if result.status != "completed":
            errors = [f"Agent turn {result.status}: {result.error or 'no answer'}"]
            break
        try:
            data = parse_json(result.answer)
            errors = check(data)
        except ValueError as exc:
            data, errors = None, [f"Answer is not valid JSON: {exc}"]
        if not errors:
            break
        request = ("Your answer failed these checks. Return the corrected full JSON object only.\n- "
                   + "\n- ".join(errors[:15]))
    return {"data": data, "errors": errors, "attempts": len(turns), "turns": turns}
