from django.shortcuts import render
from django.http import JsonResponse
import json
import os
from google import genai


client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))


def home(request):
    return render(request, 'chatbot/index.html')


def chat(request):
    if request.method == "POST":
        data = json.loads(request.body)
        message = data.get("message")

        print("User message:", message)

        conversation = request.session.get("conversation", [])

        conversation.append({
            "role": "user",
            "text": message
        })

        prompt = ""

        for item in conversation:
            prompt += f"{item['role']}: {item['text']}\n"

        response = client.models.generate_content(
            model="gemini-3.8-flash",
            contents=prompt
        )

        reply = response.text

        conversation.append({
            "role": "assistant",
            "text": reply
        })

        request.session["conversation"] = conversation

        return JsonResponse({
            "reply": reply
        })