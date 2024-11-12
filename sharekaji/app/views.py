from django.shortcuts import render, redirect, get_object_or_404, reverse
from django.views import View
from app.forms import SignupForm, ProfileImageForm, AccountEditForm, FamilyEditForm, RecurringTaskForm, IndividualTaskForm
from django.contrib.auth import authenticate, login, update_session_auth_hash, logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.db.models import Count
from django.utils import timezone
from datetime import timedelta, datetime
from .models import User, Family, Task, Comment, Recurrence
from django.views.generic.edit import CreateView, UpdateView
from django.urls import reverse_lazy
import uuid
from django.http import JsonResponse
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_GET

# Create your views here.
class SignUpView(View):
    def get(self, request):
         form = SignupForm()
         return render(request, "accounts/signup.html", context={
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
        
        return render(request, "accounts/signup.html", context={
             "form":form
         })


class LoginView(View):
    def get(self, request):
         return render(request, "accounts/login.html")
    
    def post(self, request):
        print(request.POST)
        email = request.POST.get('email')  # フォームからメールアドレスを取得
        password = request.POST.get('password')  # フォームからパスワードを取得
        user = authenticate(request, username=email, password=password)  # 認証を実施

        if user is not None:  # ユーザーが認証された場合
            login(request, user)  # ログイン
            return redirect("home")  # ホーム画面へリダイレクト

        # 認証が失敗した場合
        return render(request, "accounts/login.html", context={
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
        return render(request, 'tasks/home.html', context)


class TodayTasksView(LoginRequiredMixin, View):
    def get(self, request):
        current_date = timezone.localtime()  # 現在の日時（ローカルタイム）
        tasks = Task.objects.filter(
            user=request.user,
            scheduled_datetime__date=current_date.date()
        )

        # デバッグ用出力：取得したタスク数と内容を確認
        print(f"今日のタスク数: {tasks.count()}")
        for task in tasks:
            print(f"タスク名: {task.task_name}, 完了状態: {task.completion_status}, 担当者コメント: {task.comment}")
            task.estimated_time_hours = task.estimated_time / 60

        return render(request, 'tasks/today_tasks.html', {
            'tasks': tasks,
            'current_date': current_date
        })

    def post(self, request):
        if request.method == "POST":
            comment_text = request.POST.get("comment")
            task_id = request.POST.get("task_id") 
            task = Task.objects.get(pk=task_id)
            Comment.objects.create(user=request.user, comment=comment_text, task=task)
            
            # デバッグ用出力：追加されたコメントを確認
            print(f"コメントが追加されました: {comment_text}, タスクID: {task_id}")
        
        return redirect('today_tasks')

class RecurringTaskListView(View):
    def get(self, request):
        recurrences = Recurrence.objects.filter(user=request.user)
        context = {
            'recurrences': recurrences
        }
        return render(request, 'tasks/recurring_tasks.html', context)

class RecurringTaskCreateView(CreateView):
    model = Recurrence
    fields = ['task_name', 'user',  'start_date', 'due_time', 'estimated_time', 'recurrence_type', 'weekday', 'day_of_month', 'end_date']
    template_name = 'tasks/add_recurring_tasks.html'
    success_url = reverse_lazy('recurring_tasks')  # 登録後、周期タスク一覧にリダイレクト

    # フォーム送信時にリクエストユーザーを保存する処理
    def form_valid(self, form):
        form.instance.user = self.request.user  # 現在のユーザーを設定
        return super().form_valid(form)

class Individual_TaskCreateView(CreateView):
    model = Task
    fields = ['task_name', 'estimated_time', 'due_datetime']
    template_name = 'tasks/add_individual_tasks.html'
    success_url = reverse_lazy('today_tasks')

    def form_valid(self, form):
        form.instance.user = self.request.user
        
        # `scheduled_datetime`をローカルタイムの日付として設定
        form.instance.scheduled_datetime = timezone.localtime(timezone.now()).replace(hour=0, minute=0, second=0, microsecond=0)

        # デバッグ出力で確認
        print("タスク登録処理が呼ばれました")
        print("タスク名:", form.instance.task_name)
        print("所要時間（分）:", form.instance.estimated_time)
        print("完了期限:", form.instance.due_datetime)
        print("予定日時:", form.instance.scheduled_datetime)
        print("ユーザー:", form.instance.user)

        saved_task = form.save(commit=True)
        if saved_task:
            print("タスクが正常に保存されました。")
        else:
            print("タスクの保存に失敗しました。")

        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.user.is_authenticated:
            context['family_members'] = User.objects.filter(family_id=self.request.user.family_id)
        else:
            context['family_members'] = []
        return context

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
        return render(request, 'tasks/task_analysis.html',context)

class MyPageView(LoginRequiredMixin, View):
    def get(self, request):
        user = request.user
        family = user.family_id if user.family_id else None
        family_members = user.family_id.members.all() if user.family_id else []
        image_form = ProfileImageForm(instance=user)
        return render(request, 'accounts/mypage.html', {
            'user': user,
            'family': family,
            'family_members': family_members,
            'image_form': image_form
        })
    
    def post(self, request):
        print("POST request received")
        image_form = ProfileImageForm(request.POST, request.FILES, instance=request.user)

        if image_form.is_valid():
            user = image_form.save(commit=False)
            profile_image = request.FILES.get('profile_image')   # アップロードされた画像を取得

            print("Profile image uploaded:", profile_image is not None)

            if 'profile_image-clear' in request.POST:
                user.profile_image = None  # 画像をクリア
            elif profile_image:
                user.profile_image = profile_image  # 画像を設定
                print("Profile image saved:", user.profile_image)  # 画像が設定されたか確認

            user.save()
            print("Uploaded image URL:", user.profile_image.url if user.profile_image else "No image")  # URLが表示されるか確認
            return redirect('mypage')
        else:
            print("Form errors:", image_form.errors)
        
        user = request.user
        family = user.family_id if user.family_id else None
        family_members = user.family_id.members.all() if user.family_id else[]
        return render(request, 'accounts/mypage.html',{
            'user':user,
            'family': family,
            'family_members':family_members,
            'image_form':image_form
        })

class AccountEditView(LoginRequiredMixin, UpdateView):
    model = User
    form_class = AccountEditForm
    template_name = 'accounts/account_edit.html'
    success_url = reverse_lazy('mypage')

    def get_object(self, queryset=None):
        return self.request.user
    
    def form_valid(self, form):
        # パスワードが変更された場合、セッションを更新してログアウトを防ぐ
        response = super().form_valid(form)
        if form.cleaned_data.get('new_password'):
            update_session_auth_hash(self.request, self.object)
        return response

class FamilyEditView(LoginRequiredMixin, UpdateView):
    model = Family
    form_class = FamilyEditForm
    template_name = 'accounts/family_edit.html'
    success_url = reverse_lazy('mypage')

    def get_object(self, queryset=None):
        return self.request.user.family_id

class FamilyInviteUrlView(LoginRequiredMixin, View):
    def get(self, request):
        return render(request, 'accounts/family_invite_url.html')

# 家族招待URLを生成してJSONで返すAPIエンドポイント
@login_required
@require_GET
def generate_invite_url(request):
    user = request.user
    family = user.family_id
    
    # もし招待URLが設定されていない場合、新しいUUIDを生成して保存
    if not family.invite_url:
        family.invite_url = str(uuid.uuid4())
        family.save()

    # フロントエンドに返すURLを準備
    response_data = {
        "url": request.build_absolute_uri(reverse('signup_family_invite', args=[family.invite_url]))
    }
    return JsonResponse(response_data)

# 招待リンクを通じたアカウント登録ビュー
def signup_family_invite(request, invite_url):
    family = get_object_or_404(Family, invite_url=invite_url)

    if request.method == "POST":
        form = SignupForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.family_id = family
            user.save()
            return redirect("login")
    else:
        form = SignupForm()
    
    return render(request, "accounts/signup_family_invite.html",{
        "form": form,
        "family_name": family.name
    })
    
class SignupInviteView(View):
    def get(self, request, invite_code):
        family = get_object_or_404(Family, invitate_url=invite_code)
        form = SignupForm()
        return render(request, 'accounts/signup_family_invite.html', {'form':form, 'family':family})
    
    def post(self, request, invite_code):
        family = get_object_or_404(Family, invitate_url=invite_code)
        form = SignupForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.family_id = family
            user.save()
            login(request, user)
            return redirect('mypage')
        return render(request, 'accounts/signup_family_invite.html', {'form':form, 'family':family})

class AccountDeleteView(LoginRequiredMixin, View):
    def get(self, request):
        # 未完了のタスクがあるか確認
        has_incomplete_tasks = request.user.task_set.filter(completion_status=False).exists()
        return render(request, 'accounts/account_delete.html', {
            'has_incomplete_tasks': has_incomplete_tasks,
        })

    def post(self, request):
        user = request.user
        password = request.POST.get('password')
        confirm = request.POST.get('confirm') == 'true'

        # confirmがtrueなら削除を実行
        if confirm:
            user.delete()
            logout(request)
            return redirect('login')

        # パスワードの確認
        if authenticate(username=user.email, password=password):
            has_incomplete_tasks = user.task_set.filter(completion_status=False).exists()
            if has_incomplete_tasks:
                # 未完了タスクがある場合はエラーメッセージとともに画面を再表示
                return render(request, 'accounts/account_delete.html', {
                    'has_incomplete_tasks': True,
                    'error_message': '未完了のタスクがあるため、アカウント削除できません。'
                })
             # 削除確認ポップアップを表示する
            return render(request, 'accounts/account_delete.html', {
                'show_confirm_popup': True,
            })
        else:
            # パスワードが間違っている場合
            return render(request, 'accounts/account_delete.html', {
                'has_incomplete_tasks': False,
                'error_message': 'パスワードが正しくありません。'
            })

class RecurringTaskEditView(LoginRequiredMixin, UpdateView):
    model = Recurrence
    form_class = RecurringTaskForm
    template_name = 'tasks/recurring_task_edit.html'
    success_url = reverse_lazy('recurring_tasks')

    def form_valid(self, form):
        response = super().form_valid(form)
        return response

class IndividualTaskEditView(LoginRequiredMixin, UpdateView):
    model = Task
    form_class = IndividualTaskForm
    template_name = 'tasks/individual_task_edit.html'
    success_url = reverse_lazy('today_tasks')

    def form_valid(self, form):
        response = super().form_valid(form)
        return response