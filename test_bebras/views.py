from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from .models import Test, Answer, Choice, Attempt
from django.utils.timezone import now
from collections import defaultdict


@login_required
def test_list(request):
    if is_teacher_or_staff(request.user):
        if request.user.is_staff:
            tests = Test.objects.all().order_by('name')
        else:
            tests = Test.objects.filter(creator=request.user).order_by('name')
    else:
        user_groups_ids = request.user.groups.values_list('id', flat=True)
        tests = Test.objects.filter(assigned_groups__id__in=user_groups_ids).distinct().order_by('name')

    return render(request, 'tests/test_list.html', {'tests': tests})

@login_required
def test_detail(request, test_id):
    test = get_object_or_404(Test, id=test_id)

    if is_teacher_or_staff(request.user):
        if not request.user.is_staff and test.creator != request.user:
            messages.error(request, "No tienes permiso para ver este test.")
            return redirect('test_list')
    elif is_student(request.user):
        user_groups_ids = request.user.groups.values_list('id', flat=True)
        if not Test.objects.filter(id=test_id, assigned_groups__id__in=user_groups_ids).exists():
            messages.error(request, "Este test no está asignado a ninguno de tus grupos.")
            return redirect('test_list')
    else:
            return redirect('test_list')
    else:
        messages.error(request, "No tienes permiso para acceder a los tests.")
        return redirect('simple_login')

    service = TestAttemptService(request.user, test, request.session, request.POST if request.method == 'POST' else None)
        request.session['current_test_id'] = test.id
        request.session['current_question_index'] = 0
    else:
        attempt = get_object_or_404(Attempt, id=request.session['attempt_id'])

    if request.method == 'POST':
        process_results = service.process_post_request()

        if process_results['status'] == 'redirect':
            return redirect(reverse(process_results['view_name'], kwargs=process_results['kwargs']))
        elif process_results['status'] == 'validation_error':
            context = service.get_current_state() 
            context['error'] = process_results['message']
                    attempt=attempt,
                    question=current_question,
                    answer_choice=answer_choice,
                    user=request.user
                )

        if not Answer.objects.filter(attempt=attempt, question=current_question).exists():
            return render(request, 'tests/test_detail.html', {
                'test': test,
                'current_question': current_question,
                'question_number': request.session['current_question_index'] + 1,
                'answered': False,
                'error': "Debes responder antes de continuar."
            })
        
        request.session['current_question_index'] += 1
        return redirect(reverse('test_detail', kwargs={'test_id': test_id}))

    return render(request, 'tests/test_detail.html', {
        'test': test,
        'attempt': attempt,
        'current_question': current_question,
        'question_number': request.session['current_question_index'] + 1,
        'answered': answered,
        'error': None
    })

@login_required
def test_review(request, test_id, attempt_id):
    test = get_object_or_404(Test, id=test_id) 
    attempt = get_object_or_404(Attempt, id=attempt_id) 
    answers = Answer.objects.filter(attempt=attempt)  
    
    total_correct = 0
    total_questions = answers.count()
    total_score = 0
    question_results = []

    for answer in answers:
        is_correct = False
        scoring = getattr(answer.question, 'scoringconfiguration', None)
        question_score = 0
        correct_answer = None

        if answer.question.response_format == 'choice':
            correct_choice = answer.question.choices.filter(is_correct=True).first()
            correct_answer = correct_choice.text if correct_choice else "No disponible"
            if answer.answer_choice and answer.answer_choice.is_correct:
                is_correct = True
        elif answer.question.response_format == 'text':
            correct_answer = answer.question.correct_answer or "No disponible"
            if not answer.answer_text:  
                is_correct = False 
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
def test_attempts(request):
    user = request.user

    if user.groups.filter(name='Student').exists():
        attempts = Attempt.objects.filter(user=user).order_by('-date_taken')
        show_user = False
    else:
        attempts = Attempt.objects.all().order_by('test__name', '-date_taken')
        show_user = True

    grouped_attempts = defaultdict(list)
    
    for attempt in attempts:
        total_correct = attempt.correct_count
        total_questions = attempt.test.questions.count()
        
        if total_questions > 0:
            total_score = (total_correct / total_questions) * 100
        else:
            total_score = 0  
        attempt.score = total_score 

        grouped_attempts[attempt.test].append(attempt)

    return render(request, 'tests/test_attempts.html', {
        'grouped_attempts': dict(grouped_attempts),
        'show_user': show_user,
    })

def simple_login(request):
    if request.user.is_authenticated:
        return redirect('test_list') 

    user, created = User.objects.get_or_create(username='testuser')
    if created:
        user.set_password('testpassword')
        user.save()

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            return redirect('test_list')

    return render(request, 'tests/login.html')

def simple_logout(request):
    logout(request)
    return redirect('simple_login')