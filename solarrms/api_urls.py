from rest_framework_nested import routers
from solarrms.api_views import PlantsViewSet, InvertersViewSet, InvertersDataSet, PlantsEnergyData, \
    InverterEnergyData, PlantsPowerData, PlantEventsViewSet, PerformanceRatioData, PlantSummaryView, \
    PlantTicketViewSet, PlantTicketNewViewSet, TicketFollowUpView,CUFDataView, GroupsPowerData, SolarClientView, EnergyLossView, \
    PowerIrradiationData, V1_SolarClientView, V1_PlantSummaryView, V1_InverterLiveStatusView, PlantResidualData, \
    InvertersTotalYield, PlantDevicesView, InvertersTotalYieldExcel, MultipleDevicesMultipleStreamsView, PlantExcelReport,\
    EnergyPredictionView, CleaningDumpView, PlantKPIValues, MultipleDevicesMultipleStreamsDownloadView, SpecificYieldData, \
    V1_MobileSolarClientView, V1_AC_SLD_LiveStatusView, V1_PlantEnergyViewSet, AcrossPlantsDevicesView, DeviceTicketDetails,\
    PlantsSummaryDateRange,PlantAssociationViewSet, IdentifierTicketDetails, V1_WeatherDataViewSet,\
    V1_NewPredictionDataViewSet, V1_Insolation_View, InvertersEnergyFromPowerDaterange, AcrossPlantsInverters, PlantPdfReport,\
    V1_DSM_Charge_View, V1_DSM_Charge_Missing_Data_View, PortfolioExcelReport, MultipleDevicesMultipleStreamsDownloadViewNew

from widgets.views import WidgetViewSet, ClientWidgetViewSet

from solarrms.mobile_app.api_views import V1_Mobile_Client_Summary_CEO_View, V1_Mobile_Client_Summary_OandM_Manager_View,\
    V1_Mobile_Select_Plant_View, V1_Mobile_Plant_Summary_View

from oandmmanager.views import OandMPreferencesView, OandMTasksListView, OandMTaskItemView

from solarrms.api_views_v2 import EditUserPreferences, EditPlantPreferences, EditUserProfile,\
    UserSolarPlantWigetsConfigView, UserTableWidgetsConfigView, PlantGroupView, DataglenClientView,\
    V2_NewPredictionDataViewSet, GECleaningTrigger, CustomReportFormatView, OneDayPDFReport, PVSystAchievementReportDownload,\
    MonthlyGenerationBill, MonthlyPDFReport, AllPlantsDetails
from eventsframework.api_views import EventDetailViewSet, CompanyView, FieldTechnicianView, MaintenanceContractView

from solarrms2.api_views import BillingEntityView, BankAccountView, SolarEventsPriorityMappingView, \
    EnergyOffTakerView, EnergyContractView

from dganalysis.api import DataAnalysisViewSet, QueryOptionViewSet, AggregationFunctionViewSet, \
    DruidAnalysisViewSet, DevicesListViewSet, AnalysisDashboardView

router = routers.SimpleRouter()
router.register(r'plants', PlantsViewSet, base_name="plants")

plants_router = routers.NestedSimpleRouter(router, r'plants', lookup='plant')
plants_router.register(r'inverters', InvertersViewSet, base_name="inverters")
plants_router.register(r'energy', PlantsEnergyData, base_name="plant-energy")
plants_router.register(r'residual', PlantResidualData, base_name="plant-residual")
plants_router.register(r'power', PlantsPowerData, base_name="plant-power")
plants_router.register(r'events', PlantEventsViewSet, base_name="plant-events")
plants_router.register(r'status', PlantSummaryView, base_name="plant-status")
plants_router.register(r'performance', PerformanceRatioData, base_name="plant-performance")
plants_router.register(r'specific_yield', SpecificYieldData, base_name="plant-specific_yield")
plants_router.register(r'tickets', PlantTicketViewSet, base_name="tickets")
plants_router.register(r'newtickets', PlantTicketNewViewSet, base_name="newtickets")
plants_router.register(r'associations', PlantAssociationViewSet, base_name="associations")
plants_router.register(r'CUF', CUFDataView, base_name="CUF")
plants_router.register(r'groups-power', GroupsPowerData, base_name="groups-power")
plants_router.register(r'losses', EnergyLossView, base_name="energy-loss")
plants_router.register(r'irradiation-power', PowerIrradiationData, base_name="plant-irradiation-power")

