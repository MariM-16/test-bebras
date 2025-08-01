# Generated by Django 5.1.7 on 2025-07-09 19:27

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('test_bebras', '0005_alter_testassignment_assigned_by'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='answer',
            name='grade_status',
            field=models.CharField(choices=[('pending', 'Pendiente de Revisión'), ('graded', 'Corregida'), ('not_applicable', 'No Aplica (auto-corregida)')], default='not_applicable', max_length=20),
        ),
        migrations.AddField(
            model_name='answer',
            name='graded_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='answer',
            name='graded_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='graded_answers', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='answer',
            name='manual_grade',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True),
        ),
    ]
