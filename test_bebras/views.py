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
    tests = Test.objects.all()
    return render(request, 'tests/test_list.html', {'tests': tests})

@login_required
def test_detail(request, test_id):
    test = get_object_or_404(Test, id=test_id)
    questions = list(test.questions.order_by('id'))  # orden explícito
    total_questions = len(questions)

    if 'attempt_id' not in request.session or request.session.get('current_test_id') != test.id:
        attempt = Attempt.objects.create(user=request.user, test=test)
        request.session['attempt_id'] = attempt.id
        request.session['current_test_id'] = test.id
        request.session['current_question_index'] = 0
    else:
        attempt = get_object_or_404(Attempt, id=request.session['attempt_id'])

    if request.session['current_question_index'] >= total_questions:
        return redirect('test_review', test_id=test.id, attempt_id=attempt.id)

    current_question = questions[request.session['current_question_index']]
    answered = Answer.objects.filter(attempt=attempt, question=current_question).exists()

    if request.method == 'POST':

        if request.POST.get('force_finish') == 'true':
            answered_questions = Answer.objects.filter(attempt=attempt).values_list('question_id', flat=True)
            unanswered_questions = [q for q in questions if q.id not in answered_questions]

            for question in unanswered_questions:
                data = {
                    "attempt": attempt,
                    "question": question,
                    "user": request.user,
                }

                if question.response_format == 'text':
                    data["answer_text"] = ""
                elif question.response_format == 'number':
                    data["answer_number"] = None
                elif question.response_format == 'choice':
                    data["answer_choice"] = None

                Answer.objects.create(**data)

            request.session['current_question_index'] = len(questions)
            attempt.end_time = now()
            attempt.save()
            return redirect('test_review', test_id=test.id, attempt_id=attempt.id)

        if current_question.response_format == 'text':
            answer_text = request.POST.get(f'question_{current_question.id}')
            if answer_text:
                Answer.objects.create(
                    attempt=attempt,
                    question=current_question,
                    answer_text=answer_text,
                    user=request.user
                )

        elif current_question.response_format == 'number':
            answer_number = request.POST.get(f'question_{current_question.id}')
            if answer_number:
                Answer.objects.create(
                    attempt=attempt,
                    question=current_question,
                    answer_number=int(answer_number),
                    user=request.user
                )

        elif current_question.response_format == 'choice':
            answer_choice_id = request.POST.get(f'question_{current_question.id}')
            if answer_choice_id:
                answer_choice = Choice.objects.get(id=answer_choice_id)
                Answer.objects.create(
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
            elif answer.question.correct_answer:
                is_correct = answer.answer_text == answer.question.correct_answer
            else:
                is_correct = None
        elif answer.question.response_format == 'number':
            correct_answer = answer.question.correct_answer if answer.question.correct_answer is not None else None
            if answer.answer_number is not None and correct_answer is not None:
                is_correct = float(answer.answer_number) == float(correct_answer)

        if is_correct:
            total_correct += 1
            if scoring:
                question_score = scoring.points_per_difficulty * answer.question.difficulty
        else:
            if scoring and scoring.penalty_for_incorrect:
                question_score = -scoring.fixed_penalty if scoring.fixed_penalty else 0

        total_score += question_score

        if answer.question.response_format == 'choice':
            user_answer = answer.answer_choice.text if answer.answer_choice else 'Sin respuesta'
        elif answer.question.response_format == 'text':
            user_answer = answer.answer_text if answer.answer_text else 'Sin respuesta'
        elif answer.question.response_format == 'number':
            user_answer = answer.answer_number if answer.answer_number is not None else None

        question_results.append({
            'question': answer.question,
            'user_answer': user_answer,
            'correct_answer': correct_answer,
            'is_correct': is_correct,
            'question_score': question_score,
        })
    attempt.score = total_score
    attempt.correct_count = total_correct
    attempt.save()

    return render(request, 'tests/test_review.html', {
        'test': test,
        'total_correct': total_correct,
        'total_questions': total_questions,
        'total_score': total_score,
        'question_results': question_results,
    })

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