from django.shortcuts import render
from django.http import JsonResponse

import json
import os
import time

from google import genai
from google.genai import types


# ==========================================
# SETTINGS
# ==========================================

MODELS = [
    "gemini-3.1-flash-lite",   # primary
    "gemini-3.5-flash-lite",   # fallback 1
    "gemini-3.8-flash",        # fallback 2 (skipped if quota is used up)
]

MAX_ATTEMPTS_PER_MODEL = 3
RETRY_WAITS = [1.5, 3]     # seconds to wait before attempt 2 and 3
TOTAL_TIME_LIMIT = 40      # stop trying after 40 seconds in total

MAX_MESSAGE_LENGTH = 2000

# Each Gemini call gives up after 10 seconds (value is in milliseconds)
client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY"),
    http_options=types.HttpOptions(timeout=10000),
)


# ==========================================
# HOME PAGE
# ==========================================

def home(request):
    return render(request, "chatbot/index.html")


# ==========================================
# ERROR HELPERS
# ==========================================

class AIServiceError(Exception):
    """kind is one of: busy, quota, empty, other"""

    def __init__(self, kind):
        super().__init__(kind)
        self.kind = kind


def get_error_code(error):
    code = getattr(error, "code", None)
    if isinstance(code, int):
        return code

    text = str(error)
    if "429" in text:
        return 429
    if "503" in text:
        return 503
    return None


def is_timeout(error):
    text = (type(error).__name__ + " " + str(error)).lower()
    return "timeout" in text or "timed out" in text


# ==========================================
# GEMINI AI FUNCTION
# ==========================================

def generate_ai_response(prompt):

    start = time.monotonic()
    seen = set()   # kinds of failures we ran into

    def fail():
        # Report "busy" first, because that is the most useful message
        for kind in ("busy", "quota", "empty", "other"):
            if kind in seen:
                raise AIServiceError(kind)
        raise AIServiceError("busy")

    for model in MODELS:

        for attempt in range(MAX_ATTEMPTS_PER_MODEL):

            if time.monotonic() - start > TOTAL_TIME_LIMIT:
                print("Time limit reached, giving up.")
                fail()

            try:
                print(f"Trying {model} (attempt {attempt + 1})")

                response = client.models.generate_content(
                    model=model,
                    contents=prompt
                )

                text = response.text

                if text and text.strip():
                    print("SUCCESS:", model)
                    return text.strip()

                print("EMPTY RESPONSE from", model)
                seen.add("empty")
                break  # next model

            except Exception as e:

                code = get_error_code(e)
                print(f"ERROR from {model}: code={code} error={e!r}")

                # Quota used up: retrying this model is pointless
                if code == 429:
                    seen.add("quota")
                    break

                # Temporary problem: wait a bit longer each time, then retry
                if code in (500, 503, 504) or is_timeout(e):
                    seen.add("busy")
                    if attempt < MAX_ATTEMPTS_PER_MODEL - 1:
                        time.sleep(RETRY_WAITS[attempt])
                    continue

                # Anything else (wrong model name, etc.): next model
                seen.add("other")
                break

    fail()


# ==========================================
# CHAT API
# ==========================================

ERROR_RESPONSES = {
    "busy": (
        "AI service is temporarily busy. Please try again in a few seconds.",
        503,
    ),
    "quota": (
        "The AI usage limit has been reached for now. Please try again later.",
        429,
    ),
    "empty": (
        "The AI could not answer that. Please try rephrasing your message.",
        502,
    ),
    "other": (
        "Something went wrong on the server. Please try again.",
        500,
    ),
}


def chat(request):

    if request.method != "POST":
        return JsonResponse(
            {"error": "Only POST requests are allowed."},
            status=405
        )

    # ----------------------------------
    # Read request
    # ----------------------------------

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid request."}, status=400)

    message = data.get("message", "") if isinstance(data, dict) else ""

    if not isinstance(message, str) or not message.strip():
        return JsonResponse(
            {"error": "Please enter a message."},
            status=400
        )

    message = message.strip()

    if len(message) > MAX_MESSAGE_LENGTH:
        return JsonResponse(
            {"error": "Message is too long. Please shorten it."},
            status=400
        )

    print("User message:", message)

    try:

        # ----------------------------------
        # Load history and remove bad entries
        # ----------------------------------

        saved = request.session.get("conversation", [])

        conversation = [
            item for item in saved
            if isinstance(item, dict)
            and item.get("role") in ("user", "assistant")
            and isinstance(item.get("text"), str)
        ]

        conversation.append({"role": "user", "text": message})
        conversation = conversation[-20:]

        # ----------------------------------
        # Build prompt
        # ----------------------------------

        prompt = (
            "You are Tharun AI, a helpful, friendly, "
            "and intelligent chatbot.\n\n"
            "Remember information that the user tells "
            "you during the conversation.\n\n"
            "Answer naturally and clearly.\n\n"
            "Conversation history:\n\n"
        )

        for item in conversation:
            speaker = "User" if item["role"] == "user" else "Assistant"
            prompt += f"{speaker}: {item['text']}\n"

        prompt += "\nAssistant:"

        # ----------------------------------
        # Ask Gemini
        # ----------------------------------

        reply = generate_ai_response(prompt)

        # ----------------------------------
        # Save to session (only on success)
        # ----------------------------------

        conversation.append({"role": "assistant", "text": reply})
        request.session["conversation"] = conversation[-20:]
        request.session.modified = True

        return JsonResponse({"reply": reply})

    except AIServiceError as e:
        text, status = ERROR_RESPONSES.get(e.kind, ERROR_RESPONSES["other"])
        print("CHAT FAILED:", e.kind)
        return JsonResponse({"error": text}, status=status)

    except Exception as e:
        print("CHAT ERROR:", repr(e))
        text, status = ERROR_RESPONSES["other"]
        return JsonResponse({"error": text}, status=status)