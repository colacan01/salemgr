from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy, reverse
from django.contrib import messages
from django.utils import timezone
from django.http import JsonResponse
from django.db import transaction
from django.db.models import Sum, F, Q
from decimal import Decimal
import json

from accounts.permissions import StoreStaffRequiredMixin, StoreManagerRequiredMixin
from inventory.models import Product, ProductPrice
from .models import Sale, SaleItem, Payment
from .forms import SaleForm, SaleItemForm, PaymentFormSet, SaleItemFormSet
from accounts.models import Store  # Store 모델을 import 해야 합니다

class SaleListView(StoreStaffRequiredMixin, ListView):
    model = Sale
    template_name = 'sales/sale_list.html'
    context_object_name = 'sales'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # 검색 필터링
        search_query = self.request.GET.get('search', '')
        if search_query:
            queryset = queryset.filter(
                Q(sale_number__icontains=search_query) |
                Q(customer_name__icontains=search_query) |
                Q(customer_phone__icontains=search_query)
            )
        
        # 앱 관리자가 아닌 경우 기본적으로 자신의 매장으로 필터링
        if self.request.user.user_type != 'app_admin':
            queryset = queryset.filter(store=self.request.user.store)
        
        # 매장 필터링 (앱 관리자만 사용 가능)
        if self.request.user.user_type == 'app_admin':
            store_id = self.request.GET.get('store')
            if store_id:
                queryset = queryset.filter(store_id=store_id)
        
        # 상태 필터링
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)
        
        # 날짜 범위 필터링
        start_date = self.request.GET.get('start_date')
        end_date = self.request.GET.get('end_date')
        
        if start_date:
            queryset = queryset.filter(sale_date__gte=start_date)
        if end_date:
            queryset = queryset.filter(sale_date__lte=end_date + ' 23:59:59')
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('search', '')
        context['selected_status'] = self.request.GET.get('status', '')
        context['start_date'] = self.request.GET.get('start_date', '')
        context['end_date'] = self.request.GET.get('end_date', '')
        
        # 매장 정보 컨텍스트에 추가
        if self.request.user.user_type == 'app_admin':
            context['selected_store'] = self.request.GET.get('store', '')
            context['is_admin'] = True
            # 앱 관리자에게는 모든 매장 목록을 제공
            context['available_stores'] = Store.objects.order_by('name')
        else:
            # 일반 사용자는 자신의 매장만 볼 수 있음
            context['selected_store'] = self.request.user.store.id if self.request.user.store else None
            context['user_store_name'] = self.request.user.store.name if self.request.user.store else '지정되지 않음'
            context['is_admin'] = False
        
        # 페이지의 판매 총액 계산
        context['total_sales_amount'] = self.get_queryset().aggregate(
            total=Sum('final_amount')
        )['total'] or 0
        
        return context


class SaleDetailView(StoreStaffRequiredMixin, DetailView):
    model = Sale
    template_name = 'sales/sale_detail.html'
    context_object_name = 'sale'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['items'] = self.object.saleitems.all()
        context['payments'] = self.object.payments.all()
        return context


class SaleCreateView(StoreStaffRequiredMixin, CreateView):
    model = Sale
    form_class = SaleForm
    template_name = 'sales/sale_form.html'
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        if self.request.POST:
            context['item_formset'] = SaleItemFormSet(
                self.request.POST, instance=self.object,
                user=self.request.user  # user 파라미터 전달
            )
            context['payment_formset'] = PaymentFormSet(
                self.request.POST, instance=self.object
            )
        else:
            context['item_formset'] = SaleItemFormSet(
                instance=self.object,
                user=self.request.user  # user 파라미터 전달
            )
            context['payment_formset'] = PaymentFormSet(
                instance=self.object
            )
        
        # 상품 목록 필터링 (기존 코드 유지)
        if self.request.user.user_type == 'app_admin':
            context['products'] = Product.objects.filter(is_active=True)
        else:
            context['products'] = Product.objects.filter(
                Q(store=self.request.user.store) | Q(store__isnull=True),
                is_active=True
            )
        
        return context
    
    def form_valid(self, form):
        context = self.get_context_data()
        item_formset = context['item_formset']
        payment_formset = context['payment_formset']
        
        if not item_formset.is_valid() or not payment_formset.is_valid():
            return self.form_invalid(form)
        
        with transaction.atomic():
            form.instance.created_by = self.request.user
            
            # 판매번호 자동 생성 (YYYYMMDDxxxx 형식)
            today = timezone.now().strftime('%Y%m%d')
            last_sale = Sale.objects.filter(sale_number__startswith=today).order_by('-sale_number').first()
            
            if last_sale:
                last_num = int(last_sale.sale_number[8:])
                form.instance.sale_number = f"{today}{last_num+1:04d}"
            else:
                form.instance.sale_number = f"{today}0001"
            
            self.object = form.save()
            
            # 판매 항목과 총액 계산
            total_amount = Decimal('0')
            for item_form in item_formset:
                if item_form.is_valid() and item_form.cleaned_data and not item_form.cleaned_data.get('DELETE', False):
                    item = item_form.save(commit=False)
                    # 소계 계산
                    # item.subtotal = (item.price * Decimal(item.quantity)) - item.discount
                    item.subtotal = (item.price * Decimal(item.quantity))
                    total_amount += item.subtotal
            
            self.object.total_amount = total_amount
            self.object.final_amount = total_amount - self.object.discount_amount
            self.object.save()
            
            item_formset.instance = self.object
            item_formset.save()
            
            # 결제 정보 처리
            payment_formset.instance = self.object
            payment_formset.save()
            
            messages.success(self.request, f'판매번호 {self.object.sale_number}가 성공적으로 등록되었습니다.')
            return super().form_valid(form)
    
    def get_success_url(self):
        return reverse('sales:sale_detail', kwargs={'pk': self.object.pk})


