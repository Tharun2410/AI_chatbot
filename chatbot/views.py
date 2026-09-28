from django.shortcuts import render
from django.http import JsonResponse
import json
import os
from google import genai


# Gemini client
client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY")
)


def home(request):
    return render(request, "chatbot/index.html")


def generate_with_retry(prompt):

    # Primary model + fallback model
    models = [
        "gemini-3.5-flash-lite",
        "gemini-3.1-flash-lite"
    ]

    for model in models:

        try:

            print("Trying model:", model)

            response = client.models.generate_content(
                model=model,
                contents=prompt
            )

            print("Success with model:", model)

            return response

        except Exception as e:

            print(f"{model} failed:", repr(e))

            # Only try fallback for temporary 503 errors
            if "503" not in str(e):
                raise

            print("Trying fallback model...")


    # Both models failed
    raise Exception(
        "All Gemini models are temporarily unavailable."
    )


def chat(request):

    # Allow only POST requests
    if request.method != "POST":

        return JsonResponse({
            "error": "Only POST requests are allowed."
        }, status=405)


    try:

        # Read JSON from frontend
        data = json.loads(request.body)

        message = data.get("message", "").strip()


        # Check empty message
        if not message:

            return JsonResponse({
                "error": "Please enter a message."
            }, status=400)


        print("User message:", message)


        # Get previous conversation
        conversation = request.session.get(
            "conversation",
            []
        )


        # Add user's message
        conversation.append({
            "role": "user",
            "text": message
        })


        # Create prompt from conversation
        prompt = ""

        for item in conversation:

            prompt += (
                f"{item['role']}: "
                f"{item['text']}\n"
            )


        # Send prompt to Gemini
        response = generate_with_retry(prompt)


        # Get AI response
        reply = response.text


        # Save AI response
        conversation.append({
            "role": "assistant",
            "text": reply
        })


        # Save conversation in Django session
        request.session["conversation"] = conversation
        request.session.modified = True


        # Send response to frontend
        return JsonResponse({
            "reply": reply
        })


    except Exception as e:

        print("CHAT ERROR:", repr(e))


        return JsonResponse({
            "error": (
                "AI service is temporarily unavailable. "
                "Please try again later."
            )
        }, status=503)