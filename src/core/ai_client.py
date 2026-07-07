"""Gemini Proxy AI Client with Continuous Chat support."""

import json
import re
import requests
from pathlib import Path
from datetime import datetime
from typing import Optional

# ── Logging ──────────────────────────────────────────────────────────

LOG_DIR = Path(__file__).resolve().parent.parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / "ai_proxy.log"

def _log_interaction(payload: dict, response_text: str, row_id: Optional[int] = None) -> None:
    """Append request/response pair to the log file."""
    timestamp = datetime.now().isoformat()
    row_label = f"ROW: {row_id}" if row_id is not None else "GENERAL"
    try:
        log_entry = (
            f"\n{'='*20} {row_label} {'='*20}\n"
            f"TIMESTAMP: {timestamp}\n"
            f"REQUEST PAYLOAD:\n{json.dumps(payload, ensure_ascii=True, indent=2)}\n"
            f"{'-'*40}\n"
            f"RESPONSE TEXT:\n{response_text}\n"
            f"{'='*80}\n"
        )
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(log_entry)
    except Exception as e:
        print(f"  [!] Failed to write to log: {e}")

# ── Configuration ────────────────────────────────────────────────────

# Providers: "GEMINI_PROXY", "OMNIROAD" or "WEB2API"
PROVIDER               = "WEB2API"

# Gemini Proxy Config
API_URL                = "http://127.0.0.1:2048/v1/chat/completions"
NEW_CHAT_URL           = "http://127.0.0.1:2048/api/new-chat"
SYSTEM_INSTRUCTIONS_URL = "http://127.0.0.1:2048/api/system-instructions"
SWITCH_MODEL_URL       = "http://127.0.0.1:2048/api/switch-model"
MODEL_GEMINI           = "gemini-flash-lite-latest"

# OmniRoad Config
OMNIROAD_URL           = "http://localhost:20128/v1/chat/completions"
MODEL_OMNI             = "kr/claude-sonnet-4.5"

# Gemini Web2API Config
WEB2API_URL            = "http://localhost:8081/v1/chat/completions"
MODEL_WEB2API          = "gemini-3.5-flash"

# Active Model (will be chosen based on PROVIDER)
if PROVIDER == "OMNIROAD":
    MODEL = MODEL_OMNI
elif PROVIDER == "WEB2API":
    MODEL = MODEL_WEB2API
else:
    MODEL = MODEL_GEMINI

TIMEOUT                = 180

# ── Prompts ──────────────────────────────────────────────────────────

PROMPTS_FILE = Path(__file__).resolve().parent.parent.parent / "data" / "prompts.json"

