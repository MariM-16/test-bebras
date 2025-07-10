from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.urls import reverse

from ..models import TestAssignment, Test, Group, User


def assign_tests_and_notify(selected_tests_queryset, target_group, assigned_by_user,
                             send_notification_email, email_subject, email_message, request_obj=None):
    newly_assigned_tests = []
    already_assigned_tests = []

    for test in selected_tests_queryset:
        test_assignment, created = TestAssignment.objects.get_or_create(
            test=test,
            group=target_group,
            defaults={'assigned_by': assigned_by_user}
        )
        if created:
            newly_assigned_tests.append(test.name)
        else:
            already_assigned_tests.append(test.name)

    email_sent = False
    email_result_message = ""
    email_error = None

    if send_notification_email and newly_assigned_tests:
        student_emails = [s.email for s in target_group.user_set.all() if s.email]
        valid_student_emails = [email for email in student_emails if "@" in email and "." in email]

        if valid_student_emails:
            test_names_list = "\n".join([f"- {name}" for name in newly_assigned_tests])
            context = {
                'group_name': target_group.name,
                'teacher_name': assigned_by_user.get_full_name() or assigned_by_user.username,
                'assigned_tests_list': test_names_list,
                'custom_message': email_message,
                'platform_url': request_obj.build_absolute_uri(reverse('test_list')) if request_obj else "URL_NO_DISPONIBLE"
            }

            html_message = render_to_string('emails/test_assignment_notification.html', context)
            plain_message = strip_tags(html_message)

            try:
                send_mail(
                    email_subject,
                    plain_message,
                    settings.EMAIL_HOST_USER,
                    valid_student_emails,
                    html_message=html_message,
                    fail_silently=False,
                )
                email_sent = True
                email_result_message = f"Email(s) de notificación enviados a {len(valid_student_emails)} estudiantes de '{target_group.name}'."
            except Exception as e:
                email_sent = False
                email_error = f"Error al enviar emails: {e}. Revisa la configuración de tu correo."
                email_result_message = email_error
        else:
            email_result_message = f"No hay estudiantes con email válido en el grupo '{target_group.name}' para enviar notificaciones."
    elif send_notification_email and not newly_assigned_tests:
        email_result_message = "No se enviaron emails porque no hay nuevos tests asignados."

    return {
        'newly_assigned_tests': newly_assigned_tests,
        'already_assigned_tests': already_assigned_tests,
        'email_sent': email_sent,
        'email_message': email_result_message,
        'email_error': email_error,
    }