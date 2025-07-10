from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.shortcuts import redirect
from django.contrib import messages
from django.contrib.auth.models import User

class NoSignupSocialAccountAdapter(DefaultSocialAccountAdapter):
    def pre_social_login(self, request, sociallogin):

        email = sociallogin.account.extra_data.get('email')
        if not email:
            return

        try:
            user = User.objects.get(email=email)
            sociallogin.connect(request, user) 
        except User.DoesNotExist:
            messages.error(request, "Este correo no está registrado. Contacta al administrador.")
            raise Exception("No autorizado") 