def _load_prompts() -> dict[str, str]:
    if not PROMPTS_FILE.exists():
        return {"translate": "", "shadok": ""}
    with open(PROMPTS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

_PROMPTS = _load_prompts()
SYSTEM_PROMPT = _PROMPTS.get("translate", "")
SHADOK_SYSTEM_PROMPT = _PROMPTS.get("shadok", "")

# ── Public API ───────────────────────────────────────────────────────

def init_session() -> None:
    """Initialize session based on provider."""
    # Clear log
    print("  [INIT] Clearing log file...")
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        f.write(f"--- NEW SESSION STARTED AT {datetime.now().isoformat()} | PROVIDER: {PROVIDER} ---\n")

    if PROVIDER in ("OMNIROAD", "WEB2API"):
        print(f"  [INIT] {PROVIDER} ({MODEL}) selected. Ready!")
        return

    # Gemini Proxy initialization
    print("  [INIT] Creating new chat...")
    try:
        resp = requests.post(NEW_CHAT_URL, timeout=15)
        print(f"  [INIT] New chat: OK ({resp.status_code})")
    except Exception as e:
        print(f"  [INIT] WARNING: new-chat failed: {e}")

    # Switch model first
    print(f"  [INIT] Switching model -> {MODEL}...")
    try:
        resp = requests.post(
            SWITCH_MODEL_URL,
            json={"model": MODEL},
            timeout=30,
        )
        print(f"  [INIT] Model switch: OK ({resp.status_code})")
    except Exception as e:
        print(f"  [INIT] WARNING: switch-model failed: {e}")

    # Then set system instructions
    print(f"  [INIT] Setting system instructions...")
    try:
        resp = requests.post(
            SYSTEM_INSTRUCTIONS_URL,
            json={"content": SYSTEM_PROMPT},
            timeout=15,
        )
        print(f"  [INIT] System instructions: OK ({resp.status_code})")
    except Exception as e:
        print(f"  [INIT] WARNING: system-instructions failed: {e}")

    print(f"  [INIT] Ready!")



def init_session_shadok() -> None:
    """Initialize a NEW chat session with shadok-specific system instructions."""
    if PROVIDER in ("OMNIROAD", "WEB2API"):
        print(f"  [SHADOK-INIT] {PROVIDER} ({MODEL}) selected. Ready!")
        return

    print("  [SHADOK-INIT] Creating new chat for Shadok block...")
    try:
        requests.post(NEW_CHAT_URL, timeout=15)
    except Exception as e:
        print(f"  [SHADOK-INIT] WARNING: new-chat failed: {e}")

    print(f"  [SHADOK-INIT] Switching model -> {MODEL}...")
    try:
        requests.post(SWITCH_MODEL_URL, json={"model": MODEL}, timeout=30)
    except Exception as e:
        print(f"  [SHADOK-INIT] WARNING: switch-model failed: {e}")

    print(f"  [SHADOK-INIT] Setting Shadok system instructions...")
    try:
        requests.post(
            SYSTEM_INSTRUCTIONS_URL,
            json={"content": SHADOK_SYSTEM_PROMPT},
            timeout=15,
        )
    except Exception as e:
        print(f"  [SHADOK-INIT] WARNING: system-instructions failed: {e}")

    print(f"  [SHADOK-INIT] Ready!")



def _make_request_with_retry(url: str, safe_data: bytes, payload: dict, row_id: Optional[int] = None, is_shadok: bool = False, is_refine: bool = False) -> dict[str, str]:
    import time
    MAX_RETRIES = 2
    last_error = None
    headers = {"Content-Type": "application/json"}
    
    tag = "SHADOK" if is_shadok else f"Row {row_id}"
    log_id = "SHADOK" if is_shadok else row_id

    for attempt in range(MAX_RETRIES + 1):
        resp_text = "N/A"
        try:
            resp = requests.post(url, data=safe_data, headers=headers, timeout=300 if is_shadok else TIMEOUT)
            resp_text = resp.text

            if resp.status_code != 200:
                if not is_shadok:
                    print(f"  [{tag}] Proxy error {resp.status_code} (attempt {attempt + 1})")
                _log_interaction(payload, resp_text, row_id=log_id)
                raise requests.HTTPError(f"Status {resp.status_code}")

            # For Shadok blocks, fix invalid \' in the raw response text BEFORE parsing JSON
            if is_shadok:
                # Replace backslash-apostrophe with just apostrophe
                # In the raw text, this is literally the two characters: \ and '
                resp_text = resp_text.replace("\\'", "'")

            # Parse JSON manually to handle the response
            data = json.loads(resp_text)
            content = data["choices"][0]["message"]["content"]

            if is_shadok:
                print(f"  [{tag}-DEBUG] content len={len(content)}, first 80: {repr(content[:80])}")

            _log_interaction(payload, resp_text, row_id=log_id)
            return _extract_json(content)

        except Exception as e:
            last_error = e
            if resp_text == "N/A" and hasattr(e, 'response') and e.response is not None:
                resp_text = getattr(e.response, 'text', 'N/A')
            elif resp_text == "N/A" and "resp" in locals():
                resp_text = getattr(resp, 'text', 'N/A')
            _log_interaction(payload, resp_text, row_id=log_id)

            # Debug: show raw bytes of response
            if is_shadok and attempt == 0:
                print(f"  [DEBUG] Raw response bytes (first 300): {resp_text[:300].encode('utf-8')}")

            if attempt < MAX_RETRIES:
                wait = 3 * (attempt + 1) if is_shadok else 2 * (attempt + 1)
                action = "Refine retry" if is_refine else "Retry"
                print(f"  [{tag}] {action} {attempt + 1}/{MAX_RETRIES} in {wait}s...")
                time.sleep(wait)
            else:
                action_fail = "All retries failed" if not is_refine else "Refine retries exhausted"
                print(f"  [{tag}] {action_fail}. Reinitializing...")
                try:
                    if is_shadok:
                        init_session_shadok()
                    else:
                        init_session()
                    time.sleep(1)
                    resp = requests.post(url, data=safe_data, headers=headers, timeout=300 if is_shadok else TIMEOUT)
                    resp_text = resp.text

                    # For Shadok blocks, fix invalid \' in raw response
                    if is_shadok:
                        resp_text = resp_text.replace("\\'", "'")

                    if resp.status_code == 200:
                        data = json.loads(resp_text)
                        content = data["choices"][0]["message"]["content"]

                        if is_shadok:
                            print(f"  [{tag}-DEBUG] content len={len(content)}:\n{content}\n" + "-"*40)

                        _log_interaction(payload, resp_text, row_id=log_id)
                        return _extract_json(content)
                except Exception as recovery_error:
                    print(f"  [{tag}] Recovery failed: {recovery_error}")
                    _log_interaction(payload, str(recovery_error), row_id=log_id)

    raise RuntimeError(f"Translation failed after {MAX_RETRIES} retries + session recovery: {last_error}")


def translate_shadok_block(full_text: str, target_langs: list[str], max_line_length: int) -> dict[str, str]:
    """Translate the full Shadok text as one literary block."""
    import time

    user_content = json.dumps(
        {"text": full_text, "languages": target_langs},
        ensure_ascii=True
    )

    if PROVIDER in ("OMNIROAD", "WEB2API"):
        messages = [
            {"role": "system", "content": SHADOK_SYSTEM_PROMPT},
            {"role": "user", "content": user_content}
        ]
        url = OMNIROAD_URL if PROVIDER == "OMNIROAD" else WEB2API_URL
    else:
        messages = [{"role": "user", "content": user_content}]
        url = API_URL

    payload = {
        "model": MODEL,
        "messages": messages,
        "stream": False,
    }

    # SAFE ENCODING: We manually dump and encode to ensure non-ASCII characters 
    # are escaped as \uXXXX. This prevents proxy-level encoding corruption.
    safe_data = json.dumps(payload, ensure_ascii=True).encode('utf-8')
    return _make_request_with_retry(url, safe_data, payload, row_id=None, is_shadok=True)


def translate_batch(text: str, target_langs: list[str], row_id: Optional[int] = None) -> dict[str, str]:
    """Translate text with automatic retry and session recovery."""
    import time

    user_content = json.dumps(
        {"text": text, "languages": target_langs},
        ensure_ascii=True
    )

    if PROVIDER in ("OMNIROAD", "WEB2API"):
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content}
        ]
        url = OMNIROAD_URL if PROVIDER == "OMNIROAD" else WEB2API_URL
    else:
        messages = [{"role": "user", "content": user_content}]
        url = API_URL

    payload = {
        "model": MODEL,
        "messages": messages,
        "stream": False,
    }

    # SAFE ENCODING
    safe_data = json.dumps(payload, ensure_ascii=True).encode('utf-8')
    return _make_request_with_retry(url, safe_data, payload, row_id=row_id, is_shadok=False)


