from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Store

class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'user_type', 'store', 'is_staff')
    fieldsets = UserAdmin.fieldsets + (
        ('추가 정보', {'fields': ('user_type', 'phone_number', 'profile_image', 'store')}),
    )
    list_filter = UserAdmin.list_filter + ('user_type', 'store')
    
admin.site.register(User, CustomUserAdmin)
admin.site.register(Store)