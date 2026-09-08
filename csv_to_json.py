"""
csv_to_json.py — converts data/cases.csv into data/cases.json so the static
frontend (index.html/script.js) can load it with a plain fetch() call.

Usage:
    python3 scripts/csv_to_json.py
"""
import csv
import json
import os

def main():
    base = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    csv_path = os.path.join(base, "data", "cases.csv")
    json_path = os.path.join(base, "data", "cases.json")

    cases = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            cases.append(row)

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(cases, f, indent=2)

    print(f"Wrote {len(cases)} cases to {json_path}")

if __name__ == "__main__":
    main()
