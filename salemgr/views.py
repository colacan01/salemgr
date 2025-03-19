from django.shortcuts import render

def home(request):
    """
    메인 홈페이지 뷰
    """
    return render(request, 'home.html')