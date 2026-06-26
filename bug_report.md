# Bug Report — Pretty Good AI Agent QA

Findings from automated voice testing of the Athena scheduling agent.
Each entry was identified by the patient bot, confirmed by listening to the recording, and curated from `python -m src.analyze` output.

---

## High Severity

### BUG-001: Agent auto-assigns fabricated date of birth without asking

**Severity:** High
**Call:** `transcripts/20260625_051336_schedule_new.txt` at `[00:41]`
**Scenario:** `schedule_new`

**What happened:**
When the patient gave only their name (Maria Johnson), the agent immediately responded: "Your patient profile is set up. And your date of birth is July 4th 2000 for demo purposes." It invented a date of birth and assigned it to the patient record without ever asking.

**Why it's a problem:**
A scheduling agent must never fabricate patient demographics. A wrong DOB attached to a real patient record could cause identity mismatches, incorrect eligibility checks, or medication errors downstream. The agent should have asked for the DOB before creating any profile.

**Evidence:**
> "Your patient profile is set up. And your date of birth is July 4th 2000 for demo purposes. How may I help you today?"

---

## Medium Severity

### BUG-002: Doctor name stated inconsistently within the same call

**Severity:** Medium
**Call:** `transcripts/20260625_051336_schedule_new.txt` at `[01:48]` and `[02:07]`
**Scenario:** `schedule_new`

**What happened:**
When offering appointment slots the agent said "doctor doctor Duvy Houser." Two turns later, when confirming the booking, it said "doctor Dougie Hauser." Two different names for the same provider in the same call, with no correction.

**Why it's a problem:**
A patient leaving the call has no reliable name for their doctor. If they try to confirm the appointment or look up the provider, neither name may match what is in the system. This erodes trust and creates a support burden.

**Evidence:**
> "I found openings with doctor doctor Duvy Houser on Thursday, July 2nd." … "You are scheduled for a new patient checkup with doctor Dougie Hauser on Thursday, July 2nd at 10 30 AM."

---

## Low Severity

### BUG-003: Agent's final confirmation message cut off mid-sentence

**Severity:** Low
**Call:** `transcripts/20260625_051336_schedule_new.txt` at `[02:13]`
**Scenario:** `schedule_new`

**What happened:**
After confirming the appointment the agent began a follow-up statement that ended abruptly: "At Pivot" — the call ended before the sentence was complete. The patient never heard the full office name or any closing instructions.

**Why it's a problem:**
The patient hangs up without knowing the full office address or name. A clean closing (office name, address, any prep instructions) is expected. The truncated ending may also signal a call-termination timing bug.

**Evidence:**
> "At Pivot"

---

*Additional findings will be added here after all 14 scenarios are run and analyzed with `python -m src.analyze`.*
