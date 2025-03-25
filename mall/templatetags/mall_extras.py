from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """딕셔너리에서 키 값으로 항목을 가져옵니다."""
    return dictionary.get(key)

@register.filter
def currency(value):
    """숫자를 통화 형식으로 표시합니다."""
    try:
        return f"{int(value):,}원"
    except (ValueError, TypeError):
        return value