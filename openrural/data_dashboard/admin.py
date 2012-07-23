from django.contrib import admin
from django.db import models

from openrural.data_dashboard.models import Scraper, Run, Stat, Geocode
from openrural.data_dashboard.forms import GeocodeForm, GoogleMapsLink


class ScraperAdmin(admin.ModelAdmin):
    list_display = ('slug', 'schema')


class RunAdmin(admin.ModelAdmin):
    list_display = ('id', 'scraper', 'date', 'end_date')


class StatAdmin(admin.ModelAdmin):
    list_display = ('id', 'run', 'name', 'value')


class GeocodeAdmin(admin.ModelAdmin):
    list_display = ('id', 'run', 'date', 'success', 'location', 'name',
                    'zipcode')
    list_filter = ('success', 'date', 'name', 'scraper', 'zipcode')
    search_fields = ('location', 'description')
    ordering = ('-date',)
    readonly_fields = ('success', 'name', 'run', 'news_item', 'scraper',
                       'zipcode')
    form = GeocodeForm
    formfield_overrides = {
        models.CharField: {'widget': GoogleMapsLink},
    }
    def save_model(self, request, obj, form, change):
        obj.news_item.location = form.cleaned_data['result']['point']
        obj.news_item.save()
        obj.name = ''
        obj.success = True
        obj.save()


admin.site.register(Scraper, ScraperAdmin)
admin.site.register(Run, RunAdmin)
admin.site.register(Stat, StatAdmin)
admin.site.register(Geocode, GeocodeAdmin)
