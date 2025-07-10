from django.shortcuts import get_object_or_404
from django.utils.timezone import now
from django.db import transaction

from ..models import Test, Attempt, Answer, Choice

class TestAttemptService:
    def __init__(self, user, test, session, request_post_data=None):
        self.user = user
        self.test = test
        self.session = session
        self.request_post_data = request_post_data
        self.attempt = self._get_or_create_attempt()
        self.questions = list(self.test.questions.order_by('id'))
        self.total_questions = len(self.questions)
        self.current_question_index = self.session.get('current_question_index', 0)

    def _get_or_create_attempt(self):
        attempt_id = self.session.get('attempt_id')
        current_test_id = self.session.get('current_test_id')

        if not attempt_id or current_test_id != self.test.id:
            attempt = Attempt.objects.create(user=self.user, test=self.test)
            self.session['attempt_id'] = attempt.id
            self.session['current_test_id'] = self.test.id
            self.session['current_question_index'] = 0
            return attempt
        else:
            attempt = get_object_or_404(Attempt, id=attempt_id)
            if attempt.user != self.user or attempt.test != self.test:
                attempt = Attempt.objects.create(user=self.user, test=self.test)
                self.session['attempt_id'] = attempt.id
                self.session['current_test_id'] = self.test.id
                self.session['current_question_index'] = 0
            return attempt

    def get_current_state(self):
        self.current_question_index = max(0, self.current_question_index)
        self.current_question_index = min(self.current_question_index, self.total_questions)

        if self.current_question_index >= self.total_questions:
            return {'status': 'finished', 'attempt_id': self.attempt.id}

        current_question = self.questions[self.current_question_index]
        existing_answer = Answer.objects.filter(attempt=self.attempt, question=current_question).first()

        user_answer_data = None
        if existing_answer:
            if current_question.response_format == 'text':
                user_answer_data = existing_answer.answer_text
            elif current_question.response_format == 'number':
                user_answer_data = existing_answer.answer_number
            elif current_question.response_format == 'choice':
                user_answer_data = existing_answer.answer_choice.id if existing_answer.answer_choice else None

        return {
            'status': 'in_progress',
            'attempt': self.attempt,
            'current_question': current_question,
            'question_number': self.current_question_index + 1,
            'answered': existing_answer is not None,
            'total_questions': self.total_questions,
            'user_answer_data': user_answer_data,
            'allow_backtracking': self.test.allow_backtracking,
            'error': None
        }

    def process_post_request(self):
        if not self.request_post_data:
            return {'status': 'error', 'message': 'No hay datos POST para procesar.'}

        if self.request_post_data.get('force_finish') == 'true':
            return self._handle_force_finish()
        elif 'next_question' in self.request_post_data:
            return self._handle_next_question()
        elif 'previous_question' in self.request_post_data and self.test.allow_backtracking:
            return self._handle_previous_question()
        return {'status': 'no_action'}


    def _handle_force_finish(self):
        with transaction.atomic():
            answered_questions = Answer.objects.filter(attempt=self.attempt).values_list('question_id', flat=True)
            unanswered_questions = [q for q in self.questions if q.id not in answered_questions]

            for question in unanswered_questions:
                data = {
                    "attempt": self.attempt,
                    "question": question,
                    "user": self.user,
                }

                if question.response_format == 'text':
                    data["answer_text"] = ""
                elif question.response_format == 'number':
                    data["answer_number"] = None
                elif question.response_format == 'choice':
                    data["answer_choice"] = None
                Answer.objects.create(**data)

            self.session['current_question_index'] = len(self.questions)
            self.attempt.end_time = now()
            self.attempt.save()
        return {'status': 'redirect', 'view_name': 'test_review', 'kwargs': {'test_id': self.test.id, 'attempt_id': self.attempt.id}}

    def _handle_next_question(self):
        current_question = self.questions[self.current_question_index]
        Answer.objects.filter(attempt=self.attempt, question=current_question).delete()

        user_provided_answer = False
        answer_data = {
            "attempt": self.attempt,
            "question": current_question,
            "user": self.user,
        }

        if current_question.response_format == 'text':
            answer_text = self.request_post_data.get(f'question_{current_question.id}', '').strip()
            answer_data["answer_text"] = answer_text
            if answer_text:
                user_provided_answer = True

        elif current_question.response_format == 'number':
            answer_number_str = self.request_post_data.get(f'question_{current_question.id}', '')
            answer_data["answer_number"] = None
            if answer_number_str:
                try:
                    answer_data["answer_number"] = int(answer_number_str)
                    user_provided_answer = True
                except ValueError:
                    pass

        elif current_question.response_format == 'choice':
            answer_choice_id = self.request_post_data.get(f'question_{current_question.id}')
            answer_data["answer_choice"] = None
            if answer_choice_id:
                try:
                    answer_data["answer_choice"] = Choice.objects.get(id=answer_choice_id)
                    user_provided_answer = True
                except Choice.DoesNotExist:
                    pass

        if not self.test.allow_no_response and not user_provided_answer:
            return {'status': 'validation_error', 'message': "Debes responder antes de continuar."}

        with transaction.atomic():
            Answer.objects.create(**answer_data)
        self.session['current_question_index'] += 1
        return {'status': 'redirect', 'view_name': 'test_detail', 'kwargs': {'test_id': self.test.id}}

    def _handle_previous_question(self):
        if self.current_question_index > 0:
            self.session['current_question_index'] -= 1
            return {'status': 'redirect', 'view_name': 'test_detail', 'kwargs': {'test_id': self.test.id}}
        return {'status': 'no_action'}
