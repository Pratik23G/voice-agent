# Pretty Good AI — Voice Bot QA Challenge

An automated voice bot that places outbound calls to a medical scheduling AI agent, simulates realistic patient scenarios, and surfaces quality bugs. The bot uses Vapi for telephony and voice, runs 14 distinct patient personas, and records full conversations with transcripts.

## Quick Start (local dev)

```bash
# 1. Clone and enter the repo
cd voice-agent

# 2. Create and activate venv
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure credentials
cp .env.example .env
# Edit .env — fill in VAPI_API_KEY and VAPI_PHONE_NUMBER_ID

# 5. Verify config (no call placed)
python -m src.run_call --scenario schedule_new --dry-run

# 6. Run a single call
python -m src.run_call --scenario schedule_new

# 7. Run all 14 scenarios
python -m src.run_call --all

# 8. Analyze transcripts for bugs (requires LLM_API_KEY in .env)
python -m src.analyze
```

## Prerequisites

- Python 3.11 or higher
- A Vapi account (vapi.ai) with a provisioned US phone number
- Your Vapi private API key and phone number ID (from the Vapi dashboard)
- Optionally: an Anthropic API key for running `analyze.py`

## Setup

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# Fill in .env with your credentials (see below)
```

### Required values in `.env`

| Variable               | Where to find it                                                     |
| ---------------------- | -------------------------------------------------------------------- |
| `VAPI_API_KEY`         | Vapi dashboard > Org Settings > API Keys > Private key               |
| `VAPI_PHONE_NUMBER_ID` | Vapi dashboard > Phone Numbers > select your US number > copy the ID |

### Optional values in `.env`

| Variable           | Purpose                                                              |
| ------------------ | -------------------------------------------------------------------- |
| `DEEPGRAM_API_KEY` | BYO Deepgram key (reduces STT cost; Vapi's default works without it) |
| `LLM_API_KEY`      | Anthropic API key required only for running `analyze.py`             |

`TARGET_PHONE_NUMBER` is pre-set to `+18054398008` (the test line). Do not change it.

## Running calls

List all available scenarios:

```bash
python -m src.run_call --list
```

**Run a single scenario:**

```bash
python -m src.run_call --scenario schedule_new
```

**Run all 14 scenarios sequentially:**

```bash
python -m src.run_call --all
```

**Dry run — see the payload without placing any call:**

```bash
python -m src.run_call --scenario weekend_trap --dry-run
```

## Outputs

- **Recordings:** `recordings/<timestamp>_<scenario>.mp3`
- **Transcripts:** `transcripts/<timestamp>_<scenario>.txt` and `.json`

Both directories are gitignored. One timestamped file set is written per call.

## Running the analysis

After collecting transcripts, run the LLM judge to surface bug candidates:

```bash
python -m src.analyze
```

This reads all JSON files in `transcripts/`, sends each to Claude Haiku, and prints a ranked list of issues. Set `LLM_API_KEY` in `.env` to your Anthropic API key before running. Curate the output into `bug_report.md`.

## Available scenarios

| Key                   | Description                                                      |
| --------------------- | ---------------------------------------------------------------- |
| `schedule_new`        | New patient scheduling first appointment                         |
| `reschedule`          | Reschedule existing appointment due to work conflict             |
| `cancel`              | Cancel an upcoming appointment                                   |
| `refill_lisinopril`   | Medication refill — simple drug name                             |
| `refill_esomeprazole` | Medication refill — hard-to-pronounce drug name                  |
| `office_hours`        | Office hours and Saturday availability inquiry                   |
| `insurance_check`     | Insurance coverage and co-pay questions                          |
| `location_parking`    | Office address and parking inquiry                               |
| `weekend_trap`        | Trap: request Sunday/Saturday appointment                        |
| `ambiguous_date`      | Trap: schedule "next Tuesday" without specifying exact date      |
| `topic_switch`        | Mid-call pivot from scheduling to medication refill              |
| `out_of_scope`        | Out-of-scope requests (jury duty note, OTC advice)               |
| `inconsistent_info`   | Trap: contradictory name and date of birth                       |
| `urgent_caller`       | Urgent symptom (chest tightness) + impatient interrupting caller |

## Cost

Well under $10 total for 14+ calls (typically 1–3 minutes each), comfortably within Vapi's free credit. Using BYO `DEEPGRAM_API_KEY` or `LLM_API_KEY` reduces per-call cost further but is not required.

## Constraints

- The bot only dials `TARGET_PHONE_NUMBER` (`+18054398008`). No other number is ever called.
- Never commit `.env` or any file containing real API keys. Both are gitignored.
