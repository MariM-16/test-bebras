from django.urls import path
from . import views


urlpatterns = [
    path('', views.test_list, name='test_list'),
    path('login/', views.simple_login, name='simple_login'),
    path('logout/', views.simple_logout, name='simple_logout'),
    path('<int:test_id>/', views.test_detail, name='test_detail'),
    path('<int:test_id>/teacher-view/', views.test_detail_teacher, name='test_detail_teacher'),
    path('review/<int:test_id>/<int:attempt_id>/', views.test_review, name='test_review'),
    path('test_attempts/', views.test_attempts, name='test_attempts'),
    path('create/auto/', views.auto_test_creation_view, name='auto_test_create'),
    path('students/upload/', views.upload_students_view, name='upload_students'),
    path('assign-test/', views.assign_test_to_group_view, name='assign_test_to_group'),
    path('groups/', views.group_list_view, name='group_list'), 
    path('groups/<int:group_id>/', views.group_detail_view, name='group_detail'),    
    path('export/attempts/xlsx/', views.export_attempts_xlsx, name='export_attempts_xlsx'),
    path('group/<int:group_id>/history/', views.group_history_results, name='group_history_results'),
    path('statistics/', views.test_statistics_dashboard, name='test_statistics_dashboard'),
]