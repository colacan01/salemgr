from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib import messages
from django.db import transaction
from django.utils import timezone
from django.db.models import Q

from accounts.permissions import StoreStaffRequiredMixin, StoreManagerRequiredMixin
from .models import Return, ReturnItem
from sales.models import Sale, SaleItem
from .forms import ReturnForm, ReturnItemFormSet
# from inventory.models import Product


class ReturnListView(StoreStaffRequiredMixin, ListView):
    """반품 목록 조회"""
    model = Return
    template_name = 'returns/return_list.html'
    context_object_name = 'returns'
    paginate_by = 10
    
    def get_queryset(self):
        queryset = super().get_queryset()
        search = self.request.GET.get('search', '')
        status = self.request.GET.get('status', '')
        start_date = self.request.GET.get('start_date', '')
        end_date = self.request.GET.get('end_date', '')
        
        # 검색어 필터링
        if search:
            queryset = queryset.filter(
                Q(return_number__icontains=search) |
                Q(sale__sale_number__icontains=search) |
                Q(customer_name__icontains=search) |
                Q(customer_phone__icontains=search)
            )
        
        # 상태 필터링
        if status:
            queryset = queryset.filter(status=status)
        
        # 날짜 필터링
        if start_date:
            queryset = queryset.filter(return_date__date__gte=start_date)
        if end_date:
            queryset = queryset.filter(return_date__date__lte=end_date)
        
        # 매장 필터링 (앱 관리자가 아니면 자신의 매장만)
        if self.request.user.user_type != 'app_admin':
            queryset = queryset.filter(store=self.request.user.store)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search'] = self.request.GET.get('search', '')
        context['status'] = self.request.GET.get('status', '')
        context['start_date'] = self.request.GET.get('start_date', '')
        context['end_date'] = self.request.GET.get('end_date', '')
        
        # 상태별 집계
        if self.request.user.user_type == 'app_admin':
            base_query = Return.objects
        else:
            base_query = Return.objects.filter(store=self.request.user.store)
            
        context['stats'] = {
            'total': base_query.count(),
            'pending': base_query.filter(status='pending').count(),
            'approved': base_query.filter(status='approved').count(),
            'rejected': base_query.filter(status='rejected').count(),
            'completed': base_query.filter(status='completed').count(),
        }
        
        return context
    
class ReturnDetailView(StoreStaffRequiredMixin, DetailView):
    """반품 상세 조회"""
    model = Return
    template_name = 'returns/return_detail.html'
    context_object_name = 'return'
    
    def get_queryset(self):
        queryset = super().get_queryset()
        # 매장 필터링 (앱 관리자가 아니면 자신의 매장만)
        if self.request.user.user_type != 'app_admin':
            queryset = queryset.filter(store=self.request.user.store)
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return_obj = self.get_object()
        
        # 액션 버튼 가시성 설정
        context['can_approve'] = (return_obj.status == 'pending' and 
                                    self.request.user.user_type in ['app_admin', 'store_manager'])
        context['can_reject'] = (return_obj.status == 'pending' and 
                                self.request.user.user_type in ['app_admin', 'store_manager'])
        context['can_complete'] = (return_obj.status == 'approved')
        context['can_update'] = (return_obj.status == 'pending')
        context['can_delete'] = (return_obj.status == 'pending' and 
                                self.request.user == return_obj.created_by)
        
        return context

