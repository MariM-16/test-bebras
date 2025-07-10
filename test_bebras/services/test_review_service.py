import json
from django.db import transaction
from django.shortcuts import get_object_or_404
from decimal import Decimal, InvalidOperation
from django.utils import timezone

from ..models import Test, Attempt, Answer, Choice

class TestReviewService:
    def __init__(self, test_id, attempt_id, request_user=None, post_data=None):
        self.test = get_object_or_404(Test, id=test_id)
        self.attempt = get_object_or_404(Attempt, id=attempt_id)
        self.answers = Answer.objects.filter(attempt=self.attempt).select_related('question', 'answer_choice')
        self.total_questions = self.test.questions.count()

        self.points_per_difficulty = {k: Decimal(str(v)) for k, v in (self.test.points_per_difficulty or {}).items()}
        self.penalty_type = self.test.penalty_type
        self.fixed_penalty = Decimal(str(self.test.fixed_penalty or 0))
        self.penalty_by_difficulty = {k: Decimal(str(v)) for k, v in (self.test.penalty_by_difficulty or {}).items()}

        self.total_correct = 0
        self.total_raw_score = Decimal(0)
        self.question_results = []
        self.final_percentage_score = Decimal(0)

        self.request_user = request_user
        self.post_data = post_data

    def _calculate_answer_score_and_status(self, answer):
        is_correct = False
        question_score_value = Decimal(0)
        correct_answer_display = "No disponible"
        difficulty = answer.question.difficulty

        question_status = ""

        if answer.question.response_format == 'choice':
            correct_choice = answer.question.choices.filter(is_correct=True).first()
            if correct_choice:
                correct_answer_display = correct_choice.text
            is_correct = answer.answer_choice and answer.answer_choice.is_correct
            answer.grade_status = 'correct' if is_correct else 'incorrect'
            answer.manual_grade = None
            answer.is_correct_manual = None
        elif answer.question.response_format == 'text' or answer.question.response_format == 'number':
            if answer.question.response_format == 'text':
                if answer.question.correct_answer:
                    correct_answer_display = answer.question.correct_answer
                if answer.answer_text is not None and answer.question.correct_answer:
                    is_correct = answer.answer_text.strip().lower() == answer.question.correct_answer.strip().lower()
                else:
                    is_correct = False
            elif answer.question.response_format == 'number':
                if answer.question.correct_answer:
                    correct_answer_display = answer.question.correct_answer
                if answer.answer_number is not None and correct_answer_display is not None:
                    try:
                        user_num = Decimal(str(answer.answer_number))
                        correct_num = Decimal(str(correct_answer_display))
                        is_correct = user_num == correct_num
                    except (ValueError, InvalidOperation):
                        is_correct = False
                else:
                    is_correct = False

            if answer.grade_status == 'graded':
                is_correct = answer.is_correct_manual
                question_score_value = answer.manual_grade if answer.manual_grade is not None else Decimal('0.0')
                question_status = "graded"
            else:
                user_attempted_to_answer = False
                if answer.question.response_format == 'text' and answer.answer_text is not None and answer.answer_text != "":
                    user_attempted_to_answer = True
                elif answer.question.response_format == 'number' and answer.answer_number is not None:
                    user_attempted_to_answer = True

                if user_attempted_to_answer:
                    question_status = "pending"
                else:
                    question_status = "incorrect"

        if question_status == "correct" or (question_status == "graded" and is_correct):
            question_score_value = self.points_per_difficulty.get(str(difficulty), Decimal(0))
        elif question_status == "incorrect" or (question_status == "graded" and not is_correct):
            if self.penalty_type == 'fixed':
                question_score_value = -self.fixed_penalty
            elif self.penalty_type == 'by_difficulty':
                question_score_value = -self.penalty_by_difficulty.get(str(difficulty), Decimal(0))
            else:
                question_score_value = Decimal(0)
        elif question_status == "pending":
            question_score_value = Decimal(0)

        user_answer_display = 'Sin respuesta'
        if answer.question.response_format == 'choice':
            if answer.answer_choice:
                user_answer_display = answer.answer_choice.text
        elif answer.question.response_format == 'text':
            if answer.answer_text is not None and answer.answer_text != "":
                user_answer_display = answer.answer_text
        elif answer.question.response_format == 'number':
            if answer.answer_number is not None:
                user_answer_display = str(answer.answer_number)

        return {
            'answer_obj': answer,
            'question': answer.question,
            'user_answer': user_answer_display,
            'correct_answer': correct_answer_display,
            'is_correct_auto': is_correct,
            'question_score': question_score_value,
            'status': question_status,
            'is_editable': question_status == '  pending',
            'current_is_correct_manual': answer.is_correct_manual if answer.is_correct_manual is not None else False,
            'current_manual_grade': answer.manual_grade if answer.manual_grade is not None else Decimal('0.0')
        }

    def calculate_review_results(self):
        self.total_correct = 0
        self.total_raw_score = Decimal(0)
        self.question_results = []

        for answer in self.answers:
            result = self._calculate_answer_score_and_status(answer)
            self.question_results.append(result)

            if result['status'] == 'correct' or \
               (result['status'] == 'graded' and result['is_correct_auto']):
                self.total_correct += 1
            elif result['status'] == '  pending':
                pass
            elif result['status'] == 'incorrect' or \
                 (result['status'] == 'graded' and not result['is_correct_auto']):
                pass

            self.total_raw_score += result['question_score']

        max_possible_test_score = Decimal(0)
        for q in self.test.questions.all():
            max_possible_test_score += self.points_per_difficulty.get(str(q.difficulty), Decimal(0))

        if max_possible_test_score > Decimal(0):
            self.final_percentage_score = (self.total_raw_score / max_possible_test_score) * Decimal(100)
            self.final_percentage_score = max(Decimal(0), min(Decimal(100), self.final_percentage_score))
        else:
            self.final_percentage_score = Decimal(0)

        return {
            'test': self.test,
            'total_correct': self.total_correct,
            'total_questions': self.total_questions,
            'total_score': self.final_percentage_score,
            'raw_score': self.total_raw_score,
            'question_results': self.question_results,
            'attempt_id': self.attempt.id
        }

    @transaction.atomic
    def process_manual_corrections(self):
        updated_answers = []
        for answer in self.answers:
            if answer.grade_status == '  pending' and \
               answer.question.response_format in ['text', 'number']:
                
                checkbox_name = f'is_correct_manual_{answer.id}'
                is_correct_manual_checked = checkbox_name in self.post_data

                if is_correct_manual_checked != (answer.is_correct_manual if answer.is_correct_manual is not None else False):
                    answer.is_correct_manual = is_correct_manual_checked
                    answer.grade_status = 'graded'
                    answer.graded_by = self.request_user
                    answer.graded_at = timezone.now()

                    if answer.is_correct_manual:
                        test_points_config = self.test.points_per_difficulty
                        if test_points_config and str(answer.question.difficulty) in test_points_config:
                            answer.manual_grade = Decimal(str(test_points_config[str(answer.question.difficulty)]))
                        else:
                            answer.manual_grade = Decimal('0.0')
                    else:
                        calculated_penalty = Decimal('0.0')
                        test_penalty_type = self.test.penalty_type
                        if test_penalty_type == 'fixed':
                            calculated_penalty = self.test.fixed_penalty if self.test.fixed_penalty is not None else Decimal('0.0')
                        elif test_penalty_type == 'by_difficulty':
                            penalty_config = self.test.penalty_by_difficulty
                            if penalty_config and str(answer.question.difficulty) in penalty_config:
                                calculated_penalty = Decimal(str(penalty_config[str(answer.question.difficulty)]))
                            else:
                                calculated_penalty = Decimal('0.0')
                        answer.manual_grade = -calculated_penalty
                    
                    updated_answers.append(answer)
        
        if updated_answers:
            Answer.objects.bulk_update(updated_answers, ['is_correct_manual', 'grade_status', 'graded_by', 'graded_at', 'manual_grade'])

        recalculated_results = self.calculate_review_results()
        
        self.attempt.score = recalculated_results['total_score']
        self.attempt.correct_count = recalculated_results['total_correct']
        self.attempt.save()

        return True

