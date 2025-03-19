"""
URL configuration for salemgr project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from . import views  # 새로 추가한 views 모듈 import

urlpatterns = [
    path('', views.home, name='home'),  # 루트 URL에 홈 뷰 연결
    path('admin/', admin.site.urls),
    path('inventory/', include('inventory.urls')),
    path('sales/', include('sales.urls')),
    path('accounts/', include('accounts.urls')),
    path('returns/', include('returns.urls')),
]

# 개발 환경에서 미디어 파일 서빙 설정 추가
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)