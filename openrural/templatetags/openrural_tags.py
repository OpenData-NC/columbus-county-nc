import string

from django import template
from django.conf import settings

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
def get_newsitem_full_address(newsitem):
    addr = newsitem.location_name.strip()
    locs = newsitem.location_set.all()
    try:
        city = locs.filter(location_type__slug='cities').get().name.title().strip()
    except:
        city = ''
    try:
        zip_code = locs.filter(location_type__slug='zipcodes').get().name.strip()
    except:
        zip_code = ''

    if city:
        full_addr = '{0}, {1}, NC {2}'.format(addr, city, zip_code).strip()
    else:
        full_addr = '{0}, NC {1}'.format(addr, zip_code).strip()

    return full_addr


@register.inclusion_tag('db/snippets/alphabet_menu.html')
def get_alphabet_menu(alpha_list):
    """
    Renders a menu containing all letters of the alphabet. For letters which
    are in alpha_list, the letter links to the associated list of streets.
    The '#' sign links to streets which do not begin with letters, if such
    streets exist.
    """
    alphabet = '#' + string.ascii_lowercase  # '#' represents numbered streets
    letter_list = [entry['grouper'].lower() for entry in alpha_list]
    return {
        'alphabet': alphabet,
        'letter_list': letter_list,
    }


@register.simple_tag(takes_context=True)
def regroup_numbered_streets(context):
    """
    Regroups the 'alpha_list' context variable such that all streets which
    do not begin with letters are grouped by '#'.  If such streets exist,
    this will be the first entry in 'alpha_list.'
    """
    alpha_list = []
    numbered_streets = []
    for entry in context['alpha_list']:
        if entry['grouper'].lower() in string.ascii_lowercase:
            alpha_list.append(entry)
        else:
            numbered_streets.extend(entry['list'])
    if numbered_streets:
        entry = {'list': numbered_streets, 'grouper': '#'}
        alpha_list.insert(0, entry)
    context['alpha_list'] = alpha_list
    return ''


@register.simple_tag
def get_editor_email():
    return getattr(settings, 'OPENRURAL_EDITOR_EMAIL', '')


@register.filter
def truncatechars(value, arg):
    """Truncate the text when it exceeds a certain number of characters.
    Deletes the last word only if partial.
    Adds '...' at the end of the text.

    Based on http://djangosnippets.com/snippets/2653/
    """
    try:
        length = int(arg)
    except ValueError:
        return value

    if len(value) > length:
        if value[length:length + 1].isspace():
            return value[:length].rstrip() + '...'
        else:
            return value[:length].rsplit(' ', 1)[0].rstrip() + '...'
    else:
        return value
