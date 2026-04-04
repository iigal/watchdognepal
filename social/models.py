from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class SocialPost(models.Model):
    """
    Represents a social media post (Image or Reel) created by a user.
    Follows workflow: Draft → Pending → Approved → Published (or Rejected).
    """
    POST_TYPE_CHOICES = [
        ('image', 'Image Post'),
        ('reel', 'Reel / Video'),
    ]
    
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('published', 'Published'),
        ('rejected', 'Rejected'),
    ]
    
    TEMPLATE_CHOICES = [
        ('keyword_highlight', 'Template A: Keyword Highlight'),
        ('red_box_title', 'Template B: Red Box Title'),
    ]
    
    ASPECT_RATIO_CHOICES = [
        ('1:1', 'Square (1:1) — 1080×1080'),
        ('4:5', 'Portrait (4:5) — 1080×1350'),
    ]
    
    # ── Content ──────────────────────────────────────────────────────
    post_type = models.CharField(max_length=10, choices=POST_TYPE_CHOICES, default='image')
    title = models.CharField(max_length=300)
    caption = models.TextField(blank=True, help_text="Caption text for the social media post.")
    description = models.TextField(blank=True, help_text="Short description for Template B.")
    keywords = models.TextField(
        blank=True,
        help_text="Comma-separated important words for Template A yellow highlighting."
    )
    template_choice = models.CharField(
        max_length=20, choices=TEMPLATE_CHOICES, default='keyword_highlight'
    )
    aspect_ratio = models.CharField(
        max_length=5, choices=ASPECT_RATIO_CHOICES, default='1:1'
    )
    
    # ── Media Files ──────────────────────────────────────────────────
    original_image = models.ImageField(
        upload_to='social/originals/', blank=True, null=True,
        help_text="Original uploaded image (before branding)."
    )
    branded_image = models.ImageField(
        upload_to='social/branded/', blank=True, null=True,
        help_text="Pillow-generated branded image with logo, text, and date."
    )
    video_file = models.FileField(
        upload_to='social/videos/', blank=True, null=True,
        help_text="Final reel video (merged via ffmpeg.wasm in browser)."
    )
    voiceover_file = models.FileField(
        upload_to='social/voiceovers/', blank=True, null=True,
        help_text="Generated TTS voiceover audio file."
    )
    
    # ── Workflow ─────────────────────────────────────────────────────
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='draft')
    created_by = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='social_posts'
    )
    approved_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='approved_social_posts'
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)
    
    # ── Publishing Results ───────────────────────────────────────────
    published_at = models.DateTimeField(null=True, blank=True)
    instagram_post_id = models.CharField(max_length=100, blank=True)
    facebook_post_id = models.CharField(max_length=100, blank=True)
    twitter_post_id = models.CharField(max_length=100, blank=True)
    publish_errors = models.TextField(blank=True)
    
    # ── Timestamps ───────────────────────────────────────────────────
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Social Post"
        verbose_name_plural = "Social Posts"
    
    def __str__(self):
        return f"[{self.get_post_type_display()}] {self.title} ({self.get_status_display()})"
    
    @property
    def is_image(self):
        return self.post_type == 'image'
    
    @property
    def is_reel(self):
        return self.post_type == 'reel'
    
    @property
    def is_publishable(self):
        """Check if post has the required media for publishing."""
        if self.is_image:
            return bool(self.branded_image)
        return bool(self.video_file)
    
    @property
    def publish_targets(self):
        """Returns list of platforms where this was published."""
        targets = []
        if self.instagram_post_id:
            targets.append('Instagram')
        if self.facebook_post_id:
            targets.append('Facebook')
        if self.twitter_post_id:
            targets.append('Twitter')
        return targets
    
    def approve(self, approver):
        """Mark post as approved."""
        self.status = 'approved'
        self.approved_by = approver
        self.approved_at = timezone.now()
        self.save()
    
    def reject(self, reason=""):
        """Mark post as rejected."""
        self.status = 'rejected'
        self.rejection_reason = reason
        self.save()
    
    def mark_published(self):
        """Mark post as successfully published."""
        self.status = 'published'
        self.published_at = timezone.now()
        self.save()
