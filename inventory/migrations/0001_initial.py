# Generated by Django 5.1.7 on 2025-03-18 14:49

import django.core.validators
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('accounts', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Category',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, verbose_name='카테고리명')),
                ('description', models.TextField(blank=True, null=True, verbose_name='설명')),
            ],
            options={
                'verbose_name': '카테고리',
                'verbose_name_plural': '카테고리',
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='Product',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code', models.CharField(max_length=50, unique=True, verbose_name='상품코드')),
                ('name', models.CharField(max_length=200, verbose_name='상품명')),
                ('description', models.TextField(blank=True, null=True, verbose_name='상품설명')),
                ('barcode', models.CharField(blank=True, max_length=100, null=True, verbose_name='바코드')),
                ('image', models.ImageField(blank=True, null=True, upload_to='products/', verbose_name='상품이미지')),
                ('is_active', models.BooleanField(default=True, verbose_name='활성상태')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='등록일')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='수정일')),
                ('category', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='products', to='inventory.category', verbose_name='카테고리')),
            ],
            options={
                'verbose_name': '상품',
                'verbose_name_plural': '상품',
                'ordering': ['code', 'name'],
            },
        ),
        migrations.CreateModel(
            name='ProductPrice',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('price', models.DecimalField(decimal_places=2, max_digits=12, validators=[django.core.validators.MinValueValidator(0)], verbose_name='판매가격')),
                ('start_date', models.DateField(verbose_name='적용시작일')),
                ('end_date', models.DateField(verbose_name='적용종료일')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='등록일')),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='prices', to='inventory.product', verbose_name='상품')),
            ],
            options={
                'verbose_name': '상품가격',
                'verbose_name_plural': '상품가격',
                'ordering': ['-start_date'],
            },
        ),
        migrations.CreateModel(
            name='StockAdjustment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('quantity', models.IntegerField(validators=[django.core.validators.MinValueValidator(1)], verbose_name='조정수량')),
                ('adjustment_type', models.CharField(choices=[('increase', '증가'), ('decrease', '감소')], max_length=20, verbose_name='조정유형')),
                ('adjustment_date', models.DateField(verbose_name='조정일')),
                ('reason', models.TextField(verbose_name='조정사유')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='등록일')),
                ('created_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='created_adjustments', to=settings.AUTH_USER_MODEL, verbose_name='등록자')),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='adjustments', to='inventory.product', verbose_name='상품')),
                ('store', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='stock_adjustments', to='accounts.store', verbose_name='매장')),
            ],
            options={
                'verbose_name': '재고조정',
                'verbose_name_plural': '재고조정',
                'ordering': ['-adjustment_date', '-created_at'],
            },
        ),
        migrations.CreateModel(
            name='StockReceipt',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('quantity', models.IntegerField(validators=[django.core.validators.MinValueValidator(1)], verbose_name='입고수량')),
                ('cost_price', models.DecimalField(decimal_places=2, max_digits=12, validators=[django.core.validators.MinValueValidator(0)], verbose_name='매입가격')),
                ('receipt_date', models.DateField(verbose_name='입고일')),
                ('receipt_number', models.CharField(blank=True, max_length=100, null=True, verbose_name='입고번호')),
                ('note', models.TextField(blank=True, null=True, verbose_name='비고')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='등록일')),
                ('created_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='created_receipts', to=settings.AUTH_USER_MODEL, verbose_name='등록자')),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='receipts', to='inventory.product', verbose_name='상품')),
                ('store', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='stock_receipts', to='accounts.store', verbose_name='입고매장')),
            ],
            options={
                'verbose_name': '입고내역',
                'verbose_name_plural': '입고내역',
                'ordering': ['-receipt_date', '-created_at'],
            },
        ),
        migrations.CreateModel(
            name='StockRelease',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('quantity', models.IntegerField(validators=[django.core.validators.MinValueValidator(1)], verbose_name='출고수량')),
                ('release_type', models.CharField(choices=[('sale', '판매'), ('return', '반품처리'), ('transfer', '이동'), ('damage', '파손'), ('expiry', '유통기한만료'), ('other', '기타')], max_length=20, verbose_name='출고유형')),
                ('release_date', models.DateField(verbose_name='출고일')),
                ('note', models.TextField(blank=True, null=True, verbose_name='비고')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='등록일')),
                ('created_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='created_releases', to=settings.AUTH_USER_MODEL, verbose_name='등록자')),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='releases', to='inventory.product', verbose_name='상품')),
                ('store', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='stock_releases', to='accounts.store', verbose_name='출고매장')),
            ],
            options={
                'verbose_name': '출고내역',
                'verbose_name_plural': '출고내역',
                'ordering': ['-release_date', '-created_at'],
            },
        ),
        migrations.CreateModel(
            name='ProductStock',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('quantity', models.IntegerField(default=0, verbose_name='수량')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='갱신일')),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='stocks', to='inventory.product', verbose_name='상품')),
                ('store', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='product_stocks', to='accounts.store', verbose_name='매장')),
            ],
            options={
                'verbose_name': '상품재고',
                'verbose_name_plural': '상품재고',
                'unique_together': {('product', 'store')},
            },
        ),
    ]
