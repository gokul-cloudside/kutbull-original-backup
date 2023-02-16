from django.conf import settings
from django.conf.urls import patterns, include, url
from django.conf.urls.static import static
from django.contrib import admin
import debug_toolbar
from website.views import index
from organizations.backends import invitation_backend
from rest_framework.authtoken import views
from dgusers import views as dgviews
from license import views as lviews

urlpatterns = patterns('',
                       url(r'^$', index, name='landing_page'),
                       url(r'^web/', include('website.urls', namespace='website')),
                       url(r'^dashboards/', include('dashboards.urls', namespace='dashboards')),
                       url(r'^admin/', include(admin.site.urls)),
                       url(r'^dataglen/', include('errors.urls', namespace="errors")),
                       url(r'^dataglen/', include('config.urls', namespace="config")),
                       url(r'^dataglen/', include('action.urls', namespace="action")),
                       url(r'^events/', include('events.urls', namespace="events")),
                       url(r'^reports/', include('reports.urls', namespace="reports")),
                       url(r'^dataglen/', include('dataglen.urls', namespace="dataglen")),
                       url(r'^solar/', include('solarrms.urls', namespace="solar")),
                       url(r'^ioelab/', include('ioelab.urls', namespace="ioelab")),
                       url(r'^api/', include('rest.urls', namespace="api")),
                       #url(r'^api-token-auth/', views.obtain_auth_token),
                       url(r'^api-token-auth/', dgviews.DataGlenObtainAuthToken.as_view()),
                       url(r'^api-auth/', include('rest_framework.urls', namespace='rest_framework')),
                       url(r'^accounts/', include('allauth.urls')),
                       url(r'^invitations/', include(invitation_backend().get_urls())),
                       url(r'^hijack/', include('hijack.urls')),
                       url(r'helpdesk/', include('helpdesk.urls')),
                       url(r'dh/', include('ticketingsystem.urls')),
                       url(r'validate/', lviews.validate_signature),
                       url(r'add_signature/', lviews.add_signature),
                       url(r'delete_signature/', lviews.delete_signature),
                       # SWAGGER DOCS
                       url(r'^swagger/', include('rest_framework_swagger.urls')),
                       #admin utility url
                       url(r'^admin/solarrms/utility/', include('solarrms.admin_urls')),
                       ) + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
