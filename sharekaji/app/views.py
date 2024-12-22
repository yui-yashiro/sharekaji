import uuid
from datetime import datetime, timedelta

# Django公式モジュール
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.db.models import Count
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render, reverse
from django.urls import reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.decorators.http import require_GET, require_POST
from django.views.decorators.csrf import csrf_protect
from django.views.generic.edit import CreateView, UpdateView

# アプリケーション内のモジュール
from .models import Family, User, Task, Reaction, Recurrence, Comment
from app.forms import SignupForm, ProfileImageForm, AccountEditForm, FamilyEditForm, RecurringTaskForm, IndividualTaskForm

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
        # 現在時刻を定義
        now = timezone.now()

        # 完了期限2時間前を切った未完了タスク通知の作成
        reminders = Task.objects.filter(
            user=request.user,
            completion_status=False,
            due_datetime__lte=now + timedelta(hours=2),
            due_datetime__gt=now
        )

        # タスク完了通知の作成
        family_notifications = Task.objects.filter(
            user__family_id=request.user.family_id,
            completion_status=True,
            completion_datetime__gte=timezone.now() - timedelta(days=1)
        ).exclude(user=request.user)
        
        # 年月の設定（カレンダー表示用）
        if year is None or month is None:
            year = now.year
            month = now.month

        # 個別タスクを取得してイベントデータに追加（重複を防ぐため、localtimeで調整）
        tasks = Task.objects.filter(user=request.user)
        event_data = [
            {
                "title": task.task_name,
                "start": timezone.localtime(task.due_datetime).isoformat() if task.due_datetime else None
            }
            for task in tasks
        ]

        # 未完了タスクを取得
        incomplete_tasks = Task.objects.filter(
            user=request.user,
            completion_status=False
        )

        # 完了したタスクを取得
        completed_tasks = Task.objects.filter(
            completion_status=True,
            user__family_id=request.user.family_id,
            completion_datetime__isnull=False
            )

        context = {
            "event_data": event_data,
            "tasks": tasks,
            "reminders": reminders,
            "family_notifications": family_notifications,
            "incomplete_tasks": incomplete_tasks,
            "completed_tasks": completed_tasks,
        }
        return render(request, 'tasks/home.html', context)

class TodayTasksView(LoginRequiredMixin, View):
    def get(self, request, selected_date=None):
        # 選択された日付がある場合はそれを使用、なければ現在の日付を取得
        if selected_date:
            current_date = datetime.strptime(selected_date, "%Y-%m-%d").date()
        else:
            current_date = timezone.localtime().date()

        # 今日のタスクを取得
        tasks = Task.objects.filter(
            user__family_id=request.user.family_id,
            scheduled_datetime__date=current_date
        ).prefetch_related('task_comments__user')

        # タスクごとのリアクションを集計
        tasks_with_reactions = []
        for task in tasks:
            reactions = Reaction.objects.filter(task=task).values('reaction_type').annotate(count=Count('reaction_type'))
            reaction_data = [
                {
                    "emoji": dict(Reaction.REACTION_TYPES).get(reaction["reaction_type"], "❓"),
                    "count": reaction["count"],
                }
                for reaction in reactions
            ]
            tasks_with_reactions.append({"task": task, "reactions": reaction_data})

        # 取得したタスクの日時をローカルタイムに変換
        for task in tasks:
            task.scheduled_datetime = timezone.localtime(task.scheduled_datetime)
            task.due_datetime = timezone.localtime(task.due_datetime)
            task.estimated_time_hours = task.estimated_time / 60  # 分を時間に変換

        # テンプレートに渡す
        return render(request, 'tasks/today_tasks.html', {
            'tasks': tasks,
            'reaction_emojis': dict(Reaction.REACTION_TYPES),
            'current_date': current_date
        })

