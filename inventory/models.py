from django.db import models
from django.core.validators import MinValueValidator
from django.utils import timezone
from accounts.models import Store, User

class Category(models.Model):
    name = models.CharField(max_length=100, verbose_name='카테고리명')
    description = models.TextField(blank=True, null=True, verbose_name='설명')
    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name='categories', 
                              verbose_name='매장', null=True, blank=True)
    # null=True로 설정하여 기존 데이터 호환성 유지
    
    class Meta:
        verbose_name = '카테고리'
        verbose_name_plural = '카테고리'
        ordering = ['name']
        # 같은 매장 내에서 카테고리명 중복 방지
        unique_together = ['name', 'store']
    
    def __str__(self):
        store_name = self.store.name if self.store else '전체'
        return f"{self.name} ({store_name})"

class Product(models.Model):
    code = models.CharField(max_length=50, unique=True, verbose_name='상품코드')
    name = models.CharField(max_length=200, verbose_name='상품명')
    description = models.TextField(blank=True, null=True, verbose_name='상품설명')
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name='products', verbose_name='카테고리')
    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name='products', 
                             verbose_name='매장', null=True, blank=True)
    # null=True로 설정하여 기존 데이터 호환성 유지
    barcode = models.CharField(max_length=100, blank=True, null=True, verbose_name='바코드')
    image = models.ImageField(upload_to='products/', blank=True, null=True, verbose_name='상품이미지')
    is_active = models.BooleanField(default=True, verbose_name='활성상태')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='등록일')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='수정일')
    
    class Meta:
        verbose_name = '상품'
        verbose_name_plural = '상품'
        ordering = ['code', 'name']
    
    def __str__(self):
        store_name = self.store.name if self.store else '전체'
        return f"{self.code} - {self.name} ({store_name})"
    
    def save(self, *args, **kwargs):
        # 카테고리에서 매장 정보 상속
        if self.category and self.category.store and not self.store:
            self.store = self.category.store
        super().save(*args, **kwargs)
    
    def get_current_price(self, date=None):
        """특정 날짜에 유효한 가격을 반환합니다."""
        if date is None:
            date = timezone.now().date()
        
        current_price = self.prices.filter(
            start_date__lte=date,
            end_date__gte=date
        ).first()
        
        if current_price:
            return current_price.price
        return None
    
    def get_current_stock(self, store=None):
        """특정 매장의 현재 재고를 반환합니다."""
        if store:
            try:
                stock = self.stocks.get(store=store)
                return stock.quantity
            except ProductStock.DoesNotExist:
                return 0
        
        # 모든 매장의 재고 합계 반환
        return sum(stock.quantity for stock in self.stocks.all())
    
class ProductOption(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='options', verbose_name='상품')
    name = models.CharField(max_length=100, verbose_name='옵션명')
    display_order = models.PositiveIntegerField(default=0, verbose_name='표시순서')
    is_required = models.BooleanField(default=False, verbose_name='필수여부')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='등록일')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='수정일')
    
    class Meta:
        verbose_name = '상품옵션'
        verbose_name_plural = '상품옵션'
        ordering = ['display_order', 'name']
        unique_together = ['product', 'name']
        
    def __str__(self):
        return f"{self.product.name} - {self.name}"

class ProductOptionValue(models.Model):
    option = models.ForeignKey(ProductOption, on_delete=models.CASCADE, related_name='values', verbose_name='옵션')
    value = models.CharField(max_length=100, verbose_name='옵션값')
    price_adjustment = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name='가격조정')
    display_order = models.PositiveIntegerField(default=0, verbose_name='표시순서')
    is_active = models.BooleanField(default=True, verbose_name='활성상태')
    
    class Meta:
        verbose_name = '옵션값'
        verbose_name_plural = '옵션값'
        ordering = ['display_order', 'value']
        unique_together = ['option', 'value']
        
    def __str__(self):
        price_info = f"({'+' if self.price_adjustment > 0 else ''}{self.price_adjustment})" if self.price_adjustment != 0 else ""
        return f"{self.option.name}: {self.value} {price_info}"
                
class ProductPrice(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='prices', verbose_name='상품')
    price = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)], verbose_name='판매가격')
    start_date = models.DateField(verbose_name='적용시작일')
    end_date = models.DateField(verbose_name='적용종료일')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='등록일')
    
    class Meta:
        verbose_name = '상품가격'
        verbose_name_plural = '상품가격'
        ordering = ['-start_date']
    
    def __str__(self):
        return f"{self.product.name} - {self.price} ({self.start_date} ~ {self.end_date})"

