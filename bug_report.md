# Bug Report — Pretty Good AI Agent QA

Findings from automated voice testing of the Athena scheduling agent across 10 scenarios.
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
A scheduling agent must never fabricate patient demographics. A wrong DOB attached to a real patient record could cause identity mismatches, incorrect eligibility checks, or medication errors downstream.

**Evidence:**
> "Your patient profile is set up. And your date of birth is July 4th 2000 for demo purposes. How may I help you today?"

---

### BUG-002: Doctor name stated inconsistently within the same call

**Severity:** High
**Call:** `transcripts/20260625_051336_schedule_new.txt` at `[01:48]` and `[02:07]`
**Scenario:** `schedule_new`

**What happened:**
When offering slots the agent said "doctor doctor Duvy Houser." Two turns later during confirmation it said "doctor Dougie Hauser." Two different names for the same provider in the same call with no correction.

**Why it's a problem:**
A patient leaving the call has no reliable name for their doctor. If they try to confirm the appointment or look up the provider, neither name may match what is in the system.

**Evidence:**
> "I found openings with doctor doctor Duvy Houser on Thursday, July 2nd." … "You are scheduled for a new patient checkup with doctor Dougie Hauser on Thursday, July 2nd at 10 30 AM."

---

### BUG-003: Agent claims appointment exists, then admits it cannot access it

**Severity:** High
**Call:** `transcripts/20260625_052149_schedule_new.txt` at `[01:02]` and `[01:28]`
**Scenario:** `schedule_new`

**What happened:**
Agent stated "Looks like you already have a new patient consultation appointment booked" — then two turns later said "I can't access your current appointment details directly." The patient had explicitly said this should be their first appointment, and the contradiction was never resolved.

**Why it's a problem:**
The agent hallucinated a confirmation it could not actually verify, then contradicted itself. This creates confusion and erodes trust in any information the agent provides.

**Evidence:**
> "Looks like you already have a new patient consultation appointment booked." [01:02]
> "I can't access your current appointment details directly." [01:28]

---

### BUG-004: Security verification bypassed with "for demo purposes"

**Severity:** High
**Call:** `transcripts/20260626_185229_schedule_new.txt` at `[02:11]`
**Scenario:** `schedule_new`

**What happened:**
Agent said "The birthday doesn't match our records, but for demo purposes, I'll accept it" and then continued booking the appointment anyway.

**Why it's a problem:**
Identity verification is a hard gate, not a suggestion. Overriding it — even with a "demo purposes" caveat — signals that the agent can be social-engineered into bypassing verification. In a production system this would expose patient records.

**Evidence:**
> "The birthday doesn't match our records, but for demo purposes, I'll accept it. Let's get started with booking your new patient appointment."

---

### BUG-005: Agent repeatedly fails to complete tasks and transfers to dead test line

**Severity:** High
**Calls:** `reschedule`, `cancel`, `refill_lisinopril`, `refill_esomeprazole`, `insurance_check`, `weekend_trap`, `ambiguous_date`
**Scenario:** Multiple

**What happened:**
Across 7 of 10 calls, after collecting identity information, the agent said some variant of "I can't proceed further right now" and transferred to a line that immediately responded "You've reached the Pretty Good AI test line. Goodbye." — disconnecting the patient with no resolution.

**Why it's a problem:**
This is the most widespread and severe failure pattern. The agent consistently collects patient data, then abandons the task and transfers to a non-functional line. Patients leave every one of these calls without what they called for: a reschedule, cancellation, refill, or insurance answer.

**Evidence (cancel scenario):**
> "Connecting you to a representative. Please wait. Hello. You've reached the Pretty Good AI test line. Goodbye." [02:05]

---

### BUG-006: Agent never informs caller that office is closed on weekends

**Severity:** High
**Call:** `transcripts/20260626_191806_weekend_trap.txt` at `[03:18]`
**Scenario:** `weekend_trap`

**What happened:**
Patient asked for Sunday availability five times across the call. Agent spent 3+ minutes on identity verification without addressing the question, then finally said "I can't schedule the appointment right now" — never explaining that the office is closed on weekends or offering a weekday alternative.

**Why it's a problem:**
A patient who only works weekdays leaves the call with no clarity on whether weekend appointments exist and no path forward.

**Evidence:**
> "I can't schedule the appointment right now, but I'll make sure our clinic support team follows up with you." [03:18] — no mention of weekend closure.

---

### BUG-007: Agent never asks for pharmacy or prescribing doctor on refill requests

**Severity:** High
**Call:** `transcripts/20260626_190240_refill_lisinopril.txt`
**Scenario:** `refill_lisinopril`

**What happened:**
Agent collected name, DOB, and phone number but never asked which pharmacy to send the refill to or who the prescribing doctor is before failing out. Patient mentioned urgency ("only have about a week left") which was also ignored.

**Why it's a problem:**
A refill cannot be processed without pharmacy destination and prescribing physician. The agent collected the wrong information and abandoned the task, leaving a patient with a week of blood pressure medication potentially without a refill.

**Evidence:**
> Agent collected: name, DOB, phone. Agent never asked: pharmacy or prescribing physician. Then transferred to dead line.

---

## Medium Severity

### BUG-008: Ambiguous date "next Tuesday" accepted without calendar confirmation

**Severity:** Medium
**Call:** `transcripts/20260626_192200_ambiguous_date.txt` at `[00:16]`
**Scenario:** `ambiguous_date`

**What happened:**
Patient said "I'd like to schedule an appointment for next Tuesday." Agent began identity verification without ever asking which specific calendar date "next Tuesday" refers to.

**Why it's a problem:**
"Next Tuesday" is ambiguous depending on when the call occurs. Booking without confirming the exact date risks scheduling the wrong week.

**Evidence:**
> Patient: "I'd like to schedule an appointment for next Tuesday." Agent proceeds directly to identity verification with no date clarification.

---

### BUG-009: Excessive repetitive identity verification drives patient frustration

**Severity:** Medium
**Calls:** `cancel`, `insurance_check`, `weekend_trap`
**Scenario:** Multiple

**What happened:**
Across multiple calls, the agent asked patients to confirm their name and/or date of birth 3+ times in the same conversation. In `insurance_check`, the agent asked for name spelling three separate times before ultimately declining to answer the insurance question.

**Why it's a problem:**
Repetitive verification creates friction for legitimate callers and does not improve security. Collecting identity data three times for a simple informational question (like "do you accept Aetna?") is particularly egregious — basic eligibility questions should not require full patient verification.

**Evidence (insurance_check):**
> Agent asked for name/DOB spelling at [01:23], [01:45], and [02:00] — then said "I can't confirm insurance details right now."

---

### BUG-010: Agent's final confirmation message cut off mid-sentence

**Severity:** Low
**Call:** `transcripts/20260625_051336_schedule_new.txt` at `[02:13]`
**Scenario:** `schedule_new`

**What happened:**
After confirming the appointment the agent began a follow-up statement that ended abruptly: "At Pivot" — the call ended before the sentence was complete.

**Why it's a problem:**
Patient never heard the full office name or any closing instructions. Also signals a possible call-termination timing bug.

**Evidence:**
> "At Pivot"

---

*Generated from `python -m src.analyze` across 10 test calls. Remaining 4 scenarios (`topic_switch`, `out_of_scope`, `inconsistent_info`, `urgent_caller`) pending daily call limit reset.*
