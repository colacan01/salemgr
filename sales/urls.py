from django.urls import path
from . import views

app_name = 'sales'

urlpatterns = [
    # 판매 관리
    path('', views.SaleListView.as_view(), name='sale_list'),
    path('create/', views.SaleCreateView.as_view(), name='sale_create'),
    path('<int:pk>/', views.SaleDetailView.as_view(), name='sale_detail'),
    path('<int:pk>/update/', views.SaleUpdateView.as_view(), name='sale_update'),
    path('<int:pk>/delete/', views.SaleDeleteView.as_view(), name='sale_delete'),
    path('<int:pk>/cancel/', views.SaleCancelView.as_view(), name='sale_cancel'),
    
    # 대시보드
    path('dashboard/', views.sales_dashboard, name='dashboard'),
    
    # API 엔드포인트
    path('api/product-info/', views.get_product_info, name='api_product_info'),
]