class SaleUpdateView(StoreManagerRequiredMixin, UpdateView):
    model = Sale
    form_class = SaleForm
    template_name = 'sales/sale_form.html'
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        if self.request.POST:
            context['item_formset'] = SaleItemFormSet(
                self.request.POST, instance=self.object,
                user=self.request.user  # user 파라미터 전달
            )
            context['payment_formset'] = PaymentFormSet(
                self.request.POST, instance=self.object
            )
        else:
            context['item_formset'] = SaleItemFormSet(
                instance=self.object,
                user=self.request.user  # user 파라미터 전달
            )
            context['payment_formset'] = PaymentFormSet(
                instance=self.object
            )
        
        # 상품 목록 필터링 (기존 코드 유지)
        if self.request.user.user_type == 'app_admin':
            context['products'] = Product.objects.filter(is_active=True)
        else:
            context['products'] = Product.objects.filter(
                Q(store=self.request.user.store) | Q(store__isnull=True),
                is_active=True
            )
        
        context['is_update'] = True
        return context
    
    def form_valid(self, form):
        context = self.get_context_data()
        item_formset = context['item_formset']
        payment_formset = context['payment_formset']
        
        if not item_formset.is_valid() or not payment_formset.is_valid():
            return self.form_invalid(form)
        
        with transaction.atomic():
            # 기존 상품의 재고를 원복하고, 새로운 판매에 맞게 재조정 필요
            # 실제 구현은 비즈니스 요구사항에 맞게 조정 필요
            
            self.object = form.save()
            
            # 판매 항목과 총액 계산
            total_amount = Decimal('0')
            
            # 삭제된 항목 처리
            for item_form in item_formset.deleted_forms:
                if item_form.instance.pk:
                    item_form.instance.delete()
            
            # 기존 및 새 항목 처리
            for item_form in item_formset:
                if item_form.is_valid() and item_form.cleaned_data and not item_form.cleaned_data.get('DELETE', False):
                    item = item_form.save(commit=False)
                    # 소계 계산
                    item.subtotal = (item.price * Decimal(item.quantity))
                    item.sale = self.object
                    item.save()
                    total_amount += item.subtotal
            
            self.object.total_amount = total_amount
            self.object.final_amount = total_amount - self.object.discount_amount
            self.object.save()
            
            # 결제 정보 처리
            payment_formset.instance = self.object
            payment_formset.save()
            
            messages.success(self.request, f'판매번호 {self.object.sale_number}가 성공적으로 수정되었습니다.')
            return super().form_valid(form)
        
        return self.form_invalid(form)
    
    def get_success_url(self):
        return reverse('sales:sale_detail', kwargs={'pk': self.object.pk})


class SaleDeleteView(StoreManagerRequiredMixin, DeleteView):
    model = Sale
    template_name = 'sales/sale_confirm_delete.html'
    success_url = reverse_lazy('sales:sale_list')
    
    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        success_url = self.get_success_url()
        
        # 판매 삭제 전 관련 재고 처리
        # 실제 구현은 비즈니스 로직에 맞게 조정 필요
        
        self.object.delete()
        messages.success(request, "판매 내역이 성공적으로 삭제되었습니다.")
        return redirect(success_url)


