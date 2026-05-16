import json
from google import genai
from google.genai import types
from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import Conversation, Message

# Gemini client
client = genai.Client(api_key=settings.GEMINI_API_KEY)

SYSTEM_PROMPT = """Sen Altron AI san — Python bo'yicha 20 yillik tajribaga ega mutaxassis va mentor.

Qoidalaring:
- Python, Django, dasturlash bo'yicha savollarni EXPERT darajada javob berasan
- Kod yozganda tushuntirish bilan yozasan
- Xatolarni aniqlab, yechim taklif qilasan
- Qisqa va aniq gapirasan, keraksiz gap yo'q
- O'zbek tilida gapirasan, lekin texnik terminlar inglizcha qoladi
- Har doim ishonchli, do'stona va professional bo'lasan
"""


# ─── AUTH VIEWS ───────────────────────────────────────────

def register_view(request):
    if request.user.is_authenticated:
        return redirect('chat')

    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')

        if password1 != password2:
            return render(request, 'register.html', {'error': 'Parollar mos kelmadi'})

        if User.objects.filter(email=email).exists():
            return render(request, 'register.html', {'error': 'Bu email band'})

        if User.objects.filter(username=username).exists():
            return render(request, 'register.html', {'error': 'Bu username band'})

        user = User.objects.create_user(username=username, email=email, password=password1)
        login(request, user)
        return redirect('chat')

    return render(request, 'register.html')


def login_view(request):
    if request.user.is_authenticated:
        return redirect('chat')

    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')

        try:
            username = User.objects.get(email=email).username
        except User.DoesNotExist:
            return render(request, 'login.html', {'error': 'Email topilmadi'})

        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            return redirect('chat')
        else:
            return render(request, 'login.html', {'error': 'Parol noto\'g\'ri'})

    return render(request, 'login.html')


def logout_view(request):
    logout(request)
    return redirect('login')


# ─── CHAT VIEWS ───────────────────────────────────────────

@login_required
def chat_view(request, conversation_id=None):
    conversations = Conversation.objects.filter(user=request.user)
    current_conversation = None
    messages = []

    if conversation_id:
        current_conversation = get_object_or_404(Conversation, id=conversation_id, user=request.user)
        messages = current_conversation.messages.all()

    return render(request, 'chat.html', {
        'conversations': conversations,
        'current_conversation': current_conversation,
        'messages': messages,
    })


@login_required
def new_conversation(request):
    conversation = Conversation.objects.create(user=request.user)
    return redirect('chat_conversation', conversation_id=conversation.id)


@login_required
def delete_conversation(request, conversation_id):
    conversation = get_object_or_404(Conversation, id=conversation_id, user=request.user)
    conversation.delete()
    return redirect('chat')


@login_required
@csrf_exempt
def send_message(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    data = json.loads(request.body)
    user_message = data.get('message', '').strip()
    conversation_id = data.get('conversation_id')

    if not user_message:
        return JsonResponse({'error': 'Xabar bo\'sh'}, status=400)

    # Conversation olish yoki yangi yaratish
    if conversation_id:
        conversation = get_object_or_404(Conversation, id=conversation_id, user=request.user)
    else:
        conversation = Conversation.objects.create(user=request.user)

    # User xabarini saqlash
    Message.objects.create(
        conversation=conversation,
        role='user',
        content=user_message
    )

    # Conversation title — birinchi xabar bo'lsa
    if conversation.messages.count() == 1:
        conversation.title = user_message[:50]
        conversation.save()

    # Gemini uchun history tayyorlash
    all_messages = list(conversation.messages.all())
    history_messages = all_messages[:-1]  # oxirgi xabarsiz

    history = []
    for msg in history_messages:
        history.append({
            "role": "user" if msg.role == "user" else "model",
            "parts": [msg.content]
        })

    try:
        # History to'g'ri formatda
        history = []
        for msg in history_messages:
            history.append(
                types.Content(
                    role="user" if msg.role == "user" else "model",
                    parts=[types.Part(text=msg.content)]
                )
            )

        # Joriy xabarni qo'sh
        history.append(
            types.Content(
                role="user",
                parts=[types.Part(text=user_message)]
            )
        )

        response = client.models.generate_content(
            model="gemini-2.5-flash-lite",
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
            ),
            contents=history
        )
        ai_response = response.text

    except Exception as e:
        ai_response = f"Xatolik yuz berdi: {str(e)}"

    # AI javobini saqlash
    Message.objects.create(
        conversation=conversation,
        role='assistant',
        content=ai_response
    )

    return JsonResponse({
        'response': ai_response,
        'conversation_id': conversation.id,
    })