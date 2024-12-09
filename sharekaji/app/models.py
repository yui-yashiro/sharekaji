from django.db import models
from django.contrib.auth.models import AbstractUser

# Create your models here.
# users
class User(AbstractUser):
    # 不要なフィールドを完全に削除
    first_name = None
    last_name = None
    date_joined = None
    username = None
    is_superuser = None
    is_staff = None
    is_active = None

    name = models.CharField(max_length=32, unique=True) # ユーザー名
    email = models.EmailField(max_length=256, unique=True) # メールアドレス
    password = models.CharField(max_length=100) # パスワード
    family_id = models.ForeignKey('Family', on_delete=models.SET_NULL, null=True, related_name="members")  # 家族ID
    profile_image = models.ImageField(upload_to='profile_images/', blank=True, null=True)   # プロフィール画像
    family_relationship = models.CharField(max_length=32, blank=True, null=True)  # 続柄
    created_at = models.DateTimeField(auto_now_add=True) # アカウント作成日時
    updated_at = models.DateTimeField(auto_now=True) # 最終更新日時

    groups = models.ManyToManyField(
        'auth.Group',
        related_name='custom_user_groups',
        blank=True
    )

    user_permissions = models.ManyToManyField(
        'auth.Permission',
        related_name='custom_user_permissions',
        blank=True
    )

    USERNAME_FIELD = "name"
    EMAIL_FIELD = "email"
    REQUIRED_FIELDS = ["email"]

    class Meta:
        db_table = "users"

# families
class Family(models.Model):
    name =  models.CharField(max_length=32, unique=True) #家族名
    invite_url = models.TextField(null=True, blank=True) #家族招待URL
    created_at = models.DateTimeField(auto_now_add=True) # タスク作成日時
    updated_at = models.DateTimeField(auto_now=True) # 最終更新日時

    class Meta:
        db_table = "families"

# tasks
class Task(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)  # usersとのリレーション
    recurrence = models.ForeignKey('Recurrence', on_delete=models.SET_NULL, null=True, blank=True)  # 繰り返しタスクとのリレーション
    task_name = models.CharField(max_length=100)  # 家事タスク名
    scheduled_datetime = models.DateTimeField()  # 予定日時
    due_datetime = models.DateTimeField()  # 対応完了期限
    estimated_time = models.IntegerField()  # 所要時間見込 (分単位)
    completion_status = models.BooleanField(default=False)  # ステータス（0:未完了、1:完了）
    comment = models.TextField(blank=True, null=True)  # 担当者コメント
    completion_datetime = models.DateTimeField(null=True, blank=True)  # タスク完了日時
    created_at = models.DateTimeField(auto_now_add=True)  # タスク作成日時
    updated_at = models.DateTimeField(auto_now=True)  # 最終更新日時

    class Meta:
        db_table = 'tasks'

# recurrences
class Recurrence(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)  # usersとのリレーション
    task_name = models.CharField(max_length=100)  # 家事タスク名
    start_date = models.DateField()  # 繰り返し開始日
    due_time = models.TimeField()  # タスク完了期限時刻
    estimated_time = models.IntegerField()  # 所要時間見込 (分単位)
    recurrence_type = models.IntegerField()  # 繰り返し周期: 0 = なし, 1 = 日, 2 = 週, 3 = 月
    weekday = models.IntegerField(null=True, blank=True)  # 繰り返しの曜日（例: 月=0, 火=1, ...）
    day_of_month = models.IntegerField(null=True, blank=True)  # 日付指定（例: 毎月15日）
    end_date = models.DateField(null=True, blank=True)  # 繰り返し終了日
    created_at = models.DateTimeField(auto_now_add=True)  # タスク作成日時
    updated_at = models.DateTimeField(auto_now=True)  # 最終更新日時

    class Meta:
        db_table = 'recurrences'

# comments
class Comment(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='task_comments')  # tasksとのリレーション
    user = models.ForeignKey(User, on_delete=models.CASCADE)  # usersとのリレーション
    comment = models.TextField(blank=True, null=True)  # コメント内容
    created_at = models.DateTimeField(auto_now_add=True)  # コメント作成日時
    updated_at = models.DateTimeField(auto_now=True)  # 最終更新日時

    class Meta:
        db_table = 'comments'

# reactions
class Reaction(models.Model):
    REACTION_TYPES = [
        (0, '👍'),
        (1, '💖'),
        (2, '👏'),
        (3, '🙇‍♀️'),
   ]
    task = models.ForeignKey(Task, on_delete=models.CASCADE)  # tasksとのリレーション
    user = models.ForeignKey(User, on_delete=models.CASCADE)  # usersとのリレーション
    reaction_type = models.IntegerField(choices=REACTION_TYPES, null=True, blank=True) # リアクションの種類 0=👍、1=💖、2=👏、3=🙇‍♀️
    created_at = models.DateTimeField(auto_now_add=True)  # リアクション日時

    class Meta:
        db_table = 'reactions'
        unique_together = ('task', 'user', 'reaction_type')