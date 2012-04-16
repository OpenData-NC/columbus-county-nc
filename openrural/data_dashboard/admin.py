from django.contrib import admin

from openrural.data_dashboard.models import Scraper, Run, Stat


class ScraperAdmin(admin.ModelAdmin):
    list_display = ('slug', 'schema')


class RunAdmin(admin.ModelAdmin):
    list_display = ('id', 'scraper', 'date', 'end_date')


class StatAdmin(admin.ModelAdmin):
    list_display = ('id', 'run', 'name', 'value')


admin.site.register(Scraper, ScraperAdmin)
admin.site.register(Run, RunAdmin)
admin.site.register(Stat, StatAdmin)
