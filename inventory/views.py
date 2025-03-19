from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib import messages
from django.db import models
from django.db.models import Sum, Q, F
from django.utils import timezone
from django.http import JsonResponse

from accounts.permissions import StoreStaffRequiredMixin, StoreManagerRequiredMixin
from .models import (
    Category, Product, ProductPrice, ProductStock,
    StockReceipt, StockRelease, StockAdjustment
)
from .forms import (
    CategoryForm, ProductForm, ProductPriceForm, 
    StockReceiptForm, StockReleaseForm, StockAdjustmentForm
)

# 카테고리 관리
class CategoryListView(StoreStaffRequiredMixin, ListView):
    model = Category
    template_name = 'inventory/category_list.html'
    context_object_name = 'categories'
    paginate_by = 10
    
    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        
        # 앱 관리자는 모든 카테고리 조회 가능
        if user.user_type == 'app_admin':
            return queryset
        
        # 매장 관리자/직원은 자신의 매장 카테고리와 전체 매장 카테고리 조회 가능
        return queryset.filter(
            models.Q(store=user.store) | models.Q(store__isnull=True)
        )

class CategoryCreateView(StoreManagerRequiredMixin, CreateView):
    model = Category
    form_class = CategoryForm
    template_name = 'inventory/category_form.html'
    success_url = reverse_lazy('inventory:category_list')
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        # 매장 관리자/직원인 경우 자동으로 매장 설정
        if self.request.user.user_type in ['store_manager', 'store_staff'] and not form.instance.store:
            form.instance.store = self.request.user.store
            
        messages.success(self.request, '카테고리가 생성되었습니다.')
        return super().form_valid(form)

class CategoryUpdateView(StoreManagerRequiredMixin, UpdateView):
    model = Category
    form_class = CategoryForm
    template_name = 'inventory/category_form.html'
    success_url = reverse_lazy('inventory:category_list')
    
    def form_valid(self, form):
        messages.success(self.request, '카테고리가 수정되었습니다.')
        return super().form_valid(form)

class CategoryDeleteView(StoreManagerRequiredMixin, DeleteView):
    model = Category
    template_name = 'inventory/category_confirm_delete.html'
    success_url = reverse_lazy('inventory:category_list')
    
    def delete(self, request, *args, **kwargs):
        messages.success(self.request, '카테고리가 삭제되었습니다.')
        return super().delete(request, *args, **kwargs)

# 상품 관리
class ProductListView(StoreStaffRequiredMixin, ListView):
    model = Product
    template_name = 'inventory/product_list.html'
    context_object_name = 'products'
    paginate_by = 10
    
    def get_queryset(self):
        queryset = super().get_queryset()
        search_query = self.request.GET.get('search', '')
        category_id = self.request.GET.get('category', '')
        user = self.request.user
        
        # 검색어 필터링
        if search_query:
            queryset = queryset.filter(
                models.Q(name__icontains=search_query) |
                models.Q(code__icontains=search_query) |
                models.Q(barcode__icontains=search_query)
            )
        
        # 카테고리 필터링
        if category_id:
            queryset = queryset.filter(category_id=category_id)
        
        # 매장 필터링 - 앱 관리자는 모든 상품 조회 가능
        if user.user_type != 'app_admin':
            # 매장 관리자/직원은 자신의 매장 상품과 전체 매장 상품 조회 가능
            queryset = queryset.filter(
                models.Q(store=user.store) | models.Q(store__isnull=True)
            )
            
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # 사용자 권한에 따른 카테고리 목록 필터링
        if user.user_type == 'app_admin':
            context['categories'] = Category.objects.all()
        else:
            context['categories'] = Category.objects.filter(
                models.Q(store=user.store) | models.Q(store__isnull=True)
            )
            
        context['search_query'] = self.request.GET.get('search', '')
        context['selected_category'] = self.request.GET.get('category', '')
        return context

class ProductDetailView(StoreStaffRequiredMixin, DetailView):
    model = Product
    template_name = 'inventory/product_detail.html'
    context_object_name = 'product'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        product = self.get_object()
        
        # 현재 가격 및 가격 히스토리
        context['current_price'] = product.get_current_price()
        context['price_history'] = product.prices.all().order_by('-start_date')
        
        # 매장별 재고
        context['stocks'] = product.stocks.all()
        
        # 최근 입고 및 출고 내역
        context['recent_receipts'] = product.receipts.all().order_by('-receipt_date')[:5]
        context['recent_releases'] = product.releases.all().order_by('-release_date')[:5]
        
        return context

class ProductCreateView(StoreManagerRequiredMixin, CreateView):
    model = Product
    form_class = ProductForm
    template_name = 'inventory/product_form.html'
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        # 매장 관리자/직원인 경우 자동으로 매장 설정
        if self.request.user.user_type in ['store_manager', 'store_staff'] and not form.instance.store:
            form.instance.store = self.request.user.store
            
        messages.success(self.request, '상품이 생성되었습니다.')
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse_lazy('inventory:product_detail', kwargs={'pk': self.object.pk})

