from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.forms import AuthenticationForm
from django.urls import reverse_lazy
from django.views import generic
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView

from .models import User, Store
from .forms import SignupForm, ProfileEditForm, StoreForm  # ProfileEditForm 추가, StoreForm 추가

def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f"{user.get_user_type_display()}로 로그인했습니다.")
                
                # 사용자 유형에 따라 다른 페이지로 리디렉션
                if user.user_type == 'app_admin':
                    return redirect('admin:index')
                elif user.user_type in ['store_manager', 'store_staff']:
                    return redirect('sales:dashboard')
                else:  # customer
                    return redirect('home')
    else:
        form = AuthenticationForm()
    
    return render(request, 'accounts/login.html', {'form': form})

@login_required
def logout_view(request):
    logout(request)
    messages.info(request, "로그아웃되었습니다.")
    return redirect('accounts:login')

@login_required
def profile_view(request):
    return render(request, 'accounts/profile.html')

def signup_view(request):
    if request.method == 'POST':
        form = SignupForm(request.POST, request.FILES)
        if form.is_valid():
            user = form.save()
            login(request, user)  # 회원가입 후 자동 로그인
            messages.success(request, "회원가입이 완료되었습니다.")
            return redirect('home')
    else:
        form = SignupForm()
    
    return render(request, 'accounts/signup.html', {'form': form})

@login_required
def edit_profile_view(request):
    """사용자 프로필 편집 뷰"""
    if request.method == 'POST':
        form = ProfileEditForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "프로필이 성공적으로 수정되었습니다.")
            return redirect('accounts:profile')
    else:
        form = ProfileEditForm(instance=request.user)
    
    return render(request, 'accounts/edit_profile.html', {'form': form})

# 관리자/매장관리자만 접근 가능하도록 하는 믹스인
class AdminOrStoreManagerRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.user_type in ['app_admin', 'store_manager']

# 매장 목록 보기
class StoreListView(LoginRequiredMixin, AdminOrStoreManagerRequiredMixin, ListView):
    model = Store
    template_name = 'accounts/store_list.html'
    context_object_name = 'stores'
    ordering = ['name']
    
    def get_queryset(self):
        # 앱 관리자는 모든 매장을, 매장 관리자는 자신의 매장만 볼 수 있음
        if self.request.user.user_type == 'app_admin':
            return Store.objects.all().order_by('name')
        else:
            return Store.objects.filter(id=self.request.user.store.id)

# 매장 상세 보기
class StoreDetailView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    model = Store
    template_name = 'accounts/store_detail.html'
    context_object_name = 'store'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['employees'] = User.objects.filter(store=self.object).order_by('user_type', 'username')
        
        # 사용자 권한에 따른 플래그 추가
        user = self.request.user
        context['can_edit'] = (user.user_type == 'app_admin' or 
                              (user.user_type == 'store_manager' and user.store == self.object))
        context['can_delete'] = user.user_type == 'app_admin'
        
        return context
    
    # 권한 검사 로직
    def test_func(self):
        store = self.get_object()
        user = self.request.user
        
        # 앱 관리자는 모든 매장 조회 가능
        if user.user_type == 'app_admin':
            return True
            
        # 매장 관리자나 직원은 자신의 매장만 조회 가능
        if user.user_type in ['store_manager', 'store_staff'] and user.store == store:
            return True
            
        return False

# 매장 생성
class StoreCreateView(LoginRequiredMixin, AdminOrStoreManagerRequiredMixin, CreateView):
    model = Store
    form_class = StoreForm
    template_name = 'accounts/store_form.html'
    success_url = reverse_lazy('accounts:store_list')
    
    def form_valid(self, form):
        messages.success(self.request, '매장이 성공적으로 등록되었습니다.')
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_update'] = False
        return context

# 매장 수정
class StoreUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Store
    form_class = StoreForm
    template_name = 'accounts/store_form.html'
    
    def get_success_url(self):
        return reverse_lazy('accounts:store_detail', kwargs={'pk': self.object.pk})
    
    def form_valid(self, form):
        messages.success(self.request, '매장 정보가 성공적으로 수정되었습니다.')
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_update'] = True
        return context
    
    # 권한 검사 로직 강화
    def test_func(self):
        store = self.get_object()
        user = self.request.user
        
        # 앱 관리자는 모든 매장 수정 가능
        if user.user_type == 'app_admin':
            return True
            
        # 매장 관리자는 자신의 매장만 수정 가능
        if user.user_type == 'store_manager' and user.store == store:
            return True
            
        return False

# 매장 삭제
class StoreDeleteView(LoginRequiredMixin, AdminOrStoreManagerRequiredMixin, DeleteView):
    model = Store
    template_name = 'accounts/store_confirm_delete.html'
    success_url = reverse_lazy('accounts:store_list')
    context_object_name = 'store'
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, '매장이 성공적으로 삭제되었습니다.')
        return super().delete(request, *args, **kwargs)
    
    # 앱 관리자만 매장 삭제 가능
    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.user_type == 'app_admin'