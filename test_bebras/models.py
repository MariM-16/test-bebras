from django.db import models
from django.contrib.auth.models import User, Group
from ckeditor.fields import RichTextField
from ckeditor_uploader.fields import RichTextUploadingField
from django.db.models import JSONField
from django.conf import settings 

class Skill(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name

class Question(models.Model):
    statement = RichTextUploadingField()
    image = models.ImageField(upload_to='question_images/', blank=True, null=True)
    difficulty = models.IntegerField(choices=[(i, str(i)) for i in range(1, 8)])
    skills = models.ManyToManyField(Skill)
    RESPONSE_FORMAT = [
        ('text', 'Open Text'),
        ('choice', 'Choices'),
        ('number', 'Number'),
    ]
    response_format = models.CharField(max_length=20, choices=RESPONSE_FORMAT)
    correct_answer = models.TextField(null=True, blank=True)
    
    def __str__(self):
        return self.statement[:50]

class Choice(models.Model):
    question = models.ForeignKey(Question, related_name='choices', on_delete=models.CASCADE)
    text = RichTextUploadingField()
    is_correct = models.BooleanField(default=False)

    def __str__(self):
        return self.text

class Test(models.Model):
    name = models.CharField(max_length=100)
    questions = models.ManyToManyField(Question, related_name='tests_assigned')
    maximum_time = models.DurationField()
    allow_backtracking = models.BooleanField(default=True)
    allow_no_response = models.BooleanField(default=True)

    points_per_difficulty = JSONField(default=dict)
    penalty_type = models.CharField(max_length=20, choices=[('none', 'None'), ('fixed', 'Fixed'), ('by_difficulty', 'By Difficulty')], default='none')
    fixed_penalty = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    penalty_by_difficulty = JSONField(default=dict, blank=True, null=True)
    max_attempts = models.IntegerField(default=1, help_text="Maximum number of attempts allowed for this test per student.")

    creator = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_tests')
    assigned_groups = models.ManyToManyField(Group, through='TestAssignment', related_name='assigned_tests', blank=True) # <-- ¡¡ESTA ES LA LÍNEA CORRECTA CON 'through'!!
    
    def __str__(self):
        return self.name

class Answer(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    attempt = models.ForeignKey('Attempt', null=True, blank=True, on_delete=models.CASCADE)
    answer_text = models.TextField(null=True, blank=True)
    answer_number = models.IntegerField(null=True, blank=True)
    answer_choice = models.ForeignKey(Choice, null=True, blank=True, on_delete=models.SET_NULL)
    answered_at = models.DateTimeField(auto_now_add=True)
    
    GRADE_STATUS_CHOICES = [
        ('pending', 'Pendiente de Revisión'),
        ('graded', 'Corregida'),
    ]
    grade_status = models.CharField(
        max_length=20, 
        choices=GRADE_STATUS_CHOICES, 
        default='not_applicable'
    )
    manual_grade = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    graded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='graded_answers')
    graded_at = models.DateTimeField(null=True, blank=True)

    is_correct_manual = models.BooleanField(null=True, blank=True)
    question_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)


    def __str__(self):
        return f"Respuesta de {self.user} a {self.question}"
    
    def save(self, *args, **kwargs):
        if self.question.response_format == 'text' and self.grade_status == 'not_applicable':
            self.grade_status = 'pending'
        super().save(*args, **kwargs)

class Attempt(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    test = models.ForeignKey(Test, on_delete=models.CASCADE)
    date_taken = models.DateTimeField(auto_now_add=True)
    score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    correct_count = models.IntegerField(default=0)
    end_time = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Intento {self.id} de {self.user.username} para {self.test.name}"

class TestAssignment(models.Model):
    test = models.ForeignKey(Test, on_delete=models.CASCADE)
    group = models.ForeignKey(Group, on_delete=models.CASCADE)
    assigned_at = models.DateTimeField(auto_now_add=True)
    assigned_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='test_assignments_made')

    class Meta:
        unique_together = ('test', 'group') 

    def __str__(self):
        return f"{self.test.name} asignado a {self.group.name} el {self.assigned_at.strftime('%Y-%m-%d')}"