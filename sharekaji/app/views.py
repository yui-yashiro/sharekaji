from django.shortcuts import render, redirect
from django.views import View
from app.forms import SignupForm, LoginForm
from django.contrib.auth import authenticate,login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils import timezone
from datetime import timedelta, datetime, date
from .models import Task, User
from django.contrib import messages

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
        email = request.POST.get('email')  # フォームからメールアドレスを取得
        password = request.POST.get('password')  # フォームからパスワードを取得
        user = authenticate(request, username=email, password=password)  # 認証を実施

        if user is not None:  # ユーザーが認証された場合
            login(request, user)  # ログイン
            return redirect("home")  # ホーム画面へリダイレクト

        # 認証が失敗した場合
        return render(request, "login.html", context={
            "error": "メールアドレスまたはパスワードが間違っています"  # エラーメッセージを表示
        })


class HomeView(View):
    def get(self, request, year=None, month=None):
        if not request.user.is_authenticated:
            return redirect('login') 
        
        now = timezone.now()
        if year is None or month is None:
            year = now.year
            month = now.month

         # 自身に割り振られたタスクを取得
        tasks = Task.objects.filter(user=request.user)

        # リマインドの対象となるタスク（完了期限2時間前のもの）をフィルタリング
        reminders = tasks.filter(due_datetime__lte=now + timedelta(hours=2), completion_status=False)

        # 他の家族が完了したタスクを取得
        family_notifications = Task.objects.filter(user__isnull=False, completion_status=True)

         # 完了していない家事
        incomplete_tasks = tasks.filter(completion_status=False)

        # 最近完了した家事（最新3件を表示する）
        completed_tasks = tasks.filter(completion_status=True).order_by('-completion_datetime')[:3]

        # カレンダーの日付を取得
        calendar_data = self.get_calendar_dates(year, month, tasks)

        # 前月・翌月の計算
        prev_month_date = datetime(year, month, 1) - timedelta(days=1)
        next_month_date = datetime(year, month, 28) + timedelta(days=4)

        prev_month_year = prev_month_date.year
        prev_month_month = prev_month_date.month

        next_month_year = next_month_date.year
        next_month_month = next_month_date.month

        # コンテキストにデータを渡す
        context = {
            "tasks": tasks,
            "family_notifications": family_notifications,
            "reminders": reminders,
            "incomplete_tasks": incomplete_tasks, 
            "completed_tasks": completed_tasks, 
            'calendar': calendar_data,
            'current_year': year,
            'current_month': month,
            'prev_month_year': prev_month_year,
            'prev_month_month': prev_month_month,
            'next_month_year': next_month_year,
            'next_month_month': next_month_month,
        }
        return render(request, 'home.html', context)

# カレンダーの日付を取得する関数
    def get_calendar_dates(self, year, month,tasks):
        # 月の初めの曜日と月の日数を取得
        first_day = date(year, month, 1)
        last_day = (first_day.replace(month=month % 12 + 1) - timedelta(days=1)).day
        
        # カレンダー表示に必要な日付を作成
        calendar = []
        week = []
        
        # 最初の週の空セルを追加
        start_weekday = first_day.weekday()  # 0 = 月曜
        for _ in range((start_weekday + 1) % 7):
            week.append('')
        
        # 日付を追加
        for day in range(1, last_day + 1):
            day_tasks = tasks.filter(scheduled_datetime__day=day)
            day_display = f"{day}"  # 基本は日付を表示
            if day_tasks.exists():
                # タスクがある場合、その情報を日付に付与
                task_info = "<br>".join([task.task_name for task in day_tasks])
                day_display += f"<br>{' '.join([task.task_name for task in day_tasks])}"
            week.append(day)
            if len(week) == 7:
                calendar.append(week)
                week = []
        
        # 最後の週を追加
        if week:
            calendar.append(week + [''] * (7 - len(week)))
        
        return calendar

class TodayTasksView(View):
    def get(self, request):
        return render(request, 'today_tasks.html')

class RecurringTasksView(View):
    def get(self, request):
        return render(request, 'recurring_tasks.html')

class TaskAnalysisView(View):
    def get(self, request):
        return render(request, 'task_analysis.html')

class MyPageView(View):
    def get(self, request):
        return render(request, 'mypage.html')