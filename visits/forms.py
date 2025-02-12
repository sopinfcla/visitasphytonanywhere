from django import forms
from django.contrib.auth.forms import AuthenticationForm

class StaffAuthenticationForm(AuthenticationForm):
    """Formulario personalizado para autenticación del staff"""
    
    username = forms.CharField(
        widget=forms.TextInput(
            attrs={
                'class': 'form-control',
                'placeholder': 'Usuario',
                'required': True,
                'autofocus': True
            }
        )
    )
    
    password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                'class': 'form-control',
                'placeholder': 'Contraseña',
                'required': True
            }
        )
    )
    
    remember_me = forms.BooleanField(
        required=False,
        initial=False,
        widget=forms.CheckboxInput(
            attrs={
                'class': 'form-check-input'
            }
        )
    )