"""A bounded local tool-using agent: recall only, no shell or memory writes."""

import json
from urllib.request import Request

from .model import Model, SYSTEM, citation_check
from .store import text


TOOL = {"type": "function", "function": {"name": "recall_project_memory",
    "description": "Read selected memories for the application-selected current project. Cannot write or execute commands.",
    "parameters": {"type": "object", "properties": {"question": {"type": "string"}},
                   "required": ["question"], "additionalProperties": False}}}


def run_agent(model, store, project, question, max_turns=3):
    """Model chooses recall; application fixes scope and validates every tool call."""
    project = store.resolve(project)
    question = text(question, "Question", 4000)
    if type(max_turns) is not int or not 1 <= max_turns <= 3:
        raise ValueError("Agent turn limit must be 1–3.")
    if model.backend != "compatible":
        raise ValueError("This optional agent uses the directly tested compatible tool-calling adapter.")
    if not model.name:
        raise ValueError("Configure a local model before running the agent.")
    messages = [{"role": "system", "content": SYSTEM + "\nFor project-specific questions use the recall_project_memory tool before answering. The application fixes its project scope. You have no write or execution tools."},
                {"role": "user", "content": question}]
    trace, supplied = [], []
    for turn in range(max_turns):
        payload = {"model": model.name, "messages": messages, "tools": [TOOL],
                   "temperature": 0, "max_tokens": 1200, "stream": False,
                   "chat_template_kwargs": {"enable_thinking": False}}
        route = "/chat/completions" if model.url.endswith("/v1") else "/v1/chat/completions"
        request = Request(model.url + route, data=json.dumps(payload).encode(),
                          headers={"Content-Type": "application/json"}, method="POST")
        try:
            with model.opener.open(request, timeout=model.timeout) as response:
                raw = response.read(2_000_001)
            if len(raw) > 2_000_000:
                raise ValueError("Agent response exceeds the size limit.")
            message = json.loads(raw)["choices"][0]["message"]
        except (OSError, KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
            raise ValueError("Local agent request failed; no action or memory write performed.") from exc
        if not isinstance(message, dict):
            raise ValueError("Invalid agent message shape.")
        calls = message.get("tool_calls", [])
        if not calls:
            answer = text(message.get("content"), "Agent answer", 16000)
            return {"answer": answer, "trace": trace, "turns": turn+1, "project": project,
                    "citation_check": citation_check(answer, {"records": supplied}),
                    "memory_writes": 0, "commands_executed": 0}
        if not isinstance(calls, list) or len(calls) > 2:
            raise ValueError("Agent requested too many tool calls.")
        messages.append({"role": "assistant", "content": message.get("content"), "tool_calls": calls})
        for call in calls:
            if not isinstance(call, dict) or not isinstance(call.get("function"), dict):
                raise ValueError("Invalid tool-call shape.")
            function = call.get("function", {})
            if function.get("name") != "recall_project_memory":
                raise ValueError("Agent requested an unavailable tool; nothing executed.")
            arguments = function.get("arguments", "{}")
            arguments = json.loads(arguments) if isinstance(arguments, str) else arguments
            if not isinstance(arguments, dict) or set(arguments) != {"question"}:
                raise ValueError("Tool arguments do not match the allowed contract.")
            selection = store.select(project, text(arguments["question"], "Tool question", 4000), budget=7000)
            supplied.extend(selection["records"])
            trace.append({"tool": "recall_project_memory", "project": project,
                          "arguments": arguments, "record_ids": [row["id"] for row in selection["records"]]})
            messages.append({"role": "tool", "tool_call_id": text(call.get("id"), "Tool-call ID", 200),
                             "content": json.dumps(selection, ensure_ascii=False)})
    raise ValueError("Agent reached its turn limit. No memory writes or commands were performed.")