class ProductUpdateView(StoreManagerRequiredMixin, UpdateView):
    model = Product
    form_class = ProductForm
    template_name = 'inventory/product_form.html'
    
    def form_valid(self, form):
        messages.success(self.request, '상품 정보가 수정되었습니다.')
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse_lazy('inventory:product_detail', kwargs={'pk': self.object.pk})

class ProductDeleteView(StoreManagerRequiredMixin, DeleteView):
    model = Product
    template_name = 'inventory/product_confirm_delete.html'
    success_url = reverse_lazy('inventory:product_list')
    
    def delete(self, request, *args, **kwargs):
        messages.success(self.request, '상품이 삭제되었습니다.')
        return super().delete(request, *args, **kwargs)

# 상품 가격 관리
class ProductPriceCreateView(StoreManagerRequiredMixin, CreateView):
    model = ProductPrice
    form_class = ProductPriceForm
    template_name = 'inventory/product_price_form.html'
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['product'] = get_object_or_404(Product, pk=self.kwargs['product_pk'])
        return kwargs
    
    def form_valid(self, form):
        form.instance.product = get_object_or_404(Product, pk=self.kwargs['product_pk'])
        messages.success(self.request, '상품 가격이 등록되었습니다.')
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse_lazy('inventory:product_detail', kwargs={'pk': self.kwargs['product_pk']})
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['product'] = get_object_or_404(Product, pk=self.kwargs['product_pk'])
        return context

class ProductPriceUpdateView(StoreManagerRequiredMixin, UpdateView):
    model = ProductPrice
    form_class = ProductPriceForm
    template_name = 'inventory/product_price_form.html'
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['product'] = self.object.product
        return kwargs
    
    def form_valid(self, form):
        messages.success(self.request, '상품 가격이 수정되었습니다.')
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse_lazy('inventory:product_detail', kwargs={'pk': self.object.product.pk})
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['product'] = self.object.product
        return context

class ProductPriceDeleteView(StoreManagerRequiredMixin, DeleteView):
    model = ProductPrice
    template_name = 'inventory/product_price_confirm_delete.html'
    
    def get_success_url(self):
        return reverse_lazy('inventory:product_detail', kwargs={'pk': self.object.product.pk})
    
    def delete(self, request, *args, **kwargs):
        price = self.get_object()
        product_id = price.product.pk
        messages.success(self.request, '상품 가격이 삭제되었습니다.')
        return super().delete(request, *args, **kwargs)

# 입고 관리
class StockReceiptListView(StoreStaffRequiredMixin, ListView):
    model = StockReceipt
    template_name = 'inventory/stock_receipt_list.html'
    context_object_name = 'receipts'
    paginate_by = 10
    
    def get_queryset(self):
        queryset = super().get_queryset()
        search_query = self.request.GET.get('search', '')
        start_date = self.request.GET.get('start_date', '')
        end_date = self.request.GET.get('end_date', '')
        store_id = self.request.GET.get('store', '')
        
        if search_query:
            queryset = queryset.filter(
                Q(product__name__icontains=search_query) |
                Q(product__code__icontains=search_query) |
                Q(receipt_number__icontains=search_query)
            )
        
        if start_date:
            queryset = queryset.filter(receipt_date__gte=start_date)
            
        if end_date:
            queryset = queryset.filter(receipt_date__lte=end_date)
            
        if store_id:
            queryset = queryset.filter(store_id=store_id)
            
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from accounts.models import Store
        context['stores'] = Store.objects.all()
        context['search_query'] = self.request.GET.get('search', '')
        context['start_date'] = self.request.GET.get('start_date', '')
        context['end_date'] = self.request.GET.get('end_date', '')
        context['selected_store'] = self.request.GET.get('store', '')
        return context

class StockReceiptCreateView(StoreStaffRequiredMixin, CreateView):
    model = StockReceipt
    form_class = StockReceiptForm
    template_name = 'inventory/stock_receipt_form.html'
    success_url = reverse_lazy('inventory:stock_receipt_list')
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, '상품 입고가 등록되었습니다.')
        return super().form_valid(form)

class StockReceiptDetailView(StoreStaffRequiredMixin, DetailView):
    model = StockReceipt
    template_name = 'inventory/stock_receipt_detail.html'
    context_object_name = 'receipt'

class StockReceiptUpdateView(StoreStaffRequiredMixin, UpdateView):
    model = StockReceipt
    form_class = StockReceiptForm
    template_name = 'inventory/stock_receipt_form.html'
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        messages.success(self.request, '상품 입고 정보가 수정되었습니다.')
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse_lazy('inventory:stock_receipt_detail', kwargs={'pk': self.object.pk})

