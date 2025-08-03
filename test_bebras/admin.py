import json

from django.contrib import admin
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models
from django.forms import Textarea
from django.utils.timezone import now
from decimal import Decimal, InvalidOperation
from django.utils.html import strip_tags

from .models import Answer, Attempt, Choice, Question, Skill, Test, TestAssignment, GroupMetadata

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
        clean_text = strip_tags(obj.statement)
        return clean_text[:60] + '...' if len(clean_text) > 60 else clean_text
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
    
    def clean_choice_text(self, obj):
        return strip_tags(obj.text)
    clean_choice_text.short_description = "Alternativa"

@admin.register(Test)
class TestAdmin(admin.ModelAdmin):
    list_display = ('name', 'maximum_time_display', 'allow_backtracking', 'allow_no_response', 'max_attempts', 'display_points_and_penalties', 'creator')
    filter_horizontal = ('questions',)

    fieldsets = (
        (None, {
            'fields': ('name', 'questions', 'maximum_time', 'allow_backtracking', 'allow_no_response', 'max_attempts', 'creator')
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
    list_display = ('user', 'question', 'attempt', 'answered_at', 'grade_status', 'manual_grade', 'is_correct_manual', 'graded_by', 'graded_at')
    list_filter = ('answered_at', 'user', 'attempt__test', 'grade_status', 'is_correct_manual')
    search_fields = ('user__username', 'question__statement', 'answer_text')

    readonly_fields = ('user', 'question', 'attempt', 'answer_text', 'answer_number', 'answer_choice', 'answered_at', 'manual_grade', 'graded_by', 'graded_at')
    
    fieldsets = (
        (None, {
            'fields': ('user', 'question', 'attempt', 'answered_at', 'answer_text', 'answer_number', 'answer_choice')
        }),
        ('Corrección Manual', {
            'fields': ('grade_status', 'is_correct_manual'),
            'description': 'Marque si la respuesta es correcta. El puntaje se calculará automáticamente.'
        }),
    )

    def save_model(self, request, obj, form, change):
        if 'is_correct_manual' in form.changed_data:
            obj.grade_status = 'graded'
            obj.graded_by = request.user
            obj.graded_at = now()

            if obj.is_correct_manual:
                test_points_config = obj.attempt.test.points_per_difficulty
                
                if test_points_config and str(obj.question.difficulty) in test_points_config:
                    obj.manual_grade = Decimal(str(test_points_config[str(obj.question.difficulty)]))
                else:
                    obj.manual_grade = Decimal('0.0')
            else:
                calculated_penalty = Decimal('0.0')
                test_penalty_type = obj.attempt.test.penalty_type
                
                if test_penalty_type == 'fixed':
                    calculated_penalty = obj.attempt.test.fixed_penalty if obj.attempt.test.fixed_penalty is not None else Decimal('0.0')
                elif test_penalty_type == 'by_difficulty':
                    penalty_config = obj.attempt.test.penalty_by_difficulty
                    if penalty_config and str(obj.question.difficulty) in penalty_config:
                        calculated_penalty = Decimal(str(penalty_config[str(obj.question.difficulty)]))
                    else:
                        calculated_penalty = Decimal('0.0')

                obj.manual_grade = -calculated_penalty 

        elif 'grade_status' in form.changed_data and obj.grade_status != 'graded':
            obj.graded_by = None
            obj.graded_at = None
            obj.manual_grade = None
            obj.is_correct_manual = None

        super().save_model(request, obj, form, change)


    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        if obj is None:
            return super().has_change_permission(request, obj)
        
        return obj.grade_status == 'pending'

    def has_delete_permission(self, request, obj=None):
        return True


@admin.register(Attempt)
class AttemptAdmin(admin.ModelAdmin):
    list_display = ('user', 'test', 'date_taken', 'score', 'correct_count')
    list_filter = ('date_taken', 'user', 'test')
    search_fields = ('user__username', 'test__name')
    readonly_fields = ('user', 'test', 'date_taken', 'end_time', 'score', 'correct_count')

    def has_add_permission(self, request):
        return False
    def has_change_permission(self, request, obj=None):
        return False
    def has_delete_permission(self, request, obj=None):
        return True

@admin.register(TestAssignment)
class TestAssignmentAdmin(admin.ModelAdmin):
    list_display = ('test', 'group', 'assigned_by', 'assigned_at')
    list_filter = ('assigned_at', 'group', 'assigned_by')
    search_fields = ('test__name', 'group__name', 'assigned_by__username')
    readonly_fields = ('assigned_at',)

@admin.register(GroupMetadata)
class GroupMetadataAdmin(admin.ModelAdmin):
    list_display = ('group', 'created_by')
    search_fields = ('group__name', 'created_by__username')
    list_filter = ('created_by',)