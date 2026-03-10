from django.contrib import admin
from django import forms
from .models import Activity, Vote, PoliticalParty, ElectedMember, ManifestoPoint
from .widgets import NepaliDatePickerWidget

@admin.register(PoliticalParty)
class PoliticalPartyAdmin(admin.ModelAdmin):
    list_display = ('name', 'in_government')
    list_filter = ('in_government',)
    search_fields = ('name',)

@admin.register(ElectedMember)
class ElectedMemberAdmin(admin.ModelAdmin):
    list_display = ('name', 'constituency', 'party')
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
    list_display = ('title', 'party', 'elected_member', 'deadline')
    list_filter = ('party', 'elected_member', 'deadline')
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

# Register your models here.
