from django.shortcuts import render, redirect, get_object_or_404, HttpResponse
from django.contrib.auth.decorators import login_required, user_passes_test
from django.urls import reverse
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User, Group
from .models import Test, Answer, Choice, Attempt, Question, TestAssignment, Skill
from collections import defaultdict
from django.db.models import Q
from django.contrib import messages
from datetime import timedelta
from django.utils import timezone 
from django import forms
from .forms import AutoTestCreationForm, StudentUploadForm, AssignTestForm
import random
import json
import csv
import io
from django.core.mail import send_mail
from django.conf import settings
from django.db.models import Avg, Sum, Count
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.contrib.auth import get_user_model
from decimal import Decimal, InvalidOperation
from .services.excel_exporter import generate_attempts_xlsx_report
from .services.test_assignment_service import assign_tests_and_notify
from .services.test_attempt_service import TestAttemptService
from .services.test_review_service import TestReviewService
from .utils.user_roles import is_teacher_or_staff, is_student

@login_required
def test_list(request):
    user_tests = Test.objects.none() 
    is_current_user_teacher_or_staff = is_teacher_or_staff(request.user)
    if is_current_user_teacher_or_staff:
        if request.user.is_staff:
            user_tests = Test.objects.all().order_by('name')
        else:
            user_tests = Test.objects.filter(creator=request.user).order_by('name')
    else: 
        user_groups_ids = request.user.groups.values_list('id', flat=True)
        user_tests = Test.objects.filter(assigned_groups__id__in=user_groups_ids).distinct().order_by('name')

    tests_with_attempt_info = []
    for test in user_tests:
        attempts_made = Attempt.objects.filter(user=request.user, test=test).count()
        
        attempts_remaining = test.max_attempts - attempts_made
        can_start_test = attempts_remaining > 0
        
        tests_with_attempt_info.append({
            'test': test,
            'attempts_made': attempts_made,
            'attempts_remaining': attempts_remaining,
            'can_start_test': can_start_test
        })

    context = {
        'tests': tests_with_attempt_info,
        'is_teacher_user': is_current_user_teacher_or_staff,
    }
    return render(request, 'tests/test_list.html', context)

@login_required
def test_detail(request, test_id):
    user = request.user
    test = get_object_or_404(Test, id=test_id)

    if is_teacher_or_staff(user):
        if not user.is_staff and test.creator != user:
            messages.error(request, "No tienes permiso para ver este test.")
            return redirect('test_list')
    elif is_student(user):
        user_groups_ids = user.groups.values_list('id', flat=True)
        if not Test.objects.filter(id=test_id, assigned_groups__id__in=user_groups_ids).exists():
            messages.error(request, "Este test no está asignado a ninguno de tus grupos.")
            return redirect('test_list')
    else:
        messages.error(request, "No tienes permiso para acceder a los tests.")
        return redirect('simple_login')

    finalized_attempts_count = Attempt.objects.filter(
        user=user,
        test=test,
        end_time__isnull=False 
    ).count()

    if finalized_attempts_count >= test.max_attempts: 
        messages.warning(request, f"Ya has agotado tus {test.max_attempts} intentos para este test.")

        last_finalized_attempt = Attempt.objects.filter(
            user=user,
            test=test,
            end_time__isnull=False
        ).order_by('-date_taken').first() 

        if last_finalized_attempt:
            messages.info(request, "Serás redirigido a la revisión de tu último intento.")
            return redirect('test_review', test_id=test.id, attempt_id=last_finalized_attempt.id)
        else:
            return redirect('test_list')

    current_attempt = Attempt.objects.filter(user=user, test=test, end_time__isnull=True).first()

    if not current_attempt:
        current_attempt = Attempt.objects.create(user=user, test=test, score=0, correct_count=0)
        messages.info(request, f"Iniciando un nuevo intento para el test: {test.name}. Este es tu intento {finalized_attempts_count + 1} de {test.max_attempts}.")
        request.session[f'current_question_index_{current_attempt.id}'] = 0
    else:
        messages.info(request, f"Continuando con tu intento para el test: {test.name}.")

    service = TestAttemptService(user, test, request.session, request.POST if request.method == 'POST' else None, attempt=current_attempt)

    if request.method == 'POST':
        process_results = service.process_post_request()

        if process_results['status'] == 'redirect':
            return redirect(reverse(process_results['view_name'], kwargs=process_results['kwargs']))
        elif process_results['status'] == 'validation_error':
            context = service.get_current_state() 
            context['error'] = process_results['message']
            return render(request, 'tests/test_detail.html', {
                'test': test,
                'attempt': context['attempt'],
                'current_question': context['current_question'],
                'question_number': context['question_number'],
                'answered': context['answered'],
                'total_questions': context['total_questions'],
                'user_answer_data': context['user_answer_data'],
                'allow_backtracking': context['allow_backtracking'],
                'error': context['error']
            })
    
    context = service.get_current_state()

    if context['status'] == 'finished':
        attempt_id = context['attempt_id']
        try:
            attempt = Attempt.objects.get(id=attempt_id)
            if attempt.end_time is None: 
                attempt.end_time = timezone.now()
                attempt.save()
        except Attempt.DoesNotExist:
            messages.error(request, "Error: No se encontró el intento del test para finalizar.")

        return redirect('test_review', test_id=test.id, attempt_id=context['attempt_id'])

    return render(request, 'tests/test_detail.html', {
        'test': test,
        'attempt': context['attempt'],
        'current_question': context['current_question'],
        'question_number': context['question_number'],
        'answered': context['answered'],
        'total_questions': context['total_questions'],
        'user_answer_data': context['user_answer_data'],
        'allow_backtracking': context['allow_backtracking'],
        'error': context['error']
    })


