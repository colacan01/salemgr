from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from inventory.models import Category, Product, ProductPrice
import random

class Command(BaseCommand):
    help = '화장품 카테고리 및 상품 샘플 데이터를 생성합니다'

    def handle(self, *args, **kwargs):
        self.stdout.write('샘플 데이터 생성을 시작합니다...')
        
        # 카테고리 생성
        categories = self._create_categories()
        
        # 상품 생성
        products = self._create_products(categories)
        
        self.stdout.write(self.style.SUCCESS(f'성공적으로 {len(categories)}개의 카테고리와 {len(products)}개의 상품이 생성되었습니다.'))

    def _create_categories(self):
        # 이미 존재하는 카테고리 확인을 위한 리스트
        existing_categories = list(Category.objects.values_list('name', flat=True))
        
        # 카테고리 데이터
        categories_data = [
            {
                'name': '스킨케어',
                'description': '클렌저, 토너, 에센스, 세럼, 크림, 마스크팩 등 피부 관리 제품'
            },
            {
                'name': '메이크업',
                'description': '파운데이션, 컨실러, 블러셔, 아이섀도우, 마스카라, 립스틱 등 화장 제품'
            },
            {
                'name': '바디케어',
                'description': '바디워시, 바디로션, 바디스크럽, 핸드크림 등 신체 관리 제품'
            },
            {
                'name': '헤어케어',
                'description': '샴푸, 컨디셔너, 트리트먼트, 헤어 에센스, 염색약 등 모발 관리 제품'
            },
            {
                'name': '향수',
                'description': '여성용, 남성용, 중성 향수 제품'
            },
            {
                'name': '남성 화장품',
                'description': '남성용 스킨케어, 쉐이빙 제품, 그루밍 용품 등'
            },
            {
                'name': '선케어',
                'description': '자외선 차단제, 선스틱, 선스프레이, 선크림 등 자외선 차단 제품'
            },
            {
                'name': '유기농/자연주의',
                'description': '천연 성분으로 만든 유기농 인증 화장품'
            }
        ]
        
        created_categories = []
        
        for cat_data in categories_data:
            # 이미 존재하는 카테고리면 건너뛰기
            if cat_data['name'] in existing_categories:
                self.stdout.write(f"카테고리 '{cat_data['name']}'은(는) 이미 존재합니다.")
                continue
                
            category = Category.objects.create(**cat_data)
            created_categories.append(category)
            self.stdout.write(f"카테고리 '{category.name}'이(가) 생성되었습니다.")
            
        return created_categories

    def _create_products(self, created_categories):
        # 필요하다면 이미 존재하는 카테고리 가져오기
        if not created_categories:
            categories = list(Category.objects.all())
        else:
            categories = created_categories + list(Category.objects.exclude(id__in=[c.id for c in created_categories]))
        
        # 이미 존재하는 상품 코드 확인
        existing_codes = list(Product.objects.values_list('code', flat=True))
        
        # 상품 데이터
        products_data = [
            # 스킨케어 카테고리
            {
                'code': 'SK001',
                'name': '수분 진정 토너',
                'description': '건조한 피부를 촉촉하게 가꾸어주는 수분 토너입니다. 알로에 성분 함유.',
                'category_name': '스킨케어',
                'barcode': '8801234567890',
                'price': 18000
            },
            {
                'code': 'SK002',
                'name': '비타민C 세럼',
                'description': '비타민C 함유 세럼으로 피부 톤을 밝게 개선하고 안티에이징 효과를 제공합니다.',
                'category_name': '스킨케어',
                'barcode': '8801234567891',
                'price': 35000
            },
            {
                'code': 'SK003',
                'name': '수분 진정 크림',
                'description': '건조하고 민감한 피부를 위한 진정 효과가 있는 수분 크림입니다.',
                'category_name': '스킨케어',
                'barcode': '8801234567892',
                'price': 28000
            },
            
            # 메이크업 카테고리
            {
                'code': 'MU001',
                'name': '롱래스팅 파운데이션',
                'description': '하루종일 무너짐 없는 롱래스팅 파운데이션, SPF30 PA++',
                'category_name': '메이크업',
                'barcode': '8801234567893',
                'price': 32000
            },
            {
                'code': 'MU002',
                'name': '볼륨 마스카라',
                'description': '속눈썹을 풍성하게 만들어주는 워터프루프 마스카라',
                'category_name': '메이크업',
                'barcode': '8801234567894',
                'price': 17000
            },
            {
                'code': 'MU003',
                'name': '매트 립스틱',
                'description': '발색력 좋고 건조함 없는 매트 립스틱',
                'category_name': '메이크업',
                'barcode': '8801234567895',
                'price': 22000
            },
            
            # 바디케어 카테고리
            {
                'code': 'BC001',
                'name': '모이스처 바디로션',
                'description': '48시간 지속되는 강력한 보습 효과의 바디로션',
                'category_name': '바디케어',
                'barcode': '8801234567896',
                'price': 16500
            },
            {
                'code': 'BC002',
                'name': '리프레싱 바디워시',
                'description': '상쾌한 시트러스 향의 바디워시',
                'category_name': '바디케어',
                'barcode': '8801234567897',
                'price': 14500
            },
            
            # 헤어케어 카테고리
            {
                'code': 'HC001',
                'name': '데미지 케어 샴푸',
                'description': '손상된 모발을 복구하는 단백질 샴푸',
                'category_name': '헤어케어',
                'barcode': '8801234567898',
                'price': 19500
            },
            {
                'code': 'HC002',
                'name': '볼륨 컨디셔너',
                'description': '힘없는 모발에 볼륨감을 부여하는 컨디셔너',
                'category_name': '헤어케어',
                'barcode': '8801234567899',
                'price': 19500
            },
            
            # 향수 카테고리
            {
                'code': 'FR001',
                'name': '블루밍 플로럴 오 드 퍼퓸',
                'description': '은은한 꽃향기가 하루종일 지속되는 여성용 향수',
                'category_name': '향수',
                'barcode': '8801234567900',
                'price': 68000
            },
            {
                'code': 'FR002',
                'name': '우디 시트러스 오 드 뚜왈렛',
                'description': '시트러스와 우디 노트가 조화로운 남성용 향수',
                'category_name': '향수',
                'barcode': '8801234567901',
                'price': 58000
            },
            
            # 남성 화장품 카테고리
            {
                'code': 'MC001',
                'name': '올인원 스킨로션',
                'description': '남성을 위한 간편한 스킨과 로션이 하나로 합쳐진 제품',
                'category_name': '남성 화장품',
                'barcode': '8801234567902',
                'price': 24000
            },
            {
                'code': 'MC002',
                'name': '쿨링 쉐이빙 폼',
                'description': '면도 시 자극을 줄이고 쿨링 효과를 주는 쉐이빙 폼',
                'category_name': '남성 화장품',
                'barcode': '8801234567903',
                'price': 12000
            },
            
            # 선케어 카테고리
            {
                'code': 'SC001',
                'name': '워터프루프 선크림 SPF50+ PA++++',
                'description': '강력한 자외선 차단과 워터프루프 기능의 선크림',
                'category_name': '선케어',
                'barcode': '8801234567904',
                'price': 25000
            },
            {
                'code': 'SC002',
                'name': '데일리 선스틱 SPF35',
                'description': '휴대하기 편한 스틱형 자외선 차단제',
                'category_name': '선케어',
                'barcode': '8801234567905',
                'price': 18500
            },
            
            # 유기농/자연주의 카테고리
            {
                'code': 'OR001',
                'name': '오가닉 알로에 젤',
                'description': '유기농 알로에베라 성분의 촉촉한 수분젤',
                'category_name': '유기농/자연주의',
                'barcode': '8801234567906',
                'price': 23000
            },
            {
                'code': 'OR002',
                'name': '천연 시어버터 핸드크림',
                'description': '시어버터와 자연 추출물로 만든 천연 핸드크림',
                'category_name': '유기농/자연주의',
                'barcode': '8801234567907',
                'price': 15000
            },
            {
                'code': 'OR003',
                'name': '유기농 그린티 클렌저',
                'description': '유기농 녹차 성분을 함유한 순한 클렌징 폼',
                'category_name': '유기농/자연주의',
                'barcode': '8801234567908',
                'price': 20000
            }
        ]
        
        created_products = []
        today = timezone.now().date()
        one_year_later = today + timedelta(days=365)
        
        # 카테고리 이름으로 카테고리 객체를 쉽게 찾기 위한 딕셔너리 생성
        category_dict = {cat.name: cat for cat in categories}
        
        for product_data in products_data:
            # 코드가 이미 존재하는 경우 건너뛰기
            if product_data['code'] in existing_codes:
                self.stdout.write(f"상품 코드 '{product_data['code']}'는 이미 존재합니다.")
                continue
            
            # 카테고리 이름으로 카테고리 객체 찾기
            category_name = product_data.pop('category_name')
            category = category_dict.get(category_name)
            
            if not category:
                self.stdout.write(f"카테고리 '{category_name}'를 찾을 수 없습니다. 이 상품은 건너뜁니다.")
                continue
            
            # 가격 정보 추출
            price = product_data.pop('price')
            
            # 상품 생성
            product = Product.objects.create(
                category=category,
                **product_data
            )
            
            # 상품 가격 생성
            ProductPrice.objects.create(
                product=product,
                price=price,
                start_date=today,
                end_date=one_year_later
            )
            
            created_products.append(product)
            self.stdout.write(f"상품 '{product.name}'이(가) 생성되었습니다.")
        
        return created_products