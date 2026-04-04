import json
import os
from io import BytesIO

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.core.paginator import Paginator
from django.core.files.base import ContentFile

from .models import SocialPost
from .forms import ImagePostForm, ReelPostForm


@login_required
def dashboard(request):
    """Social media creation dashboard."""
    user_posts = SocialPost.objects.filter(created_by=request.user)
    pending_count = SocialPost.objects.filter(status='pending').count()
    
    context = {
        'user_posts': user_posts[:10],
        'draft_count': user_posts.filter(status='draft').count(),
        'pending_count': pending_count,
        'published_count': user_posts.filter(status='published').count(),
        'can_approve': request.user.is_superuser or (
            hasattr(request.user, 'profile') and request.user.profile.can_approve_social
        ),
    }
    return render(request, 'social/dashboard.html', context)


@login_required
def create_image_post(request):
    """Create an image-type social post."""
    if request.method == 'POST':
        form = ImagePostForm(request.POST, request.FILES)
        if form.is_valid():
            post = form.save(commit=False)
            post.post_type = 'image'
            post.created_by = request.user
            post.status = 'pending'
            post.save()
            
            # Generate branded image
            from .image_generator import generate_branded_image
            generate_branded_image(post)
            
            # Award XP
            from accounts.gamification import award_xp, XP_SOCIAL_SUBMITTED
            award_xp(request.user, XP_SOCIAL_SUBMITTED, f"Social image post submitted: {post.title}")
            
            messages.success(request, 'Image post created and submitted for review!')
            return redirect('social:post_detail', pk=post.pk)
    else:
        form = ImagePostForm()
    
    return render(request, 'social/create_image.html', {'form': form})


@login_required
def create_reel(request):
    """Create a reel/video-type social post."""
    if request.method == 'POST':
        form = ReelPostForm(request.POST, request.FILES)
        if form.is_valid():
            post = form.save(commit=False)
            post.post_type = 'reel'
            post.created_by = request.user
            post.status = 'pending'
            post.save()
            
            # Award XP
            from accounts.gamification import award_xp, XP_SOCIAL_SUBMITTED
            award_xp(request.user, XP_SOCIAL_SUBMITTED, f"Social reel submitted: {post.title}")
            
            messages.success(request, 'Reel created and submitted for review!')
            return redirect('social:post_detail', pk=post.pk)
    else:
        form = ReelPostForm()
    
    return render(request, 'social/create_reel.html', {'form': form})


@login_required
def post_list(request):
    """List of social posts with filtering."""
    if request.user.is_superuser or (hasattr(request.user, 'profile') and request.user.profile.can_approve_social):
        posts = SocialPost.objects.all()
    else:
        posts = SocialPost.objects.filter(created_by=request.user)
    
    status_filter = request.GET.get('status', '')
    if status_filter:
        posts = posts.filter(status=status_filter)
    
    paginator = Paginator(posts, 20)
    page_obj = paginator.get_page(request.GET.get('page'))
    
    context = {
        'page_obj': page_obj,
        'status_filter': status_filter,
        'status_choices': SocialPost.STATUS_CHOICES,
    }
    return render(request, 'social/post_list.html', context)


@login_required
def post_detail(request, pk):
    """View a single social post."""
    post = get_object_or_404(SocialPost, pk=pk)
    
    # Only author, superadmin, or approvers can see
    if post.created_by != request.user and not request.user.is_superuser:
        if not (hasattr(request.user, 'profile') and request.user.profile.can_approve_social):
            messages.error(request, 'You do not have permission to view this post.')
            return redirect('social:dashboard')
    
    can_approve = (
        request.user.is_superuser or
        (hasattr(request.user, 'profile') and request.user.profile.can_approve_social)
    ) and post.status == 'pending'
    
    context = {
        'post': post,
        'can_approve': can_approve,
    }
    return render(request, 'social/post_detail.html', context)


