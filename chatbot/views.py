from django.shortcuts import render
from django.http import JsonResponse
import json
import os
from google import genai


client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))


def home(request):
    return render(request, "chatbot/index.html")


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

        response = client.models.generate_content(
            model="gemini-3.5-flash-lite",
            contents=message
        )

        reply = response.text

        return JsonResponse({
            "reply": reply
        })
        
    except Exception as e:
        print("CHAT ERROR:", repr(e))

        return JsonResponse({
            "error": "AI service is temporarily unavailable. Please try again later."
        }, status=503)