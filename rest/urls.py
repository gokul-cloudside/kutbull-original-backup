from rest_framework_nested import routers
from rest.views import SourcesViewSet, StreamsViewSet, DataRecordsSet, MultipleDataRecordsSet, MultipleSourcesDataRecords, TimeSeriesDataRecords, SMSManagerViewSet, ContactUsViewSet
from django.conf.urls import patterns, include, url
from action.views import ActionRecordsSet
from action.stream_views import ActionStreamsViewSet
from config.stream_views import ConfigStreamsViewSet
from config.views import ConfigRecordsSet
from solarrms.api_urls import router as solar_router
from solarrms.api_urls import inverter_router 
from solarrms.api_urls import plants_router, ticket_router, router2, v1_router, v1_plants_router, v1_plants_router_nested
from rest import views
from events.views import EventsViewSet
from customwidgets.views import WidgetsViewSet
from errors.views import ErrorStreamsViewSet, ErrorRecordsSet
from dwebdyn.urls import router as dataentry_router
from dgusers.urls import router as dg_users_router
from otp.api_urls import router as otp_router
from dgcomments.api_urls import router as comment_router
from solarrms.api_views_v2 import ConnectionTest, GetCurrentTime, DataTransferKaco

router = routers.SimpleRouter()
router.register(r'sources', SourcesViewSet, base_name="sources")
router.register(r'contactUs', ContactUsViewSet, base_name='contactUs')

sources_router = routers.NestedSimpleRouter(router, r'sources', lookup='source')
sources_router.register(r'streams', StreamsViewSet, base_name="streams")
sources_router.register(r'data', DataRecordsSet, base_name="data")
sources_router.register(r'action', ActionRecordsSet, base_name="action")
sources_router.register(r'action_streams', ActionStreamsViewSet, base_name="action_streams")
sources_router.register(r'config_streams', ConfigStreamsViewSet, base_name="config_streams")
sources_router.register(r'config', ConfigRecordsSet, base_name="config")
#commenting out below line so as change errors API url.
#sources_router.register(r'events', EventsViewSet, base_name="events")
sources_router.register(r'events', ErrorRecordsSet, base_name="events")
sources_router.register(r'error_streams', ErrorStreamsViewSet, base_name='error_streams')

router.register(r'multisources/data', MultipleDataRecordsSet, base_name="multisources")
router.register(r'widgets', WidgetsViewSet, base_name="widgets")
router.register(r'msources/data', MultipleSourcesDataRecords, base_name="multiplesources")
router.register(r'timeseries/data', TimeSeriesDataRecords, base_name="timeseriesdata")
router.register(r'sms', SMSManagerViewSet, base_name="send-sms")


router.register(r'public/connectiontest', ConnectionTest, base_name='connection_test')
router.register(r'public/time', GetCurrentTime, base_name='get_current_time')
router.register(r'import/inverterdata', DataTransferKaco, base_name='data_transfer_kaco')


urlpatterns = patterns('',
    url(r'docs/', views.docs, name='docs'),
    url(r'^', include(router.urls)),
    url(r'^', include(sources_router.urls)),
    url(r'solar/', include(solar_router.urls)),
    url(r'solar/', include(router2.urls)),
    url(r'solar/', include(plants_router.urls)),
    url(r'solar/', include(inverter_router.urls)),
    url(r'solar/', include(ticket_router.urls)),
    url(r'v1/solar/', include(v1_router.urls)),
    url(r'v1/solar/', include(v1_plants_router.urls)),
    url(r'v1/solar/', include(v1_plants_router_nested.urls)),
    url(r'v1/plant/', include(dataentry_router.urls)),
    url(r'v1/solar/', include(dg_users_router.urls)),
    url(r'v1/otp/', include(otp_router.urls)),
    url(r'v1/comments/', include(comment_router.urls)),
)




