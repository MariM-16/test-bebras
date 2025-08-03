from django import forms
from .models import Test, Question, Skill, Group, GroupMetadata
from django.contrib.auth.models import User
from django.forms.widgets import CheckboxSelectMultiple, Textarea
import csv
import io
import json

class AutoTestCreationForm(forms.Form):
    name = forms.CharField(label='Nombre del Test', max_length=100)
    number_of_questions = forms.IntegerField(label='Número de preguntas', min_value=1)
    skills = forms.ModelMultipleChoiceField(
        queryset=Skill.objects.all(),
        required=False,
        label='Habilidades a evaluar (opcional)',
        widget=forms.CheckboxSelectMultiple
    )
    min_difficulty = forms.IntegerField(label='Dificultad mínima', min_value=1, max_value=7, initial=1)
    
    maximum_time_hours = forms.IntegerField(label='Tiempo máximo (horas)', min_value=0, initial=0)
    maximum_time_minutes = forms.IntegerField(label='Tiempo máximo (minutos)', min_value=0, max_value=59, initial=30)
    allow_backtracking = forms.BooleanField(label='Permitir retroceder en preguntas', required=False, initial=True)
    allow_no_response = forms.BooleanField(label='Permitir no responder preguntas', required=False, initial=True)
    max_attempts = forms.IntegerField(
        label='Número máximo de intentos por estudiante',
        min_value=1,
        initial=1,
        help_text='Establece el número máximo de veces que un estudiante puede intentar este test. Por defecto es 1.'
    )

    points_per_difficulty = forms.CharField(
        label='Puntos por dificultad (JSON, ej: {"1": 10, "2": 20}). Opcional si solo hay una dificultad.',
        required=False,
        widget=forms.Textarea(attrs={'rows': 3, 'placeholder': '{"1": 10, "2": 20, "3": 30}'})
    )

    penalty_type = forms.ChoiceField(
        label='Tipo de penalización por respuesta incorrecta/sin respuesta (si no permitido)',
        choices=[('none', 'Ninguna'), ('fixed', 'Fija'), ('by_difficulty', 'Por Dificultad')],
        initial='none',
        widget=forms.RadioSelect
    )
    fixed_penalty = forms.DecimalField(label='Penalización fija (puntos)', max_digits=5, decimal_places=2, required=False, initial=0.0)
    
    penalty_by_difficulty = forms.CharField(
        label='Penalización por dificultad (JSON, ej: {"1": 1, "2": 2})',
        required=False,
        widget=forms.Textarea(attrs={'rows': 3, 'placeholder': '{"1": 1, "2": 2, "3": 3, "4": 4, "5": 5, "6": 6, "7": 7}'})
    )

    def clean_penalty_by_difficulty(self):
        data = self.cleaned_data['penalty_by_difficulty']
        if data:
            try:
                json_data = json.loads(data)
                for k, v in json_data.items():
                    if not k.isdigit() or not (1 <= int(k) <= 7):
                        raise forms.ValidationError("Las claves de penalización por dificultad deben ser números del 1 al 7.")
                    if not isinstance(v, (int, float)):
                        raise forms.ValidationError("Los valores de penalización por dificultad deben ser numéricos.")
                return json_data
            except json.JSONDecodeError:
                raise forms.ValidationError("Formato JSON inválido para la penalización por dificultad.")
        return None

    def clean_points_per_difficulty(self):
        data = self.cleaned_data['points_per_difficulty']
        if data:
            try:
                json_data = json.loads(data)
                for k, v in json_data.items():
                    if not k.isdigit() or not (1 <= int(k) <= 7):
                        raise forms.ValidationError("Las claves de puntos por dificultad deben ser números del 1 al 7.")
                    if not isinstance(v, (int, float)):
                        raise forms.ValidationError("Los valores de puntos por dificultad deben ser numéricos.")
                return json_data
            except json.JSONDecodeError:
                raise forms.ValidationError("Formato JSON inválido para puntos por dificultad.")
        return None

    def clean(self):
        cleaned_data = super().clean()
        penalty_type = cleaned_data.get('penalty_type')
        fixed_penalty = cleaned_data.get('fixed_penalty')
        penalty_by_difficulty = cleaned_data.get('penalty_by_difficulty')
        points_per_difficulty = cleaned_data.get('points_per_difficulty')

        if penalty_type == 'fixed' and fixed_penalty is None:
            self.add_error('fixed_penalty', 'Este campo es requerido cuando el tipo de penalización es Fija.')
        
        if penalty_type == 'by_difficulty' and not penalty_by_difficulty:
            self.add_error('penalty_by_difficulty', 'Este campo es requerido cuando el tipo de penalización es Por Dificultad.')
        
        if not points_per_difficulty:
            pass

        return cleaned_data

class StudentUploadForm(forms.Form):
    csv_file = forms.FileField(label='')

class AssignTestForm(forms.Form):
    group = forms.ModelChoiceField(
        queryset=Group.objects.none(),
        label='Selecciona un Grupo',
        empty_label="-- Selecciona un grupo --",
        widget=forms.Select(attrs={'class': 'form-select'}),
        required=False
    )
    tests = forms.ModelMultipleChoiceField(
        queryset=Test.objects.none(),
        widget=CheckboxSelectMultiple,
        label='Selecciona Test(s) para asignar',
    )
    send_notification_email = forms.BooleanField(
        label='Enviar email de notificación.',
        required=False,
        initial=True,
    )
    email_subject = forms.CharField(
        label='Asunto del Email:',
        max_length=255,
        required=True,
        initial='Nuevos Tests Asignados en Bebras',
    )
    email_message = forms.CharField(
        label='Mensaje del Email (opcional):',
        widget=Textarea(attrs={'rows': 4}),
        required=False
    )

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        test_queryset_filter = kwargs.pop('test_queryset', None)
        group_queryset_filter = kwargs.pop('group_queryset_filter', None)
        super().__init__(*args, **kwargs)

        if test_queryset_filter is not None:
            self.fields['tests'].queryset = test_queryset_filter
        else:
            if user and not user.is_staff:
                self.fields['tests'].queryset = Test.objects.filter(creator=user).order_by('name')
            else:
                self.fields['tests'].queryset = Test.objects.all().order_by('name')

        if group_queryset_filter is not None:
            self.fields['group'].required = True
            self.fields['group'].queryset = group_queryset_filter
        else:
            if 'group' in self.fields:
                del self.fields['group']

        if not self.data:
            self.fields['email_subject'].required = False
            self.fields['email_message'].required = False
        elif 'send_notification_email' in self.data and self.data.get('send_notification_email') == 'on':
            self.fields['email_subject'].required = True
        else:
            self.fields['email_subject'].required = False
            self.fields['email_message'].required = False

        self.fields['email_subject'].widget.attrs['placeholder'] = "Ej: Nuevos Tests de Comprensión Lógica"
        self.fields['email_message'].widget.attrs['placeholder'] = "Ej: Hola estudiantes, les he asignado nuevos tests. ¡Mucha suerte!"

    def clean(self):
        cleaned_data = super().clean()
        send_email = cleaned_data.get('send_notification_email')
        email_subject = cleaned_data.get('email_subject')

        if send_email and not email_subject:
            self.add_error('email_subject', 'Este campo es obligatorio si deseas enviar un email de notificación.')
        return cleaned_data
