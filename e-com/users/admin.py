from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser

class CustomUserAdmin(UserAdmin):
    model = CustomUser
    list_display = ('email', 'first_name','last_name','is_staff', 'is_active')
    list_filter = ('role','is_staff', 'is_active')
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal Info', {'fields': ('first_name', 'last_name')}),
        ('Role & Permissions', {'fields': ('role','is_staff', 'is_active', 'is_superuser', 'groups', 'user_permissions')}),('important dates',{'fields':('last_login',)})
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'first_name','last_name','password','role','password1', 'password2', 'is_staff', 'is_active')}
        ),
    )
    search_fields = ('email','first_name','last-name')
    ordering = ('email',)

admin.site.register(CustomUser, CustomUserAdmin)
