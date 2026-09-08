# Demo Video Shot List (5–10 min)

1. **The broken lab (1 min)** — Show the Packet Tracer topology and the symptom live:
   e.g. PC-A can't reach PC-B across VLANs. Run `ping` on the PC to show the failure.
2. **Gathering evidence (1 min)** — Run the actual `show` commands on the real devices
   in Packet Tracer that match what's in `cases.csv` for this case. Paste that output.
3. **AI diagnosis (1–2 min)** — Open `netsage_console.html`, select the matching case
   (or paste your live evidence in), click "Run AI diagnosis." Talk through the JSON:
   root cause, confidence, evidence cited, next command, fix steps.
4. **Deterministic rule checker (1 min)** — Run `python3 scripts/rule_checker.py` in a
   terminal and show it independently flagging the same (or a different) issue —
   explain why a simple script and an AI model can disagree.
5. **Human review (1 min)** — In the console, Accept, Edit, or Reject the diagnosis
   with a reviewer note. If you Reject/Edit, explain what was wrong.
6. **Fix and verify (1 min)** — Apply the actual fix in Packet Tracer, re-run the
   `show` command and `ping` to prove it's resolved.
7. **Dashboard (30 sec)** — Show the Dashboard tab: case counts by category, review
   counts, agreement rate — and the Responsible AI log with corrected cases.
8. **Wrap-up (30 sec)** — One sentence on why human review stayed mandatory even
   though the AI was fast/confident.
