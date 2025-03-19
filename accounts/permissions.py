from django.contrib.auth.mixins import UserPassesTestMixin, LoginRequiredMixin
from django.shortcuts import redirect
from django.contrib import messages
from django.urls import reverse_lazy

class AppAdminRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    login_url = reverse_lazy('accounts:login')
    
    def test_func(self):
        return self.request.user.user_type == 'app_admin'
    
    def handle_no_permission(self):
        messages.error(self.request, '앱관리자 권한이 필요합니다.')
        return redirect('accounts:login')

class StoreManagerRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    login_url = reverse_lazy('accounts:login')
    
    def test_func(self):
        return self.request.user.user_type in ['app_admin', 'store_manager']
    
    def handle_no_permission(self):
        messages.error(self.request, '매장관리자 권한이 필요합니다.')
        return redirect('accounts:login')

class StoreStaffRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    login_url = reverse_lazy('accounts:login')
    
    def test_func(self):
        return self.request.user.user_type in ['app_admin', 'store_manager', 'store_staff']
    
    def handle_no_permission(self):
        messages.error(self.request, '매장직원 권한이 필요합니다.')
        return redirect('accounts:login')

class CustomerRequiredMixin(LoginRequiredMixin):
    login_url = reverse_lazy('accounts:login')