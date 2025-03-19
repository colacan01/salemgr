from django import forms
from django.db.models import Q
from django.forms import inlineformset_factory, BaseInlineFormSet
from .models import Sale, SaleItem, Payment
from inventory.models import Product

class SaleForm(forms.ModelForm):
    class Meta:
        model = Sale
        fields = ['store', 'sale_date', 'customer_name', 'customer_phone', 'payment_method', 'discount_amount', 'notes']
        widgets = {
            'store': forms.Select(attrs={'class': 'form-select'}),
            'sale_date': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'customer_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '고객명'}),
            'customer_phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '연락처'}),
            'payment_method': forms.Select(attrs={'class': 'form-select'}),
            'discount_amount': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'notes': forms.Textarea(attrs={'rows': 3, 'class': 'form-control', 'placeholder': '비고 사항을 입력하세요'}),
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # 사용자에 따른 매장 필터링 - 기존 코드
        if self.user:
            if self.user.user_type == 'app_admin':
                # 앱 관리자는 모든 매장 선택 가능
                pass
            else:
                # 매장 관리자/직원은 자신의 매장만 선택 가능하고 수정 불가
                self.fields['store'].initial = self.user.store
                self.fields['store'].widget.attrs['readonly'] = True
                self.fields['store'].queryset = self.fields['store'].queryset.filter(id=self.user.store.id)


class SaleItemForm(forms.ModelForm):
    class Meta:
        model = SaleItem
        fields = ['product', 'quantity', 'price', 'discount']
        widgets = {
            'product': forms.Select(attrs={'class': 'form-select'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'min': '1', 'value': '1'}),
            'price': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'min': '0'}),
            'discount': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'min': '0', 'value': '0'}),
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # 사용자 권한에 따라 상품 필터링
        if self.user:
            if self.user.user_type == 'app_admin':
                # 앱 관리자는 활성화된 모든 상품 조회
                self.fields['product'].queryset = Product.objects.filter(is_active=True)
            else:
                # 매장 관리자/직원은 자신의 매장 상품과 공용 상품만 조회
                self.fields['product'].queryset = Product.objects.filter(
                    Q(store=self.user.store) | Q(store__isnull=True),
                    is_active=True
                )


class PaymentForm(forms.ModelForm):
    class Meta:
        model = Payment
        fields = ['payment_type', 'amount', 'payment_details']
        widgets = {
            'payment_type': forms.Select(attrs={'class': 'form-select'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'payment_details': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '결제 세부 정보'}),
        }

# 커스텀 BaseInlineFormSet 클래스 추가
class SaleItemInlineFormSet(BaseInlineFormSet):
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
    
    def _construct_form(self, i, **kwargs):
        kwargs['user'] = self.user
        return super()._construct_form(i, **kwargs)

# 인라인 폼셋 정의 수정
SaleItemFormSet = inlineformset_factory(
    Sale, SaleItem, form=SaleItemForm, 
    formset=SaleItemInlineFormSet,
    extra=1, can_delete=True
)

PaymentFormSet = inlineformset_factory(
    Sale, Payment, form=PaymentForm,
    extra=1, can_delete=True
)