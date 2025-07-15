from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.shortcuts import redirect
from django.contrib import messages
from django.contrib.auth.models import User

class NoSignupSocialAccountAdapter(DefaultSocialAccountAdapter):
    def pre_social_login(self, request, sociallogin):

        email = sociallogin.account.extra_data.get('email')
        if not email:
            return None

        try:
            user = User.objects.get(email=email)
            sociallogin.connect(request, user) 
        except User.DoesNotExist:
            messages.error(request, "Este correo no está registrado. Contacta al administrador.")
            return redirect('/tests/login/')
        except Exception as e:
            messages.error(request, "Ocurrió un error inesperado durante el inicio de sesión. Intenta de nuevo o contacta al administrador.")
            return redirect('/tests/login/')

    def is_open_for_signup(self, request, sociallogin):
        return False