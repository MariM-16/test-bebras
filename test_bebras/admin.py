from django.contrib import admin
from .models import Skill, Question, Choice, Test, Attempt, Answer

class ChoiceInline(admin.TabularInline):
    model = Choice
    extra = 0

@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('short_statement', 'difficulty', 'response_format')
    list_filter = ('difficulty', 'response_format')
    search_fields = ('statement',)
    filter_horizontal = ('skills',)

    def get_inline_instances(self, request, obj=None):
        inlines = []
        if obj:
            if obj.response_format == 'choice':
                inlines.append(ChoiceInline(self.model, self.admin_site))
        return inlines

    def short_statement(self, obj):
        return obj.statement[:60]
    short_statement.short_description = "Question"

@admin.register(Skill)
class SkillAdmin(admin.ModelAdmin):
    search_fields = ('name',)

@admin.register(Choice)
class ChoiceAdmin(admin.ModelAdmin):
    list_display = ('question', 'text', 'is_correct')
    list_filter = ('is_correct',)

@admin.register(Test)
class TestAdmin(admin.ModelAdmin):
    list_display = ('name', 'maximum_time', 'allow_backtracking', 'points_per_difficulty', 'penalty_type', 'fixed_penalty', 'allow_no_response')
    filter_horizontal = ('questions',)

@admin.register(Answer)
class AnswerAdmin(admin.ModelAdmin):
    list_display = ('user', 'question', 'answered_at')
    list_filter = ('answered_at',)

@admin.register(Attempt)
class AttemptAdmin(admin.ModelAdmin):
    list_display = ('user', 'test', 'date_taken', 'score', 'correct_count')
    list_filter = ('date_taken',)