def refine(correction: str, target_langs: list[str], row_id: Optional[int] = None) -> dict[str, str]:
    """Send a correction into the existing chat, with retry logic."""
    import time

    user_content = (
        f"{correction}\n\n"
        f"Return the corrected full JSON object with ALL languages: "
        f"{', '.join(target_langs)}."
    )

    if PROVIDER in ("OMNIROAD", "WEB2API"):
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content}
        ]
        url = OMNIROAD_URL if PROVIDER == "OMNIROAD" else WEB2API_URL
    else:
        messages = [{"role": "user", "content": user_content}]
        url = API_URL

    payload = {
        "model": MODEL,
        "messages": messages,
        "stream": False,
    }

    MAX_RETRIES = 2
    last_error = None

    for attempt in range(MAX_RETRIES + 1):
        resp_text = "N/A"
        try:
            resp = requests.post(url, json=payload, timeout=TIMEOUT)
            resp_text = resp.text

            if resp.status_code != 200:
                _log_interaction(payload, resp_text, row_id=row_id)
                raise requests.HTTPError(f"Status {resp.status_code}")

            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            _log_interaction(payload, resp_text, row_id=row_id)
            return _extract_json(content)

        except Exception as e:
            last_error = e
            if resp_text == "N/A" and "resp" in locals():
                resp_text = getattr(resp, 'text', 'N/A')
            _log_interaction(payload, resp_text, row_id=row_id)

            if attempt < MAX_RETRIES:
                wait = 2 * (attempt + 1)
                print(f"  [Row {row_id}] Refine retry {attempt + 1}/{MAX_RETRIES} in {wait}s...")
                time.sleep(wait)
            else:
                print(f"  [Row {row_id}] Refine retries exhausted. Reinitializing session...")
                try:
                    init_session()
                    time.sleep(1)
                    resp = requests.post(url, data=safe_data, headers=headers, timeout=TIMEOUT)
                    resp_text = resp.text
                    if resp.status_code == 200:
                        data = resp.json()
                        content = data["choices"][0]["message"]["content"]
                        _log_interaction(payload, resp_text, row_id=row_id)
                        return _extract_json(content)
                except Exception as recovery_error:
                    print(f"  [Row {row_id}] Refine recovery failed: {recovery_error}")

    raise RuntimeError(f"Refine failed after {MAX_RETRIES} retries + recovery: {last_error}")