@login_required
@require_POST
def approve_post(request, pk):
    """Approve a pending social post."""
    if not request.user.is_superuser and not (hasattr(request.user, 'profile') and request.user.profile.can_approve_social):
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    post = get_object_or_404(SocialPost, pk=pk, status='pending')
    post.approve(request.user)
    
    # Award XP to author
    from accounts.gamification import award_xp, XP_SOCIAL_APPROVED
    award_xp(post.created_by, XP_SOCIAL_APPROVED, f"Social post approved: {post.title}")
    
    # Optionally publish immediately
    if request.POST.get('publish_now'):
        from .publishers import publish_post
        success, error = publish_post(post)
        if success:
            messages.success(request, f'Post approved and published!')
        else:
            messages.warning(request, f'Post approved but publishing had errors: {error}')
    else:
        messages.success(request, 'Post approved! It will be published by the next cron run.')
    
    return redirect('social:post_detail', pk=pk)


@login_required
@require_POST
def reject_post(request, pk):
    """Reject a pending social post."""
    if not request.user.is_superuser and not (hasattr(request.user, 'profile') and request.user.profile.can_approve_social):
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    post = get_object_or_404(SocialPost, pk=pk, status='pending')
    reason = request.POST.get('reason', '')
    post.reject(reason)
    
    messages.info(request, 'Post rejected.')
    return redirect('social:post_detail', pk=pk)


# ── AJAX Endpoints ───────────────────────────────────────────────────

@login_required
@require_POST
def generate_caption(request):
    """
    AJAX endpoint: Generate a caption using Google Gemini Flash 2.5.
    Expects JSON body with 'title' and optional 'description'.
    """
    try:
        data = json.loads(request.body)
        title = data.get('title', '')
        description = data.get('description', '')
        
        if not title:
            return JsonResponse({'error': 'Title is required'}, status=400)
        
        api_key = os.environ.get('GEMINI_API_KEY', '')
        if not api_key:
            return JsonResponse({'error': 'Gemini API key not configured'}, status=500)
        
        from google import genai
        
        client = genai.Client(api_key=api_key)
        
        prompt = f"""Generate a compelling social media caption for a post by Watchdog Nepal, 
a government accountability platform from Nepal.

Title: {title}
Description: {description if description else 'N/A'}

Requirements:
- Write in English (include Nepali translation if relevant)
- Be professional but engaging
- Include 3-5 relevant hashtags
- Keep it under 200 words
- Focus on government accountability and transparency themes
- Make it suitable for Instagram, Facebook, and Twitter"""
        
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
        )
        
        caption = response.text
        return JsonResponse({'caption': caption})
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_POST
def generate_branded_image(request):
    """
    AJAX endpoint: Generate a branded image for a post.
    Expects form data with post_id.
    """
    try:
        post_id = request.POST.get('post_id')
        post = get_object_or_404(SocialPost, pk=post_id, created_by=request.user)
        
        if not post.original_image:
            return JsonResponse({'error': 'No original image uploaded'}, status=400)
        
        from .image_generator import generate_branded_image as gen_image
        success = gen_image(post)
        
        if success:
            return JsonResponse({
                'success': True,
                'branded_url': post.branded_image.url,
            })
        else:
            return JsonResponse({'error': 'Image generation failed'}, status=500)
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_POST
def generate_voiceover(request):
    """
    AJAX endpoint: Generate a TTS voiceover using gTTS.
    Expects JSON body with 'text' and optional 'lang'.
    Returns the audio file.
    """
    try:
        data = json.loads(request.body)
        text = data.get('text', '')
        lang = data.get('lang', 'ne')  # Default Nepali
        
        if not text:
            return JsonResponse({'error': 'Text is required'}, status=400)
        
        from gtts import gTTS
        
        tts = gTTS(text=text, lang=lang, slow=False)
        buffer = BytesIO()
        tts.write_to_fp(buffer)
        buffer.seek(0)
        
        response = HttpResponse(buffer.read(), content_type='audio/mpeg')
        response['Content-Disposition'] = 'attachment; filename="voiceover.mp3"'
        return response
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
