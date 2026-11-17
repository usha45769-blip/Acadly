import os

from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password

from .models import Resource

ALLOWED_EXT = {".pdf", ".doc", ".docx", ".ppt", ".pptx", ".txt", ".png", ".jpg", ".jpeg", ".zip"}


class EmailLoginForm(AuthenticationForm):
    username = forms.EmailField(label="Email")


class RegisterForm(forms.Form):
    name = forms.CharField(max_length=100)
    phone = forms.RegexField(r"^[0-9]{10}$", error_messages={"invalid": "Enter a 10-digit phone number."})
    email = forms.EmailField()
    batch = forms.ChoiceField(choices=[("B1", "Batch B1"), ("B2", "Batch B2")],
                              help_text="Decides which lab you attend on Tuesday and Friday.")
    password = forms.CharField(widget=forms.PasswordInput)

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(username=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email

    def clean_password(self):
        pw = self.cleaned_data["password"]
        validate_password(pw)
        return pw


class TimetableUploadForm(forms.Form):
    image = forms.ImageField(label="Timetable photo or scan")


class ResourceForm(forms.ModelForm):
    class Meta:
        model = Resource
        fields = ["subject", "category", "title", "file", "link"]

    def clean_file(self):
        f = self.cleaned_data.get("file")
        if f:
            if os.path.splitext(f.name)[1].lower() not in ALLOWED_EXT:
                raise forms.ValidationError("Allowed types: " + ", ".join(sorted(ALLOWED_EXT)))
            if f.size > 10 * 1024 * 1024:
                raise forms.ValidationError("File must be under 10 MB.")
        return f

    def clean(self):
        data = super().clean()
        if not data.get("file") and not data.get("link"):
            raise forms.ValidationError("Upload a file or paste a link.")
        return data
