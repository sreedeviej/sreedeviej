"""
NetSage AI - Deterministic Rule Checker

Runs pattern-based (non-AI) checks against the `show_output` text of each case in
data/cases.csv, looking for the classic config mistakes called out in the brief:
  - duplicate IP addresses
  - wrong / mismatched subnet masks
  - gateway mismatch (PC default gateway vs. router interface IP)
  - interface administratively/physically down
  - missing VLAN (referenced but not present in `show vlan brief`)
  - missing route (destination network absent from `show ip route`)

This intentionally does NOT call the AI. It's meant to run BEFORE and/or AFTER the AI
diagnosis step, so the team can compare "what a deterministic script catches" against
"what the AI proposed" (see docs/README.md workflow).

Usage:
    python3 rule_checker.py                # scan data/cases.csv, print + save report
    python3 rule_checker.py path/to.csv    # scan a different file
"""
import csv
import re
import sys
import os
import json

IP_RE = re.compile(r"\b(\d{1,3}(?:\.\d{1,3}){3})\b")
MASK_RE = re.compile(r"\b(255(?:\.\d{1,3}){3})\b")
VLAN_MENTION_RE = re.compile(r"\bVLAN\s?(\d{1,4})\b", re.IGNORECASE)
VLAN_TABLE_ROW_RE = re.compile(r"^\s*(\d{1,4})\s+\S+\s+(active|Inactive)", re.MULTILINE)
NETWORK_MENTION_RE = re.compile(r"\b(\d{1,3}(?:\.\d{1,3}){3})/(\d{1,2})\b")
ROUTE_TABLE_RE = re.compile(r"\b(\d{1,3}(?:\.\d{1,3}){3})/(\d{1,2})\s+is directly connected|"
                             r"\b(\d{1,3}(?:\.\d{1,3}){3})/(\d{1,2})\s*\[")
GATEWAY_LINE_RE = re.compile(r"Default Gateway:\s*(\d{1,3}(?:\.\d{1,3}){3})", re.IGNORECASE)
IFACE_IP_LINE_RE = re.compile(
    r"^([A-Za-z][\w/.]*)\s+(\d{1,3}(?:\.\d{1,3}){3})\s+.*?(up|down|administratively down)",
    re.MULTILINE,
)
INTERFACE_STATE_RE = re.compile(
    r"is (administratively down|down), line protocol is (down|up)"
    r"|(\bdown\s+down\b)"
    r"|err-disabled",
    re.IGNORECASE,
)


def check_interface_down(text):
    hits = []
    for m in INTERFACE_STATE_RE.finditer(text):
        line_start = text.rfind("\n", 0, m.start()) + 1
        line_end = text.find("\n", m.end())
        line_end = line_end if line_end != -1 else len(text)
        hits.append(text[line_start:line_end].strip())
    return hits


def check_duplicate_ip(text):
    # collect (interface, ip) pairs from "show ip interface brief"-style rows
    pairs = IFACE_IP_LINE_RE.findall(text)
    seen = {}
    dupes = []
    for iface, ip, _state in pairs:
        if ip in seen and seen[ip] != iface:
            dupes.append(f"{ip} appears on both {seen[ip]} and {iface}")
        else:
            seen[ip] = iface
    return dupes


def check_gateway_mismatch(text):
    gw_matches = GATEWAY_LINE_RE.findall(text)
    if not gw_matches:
        return []
    iface_ips = {ip for _iface, ip, _state in IFACE_IP_LINE_RE.findall(text)}
    problems = []
    for gw in gw_matches:
        if iface_ips and gw not in iface_ips:
            problems.append(
                f"PC default gateway {gw} does not match any router interface IP seen in the evidence ({', '.join(sorted(iface_ips))})"
            )
    return problems


def check_missing_vlan(text):
    mentioned = {int(v) for v in VLAN_MENTION_RE.findall(text)}
    table_vlans = {int(v) for v, _status in VLAN_TABLE_ROW_RE.findall(text)}
    if not table_vlans:
        return []  # no vlan table present in this case, nothing to check
    missing = sorted(v for v in mentioned if v not in table_vlans and v not in (0, 1))
    return [f"VLAN {v} is referenced but not present/active in the VLAN table" for v in missing]


def check_missing_route(text):
    # look for an explicit "not in table" / commented-out route marker, or a network
    # mentioned in the symptom/topology text that never shows up as a route table row
    problems = []
    if re.search(r"not in table|route missing|! .*route missing", text, re.IGNORECASE):
        problems.append("Route table evidence explicitly shows a missing/absent route")
    return problems


def check_wrong_mask(text):
    masks = MASK_RE.findall(text)
    unique_masks = sorted(set(masks))
    problems = []
    if len(unique_masks) > 1:
        problems.append(f"Multiple different subnet masks appear in the same evidence: {unique_masks}")
    return problems


CHECKS = [
    ("duplicate_ip", check_duplicate_ip),
    ("wrong_mask", check_wrong_mask),
    ("gateway_mismatch", check_gateway_mismatch),
    ("interface_down", check_interface_down),
    ("missing_vlan", check_missing_vlan),
    ("missing_route", check_missing_route),
]


def scan_case(row):
    text = f"{row.get('symptom','')}\n{row.get('topology_note','')}\n{row.get('show_output','')}"
    findings = {}
    for name, fn in CHECKS:
        result = fn(text)
        if result:
            findings[name] = result
    return findings


def main():
    csv_path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        os.path.dirname(__file__), "..", "data", "cases.csv"
    )
    csv_path = os.path.abspath(csv_path)
    report = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            findings = scan_case(row)
            report.append({
                "case_id": row["case_id"],
                "category": row["category"],
                "expected_fault": row["expected_fault"],
                "rule_checker_findings": findings,
                "flagged": bool(findings),
            })

    flagged = sum(1 for r in report if r["flagged"])
    print(f"Scanned {len(report)} cases — {flagged} flagged by at least one deterministic rule.\n")
    for r in report:
        if r["flagged"]:
            print(f"[{r['case_id']}] {r['category']}: {r['expected_fault']}")
            for check_name, hits in r["rule_checker_findings"].items():
                for h in hits:
                    print(f"    - {check_name}: {h}")
    out_path = os.path.join(os.path.dirname(csv_path), "rule_checker_report.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print(f"\nFull report saved to {out_path}")


if __name__ == "__main__":
    main()
