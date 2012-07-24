from django.core.urlresolvers import reverse
from django.http import HttpResponsePermanentRedirect


def redirect_place_detail(request, *args, **kwargs):
    """Redirects OpenBlock's place_detail_timeline URL for UI consistency."""
       
    return HttpResponsePermanentRedirect(request.path + 'recent/')