class StockReceiptDeleteView(StoreManagerRequiredMixin, DeleteView):
    model = StockReceipt
    template_name = 'inventory/stock_receipt_confirm_delete.html'
    success_url = reverse_lazy('inventory:stock_receipt_list')
    
    def delete(self, request, *args, **kwargs):
        receipt = self.get_object()
        
        # 재고 수량 되돌리기
        stock, created = ProductStock.objects.get_or_create(
            product=receipt.product,
            store=receipt.store,
            defaults={'quantity': 0}
        )
        stock.quantity -= receipt.quantity
        stock.save()
        
        messages.success(self.request, '상품 입고 기록이 삭제되었습니다.')
        return super().delete(request, *args, **kwargs)

# 출고 관리
class StockReleaseListView(StoreStaffRequiredMixin, ListView):
    model = StockRelease
    template_name = 'inventory/stock_release_list.html'
    context_object_name = 'releases'
    paginate_by = 10
    
    def get_queryset(self):
        queryset = super().get_queryset()
        search_query = self.request.GET.get('search', '')
        start_date = self.request.GET.get('start_date', '')
        end_date = self.request.GET.get('end_date', '')
        store_id = self.request.GET.get('store', '')
        release_type = self.request.GET.get('release_type', '')
        
        if search_query:
            queryset = queryset.filter(
                Q(product__name__icontains=search_query) |
                Q(product__code__icontains=search_query)
            )
        
        if start_date:
            queryset = queryset.filter(release_date__gte=start_date)
            
        if end_date:
            queryset = queryset.filter(release_date__lte=end_date)
            
        if store_id:
            queryset = queryset.filter(store_id=store_id)
            
        if release_type:
            queryset = queryset.filter(release_type=release_type)
            
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from accounts.models import Store
        context['stores'] = Store.objects.all()
        context['release_types'] = dict(StockRelease.RELEASE_TYPE_CHOICES)
        context['search_query'] = self.request.GET.get('search', '')
        context['start_date'] = self.request.GET.get('start_date', '')
        context['end_date'] = self.request.GET.get('end_date', '')
        context['selected_store'] = self.request.GET.get('store', '')
        context['selected_release_type'] = self.request.GET.get('release_type', '')
        return context

class StockReleaseCreateView(StoreStaffRequiredMixin, CreateView):
    model = StockRelease
    form_class = StockReleaseForm
    template_name = 'inventory/stock_release_form.html'
    success_url = reverse_lazy('inventory:stock_release_list')
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, '상품 출고가 등록되었습니다.')
        return super().form_valid(form)

class StockReleaseDetailView(StoreStaffRequiredMixin, DetailView):
    model = StockRelease
    template_name = 'inventory/stock_release_detail.html'
    context_object_name = 'release'

class StockReleaseUpdateView(StoreStaffRequiredMixin, UpdateView):
    model = StockRelease
    form_class = StockReleaseForm
    template_name = 'inventory/stock_release_form.html'
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        messages.success(self.request, '상품 출고 정보가 수정되었습니다.')
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse_lazy('inventory:stock_release_detail', kwargs={'pk': self.object.pk})

class StockReleaseDeleteView(StoreManagerRequiredMixin, DeleteView):
    model = StockRelease
    template_name = 'inventory/stock_release_confirm_delete.html'
    success_url = reverse_lazy('inventory:stock_release_list')
    
    def delete(self, request, *args, **kwargs):
        release = self.get_object()
        
        # 재고 수량 되돌리기
        stock, created = ProductStock.objects.get_or_create(
            product=release.product,
            store=release.store,
            defaults={'quantity': 0}
        )
        stock.quantity += release.quantity
        stock.save()
        
        messages.success(self.request, '상품 출고 기록이 삭제되었습니다.')
        return super().delete(request, *args, **kwargs)

# 재고 조정 관리
class StockAdjustmentListView(StoreStaffRequiredMixin, ListView):
    model = StockAdjustment
    template_name = 'inventory/stock_adjustment_list.html'
    context_object_name = 'adjustments'
    paginate_by = 10
    
    def get_queryset(self):
        queryset = super().get_queryset()
        search_query = self.request.GET.get('search', '')
        start_date = self.request.GET.get('start_date', '')
        end_date = self.request.GET.get('end_date', '')
        store_id = self.request.GET.get('store', '')
        adjustment_type = self.request.GET.get('adjustment_type', '')
        
        if search_query:
            queryset = queryset.filter(
                Q(product__name__icontains=search_query) |
                Q(product__code__icontains=search_query) |
                Q(reason__icontains=search_query)
            )
        
        if start_date:
            queryset = queryset.filter(adjustment_date__gte=start_date)
            
        if end_date:
            queryset = queryset.filter(adjustment_date__lte=end_date)
            
        if store_id:
            queryset = queryset.filter(store_id=store_id)
            
        if adjustment_type:
            queryset = queryset.filter(adjustment_type=adjustment_type)
            
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from accounts.models import Store
        context['stores'] = Store.objects.all()
        context['adjustment_types'] = dict(StockAdjustment.ADJUSTMENT_TYPE_CHOICES)
        context['search_query'] = self.request.GET.get('search', '')
        context['start_date'] = self.request.GET.get('start_date', '')
        context['end_date'] = self.request.GET.get('end_date', '')
        context['selected_store'] = self.request.GET.get('store', '')
        context['selected_adjustment_type'] = self.request.GET.get('adjustment_type', '')
        return context

