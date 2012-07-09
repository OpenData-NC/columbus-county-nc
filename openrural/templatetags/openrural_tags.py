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

@register.simple_tag
def get_corporation_full_address(newsitem):
    addr = newsitem.location_name.strip()
    locs = newsitem.location_set.all()
    try:
        city = locs.filter(location_type__slug='cities').get().name.strip()
    except:
        city = ''
    try:
        zip_code = locs.filter(location_type__slug='zipcodes').get().name.strip()
    except:
        zip_code = ''

    return '{0}, {1}, NC {2}'.format(addr, city, zip_code).strip()