@csrf_protect
@login_required
def add_comment(request):
    if request.method == "POST":
        comment_text = request.POST.get("comment")
        task_id = request.POST.get("task_id")
        user = request.user
        
        if comment_text and task_id:
            comment = Comment.objects.create(
                task_id=task_id,
                user=user,
                comment=comment_text
            )

        return JsonResponse({
            "id": comment.id,
            "comment": comment_text,
            "user": user.name,
            'avatar': user.profile_image.url if user.profile_image and hasattr(user.profile_image, 'url') else '/media/profile_images/default_profile_image.png',
            "created_at": comment.created_at.strftime('%Y-%m-%d %H:%M:%S'),
        })
    return JsonResponse({'error': 'コメントの送信に失敗しました。'}, status=400)

@csrf_protect
@login_required
def delete_comment(request, comment_id):
    if request.method == "POST":
        comment = get_object_or_404(Comment, id=comment_id, user=request.user)
        comment.delete()
        return JsonResponse({"success": True})
    return JsonResponse({"error": "Invalid request method"}, status=405)

class RecurringTaskListView(View):
    def get(self, request):
        recurrences = Recurrence.objects.filter(user=request.user)
        context = {
            'recurrences': recurrences
        }
        return render(request, 'tasks/recurring_tasks.html', context)

class RecurringTaskCreateView(CreateView):
    model = Recurrence
    fields = ['task_name', 'start_date', 'due_time', 'estimated_time', 'recurrence_type', 'weekday', 'day_of_month', 'end_date']
    template_name = 'tasks/add_recurring_tasks.html'
    success_url = reverse_lazy('recurring_tasks')  # 登録後、周期タスク一覧にリダイレクト

    def form_valid(self, form):
        print("form_valid メソッドが呼ばれました")
        print(f"フォームの内容: {form.cleaned_data}")

        # 担当者が未選択の場合、自動割り当て
        assignee_id = self.request.POST.get("assignee")
        if assignee_id:
            assignee = User.objects.get(id=assignee_id)
            form.instance.user = assignee
            print(f"担当者が選択されました: {assignee}")
        else:
            form.instance.user = self.get_auto_assigned_user()
            print(f"担当者が未選択のため、自動割り当て: {form.instance.user}")

        recurrence = form.save()
        print(f"周期タスクが保存されました: {recurrence}")

        current_date = recurrence.start_date
        while current_date <= recurrence.end_date:
            if self.is_task_date(current_date, recurrence):
                # タスクを作成
                task = Task.objects.create(
                    user=form.instance.user,
                    task_name=recurrence.task_name,
                    scheduled_datetime=timezone.make_aware(datetime.combine(current_date, recurrence.due_time)),
                    due_datetime=timezone.make_aware(datetime.combine(current_date, recurrence.due_time)),
                    estimated_time=recurrence.estimated_time,
                    recurrence=recurrence  # 親タスク（周期タスク）を参照
                )
                print(f"タスク作成: {task.task_name} on {task.scheduled_datetime}")
                
                # 次回の担当者を設定
                form.instance.user = self.get_next_user(form.instance.user)
            current_date += timedelta(days=1)

        return super().form_valid(form)

    def get_auto_assigned_user(self):
        # 最初のタスクを割り当てる際に、最もタスク数が少ない家族メンバーを選ぶ
        # 家族全員を取得
        family_members = User.objects.filter(family_id=self.request.user.family_id)

        # 各メンバーのタスク数を計算
        task_counts = family_members.annotate(task_count=Count('task'))

        # タスク数が最も少ないメンバーを選択
        least_task_user = task_counts.order_by('task_count').first()

        # 家族がいない場合は入力者をデフォルトで返す
        return least_task_user or self.request.user

    def get_next_user(self, current_user):
        # 現在の担当者の次にタスクを担当するユーザーを取得（家族メンバー間で順番に回す）
        # 家族メンバーを取得
        family_members = User.objects.filter(family_id=self.request.user.family_id).order_by('id')

        # 現在の担当者の次のユーザーを取得
        current_index = list(family_members).index(current_user)
        next_index = (current_index + 1) % len(family_members)

        return family_members[next_index]

    def is_task_date(self, date, recurrence):
        if recurrence.recurrence_type == 1:  # 毎日
            return True
        elif recurrence.recurrence_type == 2 and date.weekday() == recurrence.weekday:  # 毎週
            return True
        elif recurrence.recurrence_type == 3 and date.day == recurrence.day_of_month:  # 毎月
            return True
        return False

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.user.is_authenticated:
            context['family_members'] = User.objects.filter(family_id=self.request.user.family_id)
        else:
            context['family_members'] = []

        # 1日から31日までの値をテンプレートに渡す
        context['day_range'] = range(1, 31 + 1)

        return context
    
