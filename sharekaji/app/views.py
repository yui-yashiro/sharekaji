from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from app.forms import SignupForm, ProfileImageForm, AccountEditForm, FamilyEditForm, RecurringTaskForm, IndividualTaskForm
from django.contrib.auth import authenticate, login, update_session_auth_hash
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.db.models import Count
from django.utils import timezone
from datetime import timedelta, datetime, date
from .models import User, Family, Task, Comment, Recurrence
from django.views.generic.edit import CreateView, UpdateView
from django.urls import reverse_lazy
import uuid

# Create your views here.
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
            with transaction.atomic():
                user = form.save(commit=False)
                if not user.family_id:
                    family = Family.objects.create(name=f"{user.name}家")
                    user.family_id = family
            user.save()
            login(request, user)
            return redirect("mypage")
        
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

        # 個別タスクを取得してイベントデータに追加
        tasks = Task.objects.filter(user=request.user)
        event_data = [
            {
                "title": task.task_name,
                "start": task.due_datetime.isoformat() if task.due_datetime else None
            }
            for task in tasks
        ]

        # 繰り返しタスクを取得してイベントデータに追加
        recurrences = Recurrence.objects.filter(user=request.user)
        for recurrence in recurrences:
            if recurrence.recurrence_type == 1: # 毎日繰り返し
                for day in range((recurrence.end_date - recurrence.start_date).days + 1):
                    date = recurrence.start_date + timedelta(days=day)
                    event_data.append({
                        "title":recurrence.task_name,
                        "start":datetime.combine(date, recurrence.due_time).isoformat()
                    })
            elif recurrence.recurrence_type == 2: # 週ごとに繰り返し
                current_date = recurrence.start_date
                while current_date <= recurrence.end_date:
                    if current_date.weekday() == recurrence.weekday:
                        event_data.append({
                        "title":recurrence.task_name,
                        "start":datetime.combine(current_date, recurrence.due_time).isoformat()
                        })
                    current_date += timedelta(days=1)
            elif recurrence.recurrence_type == 3: # 月ごとに繰り返し
                current_date = recurrence.start_date
                while current_date <= recurrence.end_date:
                    if current_date.day == recurrence.day_of_month:
                        event_data.append({
                        "title":recurrence.task_name,
                        "start":datetime.combine(current_date, recurrence.due_time).isoformat()
                        })
                    current_date = (current_date.replace(day=1) + timedelta(days=32)).replace(day=1)



        # リマインドの対象となるタスク（完了期限2時間前のもの）をフィルタリング
        reminders = tasks.filter(due_datetime__lte=now + timedelta(hours=2), completion_status=False)

        # 他の家族が完了したタスクを取得
        family_notifications = Task.objects.filter(user__isnull=False, completion_status=True)

        # 完了していない家事
        incomplete_tasks = tasks.filter(completion_status=False)

        # 最近完了した家事（最新3件を表示する）
        completed_tasks = tasks.filter(completion_status=True).order_by('-completion_datetime')[:3]

        # コンテキストにデータを渡す
        context = {
            "event_data": event_data,
            "tasks": tasks,
            "family_notifications": family_notifications,
            "reminders": reminders,
            "incomplete_tasks": incomplete_tasks, 
            "completed_tasks": completed_tasks, 
            'current_year': year,
            'current_month': month,
        }
        return render(request, 'home.html', context)


class TodayTasksView(View):
    def get(self, request):
        current_date = timezone.now()

        tasks = Task.objects.filter(
            user=request.user,
            scheduled_datetime__date=current_date.date()
        )

        for task in tasks:
            task.estimated_time_hours = task.estimated_time / 60
        
        return render(request, 'today_tasks.html',{
            'tasks':tasks,
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
        if not request.user.family_id:
            return redirect('home')
        
        # 家族グループのリストを取得
        family_members = request.user.family_id.members.all()

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

class MyPageView(LoginRequiredMixin, View):
    def get(self, request):
        user = request.user
        family_members = user.family_id.members.all() if user.family_id else[]
        image_form = ProfileImageForm(instance=user)
        return render(request, 'mypage.html',{
            'user':user,
            'family_members':family_members,
            'image_form':image_form
        })
    
    def post(self, request):
        image_form = ProfileImageForm(request.POST, request.FILES, instance=request.user)
        if image_form.is_valid():
            image_form.save()
            return redirect('mypage')
        
        user = request.user
        family_members = user.family_id.members.all() if user.family_id else[]
        return render(request, 'mypage.html',{
            'user':user,
            'family_members':family_members,
            'image_form':image_form
        })

class AccountEditView(LoginRequiredMixin, UpdateView):
    model = User
    form_class = AccountEditForm
    template_name = 'account_edit.html'
    success_url = reverse_lazy('mypage')

    def get_object(self, queryset=None):
        return self.request.user
    
    def form_valid(self, form):
        response = super().form_valid(form)
        update_session_auth_hash(self.request, self.object)
        return response

class FamilyEditView(LoginRequiredMixin, UpdateView):
    model = Family
    form_class = FamilyEditForm
    template_name = 'family_edit.html'
    success_url = reverse_lazy('mypage')

    def get_object(self, queryset=None):
        return self.request.user.family_id

class FamilyInviteUrlView(LoginRequiredMixin, View):
    def get(self, request):
        user = request.user
        if not user.family_id.invitate_url:
            user.family_id.invitate_url = str(uuid.uuid4())
            user.family_id.save()
        return render(request, 'family_invite_url.html', {'family_invite_url': user.family_id.invitate_url})
    
class SignupInviteView(View):
    def get(self, request, invite_code):
        family = get_object_or_404(Family, invitate_url=invite_code)
        form = SignupForm()
        return render(request, 'signup_family_invite.html', {'form':form, 'family':family})
    
    def post(self, request, invite_code):
        family = get_object_or_404(Family, invitate_url=invite_code)
        form = SignupForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.family_id = family
            user.save()
            login(request, user)
            return redirect('mypage')
        return render(request, 'signup_family_invite.html', {'form':form, 'family':family})

class AccountDeleteView(LoginRequiredMixin, View):
    def get(self, request):
        return render(request, 'account_delete.html')
    
    def post(self, request):
        user = request.user
        if user.task_set.filter(completion_status=False).exists():
            return render(request, 'account_delete.html', {
                'error':'未完了のタスクがあるため、アカウント削除できません。'
            })
        user.delete()
        return redirect('login')

class RecurringTaskEditView(LoginRequiredMixin, UpdateView):
    model = Recurrence
    form_class = RecurringTaskForm
    template_name = 'recurring_task_edit.html'
    success_url = reverse_lazy('recurring_tasks')

    def form_valid(self, form):
        responce = super().form_valid(form)
        return responce

class IndividualTaskEditView(LoginRequiredMixin, UpdateView):
    model = Task
    form_class = IndividualTaskForm
    template_name = 'indivisual_task_edit.html'
    success_url = reverse_lazy('today_tasks')

    def form_valid(self, form):
        responce = super().form_valid(form)
        return responce