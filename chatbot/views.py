import json
import os
import time
import traceback
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeout

import requests
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

OR_BASE = "https://openrouter.ai/api/v1"

SYSTEM_PROMPT = (
    "You are BRO, a helpful, friendly, clear and intelligent AI assistant. "
    "Answer naturally and keep answers clear and useful. "
    "Use the conversation so far to remember what the user has told you, "
    "but don't mention the history unless asked."
)

# Used only if the live model lookup fails. Free model names change often,
# so the code normally fetches the current list from OpenRouter instead.
FALLBACK_TEXT_MODELS = [
    "nvidia/nemotron-3-super-120b-a12b:free",
    "nvidia/nemotron-3.5-lightning:free",
    "poolside/laguna-s-2.1:free",
    "google/gemma-4-31b-it:free",
]

# Models that worked from a plain API call. Tried first.
PREFERRED_TEXT_MODELS = [
    "nvidia/nemotron-3.5-lightning:free",
    "nvidia/nemotron-3-super-120b-a12b:free",
]

# model id -> unix time until which we skip it (failed models get benched)
_blocked = {}

# One hung model must never freeze the whole request, so each call runs in a
# thread with a hard deadline. 3 models x 25s stays under gunicorn's timeout.
_executor = ThreadPoolExecutor(max_workers=8)
PER_MODEL_DEADLINE = 25
MAX_MODELS_PER_REQUEST = 3


def _block(model, seconds):
    _blocked[model] = time.time() + seconds
    print(f"BENCHING {model} for {seconds}s")


def _is_blocked(model):
    return _blocked.get(model, 0) > time.time()


# cache: (list_of_model_ids, timestamp)
_cache = {"text": ([], 0.0), "video": ([], 0.0)}
CACHE_SECONDS = 3600


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------
def _api_key():
    key = os.getenv("OPENROUTER_API_KEY")
    if not key:
        raise Exception("OPENROUTER_API_KEY is missing. Check your environment variables.")
    return key


def _headers():
    return {
        "Authorization": f"Bearer {_api_key()}",
        "Content-Type": "application/json",
    }


def get_client():
    # timeout keeps a slow model from running past gunicorn's time limit;
    # max_retries=0 because we do our own fallback across models.
    return OpenAI(
        api_key=_api_key(),
        base_url=OR_BASE,
        timeout=20,
        max_retries=0,
    )


def _all_zero(pricing):
    """True only if the model has pricing info and every price is 0."""
    if not isinstance(pricing, dict) or not pricing:
        return False
    try:
        return all(float(v) == 0 for v in pricing.values())
    except (TypeError, ValueError):
        return False


def get_free_text_models():
    """Live list of free text-output models (largest context first), cached 1 hour."""
    models, ts = _cache["text"]
    if models and time.time() - ts < CACHE_SECONDS:
        return models

    try:
        r = requests.get(f"{OR_BASE}/models", timeout=10)
        r.raise_for_status()
        found = []
        for m in r.json().get("data", []):
            outputs = m.get("architecture", {}).get("output_modalities", ["text"])
            if (
                m.get("id", "").endswith(":free")
                and outputs == ["text"]
                and _all_zero(m.get("pricing"))
            ):
                found.append((m.get("context_length") or 0, m["id"]))

        by_context = [mid for _, mid in sorted(found, reverse=True)]
        preferred = [m for m in PREFERRED_TEXT_MODELS if m in by_context]
        rest = [m for m in by_context if m not in preferred]
        free = (preferred + rest)[:8]
        if free:
            _cache["text"] = (free, time.time())
            return free
    except Exception as e:
        print("TEXT MODEL LIST ERROR:", repr(e))

    return FALLBACK_TEXT_MODELS


def get_free_video_models():
    """Live list of FREE video-generation models, cached 1 hour.

    As of now OpenRouter has none, so this normally returns an empty list.
    If a free one appears later, it will be picked up automatically.
    """
    models, ts = _cache["video"]
    if time.time() - ts < CACHE_SECONDS and ts > 0:
        return models

    try:
        r = requests.get(f"{OR_BASE}/videos/models", timeout=15)
        r.raise_for_status()
        free = [
            m["id"]
            for m in r.json().get("data", [])
            if _all_zero(m.get("pricing"))
        ]
        _cache["video"] = (free, time.time())
        return free
    except Exception as e:
        print("VIDEO MODEL LIST ERROR:", repr(e))
        return []


# --------------------------------------------------------------------------
# Pages
# --------------------------------------------------------------------------
def home(request):
    return render(request, "chatbot/index.html")


# --------------------------------------------------------------------------
# Text chat
# --------------------------------------------------------------------------
def _call_model(model, messages):
    response = get_client().chat.completions.create(model=model, messages=messages)
    text = (
        response.choices[0].message.content
        if response and response.choices
        else None
    )
    if not text:
        raise Exception("Empty response")
    return text.strip()