@login_required
def test_detail_teacher(request, test_id):
    if not is_teacher_or_staff(request.user):
        messages.error(request, "No tienes permiso para ver los detalles de tests de profesor.")
        return redirect('test_list')

    test = get_object_or_404(Test, pk=test_id)
    questions = test.questions.all().order_by('id')

    context = {
        'test': test,
        'questions': questions,
    }
    return render(request, 'tests/test_detail_teacher.html', context)

@login_required
def test_review(request, test_id, attempt_id):
    test = get_object_or_404(Test, id=test_id)
    attempt = get_object_or_404(Attempt, id=attempt_id)

    is_current_user_teacher_or_staff = is_teacher_or_staff(request.user)

    if not is_current_user_teacher_or_staff:
        if attempt.user != request.user:
            messages.error(request, "No tienes permiso para ver este intento.")
            return redirect('test_attempts')
    else:
        if not request.user.is_staff and test.creator != request.user:
            messages.error(request, "No tienes permiso para ver los resultados de este test (no lo creaste tú).")
            return redirect('test_attempts')

    review_service = TestReviewService(test_id, attempt_id)
    review_results = review_service.calculate_review_results()

    context = {
        'test': review_results['test'],
        'total_correct': review_results['total_correct'],
        'total_questions': review_results['total_questions'],
        'total_score': review_results['total_score'],
        'question_results': review_results['question_results'],
        'is_teacher_user': is_current_user_teacher_or_staff,
    }
    return render(request, 'tests/test_review.html', context)


