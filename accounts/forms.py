import re
from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from accounts.models import UserProfile
from interviews.models import InterviewDomain


class CandidateSignupForm(forms.Form):
    username = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'e.g. sarah_coder',
            'autocomplete': 'username',
            'id': 'id_username',
        })
    )
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-input',
            'placeholder': 'sarah@example.com',
            'autocomplete': 'email',
            'id': 'signup-email',
        })
    )
    target_role = forms.CharField(
        max_length=120,
        required=False,
        initial='Software Engineer',
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'e.g. Senior Backend Engineer',
            'id': 'id_target_role',
        })
    )
    preferred_domain = forms.ChoiceField(
        choices=InterviewDomain.choices,
        initial=InterviewDomain.FULLSTACK,
        widget=forms.Select(attrs={
            'class': 'form-input',
            'id': 'id_preferred_domain',
        })
    )
    password = forms.CharField(
        required=True,
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': 'Min 8 characters, letters & numbers',
            'autocomplete': 'new-password',
            'id': 'signup-password',
        })
    )
    password_confirm = forms.CharField(
        required=True,
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': 'Re-enter your password',
            'autocomplete': 'new-password',
            'id': 'id_password_confirm',
        })
    )
    anxiety_mode_default = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'checkbox-input',
            'id': 'id_anxiety_mode_default',
        })
    )

    def clean_username(self):
        username = self.cleaned_data['username'].strip()
        if not re.match(r'^[a-zA-Z0-9_.-]+$', username):
            raise ValidationError("Username can only contain alphanumeric characters, underscores, and hyphens.")
        if User.objects.filter(username__iexact=username).exists():
            raise ValidationError("This username is already taken. Please choose another.")
        return username

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError("An account with this email address already exists.")
        return email

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        password_confirm = cleaned_data.get('password_confirm')

        if password and password_confirm:
            if password != password_confirm:
                self.add_error('password_confirm', "Passwords do not match.")
            else:
                try:
                    # Run Django's configured password validators
                    validate_password(password)
                except ValidationError as e:
                    self.add_error('password', e)

        return cleaned_data


class CandidateLoginForm(forms.Form):
    username = forms.CharField(
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'e.g. alex_dev or alex@example.com',
            'autocomplete': 'username',
            'id': 'id_username',
        })
    )
    password = forms.CharField(
        required=True,
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': 'Enter your password',
            'autocomplete': 'current-password',
            'id': 'id_password',
        })
    )
    remember_me = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'checkbox-input',
            'id': 'id_remember_me',
        })
    )
