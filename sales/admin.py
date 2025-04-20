from django.contrib import admin
from django.utils.html import format_html
from .models import Sale, SaleItem, Payment

class SaleItemInline(admin.TabularInline):
    """판매 상세 내역을 인라인으로 표시하기 위한 클래스"""
    model = SaleItem
    extra = 0
    readonly_fields = ('subtotal',)
    fields = ('product', 'quantity', 'price', 'discount', 'subtotal')

class PaymentInline(admin.TabularInline):
    """결제 정보를 인라인으로 표시하기 위한 클래스"""
    model = Payment
    extra = 0
    fields = ('payment_type', 'amount', 'payment_date', 'payment_details')

@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ('sale_number', 'sale_date', 'store', 'customer_name', 
                    'payment_method', 'status', 'display_total_amount', 
                    'display_final_amount', 'sales_channel')
    
    list_filter = ('status', 'payment_method', 'sales_channel', 'store', 'sale_date')
    search_fields = ('sale_number', 'customer_name', 'customer_phone', 'notes')
    date_hierarchy = 'sale_date'
    
    fieldsets = (
        ('기본 정보', {
            'fields': ('sale_number', 'sale_date', 'store', 'status', 'sales_channel')
        }),
        ('고객 정보', {
            'fields': ('customer_name', 'customer_phone')
        }),
        ('금액 정보', {
            'fields': ('total_amount', 'discount_amount', 'final_amount')
        }),
        ('결제 정보', {
            'fields': ('payment_method', 'notes')
        }),
    )
    
    readonly_fields = ('created_at', 'updated_at')
    inlines = [SaleItemInline, PaymentInline]
    
    def display_total_amount(self, obj):
        return f"{obj.total_amount:,}원"
    display_total_amount.short_description = '총 금액'
    
    def display_final_amount(self, obj):
        # return format_html('<b>{:,}원</b>', obj.final_amount)
        formatted_amount = f"{obj.final_amount:,}원"
        return format_html('<b>{}</b>', formatted_amount)
    display_final_amount.short_description = '최종 결제액'
    
    def get_readonly_fields(self, request, obj=None):
        if obj and obj.status in ['completed', 'cancelled', 'refunded']:
            # 완료, 취소, 환불 상태인 경우 더 많은 필드를 읽기 전용으로 설정
            return self.readonly_fields + ('sale_number', 'store', 'total_amount', 
                                          'discount_amount', 'final_amount')
        return self.readonly_fields
    
    def has_delete_permission(self, request, obj=None):
        # 완료된 판매는 삭제할 수 없도록 설정 (데이터 무결성 유지)
        if obj and obj.status == 'completed':
            return False
        return super().has_delete_permission(request, obj)

@admin.register(SaleItem)
class SaleItemAdmin(admin.ModelAdmin):
    list_display = ('id', 'sale_number', 'product_name', 'quantity', 'price', 'discount', 'subtotal')
    list_filter = ('sale__status', 'sale__store')
    search_fields = ('sale__sale_number', 'product__name', 'product__code')
    
    def sale_number(self, obj):
        return obj.sale.sale_number
    sale_number.short_description = '판매번호'
    
    def product_name(self, obj):
        return obj.product.name
    product_name.short_description = '상품명'

# 추가적으로 Payment 모델 등록 (선택 사항)
@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('id', 'sale_number', 'payment_type', 'amount', 'payment_date')
    list_filter = ('payment_type', 'payment_date')
    search_fields = ('sale__sale_number', 'payment_details')
    
    def sale_number(self, obj):
        return obj.sale.sale_number
    sale_number.short_description = '판매번호'