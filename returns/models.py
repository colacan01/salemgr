from django.db import models
from django.utils import timezone
from django.db.models.signals import post_save
from django.dispatch import receiver
from decimal import Decimal

from accounts.models import Store, User
from sales.models import Sale, SaleItem
from inventory.models import Product, StockReceipt

class Return(models.Model):
    """반품 헤더 정보"""
    RETURN_STATUS = (
        ('pending', '대기중'),
        ('approved', '승인됨'),
        ('rejected', '거부됨'),
        ('completed', '완료됨'),
    )
    
    REFUND_METHODS = (
        ('cash', '현금'),
        ('card', '카드'),
        ('account', '계좌이체'),
        ('point', '포인트'),
        ('exchange', '교환'),
        ('none', '환불 없음'),
    )
    
    return_number = models.CharField(max_length=20, unique=True, verbose_name='반품번호')
    sale = models.ForeignKey(Sale, on_delete=models.PROTECT, related_name='returns', verbose_name='원판매')
    return_date = models.DateTimeField(default=timezone.now, verbose_name='반품일시')
    store = models.ForeignKey(Store, on_delete=models.PROTECT, verbose_name='반품 매장')
    customer_name = models.CharField(max_length=100, blank=True, null=True, verbose_name='고객명')
    customer_phone = models.CharField(max_length=20, blank=True, null=True, verbose_name='고객 연락처')
    status = models.CharField(max_length=10, choices=RETURN_STATUS, default='pending', verbose_name='상태')
    refund_method = models.CharField(max_length=10, choices=REFUND_METHODS, default='card', verbose_name='환불 방식')
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name='총 환불 금액')
    reason = models.TextField(verbose_name='반품 사유')
    notes = models.TextField(blank=True, null=True, verbose_name='비고')
    
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name='created_returns', verbose_name='등록자')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='생성일시')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='수정일시')
    approved_by = models.ForeignKey(User, on_delete=models.PROTECT, null=True, blank=True, 
                                    related_name='approved_returns', verbose_name='승인자')
    approved_at = models.DateTimeField(null=True, blank=True, verbose_name='승인일시')
    
    class Meta:
        verbose_name = '반품'
        verbose_name_plural = '반품 내역'
        ordering = ['-return_date']
    
    def __str__(self):
        return f"{self.return_number} ({self.return_date.strftime('%Y-%m-%d')})"
    
    def save(self, *args, **kwargs):
        # 판매 정보에서 고객 정보 자동 설정 (비어있는 경우)
        if not self.customer_name and self.sale and self.sale.customer_name:
            self.customer_name = self.sale.customer_name
            
        if not self.customer_phone and self.sale and self.sale.customer_phone:
            self.customer_phone = self.sale.customer_phone
            
        # 먼저 모델 저장
        super().save(*args, **kwargs)
        
        # 환불 금액 자동 계산 (모델 저장 후 계산)
        if self.pk:  # 모델이 데이터베이스에 저장된 경우에만
            calculated_total = sum(item.refund_amount for item in self.returnitems.all())
            if self.total_amount != calculated_total:
                # 총액이 다를 경우에만 업데이트 (무한 재귀 방지)
                Return.objects.filter(pk=self.pk).update(total_amount=calculated_total)
                # 메모리상의 객체도 업데이트
                self.total_amount = calculated_total
    
    def get_item_count(self):
        """반품에 포함된 총 상품 종류 수"""
        return self.returnitems.count()
    
    def get_total_quantity(self):
        """반품에 포함된 총 상품 수량"""
        return self.returnitems.aggregate(total=models.Sum('quantity'))['total'] or 0
    
    def approve(self, user):
        """반품 승인 처리"""
        if self.status == 'pending':
            self.status = 'approved'
            self.approved_by = user
            self.approved_at = timezone.now()
            self.save()
            return True
        return False
    
    def reject(self, user, reason):
        """반품 거부 처리"""
        if self.status == 'pending':
            self.status = 'rejected'
            self.notes = f"{self.notes or ''}\n\n거부 사유: {reason}\n거부자: {user.username}"
            self.save()
            return True
        return False
    
    def complete(self):
        """반품 완료 처리"""
        if self.status == 'approved':
            self.status = 'completed'
            self.save()
            return True
        return False


class ReturnItem(models.Model):
    """반품된 개별 상품 정보"""
    RETURN_REASONS = (
        ('defect', '상품 결함'),
        ('wrong_item', '잘못된 상품'),
        ('not_as_described', '설명과 다름'),
        ('customer_request', '고객 요청'),
        ('expired', '유통기한 만료'),
        ('damaged', '배송 중 손상'),
        ('other', '기타'),
    )
    
    ITEM_CONDITIONS = (
        ('new', '미개봉'),
        ('opened', '개봉됨'),
        ('used', '사용됨'),
        ('damaged', '훼손됨'),
    )
    
    return_parent = models.ForeignKey(Return, on_delete=models.CASCADE, related_name='returnitems', verbose_name='반품')
    sale_item = models.ForeignKey(SaleItem, on_delete=models.PROTECT, verbose_name='판매 항목', null=True, blank=True)
    product = models.ForeignKey(Product, on_delete=models.PROTECT, verbose_name='상품')
    quantity = models.PositiveIntegerField(default=1, verbose_name='수량')
    price = models.DecimalField(max_digits=12, decimal_places=2, verbose_name='판매 가격')
    refund_amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name='환불 금액')
    return_reason = models.CharField(max_length=20, choices=RETURN_REASONS, verbose_name='반품 사유')
    condition = models.CharField(max_length=10, choices=ITEM_CONDITIONS, default='new', verbose_name='상품 상태')
    restock = models.BooleanField(default=True, verbose_name='재입고 여부')
    notes = models.TextField(blank=True, null=True, verbose_name='비고')
    
    class Meta:
        verbose_name = '반품 상품'
        verbose_name_plural = '반품 상품 내역'
    
    def __str__(self):
        return f"{self.product.name} ({self.quantity}개)"
    
    def save(self, *args, **kwargs):
        # 상품 정보 자동 설정
        if not self.product_id and self.sale_item:
            self.product = self.sale_item.product
            
        # 가격 정보 자동 설정
        if not self.price and self.sale_item:
            self.price = self.sale_item.price
            
        # 환불 금액 자동 계산 (판매 가격 * 수량)
        if not self.refund_amount:
            self.refund_amount = self.price * Decimal(self.quantity)
            
        super().save(*args, **kwargs)


# # 시그널을 사용하여 반품 승인 시 자동 입고 처리
# @receiver(post_save, sender=Return)
# def process_return_stock(sender, instance, **kwargs):
#     """반품 승인 시 재고 자동 처리"""
#     # 승인 상태가 되었을 때만 재고 처리
#     if instance.status == 'approved':
#         for return_item in instance.returnitems.all():
#             # 재입고 설정된 항목만 처리
#             if return_item.restock:
#                 # 재고 입고 처리
#                 StockReceipt.objects.create(
#                     product=return_item.product,
#                     store=instance.store,
#                     quantity=return_item.quantity,
#                     cost_price=return_item.price,
#                     receipt_date=instance.return_date.date(),
#                     note=f'반품번호: {instance.return_number}에 의한 자동 입고',
#                     created_by=instance.created_by
#                 )