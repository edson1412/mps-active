from django import forms
from django.contrib.auth.forms import UserCreationForm, PasswordChangeForm

from prison.models import PrisonStation, Region

from .models import CustomUser


class CustomUserCreationForm(UserCreationForm):
    class Meta:
        model = CustomUser
        fields = (
            'username', 'email', 'first_name', 'last_name',
            'role', 'rank', 'region', 'prison_station',
        )

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

        # Only superusers can create other superusers or admins
        if not (self.request and self.request.user.is_super_admin()):
            self.fields['role'].choices = [
                (role, label)
                for role, label in self.Meta.model.ROLE_CHOICES
                if role not in [CustomUser.ROLE_SUPERUSER, CustomUser.ROLE_ADMIN]
            ]

        self.fields['prison_station'].queryset = PrisonStation.objects.all()
        self.fields['region'].queryset = Region.objects.all()

    def clean(self):
        cleaned_data = super().clean()
        role = cleaned_data.get('role')
        if role in [CustomUser.ROLE_RCO, CustomUser.ROLE_RHO, CustomUser.ROLE_REGIONAL_HR]:
            if not cleaned_data.get('region'):
                self.add_error('region', 'Regional roles must be assigned a region.')
        elif role and role not in [CustomUser.ROLE_SUPERUSER, CustomUser.ROLE_ADMIN,
                                   CustomUser.ROLE_NATIONAL_COMMISSIONER, CustomUser.ROLE_NATIONAL_HR]:
            if not cleaned_data.get('prison_station'):
                self.add_error('prison_station', 'Station level roles must be assigned a prison station.')
        return cleaned_data


class CustomPasswordChangeForm(PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['old_password'].widget.attrs.update({'class': 'form-control'})
        self.fields['new_password1'].widget.attrs.update({'class': 'form-control'})
        self.fields['new_password2'].widget.attrs.update({'class': 'form-control'})
