from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db.models import Sum, Count, F, Q, Max
from django.utils import timezone
from inventory.models import Product, ProductOption, ProductOptionValue, StockReceipt
from sales.models import Sale, SaleItem

def home(request):
    # 판매금액 기준 상위 5개 인기 상품
    popular_products = Product.objects.filter(
        is_active=True
    ).annotate(
        total_sales=Sum('items__subtotal')
    ).order_by('-total_sales')[:5]
    
    # 최신 입고 상품 5개
    new_products = Product.objects.filter(
        is_active=True,
        receipts__receipt_date__lte=timezone.now().date()  # 오늘 이전 입고된 상품
    ).annotate(
        latest_receipt=Max('receipts__receipt_date')
    ).order_by('-latest_receipt')[:5]
    
    # 카테고리 목록 
    categories = set(Product.objects.filter(
        is_active=True, category__isnull=False
    ).values_list('category__name', flat=True))
    
    context = {
        'popular_products': popular_products,
        'new_products': new_products,
        'categories': categories,
    }
    return render(request, 'mall/home.html', context)

def product_detail(request, product_id):
    product = get_object_or_404(Product, pk=product_id, is_active=True)
    options = ProductOption.objects.filter(product=product)
    
    # 각 옵션에 대한 값들 가져오기
    option_values = {}
    for option in options:
        option_values[option] = ProductOptionValue.objects.filter(option=option, is_active=True)
    
    current_stock = product.get_current_stock()
    max_purchase_qty = min(current_stock, 100) if current_stock > 0 else 0
    
    context = {
        'product': product,
        'options': options,
        'option_values': option_values,
        'current_stock': current_stock,
        'max_purchase_qty': max_purchase_qty,
    }
    return render(request, 'mall/product_detail.html', context)

@login_required
def add_to_cart(request, product_id):
    if request.method == 'POST':
        product = get_object_or_404(Product, pk=product_id, is_active=True)
        cart = request.session.get('cart', {})
        
        # 옵션 정보 가져오기
        selected_options = {}
        for key, value in request.POST.items():
            if key.startswith('option_'):
                option_id = key.replace('option_', '')
                selected_options[option_id] = value
        
        # 상품 수량
        quantity = int(request.POST.get('quantity', 1))
        
        # 카트 아이템 키 생성 (상품 ID와 선택한 옵션으로 구성)
        cart_item_key = f"{product_id}_{'-'.join([f'{k}:{v}' for k, v in selected_options.items()])}"
        
        # 현재 판매가격 가져오기
        current_price = product.get_current_price() or 0
        
        if cart_item_key in cart:
            cart[cart_item_key]['quantity'] += quantity
        else:
            cart[cart_item_key] = {
                'product_id': product_id,
                'product_name': product.name,
                'price': float(current_price),
                'options': selected_options,
                'quantity': quantity
            }
        
        request.session['cart'] = cart
        return redirect('mall:cart')
    
    return redirect('mall:product_detail', product_id=product_id)

@login_required
def cart(request):
    cart = request.session.get('cart', {})
    cart_items = []
    
    for item_key, item_data in cart.items():
        product = get_object_or_404(Product, id=item_data['product_id'])
        selected_options = []
        
        for option_id, value_id in item_data['options'].items():
            try:
                option = ProductOption.objects.get(id=int(option_id))
                option_value = ProductOptionValue.objects.get(id=int(value_id))
                selected_options.append({
                    'name': option.name,
                    'value': option_value.value,
                    'price_adjustment': float(option_value.price_adjustment)
                })
            except (ProductOption.DoesNotExist, ProductOptionValue.DoesNotExist):
                continue
        
        # 옵션 가격 조정 계산
        option_price_adjustment = sum(opt['price_adjustment'] for opt in selected_options)
        unit_price = item_data['price'] + option_price_adjustment
        
        cart_items.append({
            'item_key': item_key,
            'product': product,
            'options': selected_options,
            'quantity': item_data['quantity'],
            'unit_price': unit_price,
            'subtotal': unit_price * item_data['quantity']
        })
    
    total = sum(item['subtotal'] for item in cart_items)
    
    context = {
        'cart_items': cart_items,
        'total': total
    }
    return render(request, 'mall/cart.html', context)

