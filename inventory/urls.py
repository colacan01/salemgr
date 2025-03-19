from django.urls import path
from . import views

app_name = 'inventory'

urlpatterns = [
    # 카테고리 관리
    path('category/', views.CategoryListView.as_view(), name='category_list'),
    path('category/create/', views.CategoryCreateView.as_view(), name='category_create'),
    path('category/<int:pk>/', views.CategoryUpdateView.as_view(), name='category_update'),
    path('category/<int:pk>/delete/', views.CategoryDeleteView.as_view(), name='category_delete'),
    
    # 상품 관리
    path('product/', views.ProductListView.as_view(), name='product_list'),
    path('product/create/', views.ProductCreateView.as_view(), name='product_create'),
    path('product/<int:pk>/', views.ProductDetailView.as_view(), name='product_detail'),
    path('product/<int:pk>/update/', views.ProductUpdateView.as_view(), name='product_update'),
    path('product/<int:pk>/delete/', views.ProductDeleteView.as_view(), name='product_delete'),
    
    # 상품 가격 관리
    path('product/<int:product_pk>/price/create/', views.ProductPriceCreateView.as_view(), name='product_price_create'),
    path('price/<int:pk>/update/', views.ProductPriceUpdateView.as_view(), name='product_price_update'),
    path('price/<int:pk>/delete/', views.ProductPriceDeleteView.as_view(), name='product_price_delete'),
    
    # 입고 관리
    path('receipt/', views.StockReceiptListView.as_view(), name='stock_receipt_list'),
    path('receipt/create/', views.StockReceiptCreateView.as_view(), name='stock_receipt_create'),
    path('receipt/<int:pk>/', views.StockReceiptDetailView.as_view(), name='stock_receipt_detail'),
    path('receipt/<int:pk>/update/', views.StockReceiptUpdateView.as_view(), name='stock_receipt_update'),
    path('receipt/<int:pk>/delete/', views.StockReceiptDeleteView.as_view(), name='stock_receipt_delete'),
    
    # 출고 관리
    path('release/', views.StockReleaseListView.as_view(), name='stock_release_list'),
    path('release/create/', views.StockReleaseCreateView.as_view(), name='stock_release_create'),
    path('release/<int:pk>/', views.StockReleaseDetailView.as_view(), name='stock_release_detail'),
    path('release/<int:pk>/update/', views.StockReleaseUpdateView.as_view(), name='stock_release_update'),
    path('release/<int:pk>/delete/', views.StockReleaseDeleteView.as_view(), name='stock_release_delete'),
    
    # 재고 조정 관리
    path('adjustment/', views.StockAdjustmentListView.as_view(), name='stock_adjustment_list'),
    path('adjustment/create/', views.StockAdjustmentCreateView.as_view(), name='stock_adjustment_create'),
    path('adjustment/<int:pk>/', views.StockAdjustmentDetailView.as_view(), name='stock_adjustment_detail'),
    path('adjustment/<int:pk>/delete/', views.StockAdjustmentDeleteView.as_view(), name='stock_adjustment_delete'),
    
    # 재고 현황
    path('stock/', views.StockStatusView.as_view(), name='stock_status'),
    
    # AJAX 요청용 URL
    path('api/product-stock/', views.get_product_stock, name='api_product_stock'),
]