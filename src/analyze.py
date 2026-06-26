"""
LLM judge pass over saved transcripts.
Reads all JSON files from transcripts/ and outputs ranked bug candidates.

Usage:
    python -m src.analyze
    python -m src.analyze --transcript transcripts/20240101_120000_schedule_new.json
"""

import argparse
import json
import sys
from pathlib import Path

import anthropic

from src import config

JUDGE_SYSTEM = """\
You are a QA engineer auditing voice transcripts of an AI medical scheduling agent called "Athena."
Your job is to identify quality bugs, behavioral failures, and edge-case mishandlings.

For each issue found, output a JSON object with these fields:
- severity: "high", "medium", or "low"
- title: short bug title (one line)
- what_happened: what the agent actually said or did
- why_its_a_problem: expected behavior and why the actual behavior is wrong
- evidence: a direct quote from the transcript
- timestamp: the [MM:SS] timestamp from the transcript, or "n/a"

Return a JSON array of issue objects, sorted by severity (high first).
If no issues are found, return an empty array [].

Focus on:
- Confirming appointments on days/times the office should be closed (e.g., weekends)
- Booking without confirming ambiguous dates (e.g., "next Tuesday")
- Missing identity verification before modifying an appointment
- Hallucinated confirmations (confirming something that wasn't actually available)
- Failure to recognize urgent symptoms (chest pain, etc.) and give appropriate guidance
- Ignoring or mishandling out-of-scope requests (helping when it should decline, or harshly refusing a reasonable question)
- Failing to catch contradictory patient information
- Not asking for required information (pharmacy for refills, insurance, DOB)
- Vague or non-committal answers that leave the patient without a clear next step
- Poor turn-taking: talking over the patient, very long monologues, excessive hold/silence
- Incorrect information about hours, services, or policies
- Giving medical advice that should be referred to a clinician
"""

JUDGE_USER_TEMPLATE = """\
Scenario being tested: {scenario}
Test goal: {goal}
Known trap to check for: {trap}

Transcript:
{transcript_text}
"""


def _format_transcript(structured: dict) -> str:
    messages = structured.get("messages", [])
    raw = structured.get("raw_transcript", "")

    if not messages and raw:
        return raw

    lines = []
    for m in messages:
        role = m.get("role", "")
        speaker = "PATIENT" if role in ("assistant", "bot") else "AGENT"
        t = int(m.get("seconds_from_start", 0))
        mins, secs = divmod(t, 60)
        lines.append(f"[{mins:02d}:{secs:02d}] {speaker}: {m.get('content', '')}")

    return "\n".join(lines) if lines else "(empty transcript)"


def analyze_transcript(json_path: Path, client: anthropic.Anthropic) -> list[dict]:
    with open(json_path, encoding="utf-8") as f:
        structured = json.load(f)

    scenario_key = structured.get("scenario", "unknown")
    transcript_text = _format_transcript(structured)

    # Pull metadata from personas for context
    try:
        from src.personas import SCENARIOS
        scenario_meta = SCENARIOS.get(scenario_key, {})
        goal = scenario_meta.get("test_goal", "not specified")
        trap = scenario_meta.get("trap") or "none"
    except Exception:
        goal = "not specified"
        trap = "none"

    user_msg = JUDGE_USER_TEMPLATE.format(
        scenario=scenario_key,
        goal=goal,
        trap=trap,
        transcript_text=transcript_text,
    )

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=2048,
        system=JUDGE_SYSTEM,
        messages=[{"role": "user", "content": user_msg}],
    )

    raw_text = response.content[0].text.strip()

    # Extract JSON array from response (handle markdown code blocks)
    if "```" in raw_text:
        start = raw_text.find("[")
        end = raw_text.rfind("]") + 1
        raw_text = raw_text[start:end] if start != -1 else "[]"

    try:
        issues = json.loads(raw_text)
    except json.JSONDecodeError:
        print(f"  Warning: could not parse LLM response as JSON for {json_path.name}")
        issues = []

    return issues


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run LLM judge over call transcripts to surface bug candidates."
    )
    parser.add_argument(
        "--transcript",
        metavar="PATH",
        help="Analyze a single transcript JSON file (default: all in transcripts/)",
    )
    args = parser.parse_args()

    api_key = config.LLM_API_KEY
    if not api_key:
        print(
            "Error: LLM_API_KEY is not set. Set it in .env to your Anthropic API key.",
            file=sys.stderr,
        )
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)

    if args.transcript:
        paths = [Path(args.transcript)]
    else:
        transcripts_dir = Path(config.TRANSCRIPTS_DIR)
        paths = sorted(transcripts_dir.glob("*.json"))
        if not paths:
            print(f"No JSON transcript files found in {transcripts_dir}/")
            sys.exit(0)

    all_findings: list[dict] = []

    for path in paths:
        print(f"Analyzing {path.name}...")
        try:
            issues = analyze_transcript(path, client)
        except Exception as e:
            print(f"  Error analyzing {path.name}: {e}")
            continue

        for issue in issues:
            issue["source_file"] = path.name
        all_findings.extend(issues)
        print(f"  Found {len(issues)} issue(s)")

    if not all_findings:
        print("\nNo issues found across all transcripts.")
        return

    severity_order = {"high": 0, "medium": 1, "low": 2}
    all_findings.sort(key=lambda x: severity_order.get(x.get("severity", "low"), 99))

    print(f"\n{'='*60}")
    print(f"RANKED BUG CANDIDATES ({len(all_findings)} total)")
    print(f"{'='*60}\n")

    for i, issue in enumerate(all_findings, 1):
        sev = issue.get("severity", "?").upper()
        title = issue.get("title", "untitled")
        source = issue.get("source_file", "?")
        ts = issue.get("timestamp", "n/a")
        print(f"[{i}] [{sev}] {title}")
        print(f"     File: {source}  at {ts}")
        print(f"     What happened: {issue.get('what_happened', '')}")
        print(f"     Why it matters: {issue.get('why_its_a_problem', '')}")
        evidence = issue.get("evidence", "")
        if evidence:
            print(f"     Evidence: \"{evidence}\"")
        print()

    print("Curate these findings into bug_report.md.")


if __name__ == "__main__":
    main()
