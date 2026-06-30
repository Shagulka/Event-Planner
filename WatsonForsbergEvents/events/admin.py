from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User, Permission

from .models import Event


class UserEditForm(forms.ModelForm):
    can_edit_events = forms.BooleanField(
        required=False,
        label="Can edit events, people & companies",
        help_text="Grant full write access. Without this, the user is read-only.",
    )

    class Meta:
        model = User
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields['can_edit_events'].initial = self.instance.has_perm('events.can_edit_events')


class CustomUserAdmin(UserAdmin):
    form = UserEditForm

    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'email')}),
        ('Access', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'can_edit_events'),
            'description': 'Superusers always have full write access regardless of the checkbox below.',
        }),
        ('Groups & permissions', {
            'fields': ('groups', 'user_permissions'),
            'classes': ('collapse',),
        }),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )

    def save_related(self, request, form, formsets, change):
        # Must run after save_m2m() (called inside super()), otherwise the
        # user_permissions field on the form re-syncs from its submitted
        # data and clobbers the add/remove below.
        super().save_related(request, form, formsets, change)
        perm = Permission.objects.get(
            content_type__app_label='events',
            codename='can_edit_events',
        )
        if form.cleaned_data.get('can_edit_events'):
            form.instance.user_permissions.add(perm)
        else:
            form.instance.user_permissions.remove(perm)


admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)
admin.site.register(Event)