class ReturnCreateView(StoreStaffRequiredMixin, CreateView):
    """새로운 반품 등록"""
    model = Return
    form_class = ReturnForm
    template_name = 'returns/return_form.html'
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        if self.request.POST:
            context['item_formset'] = ReturnItemFormSet(
                self.request.POST, instance=self.object, user=self.request.user
            )
        else:
            context['item_formset'] = ReturnItemFormSet(
                instance=self.object, user=self.request.user
            )
            
            # 판매에서 바로 반품 생성 시
            sale_id = self.request.GET.get('sale_id')
            if sale_id:
                try:
                    sale = Sale.objects.get(id=sale_id)
                    context['form'].initial['sale'] = sale
                    context['form'].initial['customer_name'] = sale.customer_name
                    context['form'].initial['customer_phone'] = sale.customer_phone
                    context['form'].initial['store'] = sale.store
                    
                    # 판매 항목 불러오기
                    context['sale_items'] = sale.saleitems.all()
                except Sale.DoesNotExist:
                    pass
        
        return context
    
    def form_valid(self, form):
        context = self.get_context_data()
        item_formset = context['item_formset']
        
        # 폼셋 유효성 검사
        if not item_formset.is_valid():
            return self.form_invalid(form)
        
        try:
            with transaction.atomic():
                # 반품 객체 생성
                self.object = form.save(commit=False)
                self.object.created_by = self.request.user
                
                # 반품번호 자동 생성 (RET-YYYYMMDDxxxx 형식)
                today = timezone.now().strftime('%Y%m%d')
                last_return = Return.objects.filter(return_number__startswith=f"RET-{today}").order_by('-return_number').first()
                
                if last_return:
                    try:
                        last_num = int(last_return.return_number.split('-')[1][8:])
                        self.object.return_number = f"RET-{today}{last_num+1:04d}"
                    except (IndexError, ValueError):
                        self.object.return_number = f"RET-{today}0001"
                else:
                    self.object.return_number = f"RET-{today}0001"
                
                # 반품 객체 저장
                self.object.save()
                
                # 폼셋 저장
                item_formset.instance = self.object
                
                # 폼셋의 각 폼에서 sale_item 또는 product가 있는지 확인
                for form in item_formset.forms:
                    if form.is_valid() and not form.cleaned_data.get('DELETE', False):
                        # sale_item이 없으면서 product도 없는 경우 체크
                        if not form.cleaned_data.get('sale_item') and not form.cleaned_data.get('product'):
                            # POST 데이터에서 product_id 직접 추출
                            prefix = item_formset.prefix
                            form_index = form.prefix.split('-')[1]
                            product_id = self.request.POST.get(f'{prefix}-{form_index}-product')
                            
                            if product_id:
                                try:
                                    from inventory.models import Product
                                    form.instance.product = Product.objects.get(id=product_id)
                                except (Product.DoesNotExist, ValueError):
                                    form.add_error('product', '유효한 상품을 선택해야 합니다.')
                                    return self.form_invalid(form)
                            else:
                                form.add_error('product', '상품을 선택해야 합니다.')
                                return self.form_invalid(form)
                
                # 폼셋 저장
                items = item_formset.save(commit=False)
                
                # 각 항목 추가 데이터 설정
                for item in items:
                    if not item.product_id:
                        # sale_item을 통해 product 설정
                        try:
                            if item.sale_item:
                                item.product = item.sale_item.product
                        except Exception as e:
                            # 예외가 발생했을 때는 POST 데이터에서 product_id 찾기
                            for form in item_formset:
                                if form.instance == item:
                                    product_id = form.cleaned_data.get('product')
                                    if product_id:
                                        item.product = product_id
                    
                    # sale_item이 있으면 가격 정보 가져오기
                    if hasattr(item, 'sale_item') and item.sale_item:
                        if not item.price or item.price == 0:
                            item.price = item.sale_item.price
                    
                    # 환불 금액이 설정되지 않았으면 수량 * 가격으로 계산
                    if not item.refund_amount or item.refund_amount == 0:
                        item.refund_amount = item.price * item.quantity
                    
                    # 항목 저장
                    item.save()
                
                # 삭제된 항목 처리
                for obj in item_formset.deleted_objects:
                    obj.delete()
                
                # 총 환불 금액 계산 및 업데이트
                total_amount = sum(item.refund_amount for item in self.object.returnitems.all())
                self.object.total_amount = total_amount
                self.object.save(update_fields=['total_amount'])
                
                messages.success(self.request, f'반품번호 {self.object.return_number}가 성공적으로 등록되었습니다.')
                return redirect('returns:return_detail', pk=self.object.pk)
        
        except Exception as e:
            messages.error(self.request, f'반품 등록 중 오류가 발생했습니다: {str(e)}')
            # 디버깅을 위한 예외 정보 출력
            import traceback
            print(traceback.format_exc())
            return self.form_invalid(form)
        
