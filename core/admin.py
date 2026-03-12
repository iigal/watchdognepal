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
