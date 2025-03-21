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
from accounts.models import Store

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
        queryset = StockReceipt.objects.all().order_by('-receipt_date', '-created_at')
        
        # 검색어 필터링
        search_query = self.request.GET.get('search', '')
        if search_query:
            queryset = queryset.filter(
                Q(product__name__icontains=search_query) |
                Q(product__code__icontains=search_query) |
                Q(receipt_number__icontains=search_query)
            )
        
        # 날짜 필터링
        start_date = self.request.GET.get('start_date')
        if start_date:
            queryset = queryset.filter(receipt_date__gte=start_date)
            
        end_date = self.request.GET.get('end_date')
        if end_date:
            queryset = queryset.filter(receipt_date__lte=end_date)
        
        # 매장 필터링
        selected_store = self.request.GET.get('store')
        
        # 앱 관리자가 아니라면 자신의 매장만 표시
        if self.request.user.user_type != 'app_admin':
            if self.request.user.store:
                queryset = queryset.filter(store=self.request.user.store)
        # 앱 관리자가 특정 매장을 선택한 경우
        elif selected_store:
            queryset = queryset.filter(store_id=selected_store)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # 매장 목록
        from accounts.models import Store
        
        # 앱 관리자는 모든 매장 볼 수 있음
        if self.request.user.user_type == 'app_admin':
            context['stores'] = Store.objects.all()
        # 일반 사용자는 자신의 매장만 볼 수 있음
        elif self.request.user.store:
            context['stores'] = Store.objects.filter(id=self.request.user.store.id)
        else:
            context['stores'] = Store.objects.none()
            
        # 검색 파라미터
        context['search_query'] = self.request.GET.get('search', '')
        context['start_date'] = self.request.GET.get('start_date', '')
        context['end_date'] = self.request.GET.get('end_date', '')
        context['selected_store'] = self.request.GET.get('store', '')
        
        # 사용자 정보
        context['is_app_admin'] = self.request.user.user_type == 'app_admin'
        context['user_store'] = self.request.user.store.id if self.request.user.store else None
        
        return context

class StockReceiptCreateView(StoreStaffRequiredMixin, CreateView):
    model = StockReceipt
    form_class = StockReceiptForm
    template_name = 'inventory/stock_receipt_form.html'
    # success_url = reverse_lazy('inventory:stock_receipt_list')
    
    # def get_form_kwargs(self):
    #     kwargs = super().get_form_kwargs()
    #     kwargs['user'] = self.request.user
        
    #     # POST 요청이고 앱 관리자가 아니라면 매장을 자동 설정
    #     if self.request.method == 'POST' and self.request.user.user_type != 'app_admin' and self.request.user.store:
    #         if not kwargs.get('data'):
    #             kwargs['data'] = self.request.POST.copy()
    #         kwargs['data']['store'] = self.request.user.store.id
            
    #     return kwargs
    
    # def form_valid(self, form):
    #     form.instance.created_by = self.request.user
        
    #     # 앱 관리자가 아니라면 매장을 자동 설정
    #     if self.request.user.user_type != 'app_admin' and self.request.user.store:
    #         form.instance.store = self.request.user.store
            
    #     messages.success(self.request, '상품 입고가 등록되었습니다.')
    #     return super().form_valid(form)
    
    # def get_context_data(self, **kwargs):
    #     context = super().get_context_data(**kwargs)
    #     context['is_app_admin'] = self.request.user.user_type == 'app_admin'
    #     return context
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        
        # POST 요청이고 앱 관리자가 아니라면 매장을 자동 설정
        if self.request.method == 'POST' and self.request.user.user_type != 'app_admin' and self.request.user.store:
            if 'data' in kwargs:
                data = kwargs['data'].copy()
                data['store'] = self.request.user.store.id
                kwargs['data'] = data
        
        return kwargs
    
    def form_valid(self, form):
        # 앱 관리자가 아니라면 매장을 자동 설정
        if self.request.user.user_type != 'app_admin' and self.request.user.store:
            form.instance.store = self.request.user.store
            
        messages.success(self.request, '상품 출고 정보가 수정되었습니다.')
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse_lazy('inventory:stock_receipt_list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_app_admin'] = self.request.user.user_type == 'app_admin'
        context['user_store'] = self.request.user.store.id if self.request.user.store else None
        return context
    
    
    

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
        
        # POST 요청이고 앱 관리자가 아니라면 매장을 자동 설정
        if self.request.method == 'POST' and self.request.user.user_type != 'app_admin' and self.request.user.store:
            if 'data' in kwargs:
                # POST 데이터를 복사하여 mutable로 만듦
                data = kwargs['data'].copy()
                data['store'] = self.request.user.store.id
                kwargs['data'] = data
            
        return kwargs
    
    def form_valid(self, form):
        # 앱 관리자가 아니라면 매장을 자동 설정
        if self.request.user.user_type != 'app_admin' and self.request.user.store:
            form.instance.store = self.request.user.store
            
        messages.success(self.request, '상품 입고 정보가 수정되었습니다.')
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse_lazy('inventory:stock_receipt_detail', kwargs={'pk': self.object.pk})
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_app_admin'] = self.request.user.user_type == 'app_admin'
        context['user_store'] = self.request.user.store.id if self.request.user.store else None
        return context

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

