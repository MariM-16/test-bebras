from django.urls import path
from . import views


urlpatterns = [
    path('', views.test_list, name='test_list'),
    path('login/', views.simple_login, name='simple_login'),
    path('logout/', views.simple_logout, name='simple_logout'),
    path('<int:test_id>/', views.test_detail, name='test_detail'),
    path('review/<int:test_id>/<int:attempt_id>/', views.test_review, name='test_review'),
    path('test_attempts/', views.test_attempts, name='test_attempts'),
    path('questions/<int:test_id>/', views.question_detail, name='question_detail'),
]