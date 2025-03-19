from django.core.management.base import BaseCommand
from inventory.models import Category, Product
from accounts.models import Store

class Command(BaseCommand):
    help = '기존 카테고리와 상품에 매장 필드를 업데이트합니다'

    def handle(self, *args, **options):
        self.stdout.write('매장 필드 업데이트를 시작합니다...')
        
        # 기본 매장 가져오기 또는 생성
        default_store = Store.objects.first()
        
        if not default_store:
            self.stdout.write('기본 매장이 없습니다. 마이그레이션을 중단합니다.')
            return
        
        # 매장이 없는 카테고리 업데이트
        categories = Category.objects.filter(store__isnull=True)
        self.stdout.write(f'{categories.count()}개의 카테고리를 업데이트합니다...')
        
        # 앱 관리자 계정용 전체 매장 카테고리는 그대로 두고,
        # 나머지는 기본 매장으로 설정
        # 여기서는 예시로 모든 카테고리를 전체 매장용으로 남겨둡니다
        # 필요하다면 일부 카테고리만 선택하여 기본 매장으로 설정할 수 있습니다
        
        # 매장이 없는 상품 업데이트
        products = Product.objects.filter(store__isnull=True)
        self.stdout.write(f'{products.count()}개의 상품을 업데이트합니다...')
        
        # 카테고리를 참조하여 상품의 매장 설정
        for product in products:
            if product.category and product.category.store:
                product.store = product.category.store
            else:
                # 카테고리가 없거나 카테고리에도 매장이 없는 경우 기본 매장 설정
                product.store = default_store
            product.save()
            
        self.stdout.write(self.style.SUCCESS('매장 필드 업데이트가 완료되었습니다!'))