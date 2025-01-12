from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager

# カスタムユーザーマネージャを定義するクラス
class UserManager(BaseUserManager):
    def create_user(self, name, email, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(name=name, email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, name, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(name, email, password, **extra_fields)


# ユーザーモデル
class User(AbstractUser):
    username = models.CharField(max_length=32, null=True, unique=True) # ユーザー名
    email = models.EmailField(max_length=256, unique=True) # メールアドレス
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

    USERNAME_FIELD = "username"
    EMAIL_FIELD = "email"
    REQUIRED_FIELDS = ["email"]

    objects = UserManager()

    class Meta:
        db_table = "users"
    
    def __str__(self):
        return self.username if self.username else self.email

# families
class Family(models.Model):
    name =  models.CharField(max_length=32, unique=True) #家族名
    invite_url = models.TextField(null=True, blank=True) #家族招待URL
    created_at = models.DateTimeField(auto_now_add=True) # タスク作成日時
    updated_at = models.DateTimeField(auto_now=True) # 最終更新日時

    class Meta:
        db_table = "families"
    
    def __str__(self):
        return self.name

# tasks
class Task(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)  # usersとのリレーション
    recurrence = models.ForeignKey('Recurrence', on_delete=models.CASCADE, null=True, blank=True)  # 繰り返しタスクとのリレーション
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
    
    def __str__(self):
        return self.task_name

# recurrences
class Recurrence(models.Model):
    RECURRENCE_CHOICES = [
        (0, '日'),
        (1, '週'),
        (2, '月'),
    ]

    WEEKDAY_CHOICES = [
        (0, '月曜日'),
        (1, '火曜日'),
        (2, '水曜日'),
        (3, '木曜日'),
        (4, '金曜日'),
        (5, '土曜日'),
        (6, '日曜日'),
    ]

    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)  # usersとのリレーション
    task_name = models.CharField(max_length=100)  # 家事タスク名
    start_date = models.DateField()  # 繰り返し開始日
    due_time = models.TimeField()  # タスク完了期限時刻
    estimated_time = models.IntegerField()  # 所要時間見込 (分単位)
    recurrence_type = models.IntegerField(choices=RECURRENCE_CHOICES, null=True, blank=True)  # 繰り返し周期: 0 = 日, 1　= 週, 2　= 月
    weekday = models.IntegerField(choices=WEEKDAY_CHOICES, null=True, blank=True)   # 繰り返しの曜日（例: 月=0, 火=1, ...日=6）
    day_of_month = models.IntegerField(null=True, blank=True)  # 日付指定（例: 毎月15日）
    end_date = models.DateField(null=True, blank=True)  # 繰り返し終了日
    created_at = models.DateTimeField(auto_now_add=True)  # タスク作成日時
    updated_at = models.DateTimeField(auto_now=True)  # 最終更新日時

    class Meta:
        db_table = 'recurrences'
    
    def get_recurrence_type_display(self):
        """recurrence_type の数値をラベルに変換"""
        return dict(self.RECURRENCE_CHOICES).get(self.recurrence_type, "None")
    
    def __str__(self):
        recurrence_label = dict(self.RECURRENCE_CHOICES).get(self.recurrence_type, 'None')
        return f"{self.task_name} (Type: {recurrence_label})"

# comments
class Comment(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='task_comments')  # tasksとのリレーション
    user = models.ForeignKey(User, on_delete=models.CASCADE)  # usersとのリレーション
    comment = models.TextField(blank=True, null=True)  # コメント内容
    created_at = models.DateTimeField(auto_now_add=True)  # コメント作成日時
    updated_at = models.DateTimeField(auto_now=True)  # 最終更新日時

    class Meta:
        db_table = 'comments'
    
    def __str__(self):
        return f"Comment by {self.user.username} on {self.task.task_name}"

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
    
    def __str__(self):
        return f"{self.user.username} reacted {self.get_reaction_type_display()} to {self.task.task_name}"