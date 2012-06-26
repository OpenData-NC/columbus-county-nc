from django.conf.urls.defaults import *

from openrural.data_dashboard import views as dd


urlpatterns = patterns('',
    url(r'^$', dd.dashboard, name='dashboard'),
    url(r'^(?P<scraper_slug>[-\w]+)/$', dd.view_scraper, name='view_scraper'),
    url(r'^(?P<scraper_slug>[-\w]+)/run/$', dd.run_scraper,
        name='run_scraper'),
    url(r'^(?P<scraper_slug>[-\w]+)/(?P<run_id>[\d]+)/$',
        dd.view_run, name='view_run'),
    url(r'^(?P<scraper_slug>[-\w]+)/(?:(?P<run_id>[\d]+)/)?failures/',
        dd.list_failures, name='list_failures'),
    url(r'^(?P<scraper_slug>[-\w]+)/delete_news_items/',
        dd.delete_scraper_news_items, name='delete_scraper_news_items'),
)
