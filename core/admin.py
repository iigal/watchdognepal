from django.contrib import admin
from django import forms
from .models import Activity, Vote, PoliticalParty, ElectedMember, ManifestoPoint, SubManifesto, Commitment, SubCommitment, Petition, PetitionSignature
from .widgets import NepaliDatePickerWidget

@admin.register(PoliticalParty)
class PoliticalPartyAdmin(admin.ModelAdmin):
    list_display = ('name', 'in_government', 'oath_date')
    list_filter = ('in_government',)
    search_fields = ('name',)

@admin.register(ElectedMember)
class ElectedMemberAdmin(admin.ModelAdmin):
    list_display = ('name', 'constituency', 'party', 'oath_date', 'phone_number', 'office_email')
    list_filter = ('party',)
    search_fields = ('name', 'constituency', 'phone_number', 'office_email')
    fieldsets = (
        (None, {
            'fields': ('name', 'constituency', 'party', 'image', 'oath_date')
        }),
        ('Contact Information', {
            'fields': ('phone_number', 'alternate_phone_number', 'secretary_phone_number', 'personal_email', 'office_email')
        }),
    )


class ManifestoPointAdminForm(forms.ModelForm):
    class Meta:
        model = ManifestoPoint
        fields = '__all__'
        widgets = {
            'deadline': NepaliDatePickerWidget(),
        }


class SubManifestoInline(admin.TabularInline):
    model = SubManifesto
    extra = 1
    fields = ('title', 'deadline', 'is_completed')
    widgets = {
        'deadline': NepaliDatePickerWidget(),
    }


@admin.register(ManifestoPoint)
class ManifestoPointAdmin(admin.ModelAdmin):
    form = ManifestoPointAdminForm
    list_display = ('title', 'party', 'elected_member', 'calculated_deadline', 'is_completed', 'progress_fraction')
    list_filter = ('party', 'elected_member', 'is_completed')
    search_fields = ('title', 'description')
    inlines = [SubManifestoInline]


class CommitmentAdminForm(forms.ModelForm):
    class Meta:
        model = Commitment
        fields = '__all__'
        widgets = {
            'deadline': NepaliDatePickerWidget(),
        }


class SubCommitmentInline(admin.TabularInline):
    model = SubCommitment
    extra = 1
    fields = ('title', 'deadline', 'is_completed')
    widgets = {
        'deadline': NepaliDatePickerWidget(),
    }


@admin.register(Commitment)
class CommitmentAdmin(admin.ModelAdmin):
    form = CommitmentAdminForm
    list_display = ('title', 'party', 'elected_member', 'calculated_deadline', 'is_completed', 'progress_fraction')
    list_filter = ('party', 'elected_member', 'is_completed')
    search_fields = ('title', 'description')
    inlines = [SubCommitmentInline]

@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):
    list_display = ('title', 'level', 'status', 'manifesto_point', 'commitment', 'created_by', 'created_at', 'positive_votes', 'negative_votes')
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

from .models import VisitorLog, IPLocationCache, BannedIP

@admin.register(BannedIP)
class BannedIPAdmin(admin.ModelAdmin):
    list_display = ('ip_address', 'reason', 'timestamp')
    search_fields = ('ip_address', 'reason')
import json

@admin.register(IPLocationCache)
class IPLocationCacheAdmin(admin.ModelAdmin):
    list_display = ('ip_address', 'city', 'country', 'latitude', 'longitude', 'fetched_at')
    search_fields = ('ip_address', 'city', 'country')

class VisitorTypeFilter(admin.SimpleListFilter):
    title = 'Visitor Type'
    parameter_name = 'visitor_type'

    def lookups(self, request, model_admin):
        return (
            ('registered', 'Registered'),
            ('bot', 'Bot'),
            ('guest', 'Guest'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'registered':
            return queryset.filter(user__isnull=False)
        if self.value() == 'bot':
            return queryset.filter(device_type='Bot', user__isnull=True)
        if self.value() == 'guest':
            return queryset.filter(user__isnull=True).exclude(device_type='Bot')
        return queryset

@admin.register(VisitorLog)
class VisitorLogAdmin(admin.ModelAdmin):
    list_display = ('ip_address', 'formatted_visitor_type', 'formatted_status_code', 'user', 'path', 'method', 'device_type', 'os_name', 'browser', 'timestamp')
    list_filter = (VisitorTypeFilter, 'status_code', 'timestamp', 'method', 'device_type', 'os_name', 'browser')
    search_fields = ('ip_address', 'path', 'user__username', 'browser', 'os_name')
    actions = ['sweep_delete']

    @admin.action(description='Sweep Delete: Delete ALL logs from selected IPs')
    def sweep_delete(self, request, queryset):
        ips = list(queryset.values_list('ip_address', flat=True).distinct())
        if not ips:
            return
        
        # Count total records that will be deleted across all selected IPs
        total_to_delete = VisitorLog.objects.filter(ip_address__in=ips).count()
        
        # Perform the sweep delete
        VisitorLog.objects.filter(ip_address__in=ips).delete()
        
        # Also clean up the location cache for these IPs as they no longer have any logs
        IPLocationCache.objects.filter(ip_address__in=ips).delete()
        
        self.message_user(request, f"Successfully swept {total_to_delete} logs for {len(ips)} IP addresses.")
    
    change_list_template = "admin/core/visitorlog/change_list.html"

    def formatted_status_code(self, obj):
        if not obj.status_code:
            return "-"
        color = "#28a745" if 200 <= obj.status_code < 300 else "#dc3545"
        from django.utils.html import format_html
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.status_code
        )
    formatted_status_code.short_description = 'Status'

    def formatted_visitor_type(self, obj):
        v_type = obj.visitor_type
        colors = {
            'Registered': '#28a745', # Success green
            'Bot': '#dc3545',        # Danger red
            'Guest': '#6c757d'       # Muted grey
        }
        from django.utils.html import format_html
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            colors.get(v_type, '#000'),
            v_type
        )
    formatted_visitor_type.short_description = 'Visitor Type'

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        
        # Summary counts
        all_logs = VisitorLog.objects.all()
        extra_context['total_registered'] = all_logs.filter(user__isnull=False).count()
        extra_context['total_bots'] = all_logs.filter(device_type='Bot', user__isnull=True).count()
        extra_context['total_guests'] = all_logs.filter(user__isnull=True).exclude(device_type='Bot').count()
        
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

    def delete_model(self, request, obj):
        ip = obj.ip_address
        super().delete_model(request, obj)
        # If no more logs for this IP, delete the cache
        if not VisitorLog.objects.filter(ip_address=ip).exists():
            IPLocationCache.objects.filter(ip_address=ip).delete()

    def delete_queryset(self, request, queryset):
        # Get distinct IPs from the queryset before deleting
        ips = list(queryset.values_list('ip_address', flat=True).distinct())
        super().delete_queryset(request, queryset)
        
        # For each affected IP, if no logs remain, delete from cache
        for ip in ips:
            if not VisitorLog.objects.filter(ip_address=ip).exists():
                IPLocationCache.objects.filter(ip_address=ip).delete()
