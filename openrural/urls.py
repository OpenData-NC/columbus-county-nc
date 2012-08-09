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

from django.conf import settings
from django.conf.urls.defaults import *

from obadmin import admin


admin.autodiscover()

urlpatterns = patterns(
    '',
    (r'^admin/', include(admin.site.urls)),
    (r'^data-dashboard/', include('openrural.data_dashboard.urls')),
    # ebpub provides all the UI for an openblock site.
    (r'^', include('ebpub.urls')),
)

if settings.DEBUG:
    urlpatterns += patterns('',
        url(r'^{0}(?P<path>.*)$'.format(settings.MEDIA_URL.lstrip('/')),
            'django.views.static.serve', {'document_root': settings.MEDIA_ROOT}
        ),
    )
