from django import forms
from django.utils import timezone
from .models import (
    Category, Product, ProductPrice, StockReceipt, 
    StockRelease, StockAdjustment
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
        fields = ['product', 'store', 'quantity', 'cost_price', 
                  'receipt_date', 'receipt_number', 'note']
        widgets = {
            'receipt_date': forms.DateInput(attrs={'type': 'date'}),
            'note': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # 기본값 설정
        if not self.is_bound:
            self.fields['receipt_date'].initial = timezone.now().date()

class StockReleaseForm(forms.ModelForm):
    class Meta:
        model = StockRelease
        fields = ['product', 'store', 'quantity', 'release_type', 
                  'release_date', 'note']
        widgets = {
            'release_date': forms.DateInput(attrs={'type': 'date'}),
            'note': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # 기본값 설정
        if not self.is_bound:
            self.fields['release_date'].initial = timezone.now().date()
    
    def clean(self):
        cleaned_data = super().clean()
        product = cleaned_data.get('product')
        store = cleaned_data.get('store')
        quantity = cleaned_data.get('quantity')
        
        # 재고 확인
        if product and store and quantity:
            current_stock = product.get_current_stock(store)
            if quantity > current_stock:
                raise forms.ValidationError(f"출고 수량({quantity})이 현재 재고({current_stock})보다 많습니다.")
        
        return cleaned_data

class StockAdjustmentForm(forms.ModelForm):
    class Meta:
        model = StockAdjustment
        fields = ['product', 'store', 'quantity', 'adjustment_type', 
                  'adjustment_date', 'reason']
        widgets = {
            'adjustment_date': forms.DateInput(attrs={'type': 'date'}),
            'reason': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # 기본값 설정
        if not self.is_bound:
            self.fields['adjustment_date'].initial = timezone.now().date()