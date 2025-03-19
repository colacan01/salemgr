from django.apps import AppConfig

class ReturnsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'returns'
    verbose_name = '반품 관리'
    
    def ready(self):
        # 시그널 등록을 위한 import
        import returns.signals