import json

from django.contrib import admin
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models
from django.forms import Textarea

from .models import Answer, Attempt, Choice, Question, Skill, Test, TestAssignment


class ChoiceInline(admin.TabularInline):
    model = Choice
    extra = 0

@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('short_statement', 'difficulty', 'response_format')
    list_filter = ('difficulty', 'response_format')
    search_fields = ('statement',)
    filter_horizontal = ('skills',)
    formfield_overrides = {
        models.TextField: {'widget': Textarea(attrs={'rows': 4, 'cols': 80})},
    }

    def get_inline_instances(self, request, obj=None):
        inlines = []
        if obj:
            if obj.response_format == 'choice':
                inlines.append(ChoiceInline(self.model, self.admin_site))
        return inlines

    def short_statement(self, obj):
        return obj.statement[:60] + '...' if len(obj.statement) > 60 else obj.statement
    short_statement.short_description = "Enunciado"

@admin.register(Skill)
class SkillAdmin(admin.ModelAdmin):
    search_fields = ('name',)

@admin.register(Choice)
class ChoiceAdmin(admin.ModelAdmin):
    list_display = ('question', 'text', 'is_correct')
    list_filter = ('is_correct',)
    formfield_overrides = {
        models.TextField: {'widget': Textarea(attrs={'rows': 4, 'cols': 80})},
    }

@admin.register(Test)
class TestAdmin(admin.ModelAdmin):
    list_display = ('name', 'maximum_time_display', 'allow_backtracking', 'allow_no_response', 'display_points_and_penalties', 'creator')
    filter_horizontal = ('questions',)
    fieldsets = (
        (None, {
            'fields': ('name', 'questions', 'maximum_time', 'allow_backtracking', 'allow_no_response', 'creator')
        }),
        ('Configuración de Puntuación', {
            'fields': ('points_per_difficulty', 'penalty_type', 'fixed_penalty', 'penalty_by_difficulty'),
            'description': 'Configure cómo se calculan los puntos y las penalizaciones. Use JSON válido para los campos de dificultad (ej: {"1": 10, "2": 20}).'
        }),
    )

    formfield_overrides = {
        models.JSONField: {'widget': Textarea(attrs={'rows': 4, 'cols': 80})},
    }

    def maximum_time_display(self, obj):
        total_seconds = obj.maximum_time.total_seconds()
        minutes = int(total_seconds // 60)
        seconds = int(total_seconds % 60)
        return f"{minutes}m {seconds}s" if seconds > 0 else f"{minutes}m"
    maximum_time_display.short_description = "Tiempo Máximo"

    def display_points_and_penalties(self, obj):
        points_info = "Puntos por Dificultad: " + (json.dumps(obj.points_per_difficulty, cls=DjangoJSONEncoder) if obj.points_per_difficulty else "No definido")
        penalty_info = f"Penalización: {obj.penalty_type.capitalize()}"
        if obj.penalty_type == 'fixed':
            penalty_info += f" (Fija: {obj.fixed_penalty if obj.fixed_penalty is not None else 'N/A'} pts)"
        elif obj.penalty_type == 'by_difficulty':
            penalty_info += " (Por Dificultad: " + (json.dumps(obj.penalty_by_difficulty, cls=DjangoJSONEncoder) if obj.penalty_by_difficulty else "No definido") + ")"
        return f"{points_info}<br>{penalty_info}"
    display_points_and_penalties.short_description = "Puntos y Penalizaciones"
    display_points_and_penalties.allow_tags = True


@admin.register(Answer)
class AnswerAdmin(admin.ModelAdmin):
    list_display = ('user', 'question', 'attempt', 'answered_at')
    list_filter = ('answered_at', 'user', 'attempt__test')
    search_fields = ('user__username', 'question__statement')
    readonly_fields = ('user', 'question', 'attempt', 'answer_text', 'answer_number', 'answer_choice', 'answered_at')
    
    def has_add_permission(self, request):
        return False
    def has_change_permission(self, request, obj=None):
        return False
    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Attempt)
class AttemptAdmin(admin.ModelAdmin):
    list_display = ('user', 'test', 'date_taken', 'score', 'correct_count')
    list_filter = ('date_taken', 'user', 'test')
    search_fields = ('user__username', 'test__name')
    readonly_fields = ('user', 'test', 'date_taken', 'score', 'correct_count')

    def has_add_permission(self, request):
        return False
    def has_change_permission(self, request, obj=None):
        return False
    def has_delete_permission(self, request, obj=None):
        return False

@admin.register(TestAssignment)
class TestAssignmentAdmin(admin.ModelAdmin):
    list_display = ('test', 'group', 'assigned_by', 'assigned_at')
    list_filter = ('assigned_at', 'group', 'assigned_by')
    search_fields = ('test__name', 'group__name', 'assigned_by__username')
    readonly_fields = ('assigned_at',)