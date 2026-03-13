from django.contrib import admin
from django import forms
from .models import Activity, Vote, PoliticalParty, ElectedMember, ManifestoPoint, Petition, PetitionSignature
from .widgets import NepaliDatePickerWidget

@admin.register(PoliticalParty)
class PoliticalPartyAdmin(admin.ModelAdmin):
    list_display = ('name', 'in_government', 'oath_date')
    list_filter = ('in_government',)
    search_fields = ('name',)

@admin.register(ElectedMember)
class ElectedMemberAdmin(admin.ModelAdmin):
    list_display = ('name', 'constituency', 'party', 'oath_date')
    list_filter = ('party',)
    search_fields = ('name', 'constituency')


class ManifestoPointAdminForm(forms.ModelForm):
    class Meta:
        model = ManifestoPoint
        fields = '__all__'
        widgets = {
            'deadline': NepaliDatePickerWidget(),
        }


@admin.register(ManifestoPoint)
class ManifestoPointAdmin(admin.ModelAdmin):
    form = ManifestoPointAdminForm
    list_display = ('title', 'party', 'elected_member', 'calculated_deadline', 'completion_years', 'completion_months', 'completion_days', 'deadline')
    list_filter = ('party', 'elected_member')
    search_fields = ('title', 'description')

@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):
    list_display = ('title', 'level', 'status', 'manifesto_point', 'created_by', 'created_at', 'positive_votes', 'negative_votes')
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


class PetitionSignatureInline(admin.TabularInline):
    model = PetitionSignature
    extra = 0
    readonly_fields = ('user', 'comment', 'signed_at')


@admin.register(Petition)
class PetitionAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'target', 'goal', 'signature_count', 'status', 'created_by', 'created_at')
    list_filter = ('status', 'category', 'created_at')
    search_fields = ('title', 'description', 'target')
    inlines = [PetitionSignatureInline]


@admin.register(PetitionSignature)
class PetitionSignatureAdmin(admin.ModelAdmin):
    list_display = ('user', 'petition', 'signed_at')
    list_filter = ('signed_at',)
    search_fields = ('user__username', 'petition__title')

from .models import VisitorLog, IPLocationCache
import json

@admin.register(IPLocationCache)
class IPLocationCacheAdmin(admin.ModelAdmin):
    list_display = ('ip_address', 'city', 'country', 'latitude', 'longitude', 'fetched_at')
    search_fields = ('ip_address', 'city', 'country')

@admin.register(VisitorLog)
class VisitorLogAdmin(admin.ModelAdmin):
    list_display = ('ip_address', 'user', 'path', 'method', 'device_type', 'os_name', 'browser', 'timestamp')
    list_filter = ('timestamp', 'method', 'device_type', 'os_name', 'browser')
    search_fields = ('ip_address', 'path', 'user__username', 'browser', 'os_name')
    
    change_list_template = "admin/core/visitorlog/change_list.html"

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        
        # Get all cached locations that have valid lat/lon
        locations = IPLocationCache.objects.filter(
            latitude__isnull=False, 
            longitude__isnull=False
        ).values('latitude', 'longitude', 'city')
        
        heat_data = [
            [float(loc['latitude']), float(loc['longitude']), 1.0] # [lat, lng, intensity]
            for loc in locations
        ]
        
        extra_context['heat_data_json'] = json.dumps(heat_data)
        
        return super().changelist_view(request, extra_context=extra_context)
