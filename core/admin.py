from django.contrib import admin
from .models import Activity, Vote

@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):
    list_display = ('title', 'level', 'status', 'created_by', 'created_at', 'positive_votes', 'negative_votes')
    list_filter = ('level', 'status', 'created_at')
    search_fields = ('title', 'description', 'province')
    actions = ['mark_as_verified']

    @admin.action(description='Mark selected activities as verified')
    def mark_as_verified(self, request, queryset):
        updated = queryset.update(status='verified')
        self.message_user(request, f"{updated} activities marked as verified.")


@admin.register(Vote)
class VoteAdmin(admin.ModelAdmin):
    list_display = ('user', 'activity', 'vote_type', 'created_at')

# Register your models here.
