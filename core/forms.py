from django import forms
from django.core.exceptions import ValidationError
from .models import Activity

class ActivityForm(forms.ModelForm):
    class Meta:
        model = Activity
        fields = ['title', 'description', 'level', 'province', 'manifesto_point', 'source_link']

    def clean_source_link(self):
        source_link = self.cleaned_data.get('source_link')
        if source_link and not ('.gov' in source_link.lower()):
            raise ValidationError('The source link must be a verified government source (e.g., .gov or .gov.np).')
        return source_link
