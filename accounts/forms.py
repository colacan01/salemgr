from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from .models import Store, User

class SignupForm(UserCreationForm):
    phone_number = forms.CharField(max_length=20, required=False, help_text='연락 가능한 전화번호를 입력하세요')
    profile_image = forms.ImageField(required=False)
    
    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'password1', 'password2', 
                  'phone_number', 'profile_image')
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.user_type = 'customer'  # 기본값은 고객으로 설정
        if commit:
            user.save()
        return user

class ProfileEditForm(forms.ModelForm):
    """사용자 프로필 편집 폼"""
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'phone_number', 'profile_image']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control'}),
            'profile_image': forms.FileInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'first_name': '이름',
            'last_name': '성',
            'email': '이메일',
            'phone_number': '전화번호',
            'profile_image': '프로필 이미지',
        }
        
class StoreForm(forms.ModelForm):
    """매장 생성 및 수정을 위한 폼"""
    class Meta:
        model = Store
        fields = ['name', 'address', 'country', 'phone_number', 'email']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'country': forms.Select(attrs={'class': 'form-select'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'name': '매장명',
            'address': '주소',
            'country': '국가',
            'phone_number': '연락처',
            'email': '이메일',
        }