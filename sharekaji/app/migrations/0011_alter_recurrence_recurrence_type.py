# Generated by Django 4.1 on 2025-01-07 17:43

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0010_alter_recurrence_recurrence_type_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='recurrence',
            name='recurrence_type',
            field=models.IntegerField(blank=True, choices=[(0, '日'), (1, '週'), (2, '月')], null=True),
        ),
    ]
