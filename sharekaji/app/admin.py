from django.contrib import admin
from .models import User, Family, Task, Recurrence, Comment, Reaction

# モデルを登録
admin.site.register(User)
admin.site.register(Family)
admin.site.register(Task)
admin.site.register(Recurrence)
admin.site.register(Comment)
admin.site.register(Reaction)