class ProductStock(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='stocks', verbose_name='상품')
    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name='product_stocks', verbose_name='매장')
    quantity = models.IntegerField(default=0, verbose_name='수량')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='갱신일')
    
    class Meta:
        verbose_name = '상품재고'
        verbose_name_plural = '상품재고'
        unique_together = ['product', 'store']
    
    def __str__(self):
        return f"{self.product.name} - {self.store.name}: {self.quantity}개"

class StockReceipt(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='receipts', verbose_name='상품')
    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name='stock_receipts', verbose_name='입고매장')
    quantity = models.IntegerField(validators=[MinValueValidator(1)], verbose_name='입고수량')
    cost_price = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)], verbose_name='매입가격')
    receipt_date = models.DateField(verbose_name='입고일')
    receipt_number = models.CharField(max_length=100, blank=True, null=True, verbose_name='입고번호')
    note = models.TextField(blank=True, null=True, verbose_name='비고')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_receipts', verbose_name='등록자')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='등록일')
    
    class Meta:
        verbose_name = '입고내역'
        verbose_name_plural = '입고내역'
        ordering = ['-receipt_date', '-created_at']
    
    def __str__(self):
        return f"{self.receipt_date} - {self.product.name}: {self.quantity}개 입고"
    
    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        
        # 재고 업데이트
        if is_new:
            stock, created = ProductStock.objects.get_or_create(
                product=self.product,
                store=self.store,
                defaults={'quantity': self.quantity}
            )
            if not created:
                stock.quantity += self.quantity
                stock.save()

class StockRelease(models.Model):
    RELEASE_TYPE_CHOICES = (
        ('sale', '판매'),
        ('return', '반품처리'),
        ('transfer', '이동'),
        ('damage', '파손'),
        ('expiry', '유통기한만료'),
        ('other', '기타'),
    )
    
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='releases', verbose_name='상품')
    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name='stock_releases', verbose_name='출고매장')
    quantity = models.IntegerField(validators=[MinValueValidator(1)], verbose_name='출고수량')
    release_type = models.CharField(max_length=20, choices=RELEASE_TYPE_CHOICES, verbose_name='출고유형')
    release_date = models.DateField(verbose_name='출고일')
    note = models.TextField(blank=True, null=True, verbose_name='비고')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_releases', verbose_name='등록자')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='등록일')
    
    class Meta:
        verbose_name = '출고내역'
        verbose_name_plural = '출고내역'
        ordering = ['-release_date', '-created_at']
    
    def __str__(self):
        return f"{self.release_date} - {self.product.name}: {self.quantity}개 출고 ({self.get_release_type_display()})"
    
    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        
        # 재고 업데이트
        if is_new:
            try:
                stock = ProductStock.objects.get(product=self.product, store=self.store)
                stock.quantity -= self.quantity
                stock.save()
            except ProductStock.DoesNotExist:
                # 재고가 없으면 마이너스 재고로 등록
                ProductStock.objects.create(
                    product=self.product,
                    store=self.store,
                    quantity=-self.quantity
                )

class StockAdjustment(models.Model):
    ADJUSTMENT_TYPE_CHOICES = (
        ('increase', '증가'),
        ('decrease', '감소'),
    )
    
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='adjustments', verbose_name='상품')
    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name='stock_adjustments', verbose_name='매장')
    quantity = models.IntegerField(validators=[MinValueValidator(1)], verbose_name='조정수량')
    adjustment_type = models.CharField(max_length=20, choices=ADJUSTMENT_TYPE_CHOICES, verbose_name='조정유형')
    adjustment_date = models.DateField(verbose_name='조정일')
    reason = models.TextField(verbose_name='조정사유')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_adjustments', verbose_name='등록자')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='등록일')
    
    class Meta:
        verbose_name = '재고조정'
        verbose_name_plural = '재고조정'
        ordering = ['-adjustment_date', '-created_at']
    
    def __str__(self):
        return f"{self.adjustment_date} - {self.product.name}: {self.quantity}개 {self.get_adjustment_type_display()}"
    
    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        
        # 재고 업데이트
        if is_new:
            stock, created = ProductStock.objects.get_or_create(
                product=self.product,
                store=self.store,
                defaults={'quantity': 0}
            )
            
            if self.adjustment_type == 'increase':
                stock.quantity += self.quantity
            else:  # decrease
                stock.quantity -= self.quantity
            
            stock.save()