inverter_router = routers.NestedSimpleRouter(plants_router, r'inverters', lookup="plant")
inverter_router.register(r'data', InvertersDataSet, base_name="data")
inverter_router.register(r'energy', InverterEnergyData, base_name="inverter-energy")

ticket_router = routers.NestedSimpleRouter(plants_router, r'tickets', lookup='plant')
ticket_router.register(r'followups', TicketFollowUpView, base_name='followups')

router2 = routers.SimpleRouter()
router2.register(r'summary', SolarClientView, base_name='summary')

v1_router = routers.SimpleRouter()
v1_router.register(r'client/summary',V1_SolarClientView, base_name='v1_client_summary')
v1_router.register(r'plants_summary',PlantsSummaryDateRange, base_name='v1_plants_summary_date_range')
v1_router.register(r'inverters_energy',InvertersEnergyFromPowerDaterange, base_name='v1_inverters_energy_date_range')
v1_router.register(r'client/summary/mobile',V1_MobileSolarClientView, base_name='v1_client_summary_mobile')

v1_router.register(r'client/widgets/data',ClientWidgetViewSet, base_name='v1_client_widget_data')

v1_router.register(r'client/summary/mobile/ceo',V1_Mobile_Client_Summary_CEO_View, base_name='v1_client_summary_mobile_ceo')
v1_router.register(r'client/summary/mobile/OandM',V1_Mobile_Client_Summary_OandM_Manager_View, base_name='v1_client_summary_mobile_OandM')
v1_router.register(r'client/summary/mobile/select',V1_Mobile_Select_Plant_View, base_name='v1_client_summary_select_a_plant')
v1_router.register(r'plant/summary/mobile',V1_Mobile_Plant_Summary_View, base_name='v1_plant_summary_mobile')

v1_router.register(r'client/portfolio-report',PortfolioExcelReport, base_name='v1_client_portfolio_report')

v1_router.register(r'devices',AcrossPlantsDevicesView, base_name='v1_across_plants_devices')
v1_router.register(r'devices/inverters',AcrossPlantsInverters, base_name='v1_across_plants_inverters')

v1_plants_router = routers.SimpleRouter()
v1_plants_router.register(r'plants', PlantsViewSet, base_name="plants")
v1_plants_router_nested = routers.NestedSimpleRouter(v1_plants_router, r'plants', lookup='plant')
v1_plants_router_nested.register(r'summary', V1_PlantSummaryView, base_name="v1_plant_summary")
v1_plants_router_nested.register(r'live', V1_InverterLiveStatusView, base_name="v1_inverter_live_data")
v1_plants_router_nested.register(r'live/ac', V1_AC_SLD_LiveStatusView, base_name="v1_ac_sld_live_data")
v1_plants_router_nested.register(r'total_yield', InvertersTotalYield, base_name="v1_plant_total_yield")
v1_plants_router_nested.register(r'energy/new', V1_PlantEnergyViewSet, base_name="v1_plant_energy")
v1_plants_router_nested.register(r'insolation', V1_Insolation_View, base_name="v1_plant_insolation")
v1_plants_router_nested.register(r'dsm', V1_DSM_Charge_View, base_name="v1_dsm_view")
v1_plants_router_nested.register(r'dsm/missing', V1_DSM_Charge_Missing_Data_View, base_name="v1_dsm_missing_view")
v1_plants_router_nested.register(r'devices', PlantDevicesView, base_name="v1_plant_devices")
v1_plants_router_nested.register(r'total_yield_excel', InvertersTotalYieldExcel, base_name="v1_plant_total_yield_excel")
v1_plants_router_nested.register(r'multiple_devices_streams', MultipleDevicesMultipleStreamsView, base_name="v1_multiple_devices_multiple_streams")
v1_plants_router_nested.register(r'multiple_devices_streams/data/download', MultipleDevicesMultipleStreamsDownloadView, base_name="v1_multiple_devices_multiple_streams_data_download")
v1_plants_router_nested.register(r'multiple_devices_streams/data/download/new', MultipleDevicesMultipleStreamsDownloadViewNew, base_name="v1_multiple_devices_multiple_streams_data_download_new")
v1_plants_router_nested.register(r'report', PlantExcelReport, base_name="v1_plant_report")
v1_plants_router_nested.register(r'prediction_dump', EnergyPredictionView, base_name="v1_prediction_dump")
v1_plants_router_nested.register(r'cleaning_dump', CleaningDumpView, base_name="v1_cleaning_dump")
v1_plants_router_nested.register(r'kpi', PlantKPIValues, base_name="v1_kpi")
v1_plants_router_nested.register(r'ticket_details', DeviceTicketDetails, base_name="v1_device_ticket_details")
v1_plants_router_nested.register(r'widgets/data', WidgetViewSet, base_name="v1_widget_data")
v1_plants_router_nested.register(r'association_details', IdentifierTicketDetails, base_name="v1_association_details")