@login_required
@user_passes_test(lambda u: is_teacher_or_staff(u) or is_student(u), login_url='/login/')
def test_attempts(request):
    user = request.user
    is_current_user_teacher_or_staff = is_teacher_or_staff(user)

    if is_current_user_teacher_or_staff:
        if request.user.is_staff:
            groups_visible_to_teacher = Group.objects.exclude(name__in=['Estudiantes', 'Profesores']).order_by('name')
            tests_visible_to_teacher = Test.objects.all().order_by('name')
            attempts_queryset = Attempt.objects.all()
        else:
            groups_visible_to_teacher = Group.objects.filter(
                testassignment__assigned_by=request.user
            ).distinct().exclude(name__in=['Estudiantes', 'Profesores']).order_by('name')

            tests_visible_to_teacher = Test.objects.filter(creator=request.user).order_by('name')

            attempts_queryset = Attempt.objects.filter(test__creator=request.user)

        selected_group_id = request.GET.get('group', '')
        selected_test_id = request.GET.get('test', '')

        if selected_group_id:
            try:
                group_obj = Group.objects.get(id=selected_group_id)
                attempts_queryset = attempts_queryset.filter(user__groups=group_obj)
            except Group.DoesNotExist:
                messages.warning(request, "Grupo no válido seleccionado.")

        if selected_test_id:
            try:
                test_obj = Test.objects.get(id=selected_test_id)
                if is_current_user_teacher_or_staff and not request.user.is_staff and test_obj.creator != request.user:
                    messages.error(request, "No tienes permiso para ver los resultados de este test.")
                    attempts_queryset = attempts_queryset.none()
                else:
                    attempts_queryset = attempts_queryset.filter(test=test_obj)
            except Test.DoesNotExist:
                messages.warning(request, "Test no válido seleccionado.")

        attempts = attempts_queryset.order_by('test__name', 'user__username', '-date_taken')
        show_user_column = True

    else:
        attempts = Attempt.objects.filter(user=user).order_by('-date_taken')
        show_user_column = False

    grouped_attempts = defaultdict(list)

    for attempt in attempts:
        if is_current_user_teacher_or_staff:
            if request.user.is_staff or attempt.test.creator == request.user:
                grouped_attempts[attempt.test].append(attempt)
        else:
            grouped_attempts[attempt.test].append(attempt)

    context = {
        'grouped_attempts': dict(grouped_attempts),
        'show_user': show_user_column,
        'is_teacher_user': is_current_user_teacher_or_staff,
    }

    if is_current_user_teacher_or_staff:
        context['groups'] = groups_visible_to_teacher
        context['tests_available'] = tests_visible_to_teacher
        context['selected_group_id'] = selected_group_id
        context['selected_test_id'] = selected_test_id

    return render(request, 'tests/test_attempts.html', context)

@login_required
@user_passes_test(is_teacher_or_staff, login_url='/login/')
def group_list_view(request):
    is_current_user_staff = request.user.is_staff
    if is_current_user_staff:
        groups = Group.objects.exclude(name__in=['Estudiantes', 'Profesores']).order_by('name')
    else:
        groups = Group.objects.filter(
            groupmetadata__created_by=request.user
        ).exclude(name__in=['Estudiantes', 'Profesores']).order_by('name')

    groups_data = []
    student_role_group, _ = Group.objects.get_or_create(name='Estudiantes')

    for group in groups:
        students_in_group = User.objects.filter(groups=group).filter(groups=student_role_group).order_by('first_name', 'last_name')

        if is_current_user_staff:
            assigned_tests_count = group.assigned_tests.count()
        else:
            assigned_tests_count = group.assigned_tests.filter(creator=request.user).count()

        groups_data.append({
            'group': group,
            'student_count': students_in_group.count(),
            'assigned_tests_count': assigned_tests_count,
        })

    context = {
        'groups_data': groups_data
    }
    return render(request, 'groups/group_list.html', context)

