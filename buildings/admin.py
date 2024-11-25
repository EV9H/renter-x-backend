from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
# from .models import CustomUser
# class CustomUserAdmin(UserAdmin):
#     ordering = ('email',)
#     list_display = ('email', 'is_staff', 'is_superuser')
#     fieldsets = (
#         (None, {'fields': ('email', 'password')}),
#         ('Permissions', {'fields': ('is_staff', 'is_superuser', 'groups', 'user_permissions')}),
#         ('Important dates', {'fields': ('last_login', 'date_joined')}),
#     )
#     add_fieldsets = (
#         (None, {
#             'classes': ('wide',),
#             'fields': ('email', 'password1', 'password2'),
#         }),
#     )
#     search_fields = ('email',)
#     filter_horizontal = ()

# admin.site.register(CustomUser, CustomUserAdmin)

# admin.site.register(User, UserAdmin)