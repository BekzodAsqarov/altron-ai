
from django.conf import settings
from rest_framework.decorators import api_view
from rest_framework.response import Response
import google.generativeai as genai

genai.configure(api_key=settings.GEMINI_API_KEY)

@api_view(['POST'])
def chat_view(request):
    user_message = request.data.get("message", "")

    model = genai.GenerativeModel("gemini-1.5-flash")

    prompt = f"""
    You are a senior Python developer with 30 years experience.
    Give clean, smart, helpful answers.

    User: {user_message}
    """

    result = model.generate_content(prompt)

    return Response({
        "reply": result.text
    })