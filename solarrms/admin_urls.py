from django.conf.urls import patterns, include, url
from solarrms.admin_views import AdminInverterView, AdminMeterView, \
    AdminSetMultiplicationFactorView, get_solar_group_for_plant_admin,\
    get_source_for_plant_group_admin, get_stream_for_sources_admin, AdminAJBView,\
    AdminAddClientAndPlantView, AdminSolarFieldView, AdminPayloadErrorCheckView,\
    get_solar_plant, AdminResetPasswordView

urlpatterns = patterns('',
                       url(r'^inverter/$', AdminInverterView.as_view()),
                       url(r'^meter/$', AdminMeterView.as_view()),
                       url(r'^multiplication-factor/$', AdminSetMultiplicationFactorView.as_view()),
                       url(r'^ajb/$', AdminAJBView.as_view()),
                       url(r'^get-solar-plant/$', get_solar_plant),
                       url(r'^get-solar-group-for-plant/$', get_solar_group_for_plant_admin),
                       url(r'^get-source-key/$', get_source_for_plant_group_admin),
                       url(r'^get-source-stream/$', get_stream_for_sources_admin),
                       url(r'^add_client_and_plant/$', AdminAddClientAndPlantView.as_view()),
                       url(r'^solar-field/$', AdminSolarFieldView.as_view()),
                       url(r'^payload-error-check/$', AdminPayloadErrorCheckView.as_view()),
                       url(r'^reset-password/$', AdminResetPasswordView.as_view()),
                       )
