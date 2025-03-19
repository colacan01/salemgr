from django.contrib import admin
from .models import (
    Category, Product, ProductPrice, ProductStock,
    StockReceipt, StockRelease, StockAdjustment
)

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'store')
    list_filter = ('store',)
    search_fields = ('name',)

class ProductPriceInline(admin.TabularInline):
    model = ProductPrice
    extra = 1

class ProductStockInline(admin.TabularInline):
    model = ProductStock
    extra = 0
    readonly_fields = ('updated_at',)

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'category', 'store', 'is_active', 'current_price', 'total_stock')
    list_filter = ('category', 'store', 'is_active')
    search_fields = ('code', 'name', 'description')
    inlines = [ProductPriceInline, ProductStockInline]
    
    def current_price(self, obj):
        price = obj.get_current_price()
        return f"{price:,}" if price else "-"
    current_price.short_description = '현재 판매가'
    
    def total_stock(self, obj):
        return obj.get_current_stock()
    total_stock.short_description = '총 재고'

@admin.register(ProductPrice)
class ProductPriceAdmin(admin.ModelAdmin):
    list_display = ('product', 'price', 'start_date', 'end_date')
    list_filter = ('start_date', 'end_date')
    search_fields = ('product__name', 'product__code')
    date_hierarchy = 'start_date'

@admin.register(ProductStock)
class ProductStockAdmin(admin.ModelAdmin):
    list_display = ('product', 'store', 'quantity', 'updated_at')
    list_filter = ('store',)
    search_fields = ('product__name', 'product__code')
    readonly_fields = ('updated_at',)

@admin.register(StockReceipt)
class StockReceiptAdmin(admin.ModelAdmin):
    list_display = ('receipt_date', 'product', 'store', 'quantity', 'cost_price', 'created_by')
    list_filter = ('receipt_date', 'store')
    search_fields = ('product__name', 'product__code', 'receipt_number')
    date_hierarchy = 'receipt_date'

@admin.register(StockRelease)
class StockReleaseAdmin(admin.ModelAdmin):
    list_display = ('release_date', 'product', 'store', 'quantity', 'release_type', 'created_by')
    list_filter = ('release_date', 'store', 'release_type')
    search_fields = ('product__name', 'product__code')
    date_hierarchy = 'release_date'

@admin.register(StockAdjustment)
class StockAdjustmentAdmin(admin.ModelAdmin):
    list_display = ('adjustment_date', 'product', 'store', 'quantity', 'adjustment_type', 'created_by')
    list_filter = ('adjustment_date', 'store', 'adjustment_type')
    search_fields = ('product__name', 'product__code', 'reason')
    date_hierarchy = 'adjustment_date'