from django.db import models
from django.contrib.auth.models import User
from ckeditor.fields import RichTextField

class Skill(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name

class Question(models.Model):
    statement = RichTextField()
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
    text = RichTextField()
    is_correct = models.BooleanField(default=False)

    def __str__(self):
        return self.text

class Test(models.Model):
    name = models.CharField(max_length=100)
    questions = models.ManyToManyField(Question)
    maximum_time = models.DurationField()
    allow_backtracking = models.BooleanField(default=True)
    allow_no_response = models.BooleanField(default=True)

    points_per_difficulty = models.JSONField(default=dict)
    penalty_type = models.CharField(max_length=20, choices=[('fixed', 'Fixed'), ('by_difficulty', 'By Difficulty')], default='fixed')
    fixed_penalty = models.IntegerField(blank=True, null=True)
    penalty_by_difficulty = models.JSONField(default=dict, blank=True, null=True)

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

    def __str__(self):
        return f"Respuesta de {self.user} a {self.question}"
    

class Attempt(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    test = models.ForeignKey(Test, on_delete=models.CASCADE)
    date_taken = models.DateTimeField(auto_now_add=True)
    score = models.FloatField(default=0)
    correct_count = models.IntegerField(default=0)

    def __str__(self):
        return f"Attempt {self.id} by {self.user.username} for {self.test.name}"
