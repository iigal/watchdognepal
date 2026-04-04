from django.contrib import admin
from django.utils.html import format_html
from .models import SocialPost


@admin.register(SocialPost)
class SocialPostAdmin(admin.ModelAdmin):
    list_display = (
        'title', 'post_type_badge', 'status_badge', 'template_choice',
        'created_by', 'approved_by', 'published_platforms', 'created_at'
    )
    list_filter = ('status', 'post_type', 'template_choice', 'created_at')
    search_fields = ('title', 'caption', 'created_by__username')
    readonly_fields = (
        'branded_image_preview', 'published_at',
        'instagram_post_id', 'facebook_post_id', 'twitter_post_id',
        'publish_errors', 'created_at', 'updated_at'
    )
    actions = ['approve_posts', 'reject_posts', 'publish_now']
    
    fieldsets = (
        ('Content', {
            'fields': ('post_type', 'title', 'caption', 'description', 'keywords',
                       'template_choice', 'aspect_ratio')
        }),
        ('Media', {
            'fields': ('original_image', 'branded_image', 'branded_image_preview',
                       'video_file', 'voiceover_file')
        }),
        ('Workflow', {
            'fields': ('status', 'created_by', 'approved_by', 'approved_at',
                       'rejection_reason')
        }),
        ('Publishing', {
            'fields': ('published_at', 'instagram_post_id', 'facebook_post_id',
                       'twitter_post_id', 'publish_errors'),
            'classes': ('collapse',),
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )
    
    def post_type_badge(self, obj):
        colors = {'image': '#3b82f6', 'reel': '#a855f7'}
        icons = {'image': '🖼️', 'reel': '🎬'}
        return format_html(
            '<span style="color:{};font-weight:bold">{} {}</span>',
            colors.get(obj.post_type, '#666'),
            icons.get(obj.post_type, ''),
            obj.get_post_type_display()
        )
    post_type_badge.short_description = 'Type'
    
    def status_badge(self, obj):
        colors = {
            'draft': '#94a3b8',
            'pending': '#f59e0b',
            'approved': '#10b981',
            'published': '#3b82f6',
            'rejected': '#ef4444',
        }
        return format_html(
            '<span style="color:{};font-weight:bold">{}</span>',
            colors.get(obj.status, '#666'),
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    
    def published_platforms(self, obj):
        targets = obj.publish_targets
        if not targets:
            return format_html('<span style="color:#94a3b8">—</span>')
        return ', '.join(targets)
    published_platforms.short_description = 'Published To'
    
    def branded_image_preview(self, obj):
        if obj.branded_image:
            return format_html(
                '<img src="{}" style="max-width:400px;max-height:400px;border-radius:8px" />',
                obj.branded_image.url
            )
        return "No branded image generated yet."
    branded_image_preview.short_description = 'Branded Preview'
    
    @admin.action(description='✅ Approve selected posts')
    def approve_posts(self, request, queryset):
        from accounts.gamification import award_xp, XP_SOCIAL_APPROVED
        count = 0
        for post in queryset.filter(status__in=['pending', 'draft']):
            post.approve(request.user)
            award_xp(post.created_by, XP_SOCIAL_APPROVED, f"Social post approved: {post.title}")
            count += 1
        self.message_user(request, f"{count} post(s) approved.")
    
    @admin.action(description='❌ Reject selected posts')
    def reject_posts(self, request, queryset):
        count = queryset.filter(status__in=['pending', 'draft']).update(status='rejected')
        self.message_user(request, f"{count} post(s) rejected.")
    
    @admin.action(description='🚀 Publish approved posts now')
    def publish_now(self, request, queryset):
        from .publishers import publish_post
        count = 0
        errors = []
        for post in queryset.filter(status='approved'):
            success, error = publish_post(post)
            if success:
                count += 1
            else:
                errors.append(f"{post.title}: {error}")
        
        msg = f"{count} post(s) published."
        if errors:
            msg += f" {len(errors)} failed: " + "; ".join(errors[:3])
        self.message_user(request, msg)