def stock_receipt_create(request):
    initial_data = {}
    
    # 사용자 관련 매장이 있으면 항상 기본값으로 설정
    if request.user.store:
        initial_data['store'] = request.user.store
    
    # URL 파라미터에서 product ID를 가져와 초기 데이터로 설정
    product_id = request.GET.get('product')
    if product_id:
        try:
            product = Product.objects.get(id=product_id)
            initial_data['product'] = product
            
            # 최근 입고 가격을 기본값으로 설정
            last_receipt = StockReceipt.objects.filter(
                product=product
            ).order_by('-receipt_date').first()
            
            if last_receipt:
                initial_data['cost_price'] = last_receipt.cost_price
                
        except Product.DoesNotExist:
            messages.warning(request, '해당 상품을 찾을 수 없습니다.')
    
    if request.method == 'POST':
        post_data = request.POST.copy()
        
        # 사용자가 앱 관리자가 아니고 매장이 있는 경우 매장 필드 값 설정
        if request.user.user_type != 'app_admin' and request.user.store:
            post_data['store'] = request.user.store.id
            
        form = StockReceiptForm(post_data, user=request.user)
        if form.is_valid():
            receipt = form.save(commit=False)
            receipt.created_by = request.user
            
            # 사용자가 앱 관리자가 아니고 매장이 있는 경우 강제로 매장 설정
            if request.user.user_type != 'app_admin' and request.user.store:
                receipt.store = request.user.store
                
            receipt.save()
            
            messages.success(request, '상품 입고가 등록되었습니다.')
            
            # 상품 상세 페이지로 리디렉션 (더 나은 UX 제공)
            if 'back_to_product' in request.GET:
                return redirect('inventory:product_detail', pk=receipt.product.pk)
            return redirect('inventory:stock_receipt_detail', pk=receipt.pk)
    else:
        form = StockReceiptForm(initial=initial_data, user=request.user)
    
    context = {
        'form': form,
        'back_url': request.META.get('HTTP_REFERER', 'inventory:stock_receipt_list'),
        'product_id': product_id,
        'user_store': request.user.store.id if request.user.store else None,
        'is_app_admin': request.user.user_type == 'app_admin'  # 앱 관리자 여부 추가
    }
    
    return render(request, 'inventory/stock_receipt_form.html', context)

