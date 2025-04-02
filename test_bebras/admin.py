from django.contrib import admin
from .models import Skill, Question, Choice, ScoringConfiguration, Test, Attempt, Answer

admin.site.register(Skill)
admin.site.register(Question)
admin.site.register(Choice)
admin.site.register(ScoringConfiguration)
admin.site.register(Test)
admin.site.register(Attempt)
admin.site.register(Answer)
