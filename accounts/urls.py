from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('signup/', views.signup_view, name='signup'),
    path('profile/', views.profile_view, name='profile'),
    path('profile/edit/', views.edit_profile_view, name='edit_profile'),  # 새로 추가
    
    # 매장 관리 URL 패턴
    path('stores/', views.StoreListView.as_view(), name='store_list'),
    path('stores/create/', views.StoreCreateView.as_view(), name='store_create'),
    path('stores/<int:pk>/', views.StoreDetailView.as_view(), name='store_detail'),
    path('stores/<int:pk>/update/', views.StoreUpdateView.as_view(), name='store_update'),
    path('stores/<int:pk>/delete/', views.StoreDeleteView.as_view(), name='store_delete'),
    
    path('purchase-history/', views.purchase_history, name='purchase_history'),
    path('purchase-detail/<int:sale_id>/', views.purchase_detail, name='purchase_detail'),
]