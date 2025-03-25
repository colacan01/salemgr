from django.urls import path
from . import views

app_name = 'mall'

urlpatterns = [
    path('', views.home, name='home'),
    path('product/<int:product_id>/', views.product_detail, name='product_detail'),
    path('cart/add/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/', views.cart, name='cart'),
    path('cart/update/<str:item_key>/', views.update_cart_item, name='update_cart_item'),
    path('cart/remove/<str:item_key>/', views.remove_cart_item, name='remove_cart_item'),
    path('checkout/', views.checkout, name='checkout'),
]