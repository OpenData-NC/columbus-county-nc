from django import template

from ebpub.db.models import Schema

register = template.Library()

@register.simple_tag(takes_context=True)
def get_schema_list(context):
    schemas = Schema.objects.filter(is_public=True)
    context["schema_list"] = schemas
    return ''

@register.simple_tag(takes_context=True)
def reorder_cities_list(context):
    context['location_list'] = context['location_list'].order_by('name')
    return ''
