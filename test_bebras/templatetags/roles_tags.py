from django import template
from ..utils.user_roles import is_teacher_or_staff

register = template.Library()

@register.filter
def is_teacher(user):
    if not user.is_authenticated:
        return False
    return is_teacher_or_staff(user)