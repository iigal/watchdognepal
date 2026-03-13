from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from django.core.validators import RegexValidator

class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)
    mobile = forms.CharField(
        required=True,
        max_length=10,
        min_length=10,
        validators=[
            RegexValidator(
                regex=r'^9\d{9}$',
                message="Mobile number must be a 10-digit number starting with 9.",
                code='invalid_mobile'
            )
        ],
        help_text="Enter your 10-digit mobile number starting with 9."
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'mobile', 'password1', 'password2']
