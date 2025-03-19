from django import forms
from django.forms import inlineformset_factory, BaseInlineFormSet
from django.db.models import Q
from django.utils import timezone

from .models import Return, ReturnItem
from sales.models import Sale, SaleItem

class ReturnForm(forms.ModelForm):
    """반품 메인 폼"""
    class Meta:
        model = Return
        fields = ['sale', 'store', 'return_date', 'customer_name', 'customer_phone', 
                 'refund_method', 'reason', 'notes']
        widgets = {
            'return_date': forms.DateTimeInput(attrs={
                'type': 'datetime-local',
                'class': 'form-control'
            }),
            'customer_name': forms.TextInput(attrs={'class': 'form-control'}),
            'customer_phone': forms.TextInput(attrs={'class': 'form-control'}),
            'reason': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'sale': forms.Select(attrs={'class': 'form-select'}),
            'store': forms.Select(attrs={'class': 'form-select'}),
            'refund_method': forms.Select(attrs={'class': 'form-select'}),
        }
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # 판매 내역 필터링 (완료된 판매만)
        self.fields['sale'].queryset = Sale.objects.filter(status='completed')
        
        # 사용자 매장 기반 필터링
        if user and user.user_type != 'app_admin':
            if hasattr(user, 'store') and user.store:
                self.fields['store'].initial = user.store
                self.fields['store'].queryset = self.fields['store'].queryset.filter(id=user.store.id)
                self.fields['sale'].queryset = self.fields['sale'].queryset.filter(store=user.store)
        
        # 기본값 설정
        self.fields['return_date'].initial = timezone.now()


class ReturnItemForm(forms.ModelForm):
    """반품 상품 폼"""
    max_quantity = forms.IntegerField(widget=forms.HiddenInput(), required=False)
    
    class Meta:
        model = ReturnItem
        fields = ['sale_item', 'product', 'quantity', 'price', 'refund_amount', 
                 'return_reason', 'condition', 'restock', 'notes']
        widgets = {
            'sale_item': forms.Select(attrs={'class': 'form-select sale-item-select'}),
            'product': forms.HiddenInput(),
            'quantity': forms.NumberInput(attrs={'class': 'form-control quantity-input', 'min': 1}),
            'price': forms.NumberInput(attrs={'class': 'form-control price-input', 'readonly': True}),
            'refund_amount': forms.NumberInput(attrs={'class': 'form-control refund-amount-input'}),
            'return_reason': forms.Select(attrs={'class': 'form-select'}),
            'condition': forms.Select(attrs={'class': 'form-select condition-select'}),
            'restock': forms.CheckboxInput(attrs={'class': 'form-check-input', 'checked': True}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # sale_item을 필수 필드가 아니도록 설정
        self.fields['sale_item'].required = False
        
        # product는 필수 필드로 설정
        self.fields['product'].required = True
        
        # 인스턴스 가져오기
        instance = getattr(self, 'instance', None)
        
        # 사용자 권한에 따라 판매 항목 필터링
        if self.user and hasattr(self.user, 'store'):
            if self.user.user_type != 'app_admin':
                self.fields['sale_item'].queryset = self.fields['sale_item'].queryset.filter(
                    sale__store=self.user.store
                )
        
        # 반품 사유 선택 시 기본값 설정
        if not self.initial.get('return_reason'):
            self.initial['return_reason'] = 'customer_request'
            
        # 판매 항목이 선택된 경우 관련 정보 설정
        if instance and instance.sale_item:
            self.fields['product'].initial = instance.sale_item.product
            self.fields['price'].initial = instance.sale_item.price
            self.fields['max_quantity'].initial = instance.sale_item.quantity
            
            # 수량이 설정되지 않은 경우 기본값 1로 설정
            if not instance.quantity:
                instance.quantity = 1
                
            # 환불 금액이 설정되지 않은 경우 계산
            if not instance.refund_amount:
                instance.refund_amount = instance.sale_item.price * instance.quantity
    
    def clean_quantity(self):
        """수량 검증"""
        quantity = self.cleaned_data.get('quantity')
        sale_item = self.cleaned_data.get('sale_item')
        
        if quantity <= 0:
            raise forms.ValidationError("수량은 0보다 커야 합니다.")
            
        # sale_item이 있는 경우에만 판매 수량 제한 검사
        if sale_item and quantity > sale_item.quantity:
            raise forms.ValidationError(f"판매된 수량({sale_item.quantity}개)보다 많이 반품할 수 없습니다.")
            
        return quantity
        
    def clean(self):
        """폼 전체 검증"""
        cleaned_data = super().clean()
        sale_item = cleaned_data.get('sale_item')
        product = cleaned_data.get('product')
        price = cleaned_data.get('price')
        quantity = cleaned_data.get('quantity')
        refund_amount = cleaned_data.get('refund_amount')
        
        # product 필드가 필수임을 검증
        if not product:
            if sale_item:
                # 판매 항목이 있으면 상품 자동 설정
                cleaned_data['product'] = sale_item.product
            else:
                self.add_error('product', '상품을 선택해야 합니다.')
        
        # 가격 검증
        if not price or price <= 0:
            if sale_item:
                cleaned_data['price'] = sale_item.price
            else:
                self.add_error('price', '유효한 가격을 입력해야 합니다.')
        
        # 환불 금액 자동 계산
        if not refund_amount and price and quantity:
            cleaned_data['refund_amount'] = price * quantity
                
        return cleaned_data


class ReturnItemInlineFormSet(BaseInlineFormSet):
    """반품 상품 폼셋"""
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
    
    def _construct_form(self, i, **kwargs):
        kwargs['user'] = self.user
        return super()._construct_form(i, **kwargs)
        
    def clean(self):
        """최소 하나 이상의 반품 항목이 있는지 확인"""
        super().clean()
        
        if any(self.errors):
            return
            
        if not any(form.cleaned_data and not form.cleaned_data.get('DELETE', False)
                 for form in self.forms):
            raise forms.ValidationError("최소 하나 이상의 반품 항목을 추가해주세요.")


# 인라인 폼셋 정의
ReturnItemFormSet = inlineformset_factory(
    Return, ReturnItem, 
    form=ReturnItemForm,
    formset=ReturnItemInlineFormSet,
    extra=1, 
    can_delete=True,
    validate_max=True
)