# ── Helpers ──────────────────────────────────────────────────────────

def _extract_json(content: str) -> dict[str, str]:
    """Robustly extract a JSON object from AI response text.

    Handles cases where:
    - AI wraps JSON in ```json ... ``` code blocks
    - AI adds "thinking" text before the JSON
    - Translations contain unescaped quotes inside JSON string values
    """
    content = content.strip()

    # Step 1: Strip markdown code block if present
    code_block_match = re.search(r"```(?:json)?\s*(.*?)\s*```", content, re.DOTALL)
    if code_block_match:
        content = code_block_match.group(1).strip()

    # Step 2: Find the first { and last } — that's our JSON envelope
    first_brace = content.find("{")
    last_brace = content.rfind("}")

    if first_brace < 0 or last_brace <= first_brace:
        raise json.JSONDecodeError("No JSON object found in AI response", content, 0)

    json_str = content[first_brace:last_brace + 1]

    # Step 3: Fix invalid \' sequences using regex
    # Match backslash followed by single quote
    original_len = len(json_str)
    json_str = re.sub(r"\\\'", "'", json_str)
    fixed_len = len(json_str)

    if original_len != fixed_len:
        print(f"  [DEBUG] Fixed {(original_len - fixed_len)} backslash-apostrophe sequences")
        print(f"  [DEBUG] First 200 after fix: {repr(json_str[:200])}")

    return _parse_json_safe(json_str)


def _find_outer_brace(text: str) -> str | None:
    """Find the outermost { ... } in text using brace-depth tracking.
    
    Properly handles:
    - Escaped characters inside JSON strings
    - Nested braces inside string values
    """
    start = text.find("{")
    if start < 0:
        return None
    
    depth = 0
    in_string = False
    escape = False
    
    for i in range(start, len(text)):
        c = text[i]
        if escape:
            escape = False
            continue
        if c == "\\":
            escape = True
            continue
        if c == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return text[start:i + 1]
    
    return None


def _parse_json_safe(json_str: str) -> dict[str, str]:
    """Parse JSON string with common AI mistake fixes.

    Handles:
    - Trailing commas
    - Unescaped double quotes inside values
    - Invalid escape sequences
    """
    # Fix trailing commas
    json_str = re.sub(r",\s*}", "}", json_str)
    json_str = re.sub(r",\s*]", "]", json_str)

    # Convert literal newlines to spaces
    json_str = json_str.replace('\n', ' ')

    try:
        return json.loads(json_str)
    except json.JSONDecodeError as decode_err:
        print(f"  [DEBUG] json.loads failed: {decode_err}")
        print(f"  [DEBUG] json_str dump: {repr(json_str)}")

        # Try to extract the actual error position and show context
        if hasattr(decode_err, 'pos'):
            pos = decode_err.pos
            start = max(0, pos - 50)
            end = min(len(json_str), pos + 50)
            context = json_str[start:end]
            print(f"  [DEBUG] Error context: ...{repr(context)}...")
        pass
    
    # Fallback: manually extract "key": "value" pairs
    # This handles cases where AI puts unescaped " inside values
    result = {}
    # Match: "lang_code" : "...text..." followed by , or }
    # [a-z0-9] supports codes like es419, ptbr, zhcn, zhtw, frca, engb
    pairs = re.finditer(r'"([a-z0-9]{2,6})"\s*:\s*"', json_str)
    
    for match in pairs:
        key = match.group(1)
        val_start = match.end()  # position right after the opening quote of value
        
        # Find the closing quote of this value:
        # Look for " followed by , or } or end of string
        # This handles unescaped " inside the value
        val_end = None
        for end_match in re.finditer(r'"(?:\s*[,}]|\s*$)', json_str[val_start:]):
            candidate = val_start + end_match.start()
            # Make sure this isn't the start of the next key
            remaining = json_str[candidate + 1:].lstrip()
            if remaining.startswith(',') or remaining.startswith('}') or not remaining:
                val_end = candidate
                break
        
        if val_end is not None:
            value = json_str[val_start:val_end]
            # Replace any unescaped double quotes with single quotes in the value
            value = value.replace('"', "'")
            result[key] = value
    
    if result:
        return result
    
    raise json.JSONDecodeError("Failed to parse JSON even with fallback", json_str, 0)
