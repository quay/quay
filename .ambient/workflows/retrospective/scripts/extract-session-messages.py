#!/usr/bin/env python3
"""Extract messages from an Ambient session via the backend export endpoint.

Handles two AG-UI event patterns:
  1. Streaming deltas (active sessions): TEXT_MESSAGE_START/CONTENT/END
  2. MESSAGES_SNAPSHOT (completed sessions): full conversation array

Usage:
  python3 extract-session-messages.py <project> <session-name> [max-messages]

Requires BOT_TOKEN at /run/secrets/ambient/bot-token
"""

import json
import sys
import urllib.request


def extract_messages(events, max_messages=50):
    msg_roles = {}
    msg_deltas = {}
    messages = []
    last_snapshot = None

    for event in events:
        etype = event.get("type", "")
        mid = event.get("messageId", "")

        if etype == "TEXT_MESSAGE_START" and mid:
            msg_roles[mid] = event.get("role", "assistant")
            msg_deltas[mid] = []
        elif etype == "TEXT_MESSAGE_CONTENT" and mid:
            if "delta" in event:
                msg_deltas.setdefault(mid, []).append(event["delta"])
        elif etype == "TEXT_MESSAGE_END" and mid:
            if mid in msg_deltas:
                full_text = "".join(msg_deltas.pop(mid))
                if full_text.strip():
                    messages.append(
                        {
                            "role": msg_roles.pop(mid, "assistant"),
                            "text": full_text[:500],
                        }
                    )
        elif etype == "MESSAGES_SNAPSHOT":
            last_snapshot = event

    if not messages and last_snapshot:
        for msg in last_snapshot.get("messages", []):
            role = msg.get("role", "")
            content = msg.get("content", "")
            if role in ("user", "assistant") and isinstance(content, str) and content.strip():
                messages.append({"role": role, "text": content[:500]})

    return messages[-max_messages:]


def main():
    if len(sys.argv) < 3:
        print("Usage: extract-session-messages.py <project> <session-name> [max]")
        sys.exit(1)

    project = sys.argv[1]
    session_name = sys.argv[2]
    max_msgs = int(sys.argv[3]) if len(sys.argv) > 3 else 50

    try:
        bot_token = open("/run/secrets/ambient/bot-token").read().strip()
    except FileNotFoundError:
        print(json.dumps({"error": "bot-token not found"}))
        sys.exit(1)

    base = "http://backend-service.ambient-code.svc.cluster.local:8080/api"
    url = f"{base}/projects/{project}/agentic-sessions/{session_name}/export"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {bot_token}"})

    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read())
    except Exception as e:
        print(json.dumps({"error": str(e), "messages": []}))
        sys.exit(1)

    events = data.get("aguiEvents", [])
    messages = extract_messages(events, max_msgs)

    print(
        json.dumps(
            {
                "session": session_name,
                "total_events": len(events),
                "messages": messages,
                "message_count": len(messages),
            }
        )
    )


if __name__ == "__main__":
    main()
