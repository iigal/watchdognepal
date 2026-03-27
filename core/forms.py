from django import forms
from django.core.exceptions import ValidationError
from .models import Activity, Petition, PoliticalParty, ElectedMember, ManifestoPoint

class ActivityForm(forms.ModelForm):
    party = forms.ModelChoiceField(
        queryset=PoliticalParty.objects.all(), 
        required=True, 
        empty_label='Select Party'
    )
    member = forms.ModelChoiceField(
        queryset=ElectedMember.objects.all(), 
        required=False, 
        empty_label='Select Member (Optional)'
    )

    class Meta:
        model = Activity
        fields = ['title', 'description', 'party', 'member', 'manifesto_point', 'source_link']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self.fields['manifesto_point'].queryset = ManifestoPoint.objects.none()
        
        if 'party' in self.data:
            try:
                party_id = int(self.data.get('party'))
                member_id = self.data.get('member')
                if member_id:
                    self.fields['manifesto_point'].queryset = ManifestoPoint.objects.filter(elected_member_id=member_id)
                else:
                    self.fields['manifesto_point'].queryset = ManifestoPoint.objects.filter(party_id=party_id, elected_member__isnull=True)
            except (ValueError, TypeError):
                pass
        elif self.instance.pk and self.instance.manifesto_point:
            if self.instance.manifesto_point.elected_member:
                self.fields['manifesto_point'].queryset = ManifestoPoint.objects.filter(elected_member=self.instance.manifesto_point.elected_member)
                self.fields['party'].initial = self.instance.manifesto_point.party
                self.fields['member'].initial = self.instance.manifesto_point.elected_member
            else:
                self.fields['manifesto_point'].queryset = ManifestoPoint.objects.filter(party=self.instance.manifesto_point.party, elected_member__isnull=True)
                self.fields['party'].initial = self.instance.manifesto_point.party




class PetitionForm(forms.ModelForm):
    class Meta:
        model = Petition
        fields = ['title', 'description', 'target', 'category', 'goal', 'image']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['title'].widget.attrs.update({'placeholder': 'Enter petition title'})
        self.fields['description'].widget.attrs.update({
            'placeholder': 'Describe what this petition is about and why it matters...',
            'rows': 5,
        })
        self.fields['target'].widget.attrs.update({'placeholder': 'e.g., Ministry of Education'})
        self.fields['goal'].widget.attrs.update({'placeholder': 'e.g., 1000'})
