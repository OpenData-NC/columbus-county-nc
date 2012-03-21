from django.conf.urls.defaults import *

from openrural.data_dashboard import views as dd


urlpatterns = patterns('',
    url(r'^$', dd.dashboard, name='dashboard'),
)
