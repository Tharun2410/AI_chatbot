import json
import os
import time
import traceback

from django.http import JsonResponse
from django.shortcuts import render
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

SYSTEM_PROMPT = (
    "You are BRO, a helpful, friendly, clear and intelligent AI assistant. "
    "Answer naturally and keep answers clear and useful. "
    "Use the conversation so far to remember what the user has told you, "
    "but don't mention the history unless asked."
)


def get_client():
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise Exception("OPENROUTER_API_KEY is missing. Check your .env file.")
    return OpenAI(api_key=api_key, base_url="https://openrouter.ai/api/v1")


def home(request):
    return render(request, "chatbot/index.html")


def generate_ai_response(messages):
    """Call OpenRouter (2 attempts). `messages` is a list of {role, content}."""
    last_error = None

    for attempt in range(2):
        try:
            print(f"Trying OpenRouter (attempt {attempt + 1})")
            response = get_client().chat.completions.create(
                model="openrouter/free",
                messages=messages,
            )
            if not response or not response.choices or not response.choices[0].message.content:
                raise Exception("OpenRouter returned an empty response.")

            print("SUCCESS: OpenRouter")
            return response.choices[0].message.content.strip()

        except Exception as e:
            last_error = e
            print("OPENROUTER ERROR:", repr(e))
            if attempt == 0:
                print("Retrying after 2 seconds...")
                time.sleep(2)

    # include the real reason so it shows in the chat while you debug
    raise Exception(f"OpenRouter failed: {last_error}")


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
        return JsonResponse({"error": str(e)}, status=500)