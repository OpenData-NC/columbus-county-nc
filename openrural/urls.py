#   Copyright 2011 OpenPlans and contributors
#
#   This file is part of OpenBlock
#
#   OpenBlock is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   OpenBlock is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with OpenBlock.  If not, see <http://www.gnu.org/licenses/>.
#

from django.conf.urls.defaults import *

from ebpub.db import views as db_views
from obadmin import admin

from openrural import views


admin.autodiscover()


urlpatterns = patterns(
    '',

    (r'^admin/', include(admin.site.urls)),

    (r'^data-dashboard/', include('openrural.data_dashboard.urls')),

    # Override specific ebpub URL to redirect to redirect to another page.
    url(r'^locations/([-_a-z0-9]{1,32})/([-_a-z0-9]{1,32})/recent/$', 
        db_views.place_detail_timeline, 
        {'place_type': 'location', 'show_upcoming': False}, 
        name='ebpub-location-recent'
    ),
    url(r'^locations/([-_a-z0-9]{1,32})/([-_a-z0-9]{1,32})/$', 
        views.redirect_place_detail, 
        {'place_type': 'location', 'show_upcoming': False}
    ),

    # ebpub provides the remaining UI for an OpenBlock site.
    (r'^', include('ebpub.urls')),
)
