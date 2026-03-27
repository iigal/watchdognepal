from django import forms
from django.core.exceptions import ValidationError
from .models import Activity, Petition

class ActivityForm(forms.ModelForm):
    class Meta:
        model = Activity
        fields = ['title', 'description', 'level', 'province', 'manifesto_point', 'source_link']




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