@login_required
@user_passes_test(is_teacher_or_staff, login_url='/login/')
def group_detail_view(request, group_id):
    target_group = get_object_or_404(Group.objects.exclude(name__in=['Estudiantes', 'Profesores']), id=group_id)

    if not request.user.is_staff:
        if not TestAssignment.objects.filter(group=target_group, assigned_by=request.user).exists():
            messages.error(request, "No tienes permiso para ver este grupo.")
            return redirect('group_list')

    student_role_group, _ = Group.objects.get_or_create(name='Estudiantes')

    students_in_group = User.objects.filter(groups=target_group).filter(groups=student_role_group).order_by('first_name', 'last_name')

    if request.user.is_staff:
        assigned_tests_for_group = target_group.assigned_tests.all().order_by('name')
        available_tests_queryset = Test.objects.exclude(id__in=assigned_tests_for_group.values_list('id', flat=True)).order_by('name')
    else:
        assigned_tests_for_group = target_group.assigned_tests.filter(creator=request.user).order_by('name')
        available_tests_queryset = Test.objects.filter(creator=request.user).exclude(id__in=assigned_tests_for_group.values_list('id', flat=True)).order_by('name')

    student_emails_for_notification = [
        s.email for s in students_in_group
        if s.email and "@" in s.email and "." in s.email
    ]

    if request.method == 'POST':
        form = AssignTestForm(request.POST, user=request.user, test_queryset=available_tests_queryset)
        if form.is_valid():
            selected_tests = form.cleaned_data['tests']
            send_notification_email = form.cleaned_data['send_notification_email']
            email_subject = form.cleaned_data['email_subject']
            email_message = form.cleaned_data['email_message']

            newly_assigned_count = 0
            for test_obj in selected_tests:
                test_assignment, created = TestAssignment.objects.get_or_create(
                    test=test_obj,
                    group=target_group,
                    defaults={'assigned_by': request.user}
                )
                if created:
                    newly_assigned_count += 1

            if newly_assigned_count > 0:
                messages.success(request, f"Se asignaron {newly_assigned_count} test(s) a '{target_group.name}' correctamente.")

                if send_notification_email and student_emails_for_notification:
                    assigned_test_names = [test.name for test in selected_tests]
                    test_names_list = "\n".join([f"- {name}" for name in  assigned_test_names])
                    context_email = {
                        'group_name': target_group.name,
                        'assigned_tests_list': test_names_list,
                        'custom_message': email_message,
                        'teacher_name': request.user,
                        'platform_url': request.build_absolute_uri(reverse('test_list'))
                    }
                    html_message = render_to_string('emails/test_assignment_notification.html', context_email)
                    plain_message = strip_tags(html_message)

                    try:
                        send_mail(
                            email_subject or "Nuevos Tests Asignados",
                            plain_message,
                            settings.DEFAULT_FROM_EMAIL,
                            student_emails_for_notification,
                            html_message=html_message,
                            fail_silently=False,
                        )
                        messages.success(request, "Correo de notificación enviado a los estudiantes.")
                    except Exception as e:
                        messages.error(request, f"Error al enviar el correo de notificación: {e}")
            else:
                messages.info(request, "No se asignaron nuevos tests, ya estaban asignados.")

            return redirect('group_detail', group_id=group_id)

        else:
            messages.error(request, "Por favor, corrige los errores en el formulario.")
    else:
        form = AssignTestForm(user=request.user, test_queryset=available_tests_queryset)

    context = {
        'group': target_group,
        'students_in_group': students_in_group,
        'assigned_tests_for_group': assigned_tests_for_group,
        'assign_test_form': form,
    }
    return render(request, 'groups/group_detail.html', context)

@login_required
@user_passes_test(is_teacher_or_staff, login_url='/login/')
def auto_test_creation_view(request):
    if request.method == 'POST':
        form = AutoTestCreationForm(request.POST)
        if form.is_valid():
            name = form.cleaned_data['name']
            number_of_questions = form.cleaned_data['number_of_questions']
            skills = form.cleaned_data['skills']
            min_difficulty = form.cleaned_data['min_difficulty']
            
            maximum_time_hours = form.cleaned_data['maximum_time_hours']
            maximum_time_minutes = form.cleaned_data['maximum_time_minutes']
            allow_backtracking = form.cleaned_data['allow_backtracking']
            allow_no_response = form.cleaned_data['allow_no_response']
            max_attempts = form.cleaned_data['max_attempts']

            form_points_per_difficulty = form.cleaned_data['points_per_difficulty']
            penalty_type = form.cleaned_data['penalty_type']
            fixed_penalty = form.cleaned_data['fixed_penalty']
            penalty_by_difficulty_data = form.cleaned_data.get('penalty_by_difficulty')

            available_questions = Question.objects.all()

            if skills:
                q_objects = Q()
                for skill in skills:
                    q_objects |= Q(skills=skill)
                available_questions = available_questions.filter(q_objects).distinct()
            
            available_questions = available_questions.filter(difficulty__gte=min_difficulty)

            selected_questions = list(available_questions.order_by('?')[:number_of_questions])

            if len(selected_questions) < number_of_questions:
                messages.warning(request, f"Solo se pudieron encontrar {len(selected_questions)} preguntas que cumplen tus criterios. Se ha creado el test con estas.")
            
            if not selected_questions:
                messages.error(request, "No se encontraron preguntas que cumplan los criterios especificados. Por favor, ajusta tu selección.")
                return render(request, 'groups/auto_test_creation.html', {'form': form})

            total_time = timedelta(hours=maximum_time_hours, minutes=maximum_time_minutes)

            points_data_for_json = {}
            if form_points_per_difficulty:
                points_data_for_json = {k: float(v) for k, v in form_points_per_difficulty.items()}
            else:
                points_data_for_json = {str(i): 1.0 for i in range(1, 8)} 

            penalty_data_for_json = {}
            if penalty_by_difficulty_data:
                penalty_data_for_json = {k: float(v) for k, v in penalty_by_difficulty_data.items()}

            new_test = Test.objects.create(
                name=name,
                maximum_time=total_time,
                allow_backtracking=allow_backtracking,
                allow_no_response=allow_no_response,
                max_attempts=max_attempts,
                points_per_difficulty= points_data_for_json,
                penalty_type=penalty_type,
                fixed_penalty=fixed_penalty,
                penalty_by_difficulty=penalty_by_difficulty_data if penalty_type == 'by_difficulty' else None,
                creator=request.user 
            )
            new_test.questions.set(selected_questions)

            messages.success(request, f"Test '{new_test.name}' creado exitosamente con {len(selected_questions)} preguntas.")
            return redirect('test_list') 
        else:
            messages.error(request, "Por favor, corrige los errores en el formulario.")
    else:
        form = AutoTestCreationForm()
    
    return render(request, 'groups/auto_test_creation.html', {'form': form})

