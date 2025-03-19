# Generated by Django 5.1.7 on 2025-03-18 14:44

import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('accounts', '0001_initial'),
        ('inventory', '__first__'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Sale',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('sale_number', models.CharField(max_length=20, unique=True, verbose_name='판매번호')),
                ('sale_date', models.DateTimeField(default=django.utils.timezone.now, verbose_name='판매일시')),
                ('customer_name', models.CharField(blank=True, max_length=100, null=True, verbose_name='고객명')),
                ('customer_phone', models.CharField(blank=True, max_length=20, null=True, verbose_name='고객 연락처')),
                ('payment_method', models.CharField(choices=[('cash', '현금'), ('card', '카드'), ('transfer', '계좌이체'), ('mobile', '모바일 결제'), ('mixed', '복합 결제')], default='card', max_length=10, verbose_name='결제 방식')),
                ('status', models.CharField(choices=[('pending', '진행중'), ('completed', '완료됨'), ('cancelled', '취소됨'), ('refunded', '환불됨')], default='completed', max_length=10, verbose_name='상태')),
                ('total_amount', models.DecimalField(decimal_places=2, default=0, max_digits=12, verbose_name='총 금액')),
                ('discount_amount', models.DecimalField(decimal_places=2, default=0, max_digits=12, verbose_name='할인 금액')),
                ('final_amount', models.DecimalField(decimal_places=2, default=0, max_digits=12, verbose_name='최종 결제액')),
                ('notes', models.TextField(blank=True, null=True, verbose_name='비고')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='생성일시')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='수정일시')),
                ('created_by', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='created_sales', to=settings.AUTH_USER_MODEL, verbose_name='등록자')),
                ('store', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='accounts.store', verbose_name='판매 매장')),
            ],
            options={
                'verbose_name': '판매',
                'verbose_name_plural': '판매 내역',
                'ordering': ['-sale_date'],
            },
        ),
        migrations.CreateModel(
            name='Payment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('payment_type', models.CharField(choices=[('cash', '현금'), ('card', '신용카드'), ('card_installment', '카드 할부'), ('mobile', '모바일 결제'), ('transfer', '계좌이체'), ('gift_card', '상품권'), ('point', '포인트'), ('other', '기타')], max_length=20, verbose_name='결제 유형')),
                ('amount', models.DecimalField(decimal_places=2, max_digits=12, verbose_name='결제 금액')),
                ('payment_details', models.CharField(blank=True, max_length=255, null=True, verbose_name='결제 상세 정보')),
                ('payment_date', models.DateTimeField(default=django.utils.timezone.now, verbose_name='결제일시')),
                ('sale', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='payments', to='sales.sale', verbose_name='판매')),
            ],
            options={
                'verbose_name': '결제 정보',
                'verbose_name_plural': '결제 정보 내역',
            },
        ),
        migrations.CreateModel(
            name='SaleItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('quantity', models.PositiveIntegerField(default=1, verbose_name='수량')),
                ('price', models.DecimalField(decimal_places=2, max_digits=12, verbose_name='판매 가격')),
                ('discount', models.DecimalField(decimal_places=2, default=0, max_digits=12, verbose_name='할인액')),
                ('subtotal', models.DecimalField(decimal_places=2, max_digits=12, verbose_name='소계')),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='inventory.product', verbose_name='상품')),
                ('sale', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='saleitems', to='sales.sale', verbose_name='판매')),
            ],
            options={
                'verbose_name': '판매 상품',
                'verbose_name_plural': '판매 상품 내역',
            },
        ),
    ]
