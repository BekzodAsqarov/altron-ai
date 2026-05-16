from django.urls import path
from . import views

urlpatterns = [
    path('', views.login_view, name='home'),
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),

    # Chat
    path('chat/', views.chat_view, name='chat'),
    path('chat/<int:conversation_id>/', views.chat_view, name='chat_conversation'),
    path('chat/new/', views.new_conversation, name='new_conversation'),
    path('chat/delete/<int:conversation_id>/', views.delete_conversation, name='delete_conversation'),

    # API
    path('api/send-message/', views.send_message, name='send_message'),
]