# 출고 관리
class StockReleaseListView(StoreStaffRequiredMixin, ListView):
    model = StockRelease
    template_name = 'inventory/stock_release_list.html'
    context_object_name = 'releases'
    paginate_by = 10
    
    # def get_queryset(self):
    #     queryset = super().get_queryset()
    #     search_query = self.request.GET.get('search', '')
    #     start_date = self.request.GET.get('start_date', '')
    #     end_date = self.request.GET.get('end_date', '')
    #     store_id = self.request.GET.get('store', '')
    #     release_type = self.request.GET.get('release_type', '')
        
    #     if search_query:
    #         queryset = queryset.filter(
    #             Q(product__name__icontains=search_query) |
    #             Q(product__code__icontains=search_query)
    #         )
        
    #     if start_date:
    #         queryset = queryset.filter(release_date__gte=start_date)
            
    #     if end_date:
    #         queryset = queryset.filter(release_date__lte=end_date)
            
    #     if store_id:
    #         queryset = queryset.filter(store_id=store_id)
            
    #     if release_type:
    #         queryset = queryset.filter(release_type=release_type)
            
    #     return queryset
    
    # def get_context_data(self, **kwargs):
    #     context = super().get_context_data(**kwargs)
    #     from accounts.models import Store
    #     context['stores'] = Store.objects.all()
    #     context['release_types'] = dict(StockRelease.RELEASE_TYPE_CHOICES)
    #     context['search_query'] = self.request.GET.get('search', '')
    #     context['start_date'] = self.request.GET.get('start_date', '')
    #     context['end_date'] = self.request.GET.get('end_date', '')
    #     context['selected_store'] = self.request.GET.get('store', '')
    #     context['selected_release_type'] = self.request.GET.get('release_type', '')
    #     return context
    def get_queryset(self):
        queryset = StockRelease.objects.all().order_by('-release_date', '-created_at')
        
        # 검색어 필터링
        search_query = self.request.GET.get('search', '')
        if search_query:
            queryset = queryset.filter(
                Q(product__name__icontains=search_query) |
                Q(product__code__icontains=search_query) |
                Q(receipt_number__icontains=search_query)
            )
        
        # 날짜 필터링
        start_date = self.request.GET.get('start_date')
        if start_date:
            queryset = queryset.filter(receipt_date__gte=start_date)
            
        end_date = self.request.GET.get('end_date')
        if end_date:
            queryset = queryset.filter(receipt_date__lte=end_date)
        
        # 매장 필터링
        selected_store = self.request.GET.get('store')
        
        # 앱 관리자가 아니라면 자신의 매장만 표시
        if self.request.user.user_type != 'app_admin':
            if self.request.user.store:
                queryset = queryset.filter(store=self.request.user.store)
        # 앱 관리자가 특정 매장을 선택한 경우
        elif selected_store:
            queryset = queryset.filter(store_id=selected_store)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # 매장 목록
        from accounts.models import Store
        
        # 앱 관리자는 모든 매장 볼 수 있음
        if self.request.user.user_type == 'app_admin':
            context['stores'] = Store.objects.all()
        # 일반 사용자는 자신의 매장만 볼 수 있음
        elif self.request.user.store:
            context['stores'] = Store.objects.filter(id=self.request.user.store.id)
        else:
            context['stores'] = Store.objects.none()
            
        # 검색 파라미터
        context['search_query'] = self.request.GET.get('search', '')
        context['start_date'] = self.request.GET.get('start_date', '')
        context['end_date'] = self.request.GET.get('end_date', '')
        context['selected_store'] = self.request.GET.get('store', '')
        
        # 사용자 정보
        context['is_app_admin'] = self.request.user.user_type == 'app_admin'
        context['user_store'] = self.request.user.store.id if self.request.user.store else None
        
        return context