class Individual_TaskCreateView(CreateView):
    model = Task
    fields = ['task_name', 'estimated_time', 'due_datetime']
    template_name = 'tasks/add_individual_tasks.html'
    success_url = reverse_lazy('today_tasks')

    def form_valid(self, form):
        form.instance.user = self.request.user
        
        # `scheduled_datetime` を現在の日時として設定し、タイムゾーン情報を追加
        form.instance.scheduled_datetime = timezone.make_aware(
            datetime.combine(form.cleaned_data.get('due_datetime').date(), datetime.min.time())
        )

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

        # ラベルとデータを作成
        completed_labels = [task['user__name'] for task in completed_tasks]
        completed_data = [task['task_count'] for task in completed_tasks]
        incomplete_labels = [task['user__name'] for task in incomplete_tasks]
        incomplete_data = [task['task_count'] for task in incomplete_tasks]

        # コンテキストにデータを渡す
        context = {
            'completed_labels': completed_labels,
            'completed_data': completed_data,
            'incomplete_labels': incomplete_labels,
            'incomplete_data': incomplete_data,
        }
        return render(request, 'tasks/task_analysis.html', context)

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
        # デバッグ用出力
        print("=== フォーム送信データ ===")
        print(self.request.POST)
        print("=== フォームのクリーンデータ ===")
        print(form.cleaned_data)

        # 保存処理
        response = super().form_valid(form)

        # 必要なデータの取得
        recurrence = form.instance
        task_name = form.cleaned_data.get('task_name')
        user = form.cleaned_data.get('user')
        due_time = form.cleaned_data.get('due_time')
        estimated_time = form.cleaned_data.get('estimated_time')

        # 開始日と終了日を取得
        current_date = recurrence.start_date
        end_date = recurrence.end_date

        # 開始日から終了日までの間でタスクを更新または新規作成
        while current_date <= end_date:
            if self.is_task_date(current_date, recurrence):
                due_datetime = timezone.make_aware(
                    datetime.combine(current_date, due_time)
                )
                task, created = Task.objects.update_or_create(
                    recurrence=recurrence,
                    due_datetime=due_datetime,
                    defaults={
                        'task_name': task_name,
                        'user': user,
                        'estimated_time': estimated_time,
                        'scheduled_datetime': due_datetime,
                    }
                )
                if created:
                    print(f"タスク新規作成: {task}")
                else:
                    print(f"タスク更新: {task}")
            current_date += timedelta(days=1)

        return response

    def is_task_date(self, date, recurrence):
        """周期タスクが特定の日付に該当するかを判定"""
        if recurrence.recurrence_type == 1:  # 毎日
            return True
        elif recurrence.recurrence_type == 2 and date.weekday() == recurrence.weekday:  # 毎週
            return True
        elif recurrence.recurrence_type == 3 and date.day == recurrence.day_of_month:  # 毎月
            return True
        return False

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['family_members'] = User.objects.filter(family_id=self.request.user.family_id)
        context['day_range'] = range(1, 31 + 1)
        return context


class IndividualTaskEditView(LoginRequiredMixin, UpdateView):
    model = Task
    form_class = IndividualTaskForm
    template_name = 'tasks/individual_task_edit.html'
    success_url = reverse_lazy('today_tasks')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['family_members'] = User.objects.filter(family_id=self.request.user.family_id)
        return context
    
    def get_form_kwargs(self):
        kwargs =  super().get_form_kwargs()
        kwargs['family_id'] = self.request.user.family_id
        return kwargs

    def form_valid(self, form):
        # 担当者が未設定の場合に自動で割り当て
        if not form.cleaned_data.get('user'):
            # 家族メンバーの取得
            family_members = User.objects.filter(family_id=self.request.user.family_id)
            
            # 前回のタスクの担当者を取得
            last_task = Task.objects.filter(user__in=family_members).order_by('-due_datetime').first()
            last_assignee = last_task.user if last_task else None  # 'assignee' を 'user' に変更

            # タスク数が少ないメンバーを優先し、前回の担当者を除外
            available_members = family_members.exclude(id=last_assignee.id) if last_assignee else family_members
            assignee = available_members.annotate(task_count=Count('task')).order_by('task_count').first()

            # もし全員が前回と同じ担当者なら、除外せずに最少タスク数のメンバーを割り当て
            form.instance.user = assignee if assignee else last_assignee
        
        return super().form_valid(form)

