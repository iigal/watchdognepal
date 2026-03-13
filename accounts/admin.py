from django.contrib import admin
from .models import SMSLog, UserProfile
from .utils import get_sms_credits

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'mobile')
    search_fields = ('user__username', 'mobile')

@admin.register(SMSLog)
class SMSLogAdmin(admin.ModelAdmin):
    list_display = ('mobile_number', 'ip_address', 'is_success', 'sent_at')
    list_filter = ('is_success', 'sent_at')
    search_fields = ('mobile_number', 'ip_address')
    readonly_fields = ('mobile_number', 'ip_address', 'sent_at', 'is_success', 'response_data')
    
    # We want a custom template to display the credit balance at the top
    change_list_template = "admin/accounts/smslog/change_list.html"

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        # Add our custom credit data to the template context
        extra_context['sms_credits'] = get_sms_credits()
        return super().changelist_view(request, extra_context=extra_context)