def generate_ai_response(messages):
    """Try free models in turn. `messages` is a list of {role, content}.

    - Each call has a hard deadline, so a hung model can't kill the worker.
    - Failed models are benched so they aren't retried on every message
      (e.g. 403 "agentic harness only" models are skipped for 24 hours).
    """
    last_error = None

    candidates = [m for m in get_free_text_models() if not _is_blocked(m)]
    if not candidates:  # everything benched: start fresh rather than fail
        _blocked.clear()
        candidates = get_free_text_models()

    for model in candidates[:MAX_MODELS_PER_REQUEST]:
        try:
            print(f"Trying model: {model}")
            future = _executor.submit(_call_model, model, messages)
            text = future.result(timeout=PER_MODEL_DEADLINE)
            print("SUCCESS:", model)
            return text

        except FutureTimeout:
            last_error = Exception(f"{model} timed out")
            print(f"MODEL TIMEOUT ({model})")
            _block(model, 900)  # 15 min

        except Exception as e:
            last_error = e
            print(f"MODEL FAILED ({model}):", repr(e))
            status = getattr(e, "status_code", None)
            if status in (403, 404):
                _block(model, 86400)   # not usable from an API call
            elif status == 402:
                _block(model, 3600)
            elif status == 429:
                _block(model, 600)     # rate limited
            else:
                _block(model, 300)

    raise Exception(f"All models failed: {last_error}")


def chat(request):
    if request.method != "POST":
        return JsonResponse({"error": "Only POST requests are allowed."}, status=405)

    try:
        data = json.loads(request.body)
        message = (data.get("message") or "").strip()

        if not message:
            return JsonResponse({"error": "Please enter a message."}, status=400)

        print("User message:", message)

        # ---- conversation history (never let a session problem break the chat) ----
        try:
            conversation = request.session.get("conversation", [])
        except Exception as e:
            print("SESSION READ ERROR:", repr(e))
            conversation = []

        conversation.append({"role": "user", "content": message})
        conversation = conversation[-20:]

        messages = [{"role": "system", "content": SYSTEM_PROMPT}] + conversation

        # ---- ask the AI ----
        reply = generate_ai_response(messages)

        conversation.append({"role": "assistant", "content": reply})
        conversation = conversation[-20:]

        try:
            request.session["conversation"] = conversation
            request.session.modified = True
        except Exception as e:
            print("SESSION WRITE ERROR:", repr(e))

        return JsonResponse({"reply": reply})

    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid request."}, status=400)

    except Exception as e:
        print("CHAT ERROR:", repr(e))
        traceback.print_exc()
        return JsonResponse(
            {"error": "The AI is busy right now. Please try again in a moment."},
            status=503,
        )


def free_models(request):
    """Debug helper: shows which free models the app is currently using."""
    return JsonResponse(
        {
            "text_models": get_free_text_models(),
            "video_models": get_free_video_models(),
        }
    )


# --------------------------------------------------------------------------
# Video generation (free models only)
# --------------------------------------------------------------------------
def video_start(request):
    """Start a video job. Only ever uses FREE video models."""
    if request.method != "POST":
        return JsonResponse({"error": "Only POST requests are allowed."}, status=405)

    try:
        free_video = get_free_video_models()
        if not free_video:
            return JsonResponse(
                {
                    "error": (
                        "No free video generation models are available on "
                        "OpenRouter right now."
                    )
                },
                status=503,
            )

        data = json.loads(request.body)
        prompt = (data.get("prompt") or "").strip()
        if not prompt:
            return JsonResponse({"error": "Please enter a prompt."}, status=400)

        model = data.get("model")
        if model not in free_video:
            model = free_video[0]

        payload = {"model": model, "prompt": prompt}
        # Only pass options the chosen model supports (check /api/v1/videos/models).
        for key in ("duration", "resolution", "aspect_ratio"):
            if data.get(key):
                payload[key] = data[key]

        r = requests.post(
            f"{OR_BASE}/videos", headers=_headers(), json=payload, timeout=30
        )
        if not r.ok:
            print("VIDEO START FAILED:", r.status_code, r.text)
            return JsonResponse({"error": r.text}, status=r.status_code)

        return JsonResponse(r.json())

    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid request."}, status=400)
    except Exception as e:
        print("VIDEO START ERROR:", repr(e))
        traceback.print_exc()
        return JsonResponse({"error": "Could not start the video job."}, status=500)


def video_status(request, job_id):
    """The browser polls this every few seconds."""
    try:
        r = requests.get(f"{OR_BASE}/videos/{job_id}", headers=_headers(), timeout=20)
        return JsonResponse(r.json(), status=r.status_code)
    except Exception as e:
        print("VIDEO STATUS ERROR:", repr(e))
        return JsonResponse({"error": "Status check failed."}, status=503)


def video_content(request, job_id):
    """Proxy the finished MP4 so the API key is never exposed to the browser."""
    try:
        r = requests.get(
            f"{OR_BASE}/videos/{job_id}/content?index=0",
            headers=_headers(),
            timeout=120,
        )
        return HttpResponse(r.content, content_type="video/mp4", status=r.status_code)
    except Exception as e:
        print("VIDEO CONTENT ERROR:", repr(e))
        return JsonResponse({"error": "Could not download the video."}, status=503)