@login_required
@user_passes_test(is_teacher_or_staff, login_url='/login/')
def upload_students_view(request):
    if request.method == 'POST':
        form = StudentUploadForm(request.POST, request.FILES)
        if form.is_valid():
            csv_file = request.FILES['csv_file']

            if not csv_file.name.endswith('.csv'):
                messages.error(request, 'El archivo debe ser un CSV (.csv).')
                return render(request, 'groups/upload_students.html', {'form': form})

            decoded_file = csv_file.read().decode('utf-8').splitlines()
            reader = csv.DictReader(decoded_file)

            created_count = 0
            updated_count = 0
            errors = []

            student_role_group, _ = Group.objects.get_or_create(name='Estudiantes')

            for i, row in enumerate(reader):
                line_num = i + 2
                
                student_email = row.get('email')
                first_name = row.get('nombre', '')
                last_name = row.get('apellido', '')
                groups_str = row.get('grupos', '')

                if not student_email:
                    errors.append(f"Fila {line_num}: 'email' es un campo requerido.")
                    continue

                try:
                    user, created = User.objects.get_or_create(email=student_email, defaults={
                        'username': student_email,
                        'first_name': first_name,
                        'last_name': last_name
                    })
                    
                    if created:
                        created_count += 1
                    else:
                        user.first_name = first_name
                        user.last_name = last_name
                        user.save()
                        updated_count += 1
                    
                    user.groups.add(student_role_group)

                    if groups_str:
                        group_names = [g.strip() for g in groups_str.split(',') if g.strip()]
                        protected_group_names = ['Estudiantes', 'Profesores']
                        for group_name in group_names:
                            if group_name:
                                if group_name in protected_group_names:
                                    messages.warning(request, f"No se pudo asignar grupo para el estudiante {student_email}.")
                                    continue
                                group, _ = Group.objects.get_or_create(name=group_name)
                                user.groups.add(group)
                                GroupMetadata.objects.get_or_create(group=group, defaults={'created_by': request.user})

                except Exception as e:
                    errors.append(f"Fila {line_num} (email: {student_email}): Error al procesar - {e}")

            if created_count > 0:
                messages.success(request, f'Se crearon {created_count} nuevos estudiantes.')
            if updated_count > 0:
                messages.info(request, f'Se actualizaron {updated_count} estudiantes existentes (datos y/o grupos modificados).')
            if errors:
                for error in errors:
                    messages.error(request, error)
                messages.error(request, 'Hubo errores al procesar algunas filas. Revisa los detalles de arriba.')
            else:
                messages.success(request, 'Todos los estudiantes fueron procesados exitosamente.')

            return redirect('upload_students')
        else:
            messages.error(request, "Por favor, corrige los errores en el formulario de subida.")
    else:
        form = StudentUploadForm()
    
    return render(request, 'groups/upload_students.html', {'form': form})

