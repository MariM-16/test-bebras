# Generated by Django 5.1.7 on 2025-04-16 01:52

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('test_bebras', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='attempt',
            name='correct_count',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='attempt',
            name='score',
            field=models.FloatField(default=0),
        ),
    ]
