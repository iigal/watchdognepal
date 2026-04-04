from django.urls import path
from . import views

app_name = 'social'

urlpatterns = [
    # Dashboard
    path('', views.dashboard, name='dashboard'),
    
    # Image post creation
    path('create/image/', views.create_image_post, name='create_image'),
    
    # Reel creation
    path('create/reel/', views.create_reel, name='create_reel'),
    
    # Post management
    path('posts/', views.post_list, name='post_list'),
    path('posts/<int:pk>/', views.post_detail, name='post_detail'),
    path('posts/<int:pk>/approve/', views.approve_post, name='approve_post'),
    path('posts/<int:pk>/reject/', views.reject_post, name='reject_post'),
    
    # AJAX endpoints
    path('api/generate-caption/', views.generate_caption, name='generate_caption'),
    path('api/generate-branded-image/', views.generate_branded_image, name='generate_branded_image'),
    path('api/generate-voiceover/', views.generate_voiceover, name='generate_voiceover'),
]
