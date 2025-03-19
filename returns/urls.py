from django.urls import path
from . import views
from . import views_actions
from . import views_api

app_name = 'returns'

urlpatterns = [
    # 기본 CRUD
    path('', views.ReturnListView.as_view(), name='return_list'),
    path('create/', views.ReturnCreateView.as_view(), name='return_create'),
    path('<int:pk>/', views.ReturnDetailView.as_view(), name='return_detail'),
    path('<int:pk>/update/', views.ReturnUpdateView.as_view(), name='return_update'),
    path('<int:pk>/delete/', views.ReturnDeleteView.as_view(), name='return_delete'),
    
    # 관리 작업
    path('<int:pk>/approve/', views_actions.ReturnApproveView.as_view(), name='return_approve'),
    path('<int:pk>/reject/', views_actions.ReturnRejectView.as_view(), name='return_reject'),
    path('<int:pk>/complete/', views_actions.ReturnCompleteView.as_view(), name='return_complete'),
    path('create-from-sale/<int:sale_id>/', views_actions.CreateReturnFromSaleView.as_view(), 
         name='create_from_sale'),
    
    # API 엔드포인트
    path('api/sale-items/', views_api.get_sale_items, name='api_sale_items'),
    path('api/sale-info/', views_api.get_sale_info, name='api_sale_info'),
]