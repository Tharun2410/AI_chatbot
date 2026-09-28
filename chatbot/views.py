from django.shortcuts import render
from django.http import JsonResponse

import json
import os
import time

from google import genai


# ==========================================
# GEMINI CLIENT
# ==========================================

client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY")
)


# ==========================================
# HOME PAGE
# ==========================================

def home(request):
    return render(
        request,
        "chatbot/index.html"
    )


# ==========================================
# GEMINI AI FUNCTION
# ==========================================

def generate_ai_response(prompt):

    # Use the model that is currently
    # responding successfully first.
    primary_model = "gemini-3.1-flash-lite"

    # Backup model
    fallback_model = "gemini-3.5-flash-lite"


    # --------------------------------------
    # Try primary model
    # --------------------------------------

    try:

        print(
            "Trying primary model:",
            primary_model
        )

        response = client.models.generate_content(
            model=primary_model,
            contents=prompt
        )

        print(
            "SUCCESS:",
            primary_model
        )

        return response.text


    except Exception as e:

        error_text = str(e)

        print(
            "PRIMARY MODEL ERROR:",
            repr(e)
        )


        # ----------------------------------
        # Only fallback for 503
        # ----------------------------------

        if "503" not in error_text:
            raise


        print(
            "Primary model returned 503."
        )

        print(
            "Trying fallback model:",
            fallback_model
        )


    # --------------------------------------
    # Try fallback model
    # --------------------------------------

    for attempt in range(2):

        try:

            print(
                f"Trying fallback model "
                f"(attempt {attempt + 1})"
            )

            response = client.models.generate_content(
                model=fallback_model,
                contents=prompt
            )

            print(
                "SUCCESS:",
                fallback_model
            )

            return response.text


        except Exception as e:

            error_text = str(e)

            print(
                "FALLBACK MODEL ERROR:",
                repr(e)
            )


            # Retry only 503
            if "503" not in error_text:
                raise


            if attempt == 0:

                print(
                    "Retrying fallback model "
                    "after 2 seconds..."
                )

                time.sleep(2)


    # --------------------------------------
    # Both models unavailable
    # --------------------------------------

    raise Exception(
        "Both Gemini models are temporarily unavailable."
    )


# ==========================================
# CHAT API
# ==========================================

def chat(request):

    # --------------------------------------
    # POST only
    # --------------------------------------

    if request.method != "POST":

        return JsonResponse(
            {
                "error":
                "Only POST requests are allowed."
            },
            status=405
        )


    try:

        # ----------------------------------
        # Read request
        # ----------------------------------

        data = json.loads(
            request.body
        )

        message = data.get(
            "message",
            ""
        ).strip()


        # ----------------------------------
        # Empty message
        # ----------------------------------

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


        # ----------------------------------
        # Get conversation
        # ----------------------------------

        conversation = request.session.get(
            "conversation",
            []
        )


        # ----------------------------------
        # Add user message
        # ----------------------------------

        conversation.append(
            {
                "role": "user",
                "text": message
            }
        )


        # ----------------------------------
        # Keep last 20 messages
        # ----------------------------------

        conversation = conversation[-20:]


        # ----------------------------------
        # Build prompt
        # ----------------------------------

        prompt = """
You are Tharun AI, a helpful, friendly,
and intelligent chatbot.

Remember information that the user tells
you during the conversation.

Answer naturally and clearly.

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


        # ----------------------------------
        # Generate AI response
        # ----------------------------------

        reply = generate_ai_response(
            prompt
        )


        # ----------------------------------
        # Save AI response
        # ----------------------------------

        conversation.append(
            {
                "role": "assistant",
                "text": reply
            }
        )


        # Keep last 20 messages
        conversation = conversation[-20:]


        # ----------------------------------
        # Save session
        # ----------------------------------

        request.session[
            "conversation"
        ] = conversation

        request.session.modified = True


        # ----------------------------------
        # Return JSON
        # ----------------------------------

        return JsonResponse(
            {
                "reply": reply
            }
        )


    # ======================================
    # INVALID JSON
    # ======================================

    except json.JSONDecodeError:

        return JsonResponse(
            {
                "error":
                "Invalid request."
            },
            status=400
        )


    # ======================================
    # ANY OTHER ERROR
    # ======================================

    except Exception as e:

        print(
            "CHAT ERROR:",
            repr(e)
        )

        return JsonResponse(
            {
                "error":
                "AI service is temporarily busy. "
                "Please try again in a few seconds."
            },
            status=503
        )