class SaleCancelView(StoreManagerRequiredMixin, UpdateView):
    model = Sale
    template_name = 'sales/sale_cancel_form.html'
    fields = ['notes']
    
    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        
        if not self.object.can_be_cancelled():
            messages.error(request, "이 판매는 취소할 수 없습니다.")
            return redirect('sales:sale_detail', pk=self.object.pk)
        
        self.object.status = 'cancelled'
        self.object.notes = f"{self.object.notes or ''}\n\n취소 사유: {request.POST.get('notes', '')}"
        self.object.save()
        
        messages.success(request, f"판매번호 {self.object.sale_number}가 성공적으로 취소되었습니다.")
        return redirect('sales:sale_detail', pk=self.object.pk)


# AJAX 요청 처리를 위한 뷰
def get_product_info(request):
    """상품 정보를 JSON으로 반환하는 API"""
    product_id = request.GET.get('product_id')
    
    if not product_id:
        return JsonResponse({'error': '상품 ID가 필요합니다.'}, status=400)
    
    try:
        # 사용자 권한에 따라 액세스 제한
        user = request.user
        if user.user_type == 'app_admin':
            product = Product.objects.get(id=product_id, is_active=True)
        else:
            product = Product.objects.get(
                Q(store=user.store) | Q(store__isnull=True),
                id=product_id,
                is_active=True
            )
            
        price = product.get_current_price() or 0
        
        return JsonResponse({
            'id': product.id,
            'name': product.name,
            'code': product.code,
            'price': float(price),
            'store': product.store.name if product.store else '전체'
        })
    except Product.DoesNotExist:
        return JsonResponse({'error': '상품을 찾을 수 없습니다.'}, status=404)


def sales_dashboard(request):
    """판매 대시보드 뷰"""
    today = timezone.now().date()
    start_date = request.GET.get('start_date', (today - timezone.timedelta(days=30)).isoformat())
    end_date = request.GET.get('end_date', today.isoformat())
    
    # 사용자 권한에 따른 필터링 적용
    sales_filter = {
        'sale_date__date__gte': start_date,
        'sale_date__date__lte': end_date,
        'status': 'completed'
    }
    
    # 앱 관리자가 아닌 경우 해당 매장 데이터만 표시
    if request.user.user_type != 'app_admin':
        sales_filter['store'] = request.user.store
    
    # 날짜 범위 내 일별 판매액
    daily_sales = Sale.objects.filter(
        **sales_filter
    ).values('sale_date__date').annotate(
        total=Sum('final_amount')
    ).order_by('sale_date__date')
    
    # JSON 직렬화를 위해 데이터 변환
    daily_sales_json = []
    for entry in daily_sales:
        daily_sales_json.append({
            'sale_date__date': entry['sale_date__date'].strftime('%Y-%m-%d'),
            'total': float(entry['total']) if entry['total'] else 0
        })
    
    # 매장별 판매액 (앱 관리자만 다양한 매장 확인 가능)
    if request.user.user_type == 'app_admin':
        store_sales = Sale.objects.filter(
            **sales_filter
        ).values('store__name').annotate(
            total=Sum('final_amount')
        ).order_by('-total')
        store_sales_table = store_sales
    else:
        # 일반 사용자는 자기 매장만 표시
        store_sales = Sale.objects.filter(
            **sales_filter
        ).values('store__name').annotate(
            total=Sum('final_amount')
        )
        store_sales_table = store_sales
        
    
    # JSON 직렬화를 위해 매장별 판매 데이터 변환
    store_sales_json = []
    for entry in store_sales:
        store_sales_json.append({
            'store__name': entry['store__name'],
            'total': float(entry['total']) if entry['total'] else 0
        })
    
    # 상품별 판매량에 매장 필터 적용
    items_filter = {
        'sale__sale_date__date__gte': start_date,
        'sale__sale_date__date__lte': end_date,
        'sale__status': 'completed'
    }
    
    if request.user.user_type != 'app_admin':
        items_filter['sale__store'] = request.user.store
    
    # 상품별 판매량
    product_sales = SaleItem.objects.filter(
        **items_filter
    ).values('product__name').annotate(
        quantity=Sum('quantity'),
        total=Sum('subtotal')
    ).order_by('-quantity')[:10]
    
    total_sales = Sale.objects.filter(**sales_filter).aggregate(total=Sum('final_amount'))['total'] or 0
    
    context = {
        'daily_sales': json.dumps(daily_sales_json),
        'store_sales': json.dumps(store_sales_json),
        'store_sales_table': list(store_sales_table),
        'product_sales': list(product_sales),
        'start_date': start_date,
        'end_date': end_date,
        'total_sales': total_sales,
        'total_sales_count': Sale.objects.filter(
            **sales_filter
        ).count(),
        'user_store': request.user.store.name if hasattr(request.user, 'store') and request.user.store else '전체',
        'is_admin': request.user.user_type == 'app_admin'
    }
    
    return render(request, 'sales/dashboard.html', context)