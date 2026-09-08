"""
run_diagnosis.py — feeds every case in data/cases.csv to Claude using the
NetSage AI system prompt, and saves the results to data/ai_results.json so
the static website can display them (no API key ever touches the browser).

Setup:
    export ANTHROPIC_API_KEY=sk-ant-...        (macOS/Linux)
    setx ANTHROPIC_API_KEY "sk-ant-..."         (Windows, then reopen terminal)

Usage:
    python3 scripts/run_diagnosis.py                 # run every case
    python3 scripts/run_diagnosis.py C001 C010        # run only specific case IDs
    python3 scripts/run_diagnosis.py --overwrite      # re-run cases that already have a result

No third-party packages required — uses only Python's standard library.
"""
import csv
import json
import os
import sys
import time
import urllib.request
import urllib.error

API_URL = "https://api.anthropic.com/v1/messages"
MODEL = "claude-sonnet-4-6"

SYSTEM_PROMPT = """You are NetSage AI, a troubleshooting assistant for junior network engineers working in Cisco Packet Tracer labs. You are shown a SYMPTOM, a TOPOLOGY NOTE, and SHOW-COMMAND OUTPUT. Propose the most likely root cause using ONLY the evidence given.

Rules:
1. Never invent evidence not present in the show-command output.
2. If evidence is insufficient, say so and set confidence to "low".
3. Always name the OSI layer most responsible for the symptom.
4. Always propose exactly one concrete next command.
5. fix_steps must be reversible, non-destructive lab actions.
6. This is a DRAFT. A human reviewer will Accept, Edit, or Reject it. Do not claim the issue is resolved.
7. Respond with ONLY a single JSON object, no prose, no markdown fences.

Schema: {"root_cause":string,"confidence":"low"|"medium"|"high","evidence":string,"osi_layer":string,"next_command":string,"fix_steps":[string]}"""


def call_claude(api_key, user_message, max_retries=3):
    body = json.dumps({
        "model": MODEL,
        "max_tokens": 1000,
        "system": SYSTEM_PROMPT,
        "messages": [{"role": "user", "content": user_message}],
    }).encode("utf-8")

    req = urllib.request.Request(
        API_URL,
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        },
    )

    last_err = None
    for attempt in range(max_retries):
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                text = "".join(block.get("text", "") for block in data.get("content", []))
                clean = text.replace("```json", "").replace("```", "").strip()
                return json.loads(clean)
        except urllib.error.HTTPError as e:
            last_err = f"HTTP {e.code}: {e.read().decode('utf-8', errors='ignore')[:300]}"
            if e.code == 429:  # rate limited — back off and retry
                time.sleep(2 * (attempt + 1))
                continue
            break
        except Exception as e:
            last_err = str(e)
            time.sleep(1)
    return {"error": last_err or "Unknown error calling the API"}


def main():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: Set the ANTHROPIC_API_KEY environment variable first.")
        print('  export ANTHROPIC_API_KEY="sk-ant-..."   (Linux/macOS)')
        print('  setx ANTHROPIC_API_KEY "sk-ant-..."      (Windows, reopen terminal after)')
        sys.exit(1)

    args = sys.argv[1:]
    overwrite = "--overwrite" in args
    only_ids = {a for a in args if not a.startswith("--")}

    base = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    csv_path = os.path.join(base, "data", "cases.csv")
    out_path = os.path.join(base, "data", "ai_results.json")

    results = {}
    if os.path.exists(out_path):
        with open(out_path, encoding="utf-8") as f:
            try:
                results = json.load(f)
            except json.JSONDecodeError:
                results = {}

    with open(csv_path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    if only_ids:
        rows = [r for r in rows if r["case_id"] in only_ids]

    print(f"Running diagnosis for {len(rows)} case(s)...\n")
    for i, row in enumerate(rows, 1):
        cid = row["case_id"]
        if cid in results and not overwrite:
            print(f"[{i}/{len(rows)}] {cid} — already has a result, skipping (use --overwrite to redo)")
            continue

        user_message = (
            f"SYMPTOM: {row['symptom']}\n"
            f"TOPOLOGY NOTE: {row['topology_note']}\n"
            f"SHOW OUTPUT:\n{row['show_output']}"
        )
        print(f"[{i}/{len(rows)}] {cid} — calling Claude...")
        result = call_claude(api_key, user_message)
        results[cid] = result

        if "error" in result:
            print(f"    ERROR: {result['error']}")
        else:
            print(f"    root_cause: {result.get('root_cause','')[:90]}")
            print(f"    confidence: {result.get('confidence','')}")

        # Save after every case so a crash/interrupt doesn't lose earlier work
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)

        time.sleep(0.3)  # be polite to the API

    print(f"\nDone. Results saved to {out_path}")
    print("Refresh index.html in your browser to see the AI diagnoses.")


if __name__ == "__main__":
    main()