v1_plants_router_nested.register(r'oandmmanager/taskitem', OandMTasksListView, base_name="v1_oandm_tasks")
v1_plants_router_nested.register(r'oandmmanager/taskitem/association', OandMTaskItemView, base_name="v1_oandm_task_items")
v1_plants_router_nested.register(r'oandmmanager/preferences', OandMPreferencesView, base_name="v1_oandm_preferences")
v1_plants_router_nested.register(r'weather-data', V1_WeatherDataViewSet, base_name="v1_plant_weather_data")

v1_plants_router_nested.register(r'prediction-data', V1_NewPredictionDataViewSet, base_name="v1_plant_weather_data")
v1_plants_router_nested.register(r'prediction-data-v2', V2_NewPredictionDataViewSet, base_name="v1_plant_weather_data")
v1_plants_router_nested.register(r'pdf-report', PlantPdfReport, base_name="v1_plant_pdf_report")
v1_plants_router_nested.register(r'onedaypdf', OneDayPDFReport, base_name="v1_onedaypdf")
v1_plants_router_nested.register(r'monthlypdf', MonthlyPDFReport, base_name="v1_onedaypdf")
v1_plants_router_nested.register(r'monthly_bill', MonthlyGenerationBill, base_name="v1_monthly_bill")
v1_plants_router_nested.register(r'cleaning-trigger', GECleaningTrigger, base_name="v1_cleaning_trigger")

v1_router.register(r'edituserpreferences', EditUserPreferences, base_name="edituserpreferences")
v1_router.register(r'editplantpreferences', EditPlantPreferences, base_name="editplantpreferences")

v1_router.register(r'client/events', EventDetailViewSet, base_name='v1_client_events')

v1_router.register(r'edituserprofile', EditUserProfile, base_name="edit_user_profile")

v1_router.register(r'userplantwidgetconfig', UserSolarPlantWigetsConfigView,
                   base_name="usersolarplantwigetsconfigview")

#solarrms2
v1_router.register(r'billingentityview', BillingEntityView, base_name="billing_entity_view")
v1_router.register(r'bankaccountview', BankAccountView, base_name="bank_account_view")
v1_router.register(r'energyofftaker', EnergyOffTakerView, base_name="energy_offtaker_view")
v1_router.register(r'priority_mappings', SolarEventsPriorityMappingView,
                   base_name="solar_events_priority_mapping_view")
v1_router.register(r'energycontract', EnergyContractView, base_name="energy_contract_view")

v1_router.register(r'widgets_config', UserTableWidgetsConfigView, base_name="user_table_widgets_config_view")
v1_router.register(r'dataglenclientview', DataglenClientView, base_name="dataglen_client_view")
v1_router.register(r'pvsyst_achievement', PVSystAchievementReportDownload, base_name="pvsyst_achievement_report_dowlnoad")

#group
plants_router.register(r'groups', PlantGroupView, base_name="solar_groups")

v1_router.register(r'companyview', CompanyView, base_name="company_view")
v1_router.register(r'ftview', FieldTechnicianView, base_name="field_technician_view")
v1_router.register(r'maintenance_contract', MaintenanceContractView, base_name="maintenance_contract_view")
v1_router.register(r'custom_report_format', CustomReportFormatView, base_name="custom_report_format_view")

v1_router.register(r'analysis', DataAnalysisViewSet, base_name="analysis")
v1_router.register(r'options', QueryOptionViewSet, base_name="analysis_options")
v1_router.register(r'functions', AggregationFunctionViewSet, base_name="analysis_functions")
v1_router.register(r'datawh', DruidAnalysisViewSet, base_name="datawh")
v1_router.register(r'deviceslist', DevicesListViewSet, base_name="deviceslist")
v1_router.register(r'analysis_dashboards', AnalysisDashboardView, base_name="analysis_dashboards")
v1_router.register(r'ap_data', AllPlantsDetails, base_name="ap_data")
