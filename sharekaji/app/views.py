import uuid
from datetime import datetime, timedelta

# Django公式モジュール
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render, reverse
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.decorators import method_decorator
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
                    family = Family.objects.create(name=f"{user.username}家")
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
        # タスク表示基準を標準時間から日本時間に変更
        current_time = timezone.localtime()

        # 完了期限2時間前を切った未完了タスク通知の作成
        reminders = Task.objects.filter(
            user=request.user,
            completion_status=False,
            due_datetime__lte=current_time + timedelta(hours=2),
            due_datetime__gt=current_time
        )

        # タスク完了通知の作成
        family_notifications = Task.objects.filter(
            user__family_id=request.user.family_id,
            completion_status=True,
            completion_datetime__gte=timezone.now() - timedelta(days=1)
        ).exclude(user=request.user)
        
        # 年月の設定（カレンダー表示用）
        if year is None or month is None:
            year = current_time.year
            month = current_time.month

        # 個別タスクを取得してイベントデータに追加（重複を防ぐため、localtimeで調整）
        tasks = Task.objects.filter(user=request.user)
        event_data = [
            {
                "title": f"{task.task_name}（{timezone.localtime(task.due_datetime).strftime('%H:%M')}）" if task.due_datetime else task.task_name,
                "start": timezone.localtime(task.due_datetime).isoformat() if task.due_datetime else None
            }
            for task in tasks
        ]
        
        
        # 未完了タスクを取得
        incomplete_tasks = Task.objects.filter(
            user=request.user,
            completion_status=False,
            due_datetime__gte=current_time - timedelta(days=3),
            due_datetime__lte=current_time + timedelta(days=7)
        )

        # 完了したタスクを取得
        completed_tasks = Task.objects.filter(
            completion_status=True,
            user=request.user,
            completion_datetime__isnull=False,
            completion_datetime__gte=current_time - timedelta(days=7)
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
        for task in tasks:
            reactions = Reaction.objects.filter(task=task).values('reaction_type').annotate(count=Count('reaction_type'))
            task.reactions_data = [
                {
                    "emoji": dict(Reaction.REACTION_TYPES).get(reaction["reaction_type"], "❓"),
                    "count": reaction["count"],
                }
                for reaction in reactions
            ]

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
            "user": user.username,
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
        family_id = request.user.family_id
        recurrences = Recurrence.objects.filter(user__family_id=family_id)

        recurrence_type_mapping = {
            1: "日",
            2: "週",
            3: "月"
        }

        for recurrence in recurrences:
            # 所要時間
            hours = recurrence.estimated_time / 60
            recurrence.formatted_time = f"{hours:.1f}時間"

            # 繰り返し周期の表示
            recurrence.recurrence_type_display = recurrence_type_mapping.get(recurrence.recurrence_type)
        
        context = {
            'recurrences': recurrences
        }
        return render(request, 'tasks/recurring_tasks.html', context)

class RecurringTaskCreateView(CreateView):
    model = Recurrence
    form_class = RecurringTaskForm
    template_name = 'tasks/add_recurring_tasks.html'
    success_url = reverse_lazy('recurring_tasks')  # 登録後、周期タスク一覧にリダイレクト

    def form_valid(self, form):
        print("form_valid メソッドが呼ばれました")
        print(f"フォームの内容: {form.cleaned_data}")

        # フォームで指定された担当者を取得
        assigned_user = form.cleaned_data.get('user')
        if assigned_user:
            form.instance.user = assigned_user
            print(f"担当者が選択されました: {assigned_user}")
        else:
            # 担当者が未指定の場合、自動割り当てを実行
            form.instance.user = self.get_auto_assigned_user()
            print(f"担当者が未選択のため、自動割り当て: {form.instance.user}")

        # 繰り返し周期に基づいて不要なフィールドをクリア
        if form.cleaned_data['recurrence_type'] != 1:  # 週でない場合
            form.instance.weekday = None
        if form.cleaned_data['recurrence_type'] != 2:  # 月でない場合
            form.instance.day_of_month = None

        recurrence = form.save()  # フォームの保存
        print(f"周期タスクが保存されました: {recurrence}")

        # タスクの作成処理
        current_date = recurrence.start_date
        assigned_user = form.instance.user  # 初期担当者

        while current_date <= recurrence.end_date:
            if self.is_task_date(current_date, recurrence):
                # タスクを作成
                Task.objects.create(
                    user=assigned_user,
                    task_name=recurrence.task_name,
                    scheduled_datetime=timezone.make_aware(datetime.combine(current_date, recurrence.due_time)),
                    due_datetime=timezone.make_aware(datetime.combine(current_date, recurrence.due_time)),
                    estimated_time=recurrence.estimated_time,
                    recurrence=recurrence  # 親タスク（周期タスク）を参照
                )
                print(f"タスク作成: {recurrence.task_name} on {current_date}")

                # 担当者をローテーション
                if form.cleaned_data.get('user') is None:
                    assigned_user = self.get_next_user(assigned_user)
            current_date += timedelta(days=1)

        return super().form_valid(form)

    def get_auto_assigned_user(self):
        family_members = User.objects.filter(family_id=self.request.user.family_id)

        if not family_members.exists():
            print("家族メンバーが見つからないため、現在のユーザーを割り当てます。")
            return self.request.user

        # 未完了タスク数を計算し、タスクが最も少ないメンバーを取得
        task_counts = family_members.annotate(task_count=Count('task', filter=Q(task__completion_status=False)))
        least_task_user = task_counts.order_by('task_count').first()

        print("未完了タスク数:")
        for member in task_counts:
            print(f"{member.username}: {member.task_count} 未完了タスク")

        return least_task_user

    def get_next_user(self, current_user):
        family_members = list(User.objects.filter(family_id=self.request.user.family_id).order_by('id'))

        # 現在の担当者の次のユーザーを取得（ローテーション）
        current_index = family_members.index(current_user)
        next_index = (current_index + 1) % len(family_members)
        next_user = family_members[next_index]

        print(f"現在の担当者: {current_user.username}, 次の担当者: {next_user.username}")
        return next_user

    def is_task_date(self, date, recurrence):
        # 繰り返しの条件に応じてタスクを作成するか判定
        if recurrence.recurrence_type == 0:  # 毎日
            return True
        if recurrence.recurrence_type == 1 and date.weekday() == recurrence.weekday:  # 毎週
            return True
        if recurrence.recurrence_type == 2 and date.day == recurrence.day_of_month:  # 毎月
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
    form_class = IndividualTaskForm
    template_name = 'tasks/add_individual_tasks.html'
    success_url = reverse_lazy('today_tasks')

    def form_valid(self, form):
        print("POSTデータ:", self.request.POST)

        # フォームで指定された担当者を取得
        assigned_user = form.cleaned_data.get('user')
        print("フォームから取得した担当者:", assigned_user)

        if not assigned_user:
            # 担当者が未設定の場合、自動割り当てを実行
            print("担当者が未指定のため自動割り当てを開始します。")
            family_members = User.objects.filter(family_id=self.request.user.family_id)
            if family_members.exists():
                # 各メンバーの未完了タスク数を計算
                members_with_task_count = family_members.annotate(
                    incomplete_task_count=Count('task', filter=Q(task__completion_status=False))
                )
                assigned_user = members_with_task_count.order_by('incomplete_task_count').first()
                print("未完了タスクが最も少ない担当者を自動割り当て:", assigned_user)
            else:
                assigned_user = self.request.user
                print("家族メンバーがいないため、現在のユーザーを割り当てます:", assigned_user)

        # フォームに担当者を設定
        form.instance.user = assigned_user
        print("最終的な担当者:", form.instance.user)

         # `due_datetime` から `scheduled_datetime` を計算
        due_datetime = form.cleaned_data.get('due_datetime')
        if due_datetime:
            form.instance.scheduled_datetime = timezone.make_aware(
                datetime.combine(due_datetime.date(), datetime.min.time())
        )
        else:
            # デフォルト値として現在日時を設定
            form.instance.scheduled_datetime = timezone.now()
            print("`due_datetime` が指定されていないため、`scheduled_datetime` に現在日時を設定しました。")

        # タスクの保存
        saved_task = form.save()
        if saved_task:
            print("タスクが正常に保存されました:", saved_task)
        else:
            print("タスクの保存に失敗しました。")

        return super().form_valid(form)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['family_id'] = self.request.user.family_id
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['family_members'] = User.objects.filter(family_id=self.request.user.family_id)
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
        ).values('user__username').annotate(task_count=Count('id'))

        # 未完了タスクを家族ごとに集計
        incomplete_tasks = Task.objects.filter(
            user__in=family_members,
            completion_status=False,
        ).values('user__username').annotate(task_count=Count('id'))

        # ラベルとデータを作成
        completed_labels = [task['user__username'] for task in completed_tasks]
        completed_data = [task['task_count'] for task in completed_tasks]
        incomplete_labels = [task['user__username'] for task in incomplete_tasks]
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