class ReturnUpdateView(StoreStaffRequiredMixin, UpdateView):
    """반품 정보 수정"""
    model = Return
    form_class = ReturnForm
    template_name = 'returns/return_form.html'
    context_object_name = 'return'
    
    def get_queryset(self):
        queryset = super().get_queryset().filter(status='pending')
        # 매장 필터링 (앱 관리자가 아니면 자신의 매장만)
        if self.request.user.user_type != 'app_admin':
            queryset = queryset.filter(store=self.request.user.store)
        return queryset
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_update'] = True
        
        if self.request.POST:
            context['item_formset'] = ReturnItemFormSet(
                self.request.POST, instance=self.object, user=self.request.user
            )
        else:
            context['item_formset'] = ReturnItemFormSet(
                instance=self.object, user=self.request.user
            )
            if self.object.sale:
                context['sale_items'] = self.object.sale.saleitems.all()
        
        return context    
    
    def form_valid(self, form):
        context = self.get_context_data()
        item_formset = context['item_formset']
        
        # 폼셋 유효성 검사
        if not item_formset.is_valid():
            return self.form_invalid(form)
        
        try:
            with transaction.atomic():
                # 반품 객체 생성
                self.object = form.save(commit=False)
                self.object.created_by = self.request.user
                
                # 반품번호 자동 생성 (RET-YYYYMMDDxxxx 형식)
                today = timezone.now().strftime('%Y%m%d')
                last_return = Return.objects.filter(return_number__startswith=f"RET-{today}").order_by('-return_number').first()
                
                if last_return:
                    try:
                        last_num = int(last_return.return_number.split('-')[1][8:])
                        self.object.return_number = f"RET-{today}{last_num+1:04d}"
                    except (IndexError, ValueError):
                        self.object.return_number = f"RET-{today}0001"
                else:
                    self.object.return_number = f"RET-{today}0001"
                
                # 반품 객체 저장
                self.object.save()
                
                # 폼셋 저장
                item_formset.instance = self.object
                
                # 폼셋의 각 폼에서 sale_item 또는 product가 있는지 확인
                for form in item_formset.forms:
                    if form.is_valid() and not form.cleaned_data.get('DELETE', False):
                        # sale_item이 없으면서 product도 없는 경우 체크
                        if not form.cleaned_data.get('sale_item') and not form.cleaned_data.get('product'):
                            # POST 데이터에서 product_id 직접 추출
                            prefix = item_formset.prefix
                            form_index = form.prefix.split('-')[1]
                            product_id = self.request.POST.get(f'{prefix}-{form_index}-product')
                            
                            if product_id:
                                try:
                                    from inventory.models import Product
                                    form.instance.product = Product.objects.get(id=product_id)
                                except (Product.DoesNotExist, ValueError):
                                    form.add_error('product', '유효한 상품을 선택해야 합니다.')
                                    return self.form_invalid(form)
                            else:
                                form.add_error('product', '상품을 선택해야 합니다.')
                                return self.form_invalid(form)
                
                # 폼셋 저장
                items = item_formset.save(commit=False)
                
                # 각 항목 추가 데이터 설정
                for item in items:
                    if not item.product_id:
                        # sale_item을 통해 product 설정
                        try:
                            if item.sale_item:
                                item.product = item.sale_item.product
                        except Exception as e:
                            # 예외가 발생했을 때는 POST 데이터에서 product_id 찾기
                            for form in item_formset:
                                if form.instance == item:
                                    product_id = form.cleaned_data.get('product')
                                    if product_id:
                                        item.product = product_id
                    
                    # sale_item이 있으면 가격 정보 가져오기
                    if hasattr(item, 'sale_item') and item.sale_item:
                        if not item.price or item.price == 0:
                            item.price = item.sale_item.price
                    
                    # 환불 금액이 설정되지 않았으면 수량 * 가격으로 계산
                    if not item.refund_amount or item.refund_amount == 0:
                        item.refund_amount = item.price * item.quantity
                    
                    # 항목 저장
                    item.save()
                
                # 삭제된 항목 처리
                for obj in item_formset.deleted_objects:
                    obj.delete()
                
                # 총 환불 금액 계산 및 업데이트
                total_amount = sum(item.refund_amount for item in self.object.returnitems.all())
                self.object.total_amount = total_amount
                self.object.save(update_fields=['total_amount'])
                
                messages.success(self.request, f'반품번호 {self.object.return_number}가 성공적으로 등록되었습니다.')
                return redirect('returns:return_detail', pk=self.object.pk)
        
        except Exception as e:
            messages.error(self.request, f'반품 등록 중 오류가 발생했습니다: {str(e)}')
            # 디버깅을 위한 예외 정보 출력
            import traceback
            print(traceback.format_exc())
            return self.form_invalid(form)


class ReturnDeleteView(StoreStaffRequiredMixin, DeleteView):
    """반품 삭제"""
    model = Return
    template_name = 'returns/return_confirm_delete.html'
    success_url = reverse_lazy('returns:return_list')
    context_object_name = 'return'
    
    def get_queryset(self):
        # 대기 상태인 반품만 삭제 가능
        queryset = super().get_queryset().filter(status='pending')
        
        # 작성자만 삭제 가능
        queryset = queryset.filter(created_by=self.request.user)
        
        # 매장 필터링 (앱 관리자가 아니면 자신의 매장만)
        if self.request.user.user_type != 'app_admin':
            queryset = queryset.filter(store=self.request.user.store)
            
        return queryset
    
    def delete(self, request, *args, **kwargs):
        try:
            self.object = self.get_object()
            success_url = self.get_success_url()
            self.object.delete()
            messages.success(request, '반품 내역이 삭제되었습니다.')
            return redirect(success_url)
        except Exception as e:
            messages.error(request, f'반품 삭제 중 오류가 발생했습니다: {str(e)}')
            return redirect('returns:return_detail', pk=kwargs['pk'])