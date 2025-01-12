from django.contrib import admin
from .models import User, Family, Task, Recurrence, Comment, Reaction

# モデルを登録
admin.site.register(User)
admin.site.register(Family)
admin.site.register(Task)
admin.site.register(Comment)
admin.site.register(Reaction)

class RecurrenceAdmin(admin.ModelAdmin):
    def get_fields(self, request, obj=None):
        fields = super().get_fields(request, obj)
        if obj and obj.recurrence_type != 2:
            fields.remove('day_of_month')
        return fields

admin.site.register(Recurrence, RecurrenceAdmin)