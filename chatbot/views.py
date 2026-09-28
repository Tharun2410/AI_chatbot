from django.shortcuts import render
from django.http import JsonResponse

import json
import os
import time

from google import genai


# ==============================
# GEMINI CLIENT
# ==============================

client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY")
)


# ==============================
# HOME PAGE
# ==============================

def home(request):
    return render(
        request,
        "chatbot/index.html"
    )


# ==============================
# GEMINI RESPONSE
# ==============================

def generate_ai_response(prompt):

    # Model order
    models = [
        "gemini-3.5-flash-lite",
        "gemini-3.1-flash-lite",
        "gemini-3.6-flash",
    ]

    last_error = None

    for model in models:

        # Only retry transient server errors.
        for attempt in range(2):

            try:
                print(
                    f"Trying {model} "
                    f"(attempt {attempt + 1})"
                )

                response = client.models.generate_content(
                    model=model,
                    contents=prompt
                )

                # Make sure Gemini actually returned text.
                if not response or not response.text:
                    raise Exception(
                        "Gemini returned an empty response."
                    )

                print(
                    f"SUCCESS: {model}"
                )

                return response.text.strip()

            except Exception as e:

                last_error = e
                error_text = str(e)

                print(
                    f"ERROR from {model}: "
                    f"{repr(e)}"
                )

                # Retry only temporary errors.
                temporary_error = any(
                    code in error_text
                    for code in [
                        "503",
                        "UNAVAILABLE",
                        "429",
                        "RESOURCE_EXHAUSTED",
                        "500",
                        "502",
                        "504",
                    ]
                )

                if not temporary_error:
                    # Invalid API key, bad request,
                    # permission issue, etc.
                    print(
                        f"Non-retryable error "
                        f"from {model}"
                    )

                    raise

                # Retry once after a short delay.
                if attempt == 0:
                    print(
                        f"Retrying {model} "
                        f"after 2 seconds..."
                    )

                    time.sleep(2)

        print(
            f"{model} failed. "
            f"Moving to next model."
        )

    # All models failed.
    print(
        "ALL GEMINI MODELS FAILED:",
        repr(last_error)
    )

    raise Exception(
        "All Gemini models are temporarily unavailable."
    )


# ==============================
# CHAT API
# ==============================

def chat(request):

    if request.method != "POST":
        return JsonResponse(
            {
                "error":
                "Only POST requests are allowed."
            },
            status=405
        )

    try:

        # --------------------------
        # Read request
        # --------------------------

        data = json.loads(
            request.body
        )

        message = data.get(
            "message",
            ""
        ).strip()

        if not message:
            return JsonResponse(
                {
                    "error":
                    "Please enter a message."
                },
                status=400
            )

        print(
            "User message:",
            message
        )

        # --------------------------
        # Get conversation history
        # --------------------------

        conversation = request.session.get(
            "conversation",
            []
        )

        # Keep the conversation size
        # under control.
        conversation.append(
            {
                "role": "user",
                "text": message
            }
        )

        conversation = conversation[-20:]

        # --------------------------
        # Build AI prompt
        # --------------------------

        prompt = """
You are Tharun AI.

You are a helpful, friendly,
clear and intelligent AI assistant.

Answer the user's questions naturally.

Use the conversation history to
remember information the user has
already provided.

Do not mention that you are using
conversation history unless the user
asks about it.

Keep answers clear and useful.

Conversation history:

"""

        for item in conversation:

            if item["role"] == "user":

                prompt += (
                    "User: "
                    + item["text"]
                    + "\n"
                )

            else:

                prompt += (
                    "Assistant: "
                    + item["text"]
                    + "\n"
                )

        prompt += "\nAssistant:"

        # --------------------------
        # Call Gemini
        # --------------------------

        reply = generate_ai_response(
            prompt
        )

        # --------------------------
        # Save AI response
        # --------------------------

        conversation.append(
            {
                "role": "assistant",
                "text": reply
            }
        )

        conversation = conversation[-20:]

        request.session[
            "conversation"
        ] = conversation

        request.session.modified = True

        # --------------------------
        # Return JSON
        # --------------------------

        return JsonResponse(
            {
                "reply": reply
            }
        )

    # ------------------------------
    # Invalid JSON
    # ------------------------------

    except json.JSONDecodeError:

        return JsonResponse(
            {
                "error":
                "Invalid request."
            },
            status=400
        )

    # ------------------------------
    # Gemini / server error
    # ------------------------------

    except Exception as e:

        print(
            "CHAT ERROR:",
            repr(e)
        )

        return JsonResponse(
            {
                "error":
                "The AI service is temporarily unavailable. Please try again."
            },
            status=503
        )