class AccountDeleteView(View):
    @method_decorator(login_required)
    def get(self, request):
        return render(request, 'accounts/account_delete.html', {
            'error_message': '',
            'show_confirm_popup': False,
        })

    @method_decorator(login_required)
    def post(self, request):
        user = request.user
        password = request.POST.get('password')
        confirm = request.POST.get('confirm') == 'true'

        # パスワード確認
        if not user.check_password(password):
            return render(request, 'accounts/account_delete.html', {
                'error_message': 'パスワードが正しくありません。',
                'show_confirm_popup': False,
            })

        # 未完了タスクがあるか確認
        incomplete_tasks = user.task_set.filter(completion_status=False)
        if incomplete_tasks.exists():
            # 未完了タスクがある場合の対応
            return render(request, 'accounts/account_delete.html', {
                'error_message': '未完了のタスクがあります。他のメンバーに割り振るか、削除してください。',
                'show_confirm_popup': False,
            })

        # 確認ポップアップの状態
        if confirm:
            user.delete()
            logout(request)
            return redirect('login')

        return render(request, 'accounts/account_delete.html', {
            'error_message': '',
            'show_confirm_popup': True,
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

        # フォームで指定された担当者を取得
        assigned_user = form.cleaned_data.get('user')
        if assigned_user:
            form.instance.user = assigned_user
            print(f"担当者が選択されました: {assigned_user}")
        else:
            # 担当者が未指定の場合、自動割り当てを実行
            form.instance.user = self.get_auto_assigned_user()
            print(f"担当者が未選択のため、自動割り当て: {form.instance.user}")

        # 繰り返し周期に基づいて不要なフィールドをクリア
        if form.cleaned_data['recurrence_type'] != 1:  # 週でない場合
            form.instance.weekday = None
        if form.cleaned_data['recurrence_type'] != 2:  # 月でない場合
            form.instance.day_of_month = None

        # 保存処理
        response = super().form_valid(form)

        # 必要なデータの取得
        recurrence = form.instance
        task_name = form.cleaned_data.get('task_name')
        user = form.instance.user  # 最終決定された担当者
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

                # 担当者をローテーション
                if assigned_user is None:  # 担当者が未指定の場合のみローテーション
                    user = self.get_next_user(user)
            current_date += timedelta(days=1)

        return response

    def get_auto_assigned_user(self):
        # 家族内で未完了タスクが最も少ないメンバーを自動で割り当てる
        family_members = User.objects.filter(family_id=self.request.user.family_id)

        if not family_members.exists():
            print("家族メンバーが見つからないため、現在のユーザーを割り当てます。")
            return self.request.user

        # 未完了タスク数を計算し、タスクが最も少ないメンバーを取得
        task_counts = family_members.annotate(task_count=Count('task', filter=Q(task__completion_status=False)))
        least_task_user = task_counts.order_by('task_count').first()

        print("未完了タスク数:")
        for member in task_counts:
            print(f"{member.username}: {member.task_count} 未完了タスク")

        return least_task_user

    def get_next_user(self, current_user):
        # 家族全員を取得
        family_members = list(User.objects.filter(family_id=self.request.user.family_id).order_by('id'))

        # 現在の担当者の次のユーザーを取得（ローテーション）
        current_index = family_members.index(current_user)
        next_index = (current_index + 1) % len(family_members)
        next_user = family_members[next_index]

        print(f"現在の担当者: {current_user.username}, 次の担当者: {next_user.username}")
        return next_user

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
            print("担当者未設定。未完了タスクが最も少ないメンバーを割り当てます。")
            # 家族メンバーの取得
            family_members = User.objects.filter(family_id=self.request.user.family_id)
            
            if family_members.exists():
                # 未完了タスクが最も少ないメンバーを選択
                assigned_user = family_members.annotate(
                    incomplete_task_count=Count('task', filter=Q(task__completion_status=False))
                ).order_by('incomplete_task_count').first()
                form.instance.user = assigned_user
                print("自動割り当てされた担当者:", assigned_user)
            else:
                form.instance.user = self.request.user  # デフォルトで現在のユーザーを割り当て
                print("家族メンバーがいないため、現在のユーザーを割り当て:", form.instance.user)
        
        return super().form_valid(form)

class IndividualTaskDeleteView(LoginRequiredMixin, View):
    def get(self, request, task_id):
        task = get_object_or_404(Task, id=task_id, user=request.user)
        estimated_time_hours = task.estimated_time / 60
        return render(request, 'tasks/individual_task_delete.html', {
            'task': task,
            'estimated_time_hours': estimated_time_hours
        })
    
    def post(self, request, task_id):
        task = get_object_or_404(Task, id=task_id, user=request.user)
        task.delete()
        messages.success(request, "タスクが正常に削除されました。")
        return redirect('today_tasks')

class RecurringTaskDeleteView(LoginRequiredMixin, View):
    def get(self, request, task_id):
        recurrence = get_object_or_404(Recurrence, id=task_id)
        recurrence.formatted_time = f"{recurrence.estimated_time / 60:.1f}時間"

        recurrence_type_mapping = {
            1: "日",
            2: "週",
            3: "月"
        }
        recurrence.recurrence_type_display = recurrence_type_mapping.get(recurrence.recurrence_type)

        return render(request, 'tasks/recurring_task_delete.html', {'recurrence': recurrence})

    def post(self, request, task_id):
        try:
            recurring_task = get_object_or_404(Recurrence, id=task_id)

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