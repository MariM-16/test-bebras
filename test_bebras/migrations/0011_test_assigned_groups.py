# Generated by Django 5.1.7 on 2025-07-09 23:17

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
        ('test_bebras', '0010_remove_test_assigned_groups'),
    ]

    operations = [
        migrations.AddField(
            model_name='test',
            name='assigned_groups',
            field=models.ManyToManyField(blank=True, related_name='assigned_tests', through='test_bebras.TestAssignment', to='auth.group'),
        ),
    ]