class StockReleaseCreateView(StoreStaffRequiredMixin, CreateView):
    model = StockRelease
    form_class = StockReleaseForm
    template_name = 'inventory/stock_release_form.html'
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        
        # 폼 초기값 설정
        initial = kwargs.get('initial', {})
        
        # 사용자 매장 자동 설정 (앱 관리자가 아닐 경우)
        if self.request.user.user_type != 'app_admin' and self.request.user.store:
            initial['store'] = self.request.user.store
            
        # URL에서 product ID를 가져와 초기 데이터로 설정
        product_id = self.request.GET.get('product')
        if product_id:
            try:
                product = Product.objects.get(id=product_id)
                initial['product'] = product
            except Product.DoesNotExist:
                messages.warning(self.request, '해당 상품을 찾을 수 없습니다.')
                
        kwargs['initial'] = initial
            
        # POST 요청이고 앱 관리자가 아니라면 매장을 자동 설정
        if self.request.method == 'POST' and self.request.user.user_type != 'app_admin' and self.request.user.store:
            if 'data' in kwargs:
                data = kwargs['data'].copy()
                data['store'] = self.request.user.store.id
                kwargs['data'] = data
        
        return kwargs
    
    def form_valid(self, form):
        form.instance.created_by = self.request.user
        
        # 앱 관리자가 아니라면 매장을 자동 설정
        if self.request.user.user_type != 'app_admin' and self.request.user.store:
            form.instance.store = self.request.user.store
            
        # 재고 확인
        product = form.instance.product
        store = form.instance.store
        quantity = form.instance.quantity
        
        # 현재 매장의 재고 확인
        current_stock = product.get_current_stock(store)
        
        if current_stock < quantity:
            messages.error(self.request, f'출고 수량이 재고량보다 많습니다. 현재 재고: {current_stock}개')
            return self.form_invalid(form)
            
        messages.success(self.request, '상품 출고가 등록되었습니다.')
        return super().form_valid(form)
    
    def get_success_url(self):
        # 상품 상세에서 왔으면 상품 상세 페이지로 리디렉션
        if 'back_to_product' in self.request.GET and self.object.product:
            return reverse_lazy('inventory:product_detail', kwargs={'pk': self.object.product.pk})
        return reverse_lazy('inventory:stock_release_list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_app_admin'] = self.request.user.user_type == 'app_admin'
        context['user_store'] = self.request.user.store.id if self.request.user.store else None
        return context

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
        
        # POST 요청이고 앱 관리자가 아니라면 매장을 자동 설정
        if self.request.method == 'POST' and self.request.user.user_type != 'app_admin' and self.request.user.store:
            if 'data' in kwargs:
                data = kwargs['data'].copy()
                data['store'] = self.request.user.store.id
                kwargs['data'] = data
            
        return kwargs
    
    def form_valid(self, form):
        # 앱 관리자가 아니라면 매장을 자동 설정
        if self.request.user.user_type != 'app_admin' and self.request.user.store:
            form.instance.store = self.request.user.store
            
        # 출고 수량 변경 시 재고 확인
        product = form.instance.product
        store = form.instance.store
        new_quantity = form.instance.quantity
        original_quantity = self.get_object().quantity
        
        # 수량이 증가했다면 재고 확인
        if new_quantity > original_quantity:
            additional_quantity = new_quantity - original_quantity
            
            # 현재 매장의 재고 + 원래 출고량 (출고 취소) - 새 출고량
            current_stock = product.get_stock_by_store(store) + original_quantity
            
            if current_stock < new_quantity:
                messages.error(self.request, f'출고 수량이 재고량보다 많습니다. 현재 재고: {current_stock}개')
                return self.form_invalid(form)
            
        messages.success(self.request, '상품 출고 정보가 수정되었습니다.')
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse_lazy('inventory:stock_release_detail', kwargs={'pk': self.object.pk})
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_app_admin'] = self.request.user.user_type == 'app_admin'
        context['user_store'] = self.request.user.store.id if self.request.user.store else None
        return context

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
    
    # def get_queryset(self):
    #     queryset = super().get_queryset()
    #     search_query = self.request.GET.get('search', '')
    #     start_date = self.request.GET.get('start_date', '')
    #     end_date = self.request.GET.get('end_date', '')
    #     store_id = self.request.GET.get('store', '')
    #     adjustment_type = self.request.GET.get('adjustment_type', '')
        
    #     if search_query:
    #         queryset = queryset.filter(
    #             Q(product__name__icontains=search_query) |
    #             Q(product__code__icontains=search_query) |
    #             Q(reason__icontains=search_query)
    #         )
        
    #     if start_date:
    #         queryset = queryset.filter(adjustment_date__gte=start_date)
            
    #     if end_date:
    #         queryset = queryset.filter(adjustment_date__lte=end_date)
            
    #     if store_id:
    #         queryset = queryset.filter(store_id=store_id)
            
    #     if adjustment_type:
    #         queryset = queryset.filter(adjustment_type=adjustment_type)
            
    #     return queryset
    
    # def get_context_data(self, **kwargs):
    #     context = super().get_context_data(**kwargs)
    #     from accounts.models import Store
    #     context['stores'] = Store.objects.all()
    #     context['adjustment_types'] = dict(StockAdjustment.ADJUSTMENT_TYPE_CHOICES)
    #     context['search_query'] = self.request.GET.get('search', '')
    #     context['start_date'] = self.request.GET.get('start_date', '')
    #     context['end_date'] = self.request.GET.get('end_date', '')
    #     context['selected_store'] = self.request.GET.get('store', '')
    #     context['selected_adjustment_type'] = self.request.GET.get('adjustment_type', '')
    #     return context
    def get_queryset(self):
        queryset = StockAdjustment.objects.all().order_by('-adjustment_date', '-created_at')
        
        # 검색어 필터링
        search_query = self.request.GET.get('search', '')
        if search_query:
            queryset = queryset.filter(
                Q(product__name__icontains=search_query) |
                Q(product__code__icontains=search_query) |
                Q(receipt_number__icontains=search_query)
            )
        
        # 조정 유형 필터링
        adjustment_type = self.request.GET.get('adjustment_type')
        if adjustment_type:
            queryset = queryset.filter(adjustment_type=adjustment_type)
            
        # 날짜 필터링
        start_date = self.request.GET.get('start_date')
        if start_date:
            queryset = queryset.filter(receipt_date__gte=start_date)
            
        end_date = self.request.GET.get('end_date')
        if end_date:
            queryset = queryset.filter(receipt_date__lte=end_date)
        
        # 매장 필터링
        selected_store = self.request.GET.get('store')
        
        # 앱 관리자가 아니라면 자신의 매장만 표시
        if self.request.user.user_type != 'app_admin':
            if self.request.user.store:
                queryset = queryset.filter(store=self.request.user.store)
        # 앱 관리자가 특정 매장을 선택한 경우
        elif selected_store:
            queryset = queryset.filter(store_id=selected_store)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # 매장 목록
        from accounts.models import Store
        
        # 앱 관리자는 모든 매장 볼 수 있음
        if self.request.user.user_type == 'app_admin':
            context['stores'] = Store.objects.all()
        # 일반 사용자는 자신의 매장만 볼 수 있음
        elif self.request.user.store:
            context['stores'] = Store.objects.filter(id=self.request.user.store.id)
        else:
            context['stores'] = Store.objects.none()
            
        # 검색 파라미터
        context['search_query'] = self.request.GET.get('search', '')
        context['start_date'] = self.request.GET.get('start_date', '')
        context['end_date'] = self.request.GET.get('end_date', '')
        context['selected_store'] = self.request.GET.get('store', '')
        context['selected_adjustment_type'] = self.request.GET.get('adjustment_type', '')
        
        # 조정 유형 목록
        context['adjustment_types'] = dict(StockAdjustment.ADJUSTMENT_TYPE_CHOICES)
        
        # 사용자 정보
        context['is_app_admin'] = self.request.user.user_type == 'app_admin'
        context['user_store'] = self.request.user.store.id if self.request.user.store else None
        
        return context    

