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

from .models import ApartmentWatchlist, BuildingWatchlist
@admin.register(ApartmentWatchlist)
class ApartmentWatchlistAdmin(admin.ModelAdmin):
    list_display = ('user', 'apartment', 'notify_price_change', 'notify_availability_change', 'created_at')
    list_filter = ('notify_price_change', 'notify_availability_change')
    search_fields = ('user__email', 'apartment__unit_number')
    date_hierarchy = 'created_at'

@admin.register(BuildingWatchlist)
class BuildingWatchlistAdmin(admin.ModelAdmin):
    list_display = ('user', 'building', 'notify_new_units', 'unit_type_preference', 'max_price', 'created_at')
    list_filter = ('notify_new_units', 'unit_type_preference')
    search_fields = ('user__email', 'building__name')
    date_hierarchy = 'created_at'