@login_required
@user_passes_test(is_teacher_or_staff, login_url='/login/')
def assign_test_to_group_view(request):
    if request.user.is_staff:
        groups_queryset_for_form = Group.objects.exclude(name__in=['Estudiantes', 'Profesores']).order_by('name')
    else:
        groups_queryset_for_form = Group.objects.filter(
            testassignment__assigned_by=request.user
        ).distinct().exclude(name__in=['Estudiantes', 'Profesores']).order_by('name')

    groups_data = []
    User = get_user_model()
    student_role_group, _ = Group.objects.get_or_create(name='Estudiantes')

    for group in groups_queryset_for_form:
        students_in_group = User.objects.filter(groups=group).filter(groups=student_role_group).order_by('first_name', 'last_name')
        assigned_tests_for_group = group.assigned_tests.all().order_by('name')

        groups_data.append({
            'group': group,
            'students': students_in_group,
            'assigned_tests': assigned_tests_for_group
        })

    if request.method == 'POST':
        form = AssignTestForm(request.POST, user=request.user, group_queryset_filter=groups_queryset_for_form)
        if form.is_valid():
            selected_tests_from_form = form.cleaned_data['tests']
            target_group = form.cleaned_data['group']
            send_email = form.cleaned_data['send_notification_email']
            email_subject = form.cleaned_data['email_subject']
            email_message = form.cleaned_data['email_message']

            results = assign_tests_and_notify(
                selected_tests_queryset=selected_tests_from_form,
                target_group=target_group,
                assigned_by_user=request.user,
                send_notification_email=send_email,
                email_subject=email_subject,
                email_message=email_message,
                request_obj=request
            )

            if results['newly_assigned_tests']:
                messages.success(request, f"Test(s) '{', '.join(results['newly_assigned_tests'])}' asignados a '{target_group.name}' exitosamente.")
            if results['already_assigned_tests']:
                messages.info(request, f"Test(s) '{', '.join(results['already_assigned_tests'])}' ya estaban asignados a '{target_group.name}'.")

            if results['email_message']:
                if results['email_error']:
                    messages.error(request, results['email_message'])
                else:
                    messages.success(request, results['email_message'])

            return redirect('assign_test_to_group')
        else:
            messages.error(request, "Por favor, corrige los errores en el formulario.")
    else:
        form = AssignTestForm(user=request.user, group_queryset_filter=groups_queryset_for_form)

    context = {
        'form': form,
        'groups_data': groups_data,
    }
    return render(request, 'groups/assign_test_to_group.html', context)

