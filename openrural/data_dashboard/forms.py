import urllib

from django import forms
from django.utils.safestring import mark_safe

from ebpub import geocoder

from openrural.data_dashboard.models import Geocode, Run


__all__ = ('GoogleMapsLink', 'GeocodeForm')


class GoogleMapsLink(forms.TextInput):

    def render(self, name, value, attrs=None):
        html = super(GoogleMapsLink, self).render(name, value, attrs=None)
        location = urllib.urlencode({'q': value.encode('utf-8')})
        link = "http://maps.google.com/maps?{0}".format(location)
        html += "&nbsp;&nbsp;<a href='{0}'>Google Map</a>".format(link)
        return mark_safe(html)


class GeocodeForm(forms.ModelForm):

    class Meta(object):
        model = Geocode

    def clean_location(self):
        location = self.cleaned_data['location']
        smart_geocoder = geocoder.SmartGeocoder()
        try:
            self.cleaned_data['result'] = smart_geocoder.geocode(location)
        except geocoder.InvalidBlockButValidStreet, e:
            raise forms.ValidationError('InvalidBlockButValidStreet')
        except (geocoder.GeocodingException, geocoder.ParsingError), e:
            raise forms.ValidationError(unicode(e))
        return location


class RunCommentForm(forms.ModelForm):

    class Meta(object):
        model = Run
        fields = ['comment']


class GeocodeFailuresSearch(forms.Form):
    """
    Used to search the name, description, and location fields of a geocode
    failures list.

    """
    search = forms.CharField(required=False)


class RunListFilter(forms.Form):
    """Used to filter scraper runs by status."""
    statuses = forms.MultipleChoiceField(
            widget=forms.CheckboxSelectMultiple(),
            choices=Run.STATUS_CHOICES,
            required=False
    )
