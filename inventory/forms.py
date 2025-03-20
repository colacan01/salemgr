from django import forms
from django.utils import timezone
from .models import (
    Category, Product, ProductPrice, StockReceipt, 
    StockRelease, StockAdjustment, Store
)

class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'description', 'store']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'store': forms.Select(attrs={'class': 'form-select'}),
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # 사용자 권한에 따라 매장 선택 필드 설정
        if self.user:
            if self.user.user_type == 'app_admin':
                # 앱 관리자는 모든 매장 선택 가능 + 전체 매장용 옵션
                self.fields['store'].required = False
            elif self.user.user_type in ['store_manager', 'store_staff']:
                # 매장 관리자/직원은 자신의 매장만 선택 가능
                self.fields['store'].initial = self.user.store
                self.fields['store'].widget = forms.HiddenInput()
                self.fields['store'].required = True

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['code', 'name', 'description', 'category', 
                  'store', 'barcode', 'image', 'is_active']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'code': forms.TextInput(attrs={'class': 'form-control'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'store': forms.Select(attrs={'class': 'form-select'}),
            'barcode': forms.TextInput(attrs={'class': 'form-control'}),
            'image': forms.FileInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # 사용자 권한에 따라 매장 및 카테고리 선택 필드 설정
        if self.user:
            if self.user.user_type == 'app_admin':
                # 앱 관리자는 모든 매장 선택 가능
                self.fields['store'].required = False
                # 카테고리도 모두 선택 가능
                self.fields['category'].queryset = Category.objects.all()
            elif self.user.user_type in ['store_manager', 'store_staff']:
                # 매장 관리자/직원은 자신의 매장만 선택 가능
                self.fields['store'].initial = self.user.store
                self.fields['store'].widget = forms.HiddenInput()
                self.fields['store'].required = True
                # 해당 매장의 카테고리만 선택 가능
                self.fields['category'].queryset = Category.objects.filter(
                    store=self.user.store
                ) | Category.objects.filter(store__isnull=True)

class ProductPriceForm(forms.ModelForm):
    class Meta:
        model = ProductPrice
        fields = ['price', 'start_date', 'end_date']
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
        }
    
    def __init__(self, *args, **kwargs):
        self.product = kwargs.pop('product', None)
        super().__init__(*args, **kwargs)
        
        # 기본값 설정
        if not self.is_bound:  # 폼이 처음 생성될 때만
            self.fields['start_date'].initial = timezone.now().date()
            self.fields['end_date'].initial = timezone.now().date().replace(year=timezone.now().year + 1)
    
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        
        if start_date and end_date and start_date > end_date:
            raise forms.ValidationError("종료일은 시작일보다 이후여야 합니다.")
        
        # 같은 기간에 다른 가격이 존재하는지 확인
        if self.product and start_date and end_date:
            overlapping_prices = ProductPrice.objects.filter(
                product=self.product,
                start_date__lte=end_date,
                end_date__gte=start_date
            )
            
            # 수정 중인 경우 자기 자신 제외
            if self.instance.pk:
                overlapping_prices = overlapping_prices.exclude(pk=self.instance.pk)
            
            if overlapping_prices.exists():
                raise forms.ValidationError("해당 기간에 이미 설정된 가격이 있습니다.")
        
        return cleaned_data

class StockReceiptForm(forms.ModelForm):
    class Meta:
        model = StockReceipt
        fields = ['receipt_number', 'receipt_date', 'store', 'product', 'quantity', 'cost_price', 'note']
        widgets = {
            'receipt_date': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # 매장 선택 필드 설정
        if user:
            # 앱 관리자인 경우 모든 매장 선택 가능
            if user.user_type == 'app_admin':
                self.fields['store'].queryset = Store.objects.all()
            # 그 외 사용자는 자신의 매장만 선택 가능
            elif user.store:
                self.fields['store'].queryset = Store.objects.filter(id=user.store.id)
                # 선택지가 하나뿐이면 읽기 전용으로 설정
                self.fields['store'].widget.attrs['readonly'] = True
                self.fields['store'].widget.attrs['disabled'] = True  # HTML에서는 disabled 속성 사용
                # hidden field를 위해 초기값 설정
                self.initial['store'] = user.store

class StockReleaseForm(forms.ModelForm):
    class Meta:
        model = StockRelease
        fields = ['product', 'store', 'quantity', 'release_type', 'release_date', 'note']
        widgets = {
            'release_date': forms.DateInput(attrs={'type': 'date'}),
            'note': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # 기본 오늘 날짜 설정
        if not self.instance.pk and not self.initial.get('release_date'):
            self.initial['release_date'] = timezone.now().date()
        
        # 사용자에 따른 매장 선택 제한
        if self.user:
            if self.user.user_type == 'app_admin':
                # 앱 관리자는 모든 매장 선택 가능
                from accounts.models import Store
                self.fields['store'].queryset = Store.objects.all()
            elif self.user.store:
                # 일반 사용자는 자신의 매장만 선택 가능
                from accounts.models import Store
                self.fields['store'].queryset = Store.objects.filter(id=self.user.store.id)
                
                # 기존 값이 없을 때만 초기값 설정
                if not self.instance.pk:
                    self.initial['store'] = self.user.store

class StockAdjustmentForm(forms.ModelForm):
    class Meta:
        model = StockAdjustment
        fields = ['adjustment_date', 'store', 'product', 'adjustment_type', 'quantity', 'reason']
        widgets = {
            'adjustment_date': forms.DateInput(attrs={'type': 'date'}),
            'reason': forms.Textarea(attrs={'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # 기본 오늘 날짜 설정
        if not self.instance.pk and not self.initial.get('adjustment_date'):
            self.initial['adjustment_date'] = timezone.now().date()
        
        # 사용자에 따른 매장 선택 제한
        if self.user:
            if self.user.user_type == 'app_admin':
                # 앱 관리자는 모든 매장 선택 가능
                from accounts.models import Store
                self.fields['store'].queryset = Store.objects.all()
            elif self.user.store:
                # 일반 사용자는 자신의 매장만 선택 가능
                from accounts.models import Store
                self.fields['store'].queryset = Store.objects.filter(id=self.user.store.id)
                self.fields['store'].initial = self.user.store