from django.shortcuts import render, redirect
from django.views import View
from app.forms import SignupForm, LoginForm
from django.contrib.auth import login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils import timezone
from datetime import timedelta
from .models import Task  # Taskモデルを使う場合

# Create your views here.
class TopView(View):
    def get(self, request):
        return render(request, "top.html")

class SignUpView(View):
    def get(self, request):
         form = SignupForm()
         return render(request, "signup.html", context={
             "form":form
         })
    def post(self, request):
        print(request.POST)
        form = SignupForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("login")
        return render(request, "signup.html", context={
             "form":form
         })


class LoginView(View):
    def get(self, request):
         return render(request, "login.html")
    def post(self, request):
        print(request.POST)
        form = LoginForm(request.POST)
        if form.is_valid():
            login(request, form.user)
            return redirect("home")
        return render(request, "login.html", context={
             "form":form
         })


class HomeView(View):
    def get(self, request):
        now = timezone.now() # 現在時刻を取得
        tasks = Task.objects.all() # 全てのタスクを取得（ここでタスクは登録済みのものをデータベースから取得）
        # リマインドの対象となるタスク（完了期限2時間前のもの）をフィルタリング
        reminders = tasks.filter(due_datetime__lte=now + timedelta(hours=2), completion_status=False)
        # コンテキストにデータを渡す
        context = {
            "tasks": tasks,
            "reminders": reminders
        }
        return render(request, 'home.html', context)

