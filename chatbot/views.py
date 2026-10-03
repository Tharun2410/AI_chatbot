from django.shortcuts import render
from django.http import JsonResponse

import json
import os
import time

from dotenv import load_dotenv
from openai import OpenAI


# ==============================
# LOAD ENVIRONMENT VARIABLES
# ==============================

load_dotenv()


# ==============================
# OPENROUTER CLIENT
# ==============================

load_dotenv()

def get_client():
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise Exception("OPENROUTER_API_KEY is missing. Check your .env file.")
    return OpenAI(
        api_key=api_key,
        base_url="https://openrouter.ai/api/v1",
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
# OPENROUTER RESPONSE
# ==============================

def generate_ai_response(prompt):

    last_error = None

    for attempt in range(2):

        try:

            print(
                f"Trying OpenRouter "
                f"(attempt {attempt + 1})"
            )
            client = get_client()
            
            response = client.chat.completions.create(
                model="openrouter/free",
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )

            # Make sure OpenRouter returned text
            if (
                not response
                or not response.choices
                or not response.choices[0].message.content
            ):
                raise Exception(
                    "OpenRouter returned an empty response."
                )

            reply = response.choices[0].message.content

            print("SUCCESS: OpenRouter")

            return reply.strip()

        except Exception as e:

            last_error = e

            print(
                "OPENROUTER ERROR:",
                repr(e)
            )

            if attempt == 0:

                print(
                    "Retrying after 2 seconds..."
                )

                time.sleep(2)

    print(
        "OPENROUTER FAILED:",
        repr(last_error)
    )

    raise Exception(
        "OpenRouter service is temporarily unavailable."
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

        conversation.append(
            {
                "role": "user",
                "text": message
            }
        )

        # Keep last 20 messages
        conversation = conversation[-20:]

        # --------------------------
        # Build AI prompt
        # --------------------------

        prompt = """
You are BRO AI.

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
        # Call OpenRouter
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
    # OpenRouter / server error
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