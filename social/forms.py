from django import forms
from .models import SocialPost


class ImagePostForm(forms.ModelForm):
    """Form for creating an image-type social post."""
    class Meta:
        model = SocialPost
        fields = [
            'title', 'caption', 'description', 'keywords',
            'template_choice', 'aspect_ratio', 'original_image'
        ]
        widgets = {
            'title': forms.TextInput(attrs={
                'placeholder': 'Enter post title',
                'class': 'w-full'
            }),
            'caption': forms.Textarea(attrs={
                'placeholder': 'Write your caption here or use AI to generate one...',
                'rows': 4,
            }),
            'description': forms.Textarea(attrs={
                'placeholder': 'Short description for Template B (Red Box)',
                'rows': 2,
            }),
            'keywords': forms.TextInput(attrs={
                'placeholder': 'e.g., corruption, accountability, development',
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['description'].required = False
        self.fields['keywords'].required = False
        self.fields['caption'].required = False


class ReelPostForm(forms.ModelForm):
    """Form for creating a reel/video-type social post."""
    voiceover_text = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'placeholder': 'Enter text to convert to speech for the voiceover...',
            'rows': 3,
        }),
        help_text="This text will be converted to audio using Google TTS."
    )
    
    class Meta:
        model = SocialPost
        fields = ['title', 'caption', 'video_file']
        widgets = {
            'title': forms.TextInput(attrs={
                'placeholder': 'Enter reel title',
            }),
            'caption': forms.Textarea(attrs={
                'placeholder': 'Write your caption here...',
                'rows': 4,
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['caption'].required = False
        self.fields['video_file'].required = False  # Will be uploaded via JS after ffmpeg processing
