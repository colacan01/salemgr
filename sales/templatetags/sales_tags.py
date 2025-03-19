from django import template

register = template.Library()

@register.filter
def mult(value, arg):
    """
    두 값을 곱하는 필터
    Usage: {{ value|mult:arg }}
    """
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0

@register.filter
def divisibleby(value, arg):
    """
    첫 번째 값을 두 번째 값으로 나누는 필터
    Usage: {{ value|divisibleby:arg }}
    """
    try:
        return float(value) / float(arg)
    except (ValueError, TypeError, ZeroDivisionError):
        return 0