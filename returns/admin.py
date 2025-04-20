from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from .models import Return, ReturnItem

class ReturnItemInline(admin.TabularInline):
    """반품 상세 내역을 인라인으로 표시하기 위한 클래스"""
    model = ReturnItem
    extra = 0
    fields = ('sale_item', 'product', 'quantity', 'price', 'refund_amount', 
              'return_reason', 'condition', 'restock', 'notes')
    readonly_fields = ('refund_amount',)
    autocomplete_fields = ['product', 'sale_item']

@admin.register(Return)
class ReturnAdmin(admin.ModelAdmin):
    list_display = ('return_number', 'return_date', 'sale_link', 'store', 'customer_name', 
                   'status', 'display_total_amount', 'refund_method', 'created_by')
    
    list_filter = ('status', 'refund_method', 'store', 'return_date')
    search_fields = ('return_number', 'customer_name', 'customer_phone', 'reason', 'notes')
    date_hierarchy = 'return_date'
    
    fieldsets = (
        ('기본 정보', {
            'fields': ('return_number', 'sale', 'return_date', 'store', 'status')
        }),
        ('고객 정보', {
            'fields': ('customer_name', 'customer_phone')
        }),
        ('환불 정보', {
            'fields': ('refund_method', 'total_amount', 'reason', 'notes')
        }),
        ('처리 정보', {
            'fields': ('created_by', 'created_at', 'approved_by', 'approved_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ('created_by', 'created_at', 'approved_by', 'approved_at', 'updated_at')
    inlines = [ReturnItemInline]
    
    def sale_link(self, obj):
        if obj.sale:
            url = f"/admin/sales/sale/{obj.sale.id}/change/"
            return format_html('<a href="{}">{}</a>', url, obj.sale.sale_number)
        return "-"
    sale_link.short_description = '원판매'
    
    def display_total_amount(self, obj):
        formatted_amount = f"{obj.total_amount:,}원"
        return format_html('<b>{}</b>', formatted_amount)
    display_total_amount.short_description = '환불 금액'
    
    def save_model(self, request, obj, form, change):
        # 객체 생성 시 작성자 자동 설정
        if not change:  # 새 객체인 경우
            obj.created_by = request.user
        
        # 상태가 변경되어 승인됨으로 설정된 경우
        if change and 'status' in form.changed_data and obj.status == 'approved':
            obj.approved_by = request.user
            obj.approved_at = timezone.now()
            
        super().save_model(request, obj, form, change)
    
    def get_readonly_fields(self, request, obj=None):
        if obj and obj.status in ['approved', 'rejected', 'completed']:
            # 승인/거부/완료 상태인 경우 더 많은 필드를 읽기 전용으로 설정
            return self.readonly_fields + ('return_number', 'sale', 'store', 'reason', 
                                          'total_amount', 'refund_method')
        return self.readonly_fields
    
    def has_delete_permission(self, request, obj=None):
        # 승인/완료된 반품은 삭제할 수 없도록 설정
        if obj and obj.status in ['approved', 'completed']:
            return False
        return super().has_delete_permission(request, obj)
    
    actions = ['approve_returns', 'reject_returns', 'complete_returns']
    
    def approve_returns(self, request, queryset):
        count = 0
        for return_obj in queryset.filter(status='pending'):
            return_obj.approve(request.user)
            count += 1
        self.message_user(request, f'{count}개의 반품이 승인되었습니다.')
    approve_returns.short_description = '선택된 반품을 승인'
    
    def reject_returns(self, request, queryset):
        count = 0
        for return_obj in queryset.filter(status='pending'):
            return_obj.reject(request.user, '관리자에 의한 일괄 거부')
            count += 1
        self.message_user(request, f'{count}개의 반품이 거부되었습니다.')
    reject_returns.short_description = '선택된 반품을 거부'
    
    def complete_returns(self, request, queryset):
        count = 0
        for return_obj in queryset.filter(status='approved'):
            if return_obj.complete():
                count += 1
        self.message_user(request, f'{count}개의 반품이 완료 처리되었습니다.')
    complete_returns.short_description = '선택된 반품을 완료 처리'

@admin.register(ReturnItem)
class ReturnItemAdmin(admin.ModelAdmin):
    list_display = ('id', 'return_number', 'product_name', 'quantity', 
                   'price', 'refund_amount', 'return_reason', 'condition', 'restock')
    list_filter = ('return_reason', 'condition', 'restock', 'return_parent__status')
    search_fields = ('product__name', 'return_parent__return_number', 'notes')
    
    def return_number(self, obj):
        return obj.return_parent.return_number
    return_number.short_description = '반품번호'
    
    def product_name(self, obj):
        return obj.product.name
    product_name.short_description = '상품명'
    
    # 읽기 전용 필드 설정
    def get_readonly_fields(self, request, obj=None):
        if obj and obj.return_parent and obj.return_parent.status in ['approved', 'completed']:
            return ('return_parent', 'sale_item', 'product', 'quantity', 'price', 
                   'refund_amount', 'return_reason')
        return ()