# Responsible AI Log

Brief requirement: at least 5 cases where the AI's diagnosis was corrected by a human
reviewer, with notes explaining why. If you're using `netsage_console.html`, the
"Responsible AI log" tab fills this in automatically as you mark cases Edited or
Rejected — export those entries here for the written submission.

| Case ID | Category | AI root cause | Human correction | Why the AI was wrong | Reviewer |
|---|---|---|---|---|---|
| C0__ | | | | | |
| C0__ | | | | | |
| C0__ | | | | | |
| C0__ | | | | | |
| C0__ | | | | | |

## Patterns worth writing up

After 5+ corrections, look for a pattern across them — this is usually the most
interesting part of the write-up:
- Did the AI consistently miss evidence in a certain part of the show output (e.g.
  it reads interface status but not VLAN tables)?
- Did it over-trust one weak signal (e.g. assuming ACL is the cause whenever any ACL
  is shown, even if it's clearly not applied to the relevant interface)?
- Did confidence levels track actual correctness, or was the AI "confidently wrong"
  on some cases?

## Why human review stays mandatory

One sentence for the submission: even at high confidence, the AI's suggestions are
drafts grounded only in the evidence it was shown — it cannot verify physical
topology, cannot run commands itself, and has no way to know what it wasn't told.
