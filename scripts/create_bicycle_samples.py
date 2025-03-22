import os
import sys
import django
import random
from datetime import datetime, timedelta
from decimal import Decimal

# 프로젝트 루트 경로를 PYTHONPATH에 추가
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

# Django 설정을 로드합니다.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'salemgr.settings')
django.setup()

from inventory.models import Category, Product, ProductPrice
from accounts.models import Store
from django.utils import timezone

def create_bicycle_samples():
    """자전거 관련 샘플 데이터를 생성합니다."""
    
    print("자전거 카테고리 및 상품 샘플 데이터 생성 시작...")
    
    # 기본 매장 가져오기 (없으면 생성)
    store, _ = Store.objects.get_or_create(
        name=" scott bicycle",
        defaults={
            "address": "서울시 강남구 자전거로 123",
            "phone_number": "02-1234-5678"
        }
    )
    
    # 자전거 카테고리 생성
    categories = [
        {
            "name": "MTB(산악자전거)",
            "description": "산악지형에서의 주행을 위해 설계된 자전거로, 튼튼한 프레임과 넓은 타이어가 특징입니다."
        },
        {
            "name": "로드바이크",
            "description": "포장도로에서 고속 주행을 위한 경량 자전거로, 가늘고 매끄러운 타이어와 드롭 핸들바가 특징입니다."
        },
        {
            "name": "하이브리드 자전거",
            "description": "MTB와 로드바이크의 장점을 결합한 다목적 자전거로, 도심과 가벼운 비포장도로 모두에서 주행할 수 있습니다."
        },
        {
            "name": "자전거 부품",
            "description": "자전거의 다양한 부품들 - 변속기, 브레이크, 페달, 안장 등"
        },
        {
            "name": "자전거 액세서리",
            "description": "라이트, 헬멧, 장갑, 물통 등 자전거 주행 시 필요한 부가 장비"
        }
    ]
    
    category_objects = []
    for cat_data in categories:
        category, created = Category.objects.get_or_create(
            name=cat_data["name"],
            store=store,
            defaults={"description": cat_data["description"]}
        )
        category_objects.append(category)
        status = "생성됨" if created else "이미 존재함"
        print(f"카테고리: {category.name} - {status}")
    
    # 자전거 제품 데이터
    products = [
        # MTB(산악자전거)
        {
            "category": "MTB(산악자전거)",
            "code": "MTB-GT001",
            "name": "그랜드투어 알파인 29er",
            "description": "29인치 휠을 갖춘 전문가용 산악자전거, 알루미늄 프레임",
            "price": 1250000
        },
        {
            "category": "MTB(산악자전거)",
            "code": "MTB-TR002",
            "name": "트레일블레이저 X500",
            "description": "산악트레일에 최적화된 풀서스펜션 MTB",
            "price": 2100000
        },
        {
            "category": "MTB(산악자전거)",
            "code": "MTB-RK003",
            "name": "락호퍼 프로",
            "description": "전문 산악 경기용 경량 카본 MTB",
            "price": 3500000
        },
        {
            "category": "MTB(산악자전거)",
            "code": "MTB-FA004",
            "name": "패스트트랙 익스트림",
            "description": "다운힐 주행을 위한 프리라이드 MTB",
            "price": 2800000
        },
        {
            "category": "MTB(산악자전거)",
            "code": "MTB-EN005",
            "name": "엔듀런스 마스터 27.5",
            "description": "장거리 산악 주행용 27.5인치 MTB",
            "price": 1850000
        },
        {
            "category": "MTB(산악자전거)",
            "code": "MTB-BG006",
            "name": "비기너 에코 MTB",
            "description": "입문자용 경제적인 산악자전거",
            "price": 650000
        },
        
        # 로드바이크
        {
            "category": "로드바이크",
            "code": "RB-SP001",
            "name": "스피드스타 울트라",
            "description": "경량 카본 프레임의 고성능 로드바이크",
            "price": 4200000
        },
        {
            "category": "로드바이크",
            "code": "RB-AR002",
            "name": "에어로 레이서 프로",
            "description": "공기역학을 고려한 설계의 경기용 로드바이크",
            "price": 3800000
        },
        {
            "category": "로드바이크",
            "code": "RB-EN003",
            "name": "인듀어 클래식",
            "description": "장거리 라이딩에 최적화된 내구성 높은 로드바이크",
            "price": 2500000
        },
        {
            "category": "로드바이크",
            "code": "RB-UR004",
            "name": "어반 커뮤터 스페셜",
            "description": "도심 통근용 경량 로드바이크",
            "price": 1300000
        },
        {
            "category": "로드바이크",
            "code": "RB-GR005",
            "name": "그래블 익스플로러",
            "description": "비포장도로 주행이 가능한 그래블 로드바이크",
            "price": 1900000
        },
        {
            "category": "로드바이크",
            "code": "RB-TR006",
            "name": "투어링 마스터",
            "description": "장거리 여행을 위한 투어링 로드바이크",
            "price": 2200000
        },
        
        # 하이브리드 자전거
        {
            "category": "하이브리드 자전거",
            "code": "HB-CT001",
            "name": "시티크루저 컴포트",
            "description": "도심에서 편안한 주행을 위한 하이브리드 자전거",
            "price": 780000
        },
        {
            "category": "하이브리드 자전거",
            "code": "HB-FT002",
            "name": "피트니스 크로스",
            "description": "운동과 출퇴근을 위한 다목적 하이브리드",
            "price": 950000
        },
        {
            "category": "하이브리드 자전거",
            "code": "HB-UR003",
            "name": "어반 네비게이터",
            "description": "도시 생활에 최적화된 하이브리드 자전거",
            "price": 820000
        },
        {
            "category": "하이브리드 자전거",
            "code": "HB-TR004",
            "name": "트레일 익스플로러 하이브리드",
            "description": "가벼운 비포장길도 주행 가능한 다용도 하이브리드",
            "price": 1100000
        },
        {
            "category": "하이브리드 자전거",
            "code": "HB-EL005",
            "name": "전기 하이브리드 시티",
            "description": "전기모터 보조 기능이 있는 도심형 하이브리드",
            "price": 2400000
        },
        {
            "category": "하이브리드 자전거",
            "code": "HB-FD006",
            "name": "폴딩 하이브리드 미니",
            "description": "접이식 구조의 휴대성 좋은 하이브리드 자전거",
            "price": 680000
        },
        
        # 자전거 부품
        {
            "category": "자전거 부품",
            "code": "BP-DR001",
            "name": "프리미엄 변속기 세트",
            "description": "11단 고성능 변속기 풀세트",
            "price": 450000
        },
        {
            "category": "자전거 부품",
            "code": "BP-BR002",
            "name": "유압식 디스크 브레이크",
            "description": "전후륜용 고성능 유압 브레이크 세트",
            "price": 320000
        },
        {
            "category": "자전거 부품",
            "code": "BP-WH003",
            "name": "카본 휠셋 레이싱",
            "description": "경량 카본 휠셋 (앞/뒤)",
            "price": 1200000
        },
        {
            "category": "자전거 부품",
            "code": "BP-CR004",
            "name": "크랭크셋 울트라",
            "description": "경량 알루미늄 합금 크랭크셋",
            "price": 280000
        },
        {
            "category": "자전거 부품",
            "code": "BP-ST005",
            "name": "카본 안장대",
            "description": "충격흡수 기능이 있는 카본 소재 안장대",
            "price": 150000
        },
        {
            "category": "자전거 부품",
            "code": "BP-HD006",
            "name": "에르고노믹 핸들바",
            "description": "인체공학적 디자인의 알루미늄 핸들바",
            "price": 95000
        },
        
        # 자전거 액세서리
        {
            "category": "자전거 액세서리",
            "code": "BA-HM001",
            "name": "프로텍션 헬멧",
            "description": "고급 안전 인증 헬멧",
            "price": 180000
        },
        {
            "category": "자전거 액세서리",
            "code": "BA-LT002",
            "name": "LED 안전 라이트 세트",
            "description": "전후방용 고휘도 LED 라이트",
            "price": 65000
        },
        {
            "category": "자전거 액세서리",
            "code": "BA-GL003",
            "name": "프로 사이클링 장갑",
            "description": "충격흡수 패드가 있는 전문가용 장갑",
            "price": 45000
        },
        {
            "category": "자전거 액세서리",
            "code": "BA-BT004",
            "name": "스테인리스 물통 세트",
            "description": "물통과 물통 케이지 세트",
            "price": 35000
        },
        {
            "category": "자전거 액세서리",
            "code": "BA-LK005",
            "name": "고강도 자물쇠",
            "description": "도난 방지용 U자형 고강도 자물쇠",
            "price": 85000
        },
        {
            "category": "자전거 액세서리",
            "code": "BA-BG006",
            "name": "방수 자전거 가방",
            "description": "대용량 방수 처리된 자전거용 백팩",
            "price": 120000
        }
    ]

    # 오늘 날짜와 1년 후 날짜 설정
    today = timezone.now().date()
    one_year_later = today + timedelta(days=365)

    # 제품 생성
    for product_data in products:
        # 해당 카테고리 찾기
        category = None
        for cat in category_objects:
            if cat.name == product_data["category"]:
                category = cat
                break

        if not category:
            print(f"경고: {product_data['category']} 카테고리를 찾을 수 없습니다.")
            continue

        # 제품 생성 또는 업데이트
        product, created = Product.objects.get_or_create(
            code=product_data["code"],
            defaults={
                "name": product_data["name"],
                "description": product_data["description"],
                "category": category,
                "store": store,
                "is_active": True
            }
        )

        # 제품 가격 설정
        ProductPrice.objects.get_or_create(
            product=product,
            start_date=today,
            end_date=one_year_later,
            defaults={
                "price": Decimal(str(product_data["price"]))
            }
        )

        status = "생성됨" if created else "업데이트됨"
        print(f"제품: {product.name} ({product.code}) - {status}")

    print("샘플 데이터 생성 완료!")

if __name__ == "__main__":
    create_bicycle_samples()