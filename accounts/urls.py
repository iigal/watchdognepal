from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.register_view, name='register'),
    path('verify-otp/', views.verify_otp_view, name='verify_otp'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile_view, name='user_profile'),
    path('my-logs/', views.user_logs_view, name='user_logs'),
    path('admin-logs/', views.admin_logs_view, name='admin_user_logs'),
]