@login_required
@user_passes_test(is_teacher_or_staff)
def export_attempts_xlsx(request):
    group_id_filter = request.GET.get('group')
    test_id_filter = request.GET.get('test')

    excel_file_buffer = generate_attempts_xlsx_report(
        group_id_filter=group_id_filter,
        test_id_filter=test_id_filter
    )

    response = HttpResponse(
        excel_file_buffer.getvalue(), 
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename="resultados_tests.xlsx"'

    return response

@login_required
@user_passes_test(is_teacher_or_staff)
def group_history_results(request, group_id):
    group = get_object_or_404(Group, id=group_id)

    test_summaries = Test.objects.filter(
        attempt__user__groups=group
    ).annotate(
        avg_score=Avg('attempt__score'),
        total_attempts=Count('attempt', distinct=True)
    ).order_by('name')

    students_in_group = User.objects.filter(groups=group).order_by('username')
    student_results = []
    for student in students_in_group:
        attempts_by_student = Attempt.objects.filter(user=student, test__in=test_summaries.values_list('id', flat=True)).order_by('test__name', 'date_taken')
        student_results.append({
            'student': student,
            'attempts': attempts_by_student
        })

    context = {
        'group': group,
        'test_summaries': test_summaries,
        'student_results': student_results,
        'is_teacher_user': is_teacher_or_staff(request.user),
    }
    return render(request, 'tests/group_history_results.html', context)

@login_required
@user_passes_test(is_teacher_or_staff)
def test_statistics_dashboard(request):
    context = {}

    group_id = request.GET.get('group')
    test_id = request.GET.get('test')

    attempts_queryset = Attempt.objects.all()

    if group_id:
        attempts_queryset = attempts_queryset.filter(user__groups__id=group_id)
        context['selected_group'] = get_object_or_404(Group, id=group_id)
    if test_id:
        attempts_queryset = attempts_queryset.filter(test__id=test_id)
        context['selected_test'] = get_object_or_404(Test, id=test_id)

    if not attempts_queryset.exists():
        context['user_attempt_counts'] = []
        context['overall_performance'] = {
            'total_attempts_count': 0,
            'correct': 0,
            'incorrect': 0,
            'answered': 0,
            'unanswered': 0,
            'total_possible': 0,
        }
        context['skill_performance_data_json'] = json.dumps([])
        context['user_attempt_counts_json'] = json.dumps([])
        context['overall_performance_json'] = json.dumps(context['overall_performance'])
        return render(request, 'tests/statistics_dashboard.html', context)

    user_attempts_data = User.objects.filter(
        attempt__in=attempts_queryset
    ).annotate(
        num_attempts=Count('attempt', filter=Q(attempt__in=attempts_queryset))
    ).filter(num_attempts__gt=0).order_by('-num_attempts')

    context['user_attempt_counts'] = [
        {'username': user.get_full_name() or user.username, 'attempts': user.num_attempts}
        for user in user_attempts_data
    ]

    total_correct_global = 0
    total_answered_global = 0
    total_possible_questions_global = 0

    test_ids_in_attempts = attempts_queryset.values_list('test_id', flat=True).distinct()
    questions_per_test = {
        test.id: test.questions.count() for test in Test.objects.filter(id__in=test_ids_in_attempts)
    }

    for attempt in attempts_queryset:
        total_correct_global += attempt.correct_count

        answered_count_for_attempt = Answer.objects.filter(attempt=attempt).count()
        total_answered_global += answered_count_for_attempt

        total_possible_questions_global += questions_per_test.get(attempt.test_id, 0)

    overall_incorrect_global = total_answered_global - total_correct_global
    overall_unanswered_global = total_possible_questions_global - total_answered_global

    context['overall_performance'] = {
        'total_attempts_count': attempts_queryset.count(),
        'correct': total_correct_global,
        'incorrect': overall_incorrect_global,
        'answered': total_answered_global,
        'unanswered': overall_unanswered_global,
        'total_possible': total_possible_questions_global,
    }

    skill_performance_data = []
    relevant_skills_ids = Skill.objects.filter(
        question__tests_assigned__in=attempts_queryset.values_list('test', flat=True)
    ).values_list('id', flat=True).distinct()

    skills = Skill.objects.filter(id__in=relevant_skills_ids).order_by('name')

    for skill in skills:
        questions_in_skill_and_filtered_tests = Question.objects.filter(
            skills=skill,
            tests_assigned__in=attempts_queryset.values_list('test', flat=True)
        ).distinct()

        total_questions_answered_for_skill = 0
        total_correct_for_skill = 0

        answers_for_skill = Answer.objects.filter(
            attempt__in=attempts_queryset,
            question__in=questions_in_skill_and_filtered_tests
        ).select_related('question', 'answer_choice')

        for answer in answers_for_skill:
            total_questions_answered_for_skill += 1

            is_correct_answer = False
            if answer.question.response_format == 'choice' and answer.answer_choice:
                is_correct_answer = answer.answer_choice.is_correct
            elif answer.question.response_format == 'text' and answer.question.correct_answer:
                is_correct_answer = (answer.answer_text is not None) and (answer.answer_text.strip() == answer.question.correct_answer.strip())
            elif answer.question.response_format == 'number' and answer.question.correct_answer:
                try:
                    is_correct_answer = (answer.answer_number is not None) and (float(answer.answer_number) == float(answer.question.correct_answer))
                except (ValueError, TypeError):
                    is_correct_answer = False

            if is_correct_answer:
                total_correct_for_skill += 1

        accuracy = (total_correct_for_skill / total_questions_answered_for_skill * 100) if total_questions_answered_for_skill > 0 else 0

        if total_questions_answered_for_skill > 0:
            skill_performance_data.append({
                'skill_name': skill.name,
                'answered': total_questions_answered_for_skill,
                'correct': total_correct_for_skill,
                'accuracy': accuracy,
                'incorrect': total_questions_answered_for_skill - total_correct_for_skill
            })

    context['skill_performance_data_json'] = json.dumps(skill_performance_data)
    context['user_attempt_counts_json'] = json.dumps(context['user_attempt_counts'])
    context['overall_performance_json'] = json.dumps(context['overall_performance'])

    return render(request, 'tests/statistics_dashboard.html', context)

def simple_logout(request):
    logout(request)
    messages.info(request, "Has cerrado sesión exitosamente.")
    return redirect('simple_login')

def simple_login(request):
    if request.user.is_authenticated:
        return redirect('test_list')

    return render(request, 'tests/login.html')