class StockAdjustmentCreateView(StoreStaffRequiredMixin, CreateView):
    model = StockAdjustment
    form_class = StockAdjustmentForm
    template_name = 'inventory/stock_adjustment_form.html'
    success_url = reverse_lazy('inventory:stock_adjustment_list')
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, '재고 조정이 등록되었습니다.')
        return super().form_valid(form)

class StockAdjustmentDetailView(StoreStaffRequiredMixin, DetailView):
    model = StockAdjustment
    template_name = 'inventory/stock_adjustment_detail.html'
    context_object_name = 'adjustment'

class StockAdjustmentDeleteView(StoreManagerRequiredMixin, DeleteView):
    model = StockAdjustment
    template_name = 'inventory/stock_adjustment_confirm_delete.html'
    success_url = reverse_lazy('inventory:stock_adjustment_list')
    
    def delete(self, request, *args, **kwargs):
        adjustment = self.get_object()
        
        # 재고 수량 되돌리기
        stock, created = ProductStock.objects.get_or_create(
            product=adjustment.product,
            store=adjustment.store,
            defaults={'quantity': 0}
        )
        
        if adjustment.adjustment_type == 'increase':
            stock.quantity -= adjustment.quantity
        else:  # decrease
            stock.quantity += adjustment.quantity
            
        stock.save()
        
        messages.success(self.request, '재고 조정 기록이 삭제되었습니다.')
        return super().delete(request, *args, **kwargs)

# 재고 현황
class StockStatusView(StoreStaffRequiredMixin, ListView):
    model = ProductStock
    template_name = 'inventory/stock_status.html'
    context_object_name = 'stocks'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = super().get_queryset()
        search_query = self.request.GET.get('search', '')
        store_id = self.request.GET.get('store', '')
        category_id = self.request.GET.get('category', '')
        stock_filter = self.request.GET.get('stock_filter', '')
        
        if search_query:
            queryset = queryset.filter(
                Q(product__name__icontains=search_query) |
                Q(product__code__icontains=search_query) |
                Q(product__barcode__icontains=search_query)
            )
        
        if store_id:
            queryset = queryset.filter(store_id=store_id)
            
        if category_id:
            queryset = queryset.filter(product__category_id=category_id)
            
        if stock_filter == 'low':
            # 재고가 부족한 상품 (10개 미만)
            queryset = queryset.filter(quantity__lt=10)
        elif stock_filter == 'out':
            # 품절된 상품
            queryset = queryset.filter(quantity__lte=0)
            
        return queryset.select_related('product', 'store')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from accounts.models import Store
        context['stores'] = Store.objects.all()
        context['categories'] = Category.objects.all()
        context['search_query'] = self.request.GET.get('search', '')
        context['selected_store'] = self.request.GET.get('store', '')
        context['selected_category'] = self.request.GET.get('category', '')
        context['selected_stock_filter'] = self.request.GET.get('stock_filter', '')
        
        return context

# AJAX 요청용 뷰
def get_product_stock(request):
    """특정 상품의 매장별 재고를 JSON 형식으로 반환합니다."""
    product_id = request.GET.get('product_id')
    store_id = request.GET.get('store_id')
    
    if not product_id:
        return JsonResponse({'error': '상품 ID가 필요합니다.'}, status=400)
    
    try:
        if store_id:
            # 특정 매장의 재고만 조회
            stock = ProductStock.objects.get(product_id=product_id, store_id=store_id)
            return JsonResponse({
                'quantity': stock.quantity,
                'updated_at': stock.updated_at.strftime('%Y-%m-%d %H:%M')
            })
        else:
            # 모든 매장의 재고 조회
            stocks = ProductStock.objects.filter(product_id=product_id).select_related('store')
            result = {}
            for stock in stocks:
                result[stock.store.id] = {
                    'store_name': stock.store.name,
                    'quantity': stock.quantity,
                    'updated_at': stock.updated_at.strftime('%Y-%m-%d %H:%M')
                }
            return JsonResponse(result)
    except ProductStock.DoesNotExist:
        return JsonResponse({'quantity': 0})