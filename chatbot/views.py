from django.shortcuts import render
from django.http import JsonResponse
import json
import os
import time
from google import genai


client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))


def home(request):
    return render(request, "chatbot/index.html")


def generate_with_retry(prompt):
    delays = [2, 4, 8]

    for attempt in range(3):
        try:
            response = client.models.generate_content(
                model="gemini-3.5-flash-lite",
                contents=prompt
            )

            return response

        except Exception as e:

            print(f"Gemini attempt {attempt + 1} failed:", repr(e))

            # Retry only for temporary 503 errors
            if "503" not in str(e):
                raise

            if attempt < 2:
                print(f"Retrying in {delays[attempt]} seconds...")
                time.sleep(delays[attempt])
            else:
                raise


def chat(request):

    if request.method != "POST":
        return JsonResponse({
            "error": "Only POST requests are allowed."
        }, status=405)

    try:

        data = json.loads(request.body)
        message = data.get("message", "").strip()

        if not message:
            return JsonResponse({
                "error": "Please enter a message."
            }, status=400)

        print("User message:", message)

        # Get previous conversation
        conversation = request.session.get("conversation", [])

        # Add user's message
        conversation.append({
            "role": "user",
            "text": message
        })

        # Create prompt from conversation
        prompt = ""

        for item in conversation:
            prompt += f"{item['role']}: {item['text']}\n"

        # Ask Gemini with automatic retry
        response = generate_with_retry(prompt)

        reply = response.text

        # Save AI response
        conversation.append({
            "role": "assistant",
            "text": reply
        })

        # Save conversation in session
        request.session["conversation"] = conversation
        request.session.modified = True

        return JsonResponse({
            "reply": reply
        })

    except Exception as e:

        print("CHAT ERROR:", repr(e))

        return JsonResponse({
            "error": "AI service is temporarily unavailable. Please try again later."
        }, status=503)