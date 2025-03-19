from django.contrib.auth.models import AbstractUser, Group, Permission
from django.db import models
from django.utils.translation import gettext_lazy as _

class User(AbstractUser):
    # 사용자 유형
    USER_TYPE_CHOICES = (
        ('app_admin', '앱관리자'),
        ('store_manager', '매장관리자'),
        ('store_staff', '매장직원'),
        ('customer', '고객'),
    )
    
    user_type = models.CharField(max_length=20, choices=USER_TYPE_CHOICES, default='customer')
    phone_number = models.CharField(max_length=20, blank=True)
    profile_image = models.ImageField(upload_to='profiles/', blank=True, null=True)
    
    # 매장 관리자와 직원은 매장에 연결됨
    store = models.ForeignKey('Store', on_delete=models.SET_NULL, null=True, blank=True, related_name='employees')
    
    class Meta:
        verbose_name = _('user')
        verbose_name_plural = _('users')
    
    def __str__(self):
        return f"{self.username} ({self.get_user_type_display()})"

class Store(models.Model):
    name = models.CharField(max_length=100)
    address = models.TextField()
    country = models.CharField(max_length=50, choices=[('KR', '한국'), ('VN', '베트남')])
    phone_number = models.CharField(max_length=20)
    email = models.EmailField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.name} ({self.get_country_display()})"