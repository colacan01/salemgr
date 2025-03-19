from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.db.models import Q

from sales.models import Sale, SaleItem

@login_required
def get_sale_items(request):
    """판매 항목 가져오기 (AJAX 호출용)"""
    sale_id = request.GET.get('sale_id')
    
    if not sale_id:
        return JsonResponse({'error': '판매 ID가 필요합니다.'}, status=400)
    
    try:
        # 권한 체크
        if request.user.user_type != 'app_admin':
            sale = get_object_or_404(Sale, id=sale_id, store=request.user.store)
        else:
            sale = get_object_or_404(Sale, id=sale_id)
        
        # 판매 항목 가져오기
        items = []
        for item in sale.saleitems.all():
            items.append({
                'id': item.id,
                'product_id': item.product_id,
                'product_name': f"{item.product.code} - {item.product.name}",
                'quantity': item.quantity,
                'price': float(item.price),
                'amount': float(item.subtotal)
            })
        
        return JsonResponse({
            'success': True,
            'items': items,
            'sale': {
                'sale_number': sale.sale_number,
                'customer_name': sale.customer_name or '',
                'customer_phone': sale.customer_phone or '',
                'sale_date': sale.sale_date.strftime('%Y-%m-%d %H:%M')
            }
        })
    except Sale.DoesNotExist:
        return JsonResponse({'error': '판매 내역을 찾을 수 없습니다.'}, status=404)
    except Exception as e:
        return JsonResponse({'error': f'오류가 발생했습니다: {str(e)}'}, status=500)


@login_required
def get_sale_info(request):
    """판매 정보 가져오기 (AJAX 호출용)"""
    sale_id = request.GET.get('sale_id')
    
    if not sale_id:
        return JsonResponse({'error': '판매 ID가 필요합니다.'}, status=400)
    
    try:
        # 권한 체크
        if request.user.user_type != 'app_admin':
            sale = get_object_or_404(Sale, id=sale_id, store=request.user.store)
        else:
            sale = get_object_or_404(Sale, id=sale_id)
        
        return JsonResponse({
            'success': True,
            'sale': {
                'id': sale.id,
                'sale_number': sale.sale_number,
                'customer_name': sale.customer_name or '',
                'customer_phone': sale.customer_phone or '',
                'sale_date': sale.sale_date.strftime('%Y-%m-%d %H:%M'),
                'total_amount': float(sale.total_amount),
                'store': sale.store.name if sale.store else '',
                'store_id': sale.store.id if sale.store else None,
            }
        })
    except Sale.DoesNotExist:
        return JsonResponse({'error': '판매 내역을 찾을 수 없습니다.'}, status=404)
    except Exception as e:
        return JsonResponse({'error': f'오류가 발생했습니다: {str(e)}'}, status=500)