from django.db import models
from django.utils import timezone
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from decimal import Decimal

from accounts.models import Store, User
from inventory.models import Product, StockRelease

class Sale(models.Model):
    """판매 기록의 헤더 정보"""
    PAYMENT_METHODS = (
        ('cash', '현금'),
        ('card', '카드'),
        ('transfer', '계좌이체'),
        ('mobile', '모바일 결제'),
        ('mixed', '복합 결제'),
    )
    
    SALE_STATUS = (
        ('pending', '진행중'),
        ('completed', '완료됨'),
        ('cancelled', '취소됨'),
        ('refunded', '환불됨'),
    )
    
    sale_number = models.CharField(max_length=20, unique=True, verbose_name='판매번호')
    sale_date = models.DateTimeField(default=timezone.now, verbose_name='판매일시')
    store = models.ForeignKey(Store, on_delete=models.PROTECT, verbose_name='판매 매장')
    customer_name = models.CharField(max_length=100, blank=True, null=True, verbose_name='고객명')
    customer_phone = models.CharField(max_length=20, blank=True, null=True, verbose_name='고객 연락처')
    payment_method = models.CharField(max_length=10, choices=PAYMENT_METHODS, default='card', verbose_name='결제 방식')
    status = models.CharField(max_length=10, choices=SALE_STATUS, default='completed', verbose_name='상태')
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name='총 금액')
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name='할인 금액')
    final_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name='최종 결제액')
    notes = models.TextField(blank=True, null=True, verbose_name='비고')
    
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name='created_sales', verbose_name='등록자')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='생성일시')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='수정일시')
    
    class Meta:
        verbose_name = '판매'
        verbose_name_plural = '판매 내역'
        ordering = ['-sale_date']
    
    def __str__(self):
        return f"{self.sale_number} ({self.sale_date.strftime('%Y-%m-%d')})"
    
    def save(self, *args, **kwargs):
        # 최종 금액 자동 계산
        if not self.final_amount:
            self.final_amount = self.total_amount - self.discount_amount
        super().save(*args, **kwargs)
    
    def get_item_count(self):
        """판매에 포함된 총 상품 종류 수"""
        return self.saleitems.count()
    
    def get_total_quantity(self):
        """판매에 포함된 총 상품 수량"""
        return self.saleitems.aggregate(total=models.Sum('quantity'))['total'] or 0
    
    def can_be_cancelled(self):
        """판매 취소 가능 여부 체크"""
        # 판매일로부터 7일 이내에만 취소 가능
        return (timezone.now() - self.sale_date).days <= 7 and self.status == 'completed'


class SaleItem(models.Model):
    """판매된 개별 상품 정보"""
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name='saleitems', verbose_name='판매')
    product = models.ForeignKey(Product, on_delete=models.PROTECT, verbose_name='상품')
    quantity = models.PositiveIntegerField(default=1, verbose_name='수량')
    price = models.DecimalField(max_digits=12, decimal_places=2, verbose_name='판매 가격')
    discount = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name='할인액')
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, verbose_name='소계')
    
    class Meta:
        verbose_name = '판매 상품'
        verbose_name_plural = '판매 상품 내역'
    
    def __str__(self):
        return f"{self.product.name} ({self.quantity}개)"
    
    def save(self, *args, **kwargs):
        # 소계 자동 계산
        if not self.subtotal:
            self.subtotal = (self.price * Decimal(self.quantity)) - self.discount
        super().save(*args, **kwargs)


class Payment(models.Model):
    """판매에 대한 결제 정보"""
    PAYMENT_TYPES = (
        ('cash', '현금'),
        ('card', '신용카드'),
        ('card_installment', '카드 할부'),
        ('mobile', '모바일 결제'),
        ('transfer', '계좌이체'),
        ('gift_card', '상품권'),
        ('point', '포인트'),
        ('other', '기타'),
    )
    
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name='payments', verbose_name='판매')
    payment_type = models.CharField(max_length=20, choices=PAYMENT_TYPES, verbose_name='결제 유형')
    amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name='결제 금액')
    payment_details = models.CharField(max_length=255, blank=True, null=True, verbose_name='결제 상세 정보')
    payment_date = models.DateTimeField(default=timezone.now, verbose_name='결제일시')
    
    class Meta:
        verbose_name = '결제 정보'
        verbose_name_plural = '결제 정보 내역'
    
    def __str__(self):
        return f"{self.get_payment_type_display()} - {self.amount}"


# 시그널을 사용하여 판매 시 재고 자동 조정
@receiver(post_save, sender=SaleItem)
def adjust_stock_on_sale(sender, instance, created, **kwargs):
    """판매 상품이 저장될 때 재고 자동 감소"""
    if created and instance.sale.status == 'completed':
        # 판매로 인한 출고 내역 생성
        StockRelease.objects.create(
            product=instance.product,
            store=instance.sale.store,
            quantity=instance.quantity,
            release_type='sale',
            release_date=instance.sale.sale_date.date(),
            note=f'판매번호: {instance.sale.sale_number}에 의한 자동 출고',
            created_by=instance.sale.created_by
        )

@receiver(post_save, sender=Sale)
def update_stock_on_sale_status_change(sender, instance, **kwargs):
    """판매 상태 변경 시 재고 조정"""
    if instance.status == 'cancelled' or instance.status == 'refunded':
        # 취소 또는 환불된 경우, 각 상품의 출고 내역을 찾아 관련 재고를 조정
        for item in instance.saleitems.all():
            # 해당 판매에 연결된 출고 기록을 찾아서
            release_note = f'판매번호: {instance.sale_number}에 의한 자동 출고'
            stock_releases = StockRelease.objects.filter(
                product=item.product,
                store=instance.store,
                note__contains=release_note
            )
            
            # 각 출고 기록을 취소 처리 (이 부분은 실제 비즈니스 로직에 맞게 구현 필요)
            for release in stock_releases:
                if instance.status == 'cancelled':
                    release.delete()  # 취소 시 출고 기록 삭제
                elif instance.status == 'refunded':
                    # 환불 시, 환불 사유로 입고 처리 (선택적 구현)
                    from inventory.models import StockReceipt
                    StockReceipt.objects.create(
                        product=item.product,
                        store=instance.store,
                        quantity=item.quantity,
                        cost_price=item.price,
                        receipt_date=timezone.now().date(),
                        note=f'판매번호: {instance.sale_number} 환불에 의한 자동 입고',
                        created_by=instance.created_by
                    )