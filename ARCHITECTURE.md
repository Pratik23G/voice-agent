# Architecture

> For visual diagrams of the call lifecycle and artifact pipeline, see the [Architecture section in README](./README.md#architecture).

## How It Works

A thin Python harness calls the Vapi REST API to place outbound phone calls to the Pretty Good AI test line. For each scenario, the harness builds a transient Vapi "assistant" object inline — rather than referencing a saved assistant — so every call gets exactly the right persona and goal without any Vapi dashboard configuration. Vapi handles the full voice stack: Deepgram for speech-to-text, GPT-4o-mini for the patient LLM, and OpenAI TTS for the voice. Once a call is placed, the harness polls `GET /call/{id}` every 10 seconds until `status` is `"ended"`, then downloads the recording from `artifact.recordingUrl` and writes both a human-readable `.txt` transcript and a structured `.json` file from the `messages` array. A second LLM pass (`analyze.py`) reads every saved transcript and uses Claude Haiku to surface ranked bug candidates, which are then curated into `bug_report.md`.

## Key Design Choices

Vapi was chosen over a self-hosted media-stream pipeline (e.g., Twilio + WebSockets + Whisper) because it provides production-grade voice quality — natural turn-taking, low latency, reliable STT — without the operational overhead, and its free credit covers the full project comfortably under the $20 budget. Transient (inline) assistants were chosen over saved assistants so the code is the single source of truth for every persona: no out-of-band state in the Vapi dashboard, and persona changes only require editing `personas.py`. GPT-4o-mini was chosen for the patient bot because its low latency translates directly to better conversational flow; the patient bot does not need deep reasoning, just natural, brief responses. The 14 scenarios are designed to cover both the happy path and specific edge-case traps that are known failure modes for medical scheduling agents: weekend booking, date ambiguity, mid-call topic switches, medication name handling, and urgent symptom triage.
