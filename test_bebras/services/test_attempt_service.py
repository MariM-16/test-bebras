from django.shortcuts import get_object_or_404
from django.utils.timezone import now
from django.db import transaction
from django.contrib import messages
from django.urls import reverse
from ..models import Test, Attempt, Answer, Choice, Question


class TestAttemptService:
    def __init__(self, user, test, session, request_post_data=None, attempt=None):
        self.user = user
        self.test = test
        self.session = session
        self.request_post_data = request_post_data
        self.attempt = attempt
        self.questions = list(self.test.questions.order_by('id'))
        self.total_questions = len(self.questions)
        self.current_question_index = self.session.get(f'current_question_index_{self.attempt.id}', 0)

    def get_current_state(self):
        self.current_question_index = max(0, self.current_question_index)
        self.current_question_index = min(self.current_question_index, self.total_questions)

        if self.attempt.end_time is not None:
            return {'status': 'finished', 'attempt': self.attempt, 'attempt_id': self.attempt.id}

        if self.current_question_index >= self.total_questions:
            if self.attempt.end_time is None:
                self.attempt.end_time = now()
                self.attempt.save()
                if f'current_question_index_{self.attempt.id}' in self.session:
                    del self.session[f'current_question_index_{self.attempt.id}']
            return {'status': 'finished', 'attempt': self.attempt, 'attempt_id': self.attempt.id}

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

        if self.attempt.end_time is not None:
            messages.error(self.user, "No puedes realizar acciones en un test ya finalizado.")
            return {'status': 'redirect', 'view_name': 'test_bebras:test_review', 'kwargs': {'test_id': self.test.id, 'attempt_id': self.attempt.id}}

        if self.request_post_data.get('force_finish') == 'true':
            return self._handle_force_finish()
        elif 'next_question' in self.request_post_data:
            return self._handle_next_question()
        elif 'previous_question' in self.request_post_data and self.test.allow_backtracking:
            return self._handle_previous_question()
        return {'status': 'no_action'}


    def _handle_force_finish(self):
        with transaction.atomic():
            answered_questions_ids = Answer.objects.filter(attempt=self.attempt).values_list('question_id', flat=True)
            unanswered_questions = [q for q in self.questions if q.id not in answered_questions_ids]

            for question in unanswered_questions:
                Answer.objects.create(
                    attempt=self.attempt,
                    question=question,
                    user=self.user,
                    answer_text="",
                    answer_number=None,
                    answer_choice=None,
                    grade_status='incorrect'
                )

            if f'current_question_index_{self.attempt.id}' in self.session:
                del self.session[f'current_question_index_{self.attempt.id}']

            self.attempt.end_time = now()
            self.attempt.save()
        return {'status': 'redirect', 'view_name': 'test_bebras:test_review', 'kwargs': {'test_id': self.test.id, 'attempt_id': self.attempt.id}}

    def _handle_next_question(self):
        if self.attempt.end_time is not None:
            return {'status': 'redirect', 'view_name': 'test_bebras:test_review', 'kwargs': {'test_id': self.test.id, 'attempt_id': self.attempt.id}}

        if self.current_question_index >= self.total_questions:
            if self.attempt.end_time is None:
                self.attempt.end_time = now()
                self.attempt.save()
                if f'current_question_index_{self.attempt.id}' in self.session:
                    del self.session[f'current_question_index_{self.attempt.id}']
            return {'status': 'redirect', 'view_name': 'test_bebras:test_review', 'kwargs': {'test_id': self.test.id, 'attempt_id': self.attempt.id}}

        current_question = self.questions[self.current_question_index]
        Answer.objects.filter(attempt=self.attempt, question=current_question).delete()

        user_provided_answer = False
        answer_data = {
            "attempt": self.attempt,
            "question": current_question,
            "user": self.user,
            "grade_status": "not_applicable"
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
                    answer_data['grade_status'] = 'correct' if answer_data["answer_choice"].is_correct else 'incorrect'
                except Choice.DoesNotExist:
                    pass
            elif not self.test.allow_no_response:
                answer_data['grade_status'] = 'incorrect'

        if not self.test.allow_no_response and not user_provided_answer:
            messages.warning(self.user, "Debes responder antes de continuar.")
            return {'status': 'validation_error', 'message': "Debes responder antes de continuar."}

        if not user_provided_answer and current_question.response_format in ['text', 'number']:
            answer_data['grade_status'] = 'incorrect'

        with transaction.atomic():
            Answer.objects.create(**answer_data)

        self.session[f'current_question_index_{self.attempt.id}'] += 1

        if self.session[f'current_question_index_{self.attempt.id}'] >= self.total_questions:
            if self.attempt.end_time is None:
                self.attempt.end_time = now()
                self.attempt.save()
                if f'current_question_index_{self.attempt.id}' in self.session:
                    del self.session[f'current_question_index_{self.attempt.id}']
            return {'status': 'redirect', 'view_name': 'test_bebras:test_review', 'kwargs': {'test_id': self.test.id, 'attempt_id': self.attempt.id}}
        else:
            return {'status': 'redirect', 'view_name': 'test_bebras:test_detail', 'kwargs': {'test_id': self.test.id}}

    def _handle_previous_question(self):
        if self.current_question_index > 0:
            self.session[f'current_question_index_{self.attempt.id}'] -= 1
            return {'status': 'redirect', 'view_name': 'test_bebras:test_detail', 'kwargs': {'test_id': self.test.id}}
        return {'status': 'no_action'}