from django.shortcuts import render
from django.http import JsonResponse

import json
import os
import time

from google import genai


# -----------------------------------------
# Gemini Client
# -----------------------------------------

client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY")
)


# -----------------------------------------
# Home Page
# -----------------------------------------

def home(request):
    return render(request, "chatbot/index.html")


# -----------------------------------------
# Gemini Response
# -----------------------------------------

def generate_ai_response(prompt):

    # Primary model first
    # Fallback model second
    models = [
        "gemini-3.5-flash-lite",
        "gemini-3.1-flash-lite",
    ]

    for model in models:

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

                print(
                    f"SUCCESS: {model}"
                )

                return response.text

            except Exception as e:

                error_text = str(e)

                print(
                    f"ERROR from {model}: "
                    f"{repr(e)}"
                )

                # Only retry temporary server errors
                if "503" in error_text:

                    if attempt == 0:

                        print(
                            f"{model} returned 503. "
                            f"Retrying after 2 seconds..."
                        )

                        time.sleep(2)

                        continue

                    else:

                        print(
                            f"{model} failed twice. "
                            f"Moving to next model..."
                        )

                        break

                # Do not retry other errors
                raise

    # Both models failed
    raise Exception(
        "All Gemini models are temporarily unavailable."
    )


# -----------------------------------------
# Chat API
# -----------------------------------------

def chat(request):

    # Only POST is allowed
    if request.method != "POST":

        return JsonResponse(
            {
                "error": "Only POST requests are allowed."
            },
            status=405
        )

    try:

        # ---------------------------------
        # Read user message
        # ---------------------------------

        data = json.loads(request.body)

        message = data.get(
            "message",
            ""
        ).strip()


        # ---------------------------------
        # Empty message check
        # ---------------------------------

        if not message:

            return JsonResponse(
                {
                    "error": "Please enter a message."
                },
                status=400
            )


        print(
            "User message:",
            message
        )


        # ---------------------------------
        # Get conversation from session
        # ---------------------------------

        conversation = request.session.get(
            "conversation",
            []
        )


        # ---------------------------------
        # Add current user message
        # ---------------------------------

        conversation.append(
            {
                "role": "user",
                "text": message
            }
        )


        # ---------------------------------
        # Keep conversation size reasonable
        # ---------------------------------

        # Keep the latest 20 messages
        conversation = conversation[-20:]


        # ---------------------------------
        # Build Gemini prompt
        # ---------------------------------

        prompt = """
You are Tharun AI, a helpful and friendly chatbot.

Remember information the user tells you during this conversation.

Answer naturally and clearly.

Conversation:

"""


        for item in conversation:

            role = item["role"]
            text = item["text"]

            if role == "user":

                prompt += (
                    f"User: {text}\n"
                )

            else:

                prompt += (
                    f"Assistant: {text}\n"
                )


        prompt += "\nAssistant:"


        # ---------------------------------
        # Ask Gemini
        # ---------------------------------

        reply = generate_ai_response(
            prompt
        )


        # ---------------------------------
        # Save AI response
        # ---------------------------------

        conversation.append(
            {
                "role": "assistant",
                "text": reply
            }
        )


        # Keep only latest 20 messages
        conversation = conversation[-20:]


        # ---------------------------------
        # Save conversation in session
        # ---------------------------------

        request.session[
            "conversation"
        ] = conversation

        request.session.modified = True


        # ---------------------------------
        # Send response to JavaScript
        # ---------------------------------

        return JsonResponse(
            {
                "reply": reply
            }
        )


    except json.JSONDecodeError:

        return JsonResponse(
            {
                "error": "Invalid request."
            },
            status=400
        )


    except Exception as e:

        print(
            "CHAT ERROR:",
            repr(e)
        )

        return JsonResponse(
            {
                "error": (
                    "AI service is temporarily busy. "
                    "Please try again in a few seconds."
                )
            },
            status=503
        )