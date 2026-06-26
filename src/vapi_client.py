import json
import time
import requests
from pathlib import Path

from src import config
from src.personas import Scenario


def _headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {config.VAPI_API_KEY}",
        "Content-Type": "application/json",
    }


def build_call_payload(scenario: Scenario) -> dict:
    """Build the Vapi API payload for a scenario. No network calls."""
    transcriber: dict = {"provider": "deepgram", "model": "nova-2", "language": "en"}

    model: dict = {
        "provider": "openai",
        "model": "gpt-4o-mini",
        "systemPrompt": scenario["system_prompt"],
    }

    assistant: dict = {
        "transcriber": transcriber,
        "model": model,
        "voice": scenario["voice"],
        "recordingEnabled": True,
        "endCallFunctionEnabled": True,
        "maxDurationSeconds": scenario.get("max_duration_seconds", 240),
        "silenceTimeoutSeconds": 30,
        # Let the remote party finish their full greeting before the bot speaks
        "startSpeakingPlan": {
            "waitSeconds": 2.0,
            "smartEndpointingEnabled": True,
        },
    }

    return {
        "phoneNumberId": config.VAPI_PHONE_NUMBER_ID,
        "customer": {"number": config.TARGET_PHONE_NUMBER},
        "assistant": assistant,
    }


def create_call(scenario: Scenario) -> str:
    """Place an outbound call. Returns the Vapi call ID."""
    payload = build_call_payload(scenario)
    try:
        resp = requests.post(
            f"{config.VAPI_BASE_URL}/call",
            headers=_headers(),
            json=payload,
            timeout=30,
        )
        resp.raise_for_status()
    except requests.HTTPError as e:
        body = e.response.text if e.response is not None else ""
        raise RuntimeError(f"Vapi create_call failed ({e.response.status_code}): {body}") from e
    except requests.RequestException as e:
        raise RuntimeError(f"Vapi create_call network error: {e}") from e

    data = resp.json()
    call_id: str = data["id"]
    return call_id


def get_call(call_id: str) -> dict:
    """Fetch a call object by ID."""
    try:
        resp = requests.get(
            f"{config.VAPI_BASE_URL}/call/{call_id}",
            headers=_headers(),
            timeout=30,
        )
        resp.raise_for_status()
    except requests.HTTPError as e:
        body = e.response.text if e.response is not None else ""
        raise RuntimeError(f"Vapi get_call failed ({e.response.status_code}): {body}") from e
    except requests.RequestException as e:
        raise RuntimeError(f"Vapi get_call network error: {e}") from e

    return resp.json()


def poll_until_complete(call_id: str, timeout: int = 360) -> dict:
    """Poll every 10 seconds until status is 'ended'. Returns the final call object."""
    start = time.time()
    poll_interval = 10

    while True:
        call = get_call(call_id)
        status = call.get("status", "unknown")
        elapsed = int(time.time() - start)
        print(f"  [{elapsed}s] call {call_id[:8]}... status: {status}")

        if status == "ended":
            # Brief wait for Vapi to finalize artifacts (recording URL, transcript)
            time.sleep(8)
            return get_call(call_id)

        if time.time() - start > timeout:
            raise TimeoutError(
                f"Call {call_id} did not complete within {timeout}s (last status: {status})"
            )

        time.sleep(poll_interval)


def download_recording(recording_url: str, dest_path: Path) -> None:
    """Download a recording from a URL and write it to dest_path."""
    try:
        resp = requests.get(recording_url, timeout=120, stream=True)
        resp.raise_for_status()
    except requests.RequestException as e:
        raise RuntimeError(f"Failed to download recording from {recording_url}: {e}") from e

    dest_path.parent.mkdir(parents=True, exist_ok=True)
    with open(dest_path, "wb") as f:
        for chunk in resp.iter_content(chunk_size=16384):
            f.write(chunk)


def save_artifacts(
    call_id: str,
    scenario_key: str,
    call: dict,
    timestamp: str,
) -> dict[str, Path | None]:
    """
    Download recording and write transcript files.
    Returns paths: {"recording": Path|None, "txt": Path, "json": Path}
    """
    recordings_dir = Path(config.RECORDINGS_DIR)
    transcripts_dir = Path(config.TRANSCRIPTS_DIR)
    recordings_dir.mkdir(exist_ok=True)
    transcripts_dir.mkdir(exist_ok=True)

    stem = f"{timestamp}_{scenario_key}"
    artifact = call.get("artifact", {})

    # --- Recording ---
    recording_path: Path | None = None
    recording_url = artifact.get("recordingUrl")
    if recording_url:
        recording_path = recordings_dir / f"{stem}.mp3"
        try:
            download_recording(recording_url, recording_path)
        except RuntimeError as e:
            print(f"  Warning: could not download recording — {e}")
            recording_path = None
    else:
        print("  Warning: no recording URL on call object (may still be processing)")

    # --- Transcript ---
    messages = call.get("messages", [])
    raw_transcript = artifact.get("transcript", "")

    structured_messages = []
    for m in messages:
        role = m.get("role", "")
        if role not in ("user", "assistant", "bot", "tool"):
            continue
        if role == "tool":
            continue
        structured_messages.append({
            "role": role,
            "content": m.get("message", ""),
            "seconds_from_start": m.get("secondsFromStart", 0),
        })

    structured = {
        "call_id": call_id,
        "scenario": scenario_key,
        "timestamp": timestamp,
        "status": call.get("status"),
        "ended_reason": call.get("endedReason"),
        "messages": structured_messages,
        "raw_transcript": raw_transcript,
    }

    # Plain-text transcript — role "assistant"/"bot" = our patient bot, "user" = the agent
    lines = [
        f"Call ID : {call_id}",
        f"Scenario: {scenario_key}",
        f"Date    : {timestamp}",
        "=" * 60,
        "",
    ]
    if structured_messages:
        for msg in structured_messages:
            role = msg["role"]
            speaker = "PATIENT" if role in ("assistant", "bot") else "AGENT"
            t = int(msg["seconds_from_start"])
            mins, secs = divmod(t, 60)
            lines.append(f"[{mins:02d}:{secs:02d}] {speaker}: {msg['content']}")
    elif raw_transcript:
        lines.append(raw_transcript)
    else:
        lines.append("(no transcript available)")

    txt_path = transcripts_dir / f"{stem}.txt"
    json_path = transcripts_dir / f"{stem}.json"
    txt_path.write_text("\n".join(lines), encoding="utf-8")
    json_path.write_text(json.dumps(structured, indent=2, ensure_ascii=False), encoding="utf-8")

    return {"recording": recording_path, "txt": txt_path, "json": json_path}
