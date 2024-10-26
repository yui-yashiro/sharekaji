from django.shortcuts import render, redirect
from django.views import View
from app.forms import SignupForm
from django.contrib.auth import authenticate,login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count
from django.utils import timezone
from datetime import timedelta, datetime, date
from .models import Task, Comment, Recurrence
from django.contrib import messages
from django.views.generic.edit import CreateView
from django.urls import reverse_lazy

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
        current_date = timezone.now()
        return render(request, 'today_tasks.html',{
            'current_date': current_date
        })
    def post_comment(request):
        if request.method == "POST":
           comment_text = request.POST.get("comment")
           user = request.user
           task_id = request.POST.get("task_id") 
           task = Task.objects.get(pk=task_id)
           Comment.objects.create(user=user, text=comment_text, task=task)
        return redirect('today_tasks') 

class RecurringTaskListView(View):
    def get(self, request):
        recurrences = Recurrence.objects.filter(user=request.user)
        context = {
            'recurrences': recurrences
        }
        return render(request, 'recurring_tasks.html', context)

class RecurringTaskCreateView(CreateView):
    model = Recurrence
    fields = ['task_name', 'user',  'start_date', 'due_time', 'estimated_time', 'recurrence_type', 'weekday', 'day_of_month', 'end_date']
    template_name = 'add_recurring_tasks.html'
    success_url = reverse_lazy('recurring_tasks')  # 登録後、周期タスク一覧にリダイレクト

    # フォーム送信時にリクエストユーザーを保存する処理
    def form_valid(self, form):
        form.instance.user = self.request.user  # 現在のユーザーを設定
        return super().form_valid(form)

class Individual_TaskCreateView(CreateView):
    model = Task
    fields = ['task_name', 'user', 'estimated_time', 'due_datetime']
    template_name = 'add_individual_tasks.html'
    success_url = reverse_lazy('today_tasks')  # 登録後、本日のタスク一覧にリダイレクト

    # フォーム送信時にリクエストユーザーを保存する処理
    def form_valid(self, form):
        form.instance.user = self.request.user  # 現在のユーザーを設定
        return super().form_valid(form)

class TaskAnalysisView(View):
    def get(self, request):
        if not request.user.is_authenticated:
            return redirect('login')
            
        if not hasattr(request.user, 'family') or not request.user.family:
            return redirect('home')
        
        # 家族グループのリストを取得
        family_members = request.user.family.members.all()

        # 完了タスクを家族ごとに集計
        completed_tasks = Task.objects.filter(
            user__in=family_members,
            completion_status=True,
            completion_datetime__gte=timezone.now() - timedelta(days=7)
        ).values('user__name').annotate(task_count=Count('id'))
        
        # 未完了タスクを家族ごとに集計
        incomplete_tasks = Task.objects.filter(
            user__in=family_members,
            completion_status=False,
        ).values('user__name').annotate(task_count=Count('id'))

        # タスク数の合計を計算
        total_completed = sum(task['task_count']for task in completed_tasks)
        total_incomplete = sum(task['task_count']for task in incomplete_tasks)
        
        # パーセンテージに変換したデータを作成
        completed_data = [(task['task_count'] / total_completed) * 100 if total_completed > 0 else 0 for task in completed_tasks]
        completed_labels = [task['user__name']for task in completed_tasks]

        incomplete_data = [(task['task_count'] / total_incomplete) * 100 if total_incomplete > 0 else 0 for task in incomplete_tasks]
        incomplete_labels = [task['user__name']for task in incomplete_tasks]

        # コンテキストにデータを渡す
        context = {
            'completed_data': completed_data,
            'completed_labels':completed_labels,
            'incomplete_data': incomplete_data,
            'incomplete_labels': incomplete_labels,
        }
        return render(request, 'task_analysis.html',context)

class MyPageView(View):
    def get(self, request):
        return render(request, 'mypage.html')