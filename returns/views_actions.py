from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from django.views import View
from django.db import transaction
from django.http import Http404
from django.urls import reverse

from accounts.permissions import StoreStaffRequiredMixin, StoreManagerRequiredMixin
from inventory.models import StockReceipt, ProductStock
from .models import Return, ReturnItem
from sales.models import Sale

class ReturnApproveView(StoreManagerRequiredMixin, View):
    """반품 승인 처리"""
    def post(self, request, pk):
        try:
            # 반품 정보 가져오기
            return_obj = get_object_or_404(Return, pk=pk)
            
            # 권한 체크 (앱 관리자 또는 해당 매장 관리자만)
            if request.user.user_type != 'app_admin' and return_obj.store != request.user.store:
                messages.error(request, '이 반품을 승인할 권한이 없습니다.')
                return redirect('returns:return_detail', pk=pk)
            
            # 대기 상태인지 확인
            if return_obj.status != 'pending':
                messages.error(request, '이미 처리된 반품입니다.')
                return redirect('returns:return_detail', pk=pk)
            
            with transaction.atomic():
                # 반품 상태 업데이트
                return_obj.status = 'approved'
                return_obj.approved_by = request.user
                return_obj.approved_at = timezone.now()
                return_obj.save()
                
                # 관련 기록 저장
                # (필요 시 추가 기능)
                
                messages.success(request, f'반품번호 {return_obj.return_number}가 성공적으로 승인되었습니다.')
                
            return redirect('returns:return_detail', pk=pk)
            
        except Exception as e:
            messages.error(request, f'반품 승인 중 오류가 발생했습니다: {str(e)}')
            return redirect('returns:return_detail', pk=pk)


class ReturnRejectView(StoreManagerRequiredMixin, View):
    """반품 거부 처리"""
    def post(self, request, pk):
        try:
            # 반품 정보 가져오기
            return_obj = get_object_or_404(Return, pk=pk)
            
            # 권한 체크 (앱 관리자 또는 해당 매장 관리자만)
            if request.user.user_type != 'app_admin' and return_obj.store != request.user.store:
                messages.error(request, '이 반품을 거부할 권한이 없습니다.')
                return redirect('returns:return_detail', pk=pk)
            
            # 대기 상태인지 확인
            if return_obj.status != 'pending':
                messages.error(request, '이미 처리된 반품입니다.')
                return redirect('returns:return_detail', pk=pk)
            
            # 거절 사유
            reason = request.POST.get('reject_reason', '')
            if not reason:
                messages.error(request, '거부 사유를 입력해주세요.')
                return redirect('returns:return_detail', pk=pk)
            
            with transaction.atomic():
                # 반품 상태 업데이트
                return_obj.status = 'rejected'
                return_obj.rejected_by = request.user
                return_obj.rejected_at = timezone.now()
                return_obj.reject_reason = reason
                return_obj.save()
                
                messages.success(request, f'반품번호 {return_obj.return_number}가 거부되었습니다.')
                
            return redirect('returns:return_detail', pk=pk)
            
        except Exception as e:
            messages.error(request, f'반품 거부 중 오류가 발생했습니다: {str(e)}')
            return redirect('returns:return_detail', pk=pk)


class ReturnCompleteView(StoreStaffRequiredMixin, View):
    """반품 완료 처리 (재입고 및 환불 처리)"""
    def post(self, request, pk):
        try:
            # 반품 정보 가져오기
            return_obj = get_object_or_404(Return, pk=pk)
            
            # 권한 체크 (앱 관리자 또는 해당 매장 직원만)
            if request.user.user_type != 'app_admin' and return_obj.store != request.user.store:
                messages.error(request, '이 반품을 완료할 권한이 없습니다.')
                return redirect('returns:return_detail', pk=pk)
            
            # 승인 상태인지 확인
            if return_obj.status != 'approved':
                messages.error(request, '승인되지 않은 반품은 완료 처리할 수 없습니다.')
                return redirect('returns:return_detail', pk=pk)
            
            with transaction.atomic():
                # 반품 상태 업데이트
                return_obj.status = 'completed'
                return_obj.completed_by = request.user
                return_obj.completed_at = timezone.now()
                return_obj.save()
                
                # 재입고 처리 (재입고 대상인 항목만)
                for item in return_obj.returnitems.filter(restock=True):
                    # 상품 재고 증가
                    stock, created = ProductStock.objects.get_or_create(
                        product=item.product,
                        store=return_obj.store,
                        defaults={'quantity': 0}
                    )
                    
                    # 입고 내역 생성 (재입고 항목만)
                    receipt = StockReceipt.objects.create(
                        product=item.product,
                        store=return_obj.store,
                        quantity=item.quantity,
                        cost_price=item.price,
                        receipt_date=timezone.now(),
                        receipt_number=return_obj.return_number,            
                        note=f'반품번호 {return_obj.return_number} 재입고',
                        created_by=request.user
                    )
                    
                    # 재고 항목의 입고 내역 연결
                    stock.quantity += item.quantity
                    stock.save()
                
                messages.success(request, f'반품번호 {return_obj.return_number}가 완료 처리되었습니다.')
                
            return redirect('returns:return_detail', pk=pk)
            
        except Exception as e:
            messages.error(request, f'반품 완료 처리 중 오류가 발생했습니다: {str(e)}')
            return redirect('returns:return_detail', pk=pk)


class CreateReturnFromSaleView(StoreStaffRequiredMixin, View):
    """판매에서 바로 반품 생성"""
    def get(self, request, sale_id):
        try:
            # 판매 정보 확인
            sale = get_object_or_404(Sale, pk=sale_id)
            
            # 권한 체크
            if request.user.user_type != 'app_admin' and sale.store != request.user.store:
                raise Http404("판매 내역을 찾을 수 없습니다.")
            
            # 반품 생성 페이지로 리디렉션 (판매 ID 포함)
            return redirect(f"{reverse('returns:return_create')}?sale_id={sale_id}")
            
        except Exception as e:
            messages.error(request, f'반품 생성 중 오류가 발생했습니다: {str(e)}')
            return redirect('sales:sale_detail', pk=sale_id)