class IndividualTaskDeleteView(LoginRequiredMixin, View):
    def get(self, request, task_id):
        task = get_object_or_404(Task, id=task_id, user=request.user)
        return render(request, 'tasks/individual_task_delete.html', {'task': task})
    
    def post(self, request, task_id):
        task = get_object_or_404(Task, id=task_id, user=request.user)
        task.delete()
        messages.success(request, "タスクが正常に削除されました。")
        return redirect('today_tasks')

class RecurringTaskDeleteView(LoginRequiredMixin, View):
    def get(self, request, task_id):
        recurring_task = get_object_or_404(Recurrence, id=task_id, user=request.user)
        return render(request, 'tasks/recurring_task_delete.html', {'recurring_task': recurring_task})

    def post(self, request, task_id):
        try:
            recurring_task = get_object_or_404(Recurrence, id=task_id, user=request.user)

            # 削除対象の周期タスクに基づいて生成された未来の日付の個別タスクを取得
            future_tasks = Task.objects.filter(
                recurrence=recurring_task,
                scheduled_datetime__gte=timezone.now()
            )

            # 未来の個別タスクが存在する場合は削除
            if future_tasks.exists():
                future_tasks.delete()

            # 周期タスク自体を削除
            recurring_task.delete()

            # 成功メッセージを追加
            messages.success(request, "周期タスクと関連する未来日のタスクが正常に削除されました。")

        except Recurrence.DoesNotExist:
            # エラーメッセージを追加
            messages.error(request, "削除しようとした周期タスクが見つかりませんでした。")
        
        return redirect('recurring_tasks')
    
# タスク進捗を更新するビュー
@login_required
def update_task_progress(request, task_id):
    from .forms import ProgressForm
    task = get_object_or_404(Task, id=task_id)

    if request.method == 'POST':
        form = ProgressForm(request.POST, instance=task)
        if form.is_valid():
            task = form.save(commit=False)
            if task.completion_status:
                task.completion_datetime = timezone.now()
            else:
                task.completion_datetime = None
            task.save()
            messages.success(request, '進捗が更新されました')
            return redirect('today_tasks')
    else:
        form = ProgressForm(instance=task)

    return render(request, 'tasks/update_progress.html', {'form':form, 'task':task})

# リアクション表示のビュー
@require_POST
@login_required
def toggle_reaction(request, task_id):
    import json

    # タスクの取得
    task = get_object_or_404(Task, id=task_id)

    try:
        # リクエストボディのデータを解析
        data = json.loads(request.body)
        reaction_type = int(data.get("reaction_type"))

        # バリデーション: reaction_type が有効な範囲内か確認
        valid_reactions = [choice[0] for choice in Reaction.REACTION_TYPES]
        if reaction_type not in valid_reactions:
            return JsonResponse({"error": "Invalid reaction type."}, status=400)

        # リアクションの作成または削除
        reaction, created = Reaction.objects.get_or_create(
            task=task,
            user=request.user,
            reaction_type=reaction_type
        )
        if not created:
            reaction.delete()

        # 現在のリアクションカウントを取得
        reactions = (
            Reaction.objects.filter(task=task)
            .values("reaction_type")
            .annotate(count=Count("reaction_type"))
        )

        # レスポンスデータを準備
        response_data = [
            {
                "emoji": dict(Reaction.REACTION_TYPES).get(reaction["reaction_type"], "❓"),
                "count": reaction["count"],
            }
            for reaction in reactions
        ]

        return JsonResponse({"reaction_counts": response_data})

    except (json.JSONDecodeError, ValueError, TypeError) as e:
        return JsonResponse({"error": "Invalid data received."}, status=400)