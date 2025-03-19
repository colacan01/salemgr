from django import template

register = template.Library()

@register.filter
def add_class(field, css_class):
    return field.as_widget(attrs={"class": css_class})

@register.filter
def input_with_class(field, css_class):
    return field.as_widget(attrs={"class": f"{field.field.widget.attrs.get('class', '')} {css_class}"})