class StockAdjustmentCreateView(StoreStaffRequiredMixin, CreateView):
    model = StockAdjustment
    form_class = StockAdjustmentForm
    template_name = 'inventory/stock_adjustment_form.html'
    success_url = reverse_lazy('inventory:stock_adjustment_list')
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        
        # 폼 초기값 설정
        initial = kwargs.get('initial', {})
        
        # 사용자 매장 자동 설정 (앱 관리자가 아닐 경우)
        if self.request.user.user_type != 'app_admin' and self.request.user.store:
            initial['store'] = self.request.user.store
            
        # URL에서 product ID를 가져와 초기 데이터로 설정
        product_id = self.request.GET.get('product')
        if product_id:
            try:
                product = Product.objects.get(id=product_id)
                initial['product'] = product
            except Product.DoesNotExist:
                messages.warning(self.request, '해당 상품을 찾을 수 없습니다.')
                
        kwargs['initial'] = initial
            
        # POST 요청이고 앱 관리자가 아니라면 매장을 자동 설정
        if self.request.method == 'POST' and self.request.user.user_type != 'app_admin' and self.request.user.store:
            if 'data' in kwargs:
                data = kwargs['data'].copy()
                data['store'] = self.request.user.store.id
                kwargs['data'] = data
        
        return kwargs
    
    def form_valid(self, form):
        form.instance.created_by = self.request.user
        
        # 앱 관리자가 아니라면 매장을 자동 설정
        if self.request.user.user_type != 'app_admin' and self.request.user.store:
            form.instance.store = self.request.user.store
            
        messages.success(self.request, '재고 조정이 성공적으로 등록되었습니다.')
        return super().form_valid(form)
    
    def get_success_url(self):
        # 상품 상세에서 왔으면 상품 상세 페이지로 리디렉션
        if 'back_to_product' in self.request.GET and self.object.product:
            return reverse_lazy('inventory:product_detail', kwargs={'pk': self.object.product.pk})
        return self.success_url
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_app_admin'] = self.request.user.user_type == 'app_admin'
        context['user_store'] = self.request.user.store.id if self.request.user.store else None
        return context

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

