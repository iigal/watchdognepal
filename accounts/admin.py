from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from .models import UserProfile, UserActivityLog, SMSLog


class UserActivityLogInline(admin.TabularInline):
    model = UserActivityLog
    extra = 0
    readonly_fields = ('action', 'description', 'xp_change', 'metadata', 'created_at')
    ordering = ('-created_at',)
    
    def has_add_permission(self, request, obj=None):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Profile & Gamification'
    fieldsets = (
        ('Profile', {
            'fields': ('mobile', 'image')
        }),
        ('Gamification', {
            'fields': ('level', 'xp', 'display_level_info'),
            'description': 'User level and experience points. Level ups happen automatically via XP.',
        }),
        ('Verification Access (Manual Overrides)', {
            'fields': (
                'verification_access_override',
                'can_verify_activities',
                'can_approve_social',
                'verification_access_granted_at',
            ),
            'classes': ('collapse',),
            'description': (
                'Enable "Override" to manually control access. '
                'Otherwise access is calculated dynamically based on level and activity.'
            ),
        }),
    )
    readonly_fields = ('display_level_info',)
    
    def display_level_info(self, obj):
        if not obj or not obj.pk:
            return "-"
        access_status = "✅ Yes" if obj.has_verification_access else "❌ No"
        window = obj.verification_window_info
        return format_html(
            '<div style="line-height:1.8">'
            '<strong>Level:</strong> {} — {}<br>'
            '<strong>XP:</strong> {} / {} ({}%)<br>'
            '<strong>Dynamic Verification Access:</strong> {}<br>'
            '<strong>Window:</strong> {} activities in {}'
            '</div>',
            obj.level, obj.level_title,
            obj.xp, obj.xp_for_next_level, obj.xp_progress_percentage,
            access_status,
            window['required'], window['window']
        )
    display_level_info.short_description = 'Level Status'


# Unregister default User admin and re-register with our inline
admin.site.unregister(User)

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    inlines = (UserProfileInline,)
    list_display = (
        'username', 'email', 'first_name', 'last_name',
        'display_level', 'display_access', 'is_active', 'is_staff',
    )
    list_filter = BaseUserAdmin.list_filter + ('profile__level',)
    
    def display_level(self, obj):
        try:
            profile = obj.profile
            return format_html(
                '<span style="font-weight:bold">Lv.{}</span> {}',
                profile.level, profile.level_title
            )
        except UserProfile.DoesNotExist:
            return "-"
    display_level.short_description = 'Level'
    display_level.admin_order_field = 'profile__level'
    
    def display_access(self, obj):
        try:
            profile = obj.profile
            if profile.has_verification_access:
                return format_html('<span style="color:#10b981;font-weight:bold">✅ Verifier</span>')
            return format_html('<span style="color:#94a3b8">—</span>')
        except UserProfile.DoesNotExist:
            return "-"
    display_access.short_description = 'Access'
    
    actions = ['grant_verification_access', 'revoke_verification_access', 'set_level_5', 'set_level_10']
    
    @admin.action(description='🔓 Grant verification access (manual override)')
    def grant_verification_access(self, request, queryset):
        from .models import UserActivityLog
        count = 0
        for user in queryset:
            profile, _ = UserProfile.objects.get_or_create(user=user)
            profile.verification_access_override = True
            profile.can_verify_activities = True
            profile.save()
            UserActivityLog.objects.create(
                user=user,
                action='access_granted',
                description=f'Manual access granted by {request.user.username}',
                metadata={'granted_by': request.user.id}
            )
            count += 1
        self.message_user(request, f"Verification access granted to {count} user(s).")
    
    @admin.action(description='🔒 Revoke verification access')
    def revoke_verification_access(self, request, queryset):
        from .models import UserActivityLog
        count = 0
        for user in queryset:
            profile, _ = UserProfile.objects.get_or_create(user=user)
            profile.verification_access_override = True
            profile.can_verify_activities = False
            profile.save()
            UserActivityLog.objects.create(
                user=user,
                action='access_revoked',
                description=f'Access revoked by {request.user.username}',
                metadata={'revoked_by': request.user.id}
            )
            count += 1
        self.message_user(request, f"Verification access revoked for {count} user(s).")
    
    @admin.action(description='⬆️ Set selected users to Level 5 (Contributor)')
    def set_level_5(self, request, queryset):
        self._set_level(request, queryset, 5)
    
    @admin.action(description='⬆️ Set selected users to Level 10 (Watchdog)')
    def set_level_10(self, request, queryset):
        self._set_level(request, queryset, 10)
    
    def _set_level(self, request, queryset, level):
        from .models import UserActivityLog
        from .gamification import get_level_title
        count = 0
        for user in queryset:
            profile, _ = UserProfile.objects.get_or_create(user=user)
            old_level = profile.level
            profile.level = level
            profile.xp = 0
            profile.save()
            UserActivityLog.objects.create(
                user=user,
                action='manual_override',
                description=f'Level set to {level} ({get_level_title(level)}) by {request.user.username} (was Lv.{old_level})',
                metadata={'old_level': old_level, 'new_level': level, 'set_by': request.user.id}
            )
            count += 1
        self.message_user(request, f"Set {count} user(s) to Level {level} ({get_level_title(level)}).")


@admin.register(UserActivityLog)
class UserActivityLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'action_display', 'description_short', 'xp_change_display', 'created_at')
    list_filter = ('action', 'created_at')
    search_fields = ('user__username', 'description')
    readonly_fields = ('user', 'action', 'description', 'xp_change', 'metadata', 'created_at')
    date_hierarchy = 'created_at'
    
    def has_add_permission(self, request):
        return False
    
    def action_display(self, obj):
        return format_html('{} {}', obj.action_icon, obj.get_action_display())
    action_display.short_description = 'Action'
    
    def description_short(self, obj):
        if len(obj.description) > 80:
            return obj.description[:80] + '…'
        return obj.description
    description_short.short_description = 'Details'
    
    def xp_change_display(self, obj):
        if obj.xp_change > 0:
            return format_html('<span style="color:#10b981;font-weight:bold">+{}</span>', obj.xp_change)
        elif obj.xp_change < 0:
            return format_html('<span style="color:#f43f5e;font-weight:bold">{}</span>', obj.xp_change)
        return '—'
    xp_change_display.short_description = 'XP'


@admin.register(SMSLog)
class SMSLogAdmin(admin.ModelAdmin):
    list_display = ('mobile_number', 'ip_address', 'is_success', 'sent_at')
    list_filter = ('is_success', 'sent_at')
    search_fields = ('mobile_number', 'ip_address')
