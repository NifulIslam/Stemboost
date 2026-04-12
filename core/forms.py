"""
STEMboost Forms
"""
from django import forms
from django.contrib.auth import password_validation
from .models import User, Course, Chapter


def _base_attrs(extra=None):
    base = {'class': 'form-input', 'autocomplete': 'off', 'spellcheck': 'false'}
    if extra:
        base.update(extra)
    return base


class LoginForm(forms.Form):
    email = forms.EmailField(
        label='Email Address',
        widget=forms.EmailInput(attrs={**_base_attrs(), 'id': 'id_email',
            'placeholder': 'your@email.com', 'tabindex': '1',
            'aria-label': 'Email address', 'aria-required': 'true'}),
    )
    password = forms.CharField(
        label='Password',
        widget=forms.PasswordInput(attrs={**_base_attrs(), 'id': 'id_password',
            'placeholder': '••••••••', 'tabindex': '2',
            'aria-label': 'Password', 'aria-required': 'true'}),
    )

    def clean(self):
        cleaned = super().clean()
        email = cleaned.get('email', '').strip().lower()
        cleaned['email'] = email
        return cleaned


class RegisterForm(forms.ModelForm):
    password1 = forms.CharField(
        label='Password',
        widget=forms.PasswordInput(attrs={**_base_attrs(), 'id': 'id_password1',
            'placeholder': 'Create a strong password', 'tabindex': '3',
            'aria-label': 'Password', 'aria-required': 'true'}),
        help_text='Minimum 8 characters.',
    )
    password2 = forms.CharField(
        label='Confirm Password',
        widget=forms.PasswordInput(attrs={**_base_attrs(), 'id': 'id_password2',
            'placeholder': 'Repeat your password', 'tabindex': '4',
            'aria-label': 'Confirm password', 'aria-required': 'true'}),
    )

    class Meta:
        model = User
        fields = ['email', 'role']
        widgets = {
            'email': forms.EmailInput(attrs={**_base_attrs(), 'id': 'id_email',
                'placeholder': 'your@email.com', 'tabindex': '2',
                'aria-label': 'Email address', 'aria-required': 'true'}),
            'role': forms.Select(attrs={**_base_attrs(), 'id': 'id_role',
                'tabindex': '5', 'aria-label': 'Select your role'}),
        }
        labels = {'email': 'Email Address', 'role': 'I am a…'}

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('An account with this email already exists.')
        return email

    def clean_password2(self):
        p1 = self.cleaned_data.get('password1', '')
        p2 = self.cleaned_data.get('password2', '')
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError('The two passwords do not match.')
        return p2

    def _post_clean(self):
        super()._post_clean()
        password = self.cleaned_data.get('password1')
        if password:
            try:
                password_validation.validate_password(password, self.instance)
            except forms.ValidationError as error:
                self.add_error('password1', error)

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password1'])
        if commit:
            user.save()
        return user


class CourseForm(forms.ModelForm):
    class Meta:
        model  = Course
        fields = ['title', 'description']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-input', 'placeholder': 'Course title',
                'aria-label': 'Course title', 'required': True,
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-input', 'rows': 4,
                'placeholder': 'Brief course description…',
                'aria-label': 'Course description',
            }),
        }


class ChapterForm(forms.ModelForm):
    class Meta:
        model  = Chapter
        fields = ['title', 'content', 'image', 'order']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-input', 'placeholder': 'Chapter title',
                'aria-label': 'Chapter title', 'required': True,
            }),
            'content': forms.Textarea(attrs={
                'class': 'form-input', 'rows': 8,
                'placeholder': 'Chapter text content (this will be read aloud to learners)…',
                'aria-label': 'Chapter content',
            }),
            'image': forms.ClearableFileInput(attrs={
                'class': 'form-input', 'accept': 'image/*',
                'aria-label': 'Chapter image (optional)',
            }),
            'order': forms.NumberInput(attrs={
                'class': 'form-input', 'min': 0,
                'aria-label': 'Chapter order (lower numbers appear first)',
            }),
        }
        labels = {
            'content': 'Text Content',
            'order':   'Display Order',
        }