class StockAdjustmentUpdateView(StoreStaffRequiredMixin, UpdateView):
    model = StockAdjustment
    form_class = StockAdjustmentForm
    template_name = 'inventory/stock_adjustment_form.html'
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        
        # POST 요청이고 앱 관리자가 아니라면 매장을 자동 설정
        if self.request.method == 'POST' and self.request.user.user_type != 'app_admin' and self.request.user.store:
            if 'data' in kwargs:
                data = kwargs['data'].copy()
                data['store'] = self.request.user.store.id
                kwargs['data'] = data
            
        return kwargs
    
    def form_valid(self, form):
        # 앱 관리자가 아니라면 매장을 자동 설정
        if self.request.user.user_type != 'app_admin' and self.request.user.store:
            form.instance.store = self.request.user.store
            
        messages.success(self.request, '재고 조정 정보가 수정되었습니다.')
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse_lazy('inventory:stock_adjustment_detail', kwargs={'pk': self.object.pk})
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_app_admin'] = self.request.user.user_type == 'app_admin'
        context['user_store'] = self.request.user.store.id if self.request.user.store else None
        return context

# 재고 현황
class StockStatusView(ListView):
    model = ProductStock
    template_name = 'inventory/stock_status.html'
    context_object_name = 'stocks'
    paginate_by = 20

    def get_queryset(self):
        queryset = super().get_queryset()
        
        # 검색 필터링
        search_query = self.request.GET.get('search', '')
        if search_query:
            queryset = queryset.filter(
                Q(product__name__icontains=search_query) |
                Q(product__code__icontains=search_query) |
                Q(product__barcode__icontains=search_query)
            )
            
        # 사용자 권한에 따른 매장 필터링
        if self.request.user.user_type == 'app_admin':
            # 앱 관리자는 매장 선택 가능
            store_id = self.request.GET.get('store')
            if store_id:
                queryset = queryset.filter(store_id=store_id)
        else:
            # 일반 사용자는 자신의 매장만 볼 수 있음
            queryset = queryset.filter(store=self.request.user.store)
        
        # 카테고리 필터링
        category_id = self.request.GET.get('category')
        if category_id:
            queryset = queryset.filter(product__category_id=category_id)
            
        # 재고 상태 필터링
        stock_filter = self.request.GET.get('stock_filter')
        if stock_filter == 'low':
            queryset = queryset.filter(quantity__lt=10, quantity__gt=0)
        elif stock_filter == 'out':
            queryset = queryset.filter(quantity__lte=0)
            
        return queryset.select_related('product', 'store', 'product__category')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # 검색 및 필터 관련 컨텍스트
        context['search_query'] = self.request.GET.get('search', '')
        context['selected_category'] = self.request.GET.get('category', '')
        context['selected_stock_filter'] = self.request.GET.get('stock_filter', '')
        
        # 매장 관련 컨텍스트
        if self.request.user.user_type == 'app_admin':
            context['selected_store'] = self.request.GET.get('store', '')
            # 앱 관리자는 모든 매장 목록 제공
            # context['stores'] = Store.objects.filter(is_active=True).order_by('name')
            context['stores'] = Store.objects.order_by('name')
        else:
            # 일반 사용자는 자신의 매장 정보만 제공
            context['user_store_id'] = self.request.user.store.id if self.request.user.store else None
            context['user_store_name'] = self.request.user.store.name if self.request.user.store else '지정되지 않음'
        
        # 카테고리 목록
        context['categories'] = Category.objects.all().order_by('name')
        
        # 재고 통계
        all_stocks = ProductStock.objects.all()
        
        # 사용자 권한에 따른 필터링
        if self.request.user.user_type != 'app_admin':
            all_stocks = all_stocks.filter(store=self.request.user.store)
            
        # 부족 재고 및 품절 상품 수 계산
        context['low_stock_count'] = all_stocks.filter(quantity__lt=10, quantity__gt=0).count()
        context['out_of_stock_count'] = all_stocks.filter(quantity__lte=0).count()
        
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

def get_last_cost_price(request):
    """상품의 마지막 입고 가격 조회 API"""
    product_id = request.GET.get('product_id')
    
    if not product_id:
        return JsonResponse({'error': '상품 ID가 필요합니다.'}, status=400)
    
    # 해당 상품의 마지막 입고 정보 조회
    last_receipt = StockReceipt.objects.filter(
        product_id=product_id
    ).order_by('-receipt_date', '-created_at').first()
    
    if last_receipt:
        return JsonResponse({
            'cost_price': float(last_receipt.cost_price),
            'last_receipt_date': last_receipt.receipt_date.strftime('%Y-%m-%d') if last_receipt.receipt_date else None
        })
    else:
        return JsonResponse({'cost_price': None, 'last_receipt_date': None})