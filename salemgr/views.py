from django.shortcuts import render
from django.utils import timezone
from django.db.models import Sum, Count, Q
from datetime import timedelta

from sales.models import Sale
from inventory.models import ProductStock
from returns.models import Return

def home(request):
    context = {}
    
    if request.user.is_authenticated and request.user.user_type in ['app_admin', 'store_manager', 'store_staff']:
        today = timezone.now().date()
        
        # 사용자 권한에 따른 필터링
        store_filter = {}
        if request.user.user_type != 'app_admin' and request.user.store:
            store_filter = {'store': request.user.store}
        
        # 오늘 판매 통계
        today_sales = Sale.objects.filter(
            sale_date__date=today,
            status='completed',
            **store_filter
        )
        
        context['sales_today'] = today_sales.count()
        context['sales_amount'] = today_sales.aggregate(
            total=Sum('final_amount')
        )['total'] or 0
        
        # 재고 현황
        stock_queryset = ProductStock.objects.filter(**store_filter)
        context['low_stock_count'] = stock_queryset.filter(
            quantity__gt=0, 
            quantity__lt=10
        ).count()
        context['out_of_stock_count'] = stock_queryset.filter(
            quantity__lte=0
        ).count()
        
        # 반품 현황
        returns_queryset = Return.objects.filter(**store_filter)
        context['pending_returns'] = returns_queryset.filter(
            status__in=['pending', 'approved']
        ).count()
        context['today_returns'] = returns_queryset.filter(
            return_date__date=today
        ).count()
    
    return render(request, 'home.html', context)