from django.contrib.auth.models import Group

def is_teacher_or_staff(user):
    return user.is_staff or user.groups.filter(name='Profesores').exists()

def is_student(user):
    return user.groups.filter(name='Estudiantes').exists()