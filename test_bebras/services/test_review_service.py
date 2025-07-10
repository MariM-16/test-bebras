import json
from django.db import transaction
from django.shortcuts import get_object_or_404

from ..models import Test, Attempt, Answer, Choice

class TestReviewService:
    def __init__(self, test_id, attempt_id):
        self.test = get_object_or_404(Test, id=test_id)
        self.attempt = get_object_or_404(Attempt, id=attempt_id)
        self.answers = Answer.objects.filter(attempt=self.attempt).select_related('question', 'answer_choice')
        self.total_questions = self.test.questions.count()

        self.points_per_difficulty = self.test.points_per_difficulty or {}
        self.penalty_type = self.test.penalty_type
        self.fixed_penalty = self.test.fixed_penalty or 0
        self.penalty_by_difficulty = self.test.penalty_by_difficulty or {}

        self.total_correct = 0
        self.total_raw_score = 0
        self.question_results = []
        self.final_percentage_score = 0

    def calculate_review_results(self):
        for answer in self.answers:
            is_correct = False
            question_score = 0
            correct_answer_display = "No disponible"
            difficulty = answer.question.difficulty

            if answer.question.response_format == 'choice':
                correct_choice = answer.question.choices.filter(is_correct=True).first()
                if correct_choice:
                    correct_answer_display = correct_choice.text
                is_correct = answer.answer_choice and answer.answer_choice.is_correct

            elif answer.question.response_format == 'text':
                if answer.question.correct_answer:
                    correct_answer_display = answer.question.correct_answer
                if not answer.answer_text:
                    is_correct = False
                else:
                    is_correct = answer.answer_text.strip() == answer.question.correct_answer.strip() if answer.question.correct_answer else False

            elif answer.question.response_format == 'number':
                if answer.question.correct_answer:
                    correct_answer_display = answer.question.correct_answer
                if answer.answer_number is not None and correct_answer_display is not None:
                    try:
                        is_correct = float(answer.answer_number) == float(correct_answer_display)
                    except ValueError:
                        is_correct = False
                else:
                    is_correct = False

            if is_correct:
                self.total_correct += 1
                question_score = self.points_per_difficulty.get(str(difficulty), 0)
            else:
                user_attempted_to_answer = False
                if answer.question.response_format == 'text' and answer.answer_text is not None and answer.answer_text != "":
                    user_attempted_to_answer = True
                elif answer.question.response_format == 'number' and answer.answer_number is not None:
                    user_attempted_to_answer = True
                elif answer.question.response_format == 'choice' and answer.answer_choice is not None:
                    user_attempted_to_answer = True

                if user_attempted_to_answer or (not self.test.allow_no_response and not user_attempted_to_answer):
                    if self.penalty_type == 'fixed':
                        question_score = -self.fixed_penalty
                    elif self.penalty_type == 'by_difficulty':
                        question_score = -self.penalty_by_difficulty.get(str(difficulty), 0)
                    else:
                        question_score = 0
                else:
                    question_score = 0

            self.total_raw_score += question_score

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

            self.question_results.append({
                'question': answer.question,
                'user_answer': user_answer_display,
                'correct_answer': correct_answer_display,
                'is_correct': is_correct,
                'question_score': question_score,
            })

        max_possible_test_score = 0
        for q in self.test.questions.all():
            max_possible_test_score += self.points_per_difficulty.get(str(q.difficulty), 0)

        if max_possible_test_score > 0:
            self.final_percentage_score = (self.total_raw_score / max_possible_test_score) * 100
            self.final_percentage_score = max(0, min(100, self.final_percentage_score))
        else:
            self.final_percentage_score = 0

        with transaction.atomic():
            self.attempt.score = self.final_percentage_score
            self.attempt.correct_count = self.total_correct
            self.attempt.save()

        return {
            'test': self.test,
            'total_correct': self.total_correct,
            'total_questions': self.total_questions,
            'total_score': self.final_percentage_score,
            'question_results': self.question_results,
            'attempt_id': self.attempt.id
        }