from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

from django.db.models.signals import post_save
from django.dispatch import receiver


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    mobile = models.CharField(max_length=10, unique=True, blank=True, null=True)
    image = models.ImageField(upload_to='user_images/', blank=True, null=True)
    
    # ── Gamification Fields ──────────────────────────────────────────
    level = models.PositiveIntegerField(default=1)
    xp = models.PositiveIntegerField(default=0)
    
    # Manual superadmin overrides
    can_verify_activities = models.BooleanField(
        default=False,
        help_text="Manual override: grant this user permanent activity verification access."
    )
    can_approve_social = models.BooleanField(
        default=False,
        help_text="Manual override: grant this user social media post approval rights."
    )
    verification_access_granted_at = models.DateTimeField(
        blank=True, null=True,
        help_text="When dynamic verification access was last earned."
    )
    verification_access_override = models.BooleanField(
        default=False,
        help_text="If True, use manual can_verify_activities instead of dynamic calculation."
    )
    
    # ── Level Title ──────────────────────────────────────────────────
    @property
    def level_title(self):
        from accounts.gamification import get_level_title
        return get_level_title(self.level)
    
    # ── XP Progress ──────────────────────────────────────────────────
    @property
    def xp_for_next_level(self):
        from accounts.gamification import xp_for_level
        return xp_for_level(self.level)
    
    @property
    def xp_progress_percentage(self):
        """Percentage progress toward next level (0-100)."""
        target = self.xp_for_next_level
        if target <= 0:
            return 100
        return min(100, int((self.xp / target) * 100))
    
    # ── Dynamic Verification Access ──────────────────────────────────
    @property
    def has_verification_access(self):
        """
        Determines if this user can verify other users' activities.
        Uses dynamic calculation based on level + rolling activity window,
        unless a superadmin has set a manual override.
        """
        from accounts.gamification import check_verification_access
        return check_verification_access(self)
    
    @property
    def verification_window_info(self):
        """Returns human-readable info about this user's verification window."""
        level = self.level
        if level >= 15:
            return {"required": 15, "window": "1 year", "window_days": 365}
        elif level >= 10:
            return {"required": 10, "window": "6 months", "window_days": 180}
        elif level >= 5:
            return {"required": 5, "window": "3 months", "window_days": 90}
        else:
            return {"required": 5, "window": "30 days", "window_days": 30}
    
    def __str__(self):
        return f"{self.user.username} (Lv.{self.level} {self.level_title})"


class UserActivityLog(models.Model):
    """Tracks every significant action a user takes for audit and gamification."""
    ACTION_CHOICES = [
        ('activity_submitted', 'Activity Submitted'),
        ('activity_verified', 'Activity Verified'),
        ('activity_approved_by', "Approved Another's Activity"),
        ('social_submitted', 'Social Post Submitted'),
        ('social_approved', 'Social Post Approved'),
        ('level_up', 'Level Up'),
        ('xp_earned', 'XP Earned'),
        ('access_granted', 'Verification Access Granted'),
        ('access_revoked', 'Verification Access Revoked'),
        ('manual_override', 'Manual Admin Override'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='activity_logs')
    action = models.CharField(max_length=30, choices=ACTION_CHOICES)
    description = models.TextField(blank=True)
    xp_change = models.IntegerField(default=0)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "User Activity Log"
        verbose_name_plural = "User Activity Logs"
    
    def __str__(self):
        return f"{self.user.username}: {self.get_action_display()} ({self.created_at.strftime('%Y-%m-%d %H:%M')})"

    @property
    def action_icon(self):
        """Returns an emoji icon for the action type (used in templates)."""
        icons = {
            'activity_submitted': '📝',
            'activity_verified': '✅',
            'activity_approved_by': '🔍',
            'social_submitted': '📱',
            'social_approved': '👍',
            'level_up': '🎉',
            'xp_earned': '⭐',
            'access_granted': '🔓',
            'access_revoked': '🔒',
            'manual_override': '⚙️',
        }
        return icons.get(self.action, '📋')


class SMSLog(models.Model):
    mobile_number = models.CharField(max_length=15)
    ip_address = models.GenericIPAddressField()
    sent_at = models.DateTimeField(auto_now_add=True)
    is_success = models.BooleanField(default=True)
    response_data = models.TextField(blank=True, null=True)

    def __str__(self):
        status = "Success" if self.is_success else "Failed"
        return f"{self.mobile_number} - {status} at {self.sent_at}"


# ── Signals ──────────────────────────────────────────────────────────
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.get_or_create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    if hasattr(instance, 'profile'):
        instance.profile.save()
    else:
        UserProfile.objects.get_or_create(user=instance)