@login_required
def update_cart_item(request, item_key):
    if request.method == 'POST':
        cart = request.session.get('cart', {})
        change = int(request.GET.get('change', 0))
        
        if item_key in cart:
            cart[item_key]['quantity'] += change
            
            # 수량이 0 이하면 아이템 제거
            if cart[item_key]['quantity'] <= 0:
                del cart[item_key]
                
            request.session['cart'] = cart
            return JsonResponse({'success': True})
    
    return JsonResponse({'success': False})

@login_required
def remove_cart_item(request, item_key):
    if request.method == 'POST':
        cart = request.session.get('cart', {})
        
        if item_key in cart:
            del cart[item_key]
            request.session['cart'] = cart
            return JsonResponse({'success': True})
    
    return JsonResponse({'success': False})

@login_required
def checkout(request):
    cart = request.session.get('cart', {})
    
    if not cart:
        return redirect('mall:cart')
    
    if request.method == 'POST':
        # 결제 처리 및 주문 생성 로직
        from sales.models import Sale, SaleItem
        from accounts.models import Store
        
        # 기본 매장 가져오기 (실제 구현에서는 적절한 방법으로 매장 선택)
        store = Store.objects.first()
        
        if not store:
            return render(request, 'mall/checkout.html', {'error': '매장 정보가 없습니다.'})
        
        # 판매 생성
        sale = Sale.objects.create(
            sale_number=f"ONLINE-{timezone.now().strftime('%Y%m%d%H%M%S')}",
            sale_date=timezone.now(),
            store=store,
            customer_name=request.POST.get('name', ''),
            customer_phone=request.POST.get('phone', ''),
            payment_method=request.POST.get('payment_method', 'card'),
            status='pending',  # 주문 상태 초기값
            sales_channel='online',
            created_by=request.user
        )
        
        total_amount = 0
        
        # 장바구니 아이템을 판매 아이템으로 변환
        for item_key, item_data in cart.items():
            product = get_object_or_404(Product, id=item_data['product_id'])
            
            # 옵션 가격 조정 계산
            option_price_adjustment = 0
            for option_id, value_id in item_data['options'].items():
                try:
                    option_value = ProductOptionValue.objects.get(id=int(value_id))
                    option_price_adjustment += option_value.price_adjustment
                except ProductOptionValue.DoesNotExist:
                    pass
            
            price = item_data['price'] + option_price_adjustment
            quantity = item_data['quantity']
            subtotal = price * quantity
            
            SaleItem.objects.create(
                sale=sale,
                product=product,
                quantity=quantity,
                price=price,
                subtotal=subtotal
            )
            
            total_amount += subtotal
        
        # 판매 금액 업데이트
        sale.total_amount = total_amount
        sale.final_amount = total_amount
        sale.status = 'completed'  # 주문 완료 처리
        sale.save()
        
        # 장바구니 비우기
        request.session['cart'] = {}
        
        return render(request, 'mall/order_complete.html', {'sale': sale})
    
    # GET 요청 처리
    cart_items = []
    
    for item_key, item_data in cart.items():
        product = get_object_or_404(Product, id=item_data['product_id'])
        selected_options = []
        
        for option_id, value_id in item_data['options'].items():
            try:
                option = ProductOption.objects.get(id=int(option_id))
                option_value = ProductOptionValue.objects.get(id=int(value_id))
                selected_options.append({
                    'name': option.name,
                    'value': option_value.value,
                    'price_adjustment': float(option_value.price_adjustment)
                })
            except (ProductOption.DoesNotExist, ProductOptionValue.DoesNotExist):
                continue
        
        # 옵션 가격 조정 계산
        option_price_adjustment = sum(opt['price_adjustment'] for opt in selected_options)
        unit_price = item_data['price'] + option_price_adjustment
        
        cart_items.append({
            'item_key': item_key,
            'product': product,
            'options': selected_options,
            'quantity': item_data['quantity'],
            'unit_price': unit_price,
            'subtotal': unit_price * item_data['quantity']
        })
    
    total = sum(item['subtotal'] for item in cart_items)
    
    context = {
        'cart_items': cart_items,
        'total': total
    }
    return render(request, 'mall/checkout.html', context)