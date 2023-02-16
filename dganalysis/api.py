import datetime
from .models import DataAnalysis, QueryOption, AggregationFunction, DataSlice, CssTemplate
from rest_framework import serializers
from rest_framework import viewsets
from django.db.models import Q
from rest_framework import authentication, permissions, status
from rest_framework.response import Response
from dashboards.mixins import ProfileDataInAPIs
from .models import AnalysisDashboard, AnalysisConfiguration
from dateutil import parser
import json

class CssTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CssTemplate
        fields = ('id', 'css', 'viz_type')
        read_only_fields = ('id', )


class QueryOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = QueryOption
        fields = ('id', 'data_family', 'display_name')
        read_only_fields = ('id', 'data_family', 'display_name')


from solarrms.models import *
from solarrms.solarutils import filter_solar_plants
from django.db.models import F

def get_plants_details(plants_slugs):
    groups = SolarGroup.objects.filter(plant__slug__in=plants_slugs).annotate(sourceKey=F('id')).values('sourceKey', 'name',
                                                                                                        'plant__name', 'plant__slug')

    inverters = IndependentInverter.objects.filter(plant__slug__in=plants_slugs).values('sourceKey','name',
                                                                                        'plant__name', 'plant__slug')

    meters = EnergyMeter.objects.filter(plant__slug__in=plants_slugs).values('sourceKey', 'name',
                                                                             'plant__name', 'plant__slug')

    weather_stations = IOSensorField.objects.filter(plant_meta__plant__slug__in=plants_slugs).annotate(sourceKey=F('id'),
                                                                                                       plant__name=F('plant_meta__plant__name'),
                                                                                                       plant__slug=F('plant_meta__plant__slug'),
                                                                                                       name=F('solar_field__displayName')).values('sourceKey', 'name', 'plant__name', 'plant__slug')

    return {'data': {'sections': groups,
                     'inverters': inverters,
                     'meters': meters,
                     'weather_stations': weather_stations
                     },
            'mappings': {
                'Energy Export': {'category': 'sections', 'heading': 'Plants Sections'},
                'Performance Indicators': {'category': 'sections', 'heading': 'Plants Sections'},
                'Inverters': {'category': 'inverters', 'heading': 'Inverters'},
                'Meters': {'category': 'meters', 'heading': 'Energy Meters'},
                'Weather Parameters': {'category': 'weather_stations', 'heading': 'Weather Stations'},
            }}


class DevicesListViewSet(ProfileDataInAPIs, viewsets.ReadOnlyModelViewSet):
    authentication_classes = (authentication.TokenAuthentication, authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def list(self, request, *args, **kwargs):
        try:
            context = self.get_profile_data(**kwargs)
            plants = filter_solar_plants(context)
            plants_slugs = map(lambda plant: plant.slug, plants)
            data = get_plants_details(plants_slugs)
            return Response(data, status=200)
        except Exception as exc:
            return Response(status=400)


class QueryOptionViewSet(viewsets.ReadOnlyModelViewSet):

    authentication_classes = (authentication.TokenAuthentication, authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    queryset = QueryOption.objects.all()
    serializer_class = QueryOptionSerializer


class AggregationFunctionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AggregationFunction
        fields = ('id', 'name')
        read_only_fields = ('id', 'name')


class AggregationFunctionViewSet(viewsets.ReadOnlyModelViewSet):

    authentication_classes = (authentication.TokenAuthentication, authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    queryset = AggregationFunction.objects.all()
    serializer_class = AggregationFunctionSerializer


class DataSliceSerializer(serializers.ModelSerializer):
    query_options = QueryOptionSerializer(many=False, read_only=False)
    css_options = CssTemplateSerializer(many=False, read_only=False)
    instantaneous_aggregation = AggregationFunctionSerializer(many=False, read_only=False)
    daily_aggregation = AggregationFunctionSerializer(many=False, read_only=False)
    monthly_aggregation = AggregationFunctionSerializer(many=False, read_only=False)

    class Meta:
        model = DataSlice
        fields = ('id', 'name', 'description', 'instantaneous_minutes',
                  'query_options', 'css_options', 'instantaneous_aggregation',
                  'daily_aggregation', 'monthly_aggregation')
        read_only_fields = ('id',)


class DataAnalysisSerializer(serializers.ModelSerializer):
    slices = DataSliceSerializer(many=True, read_only=False)

    class Meta:
        model = DataAnalysis
        fields = ('id', 'name', 'category', 'description', 'system_defined',
                  'admin_view', 'enable_client_view', 'slices')
        read_only_fields = ('id', 'system_defined',)

    def create(self, validated_data):
        user = self.request.user
        dg_client = user.role.dg_client

        slices_data = validated_data.pop('slices')
        analysis = DataAnalysis.objects.create(category="Solar Custom",
                                               system_defined=False,
                                               dg_client=dg_client,
                                               created_by=user,
                                               **validated_data)
        for slice_data in slices_data:
            DataSliceSerializer.objects.create(analysis=analysis, **slice_data)
        return analysis


class DataAnalysisSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = DataAnalysis
        fields = ('id', 'name', 'category', 'description', 'system_defined')
        read_only_fields = ('id', 'system_defined',)


class DataAnalysisViewSet(ProfileDataInAPIs, viewsets.ModelViewSet):

    authentication_classes = (authentication.TokenAuthentication, authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    serializer_class = DataAnalysisSerializer

    def get_serializer_class(self):
        if self.action == 'list':
            return DataAnalysisSummarySerializer
        else:
            return DataAnalysisSerializer

    def get_queryset(self):
        user = self.request.user
        dg_client = user.role.dg_client
        role = user.role.role
        admin = user.role.enable_preference_edit

        # special case for vector
        if dg_client.slug == "vector":
            qa = DataAnalysis.objects.filter(system_defined=False,
                                             dg_client=dg_client)
            return qa.filter(is_active=True)

        # if the role is internal
        if role in ["CEO", "O&M_MANAGER", "SITE_ENGINEER"]:
            # 1. get system defined analysis
            # 2. get analysis defined by the dg_client of the user AND
            # admin_view = False if the user is not user.enable_preference_edit
            if admin:
                qa = DataAnalysis.objects.filter(Q(system_defined=True) |
                                                 Q(system_defined=False, dg_client=dg_client))
            else:
                qa = DataAnalysis.objects.filter(Q(system_defined=True) |
                                                 Q(system_defined=False, dg_client=dg_client, admin_view=False))
        else:
            # if the role is external
            # 1. get system defined analysis + enable_client_view
            # 2. get analysis defined by the dg_client of the user
            # + enable_client_view = True
            qa = DataAnalysis.objects.filter(Q(system_defined=True, enable_client_view=True) |
                                             Q(system_defined=False, dg_client=dg_client, enable_client_view=True))

        return qa.filter(is_active=True)


class DruidAnalysisViewSet(ProfileDataInAPIs, viewsets.ViewSet):

    authentication_classes = (authentication.TokenAuthentication, authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def create(self, request, id=None, **kwargs):
        """

        :param request:
        :param id:
        :param kwargs:
        :return:
        """
        try:
            from dganalysis.druid_query_converter import fetch_data_from_druid
            payload = self.request.data
            plants = payload['plants']
            interval = payload['interval']
            granularity = payload['granularity']
            analysis_id = payload['analysis_id']
            other_options = {}
            inverter_source_keys = []
            meter_source_keys = []
            solar_group_ids = []
            weather_station_source_keys = []
            if 'sections' in payload:
                group_ids = payload['sections']
                if group_ids:
                    solar_group_ids = group_ids

            if 'inverters' in payload:
                inverter_ids = payload['inverters']
                if inverter_ids:
                    inverter_source_keys = inverter_ids

            if 'meter' in payload:
                meter_ids = payload['meter']
                if meter_ids:
                    meter_source_keys.extend(meter_ids)

            if 'weather_stations' in payload:
                weather_station_ids = payload['weather_stations']
                if weather_station_ids:
                    weather_station_source_keys.extend(weather_station_ids)

            other_options['inverters'] = inverter_source_keys
            other_options['meters'] = meter_source_keys
            other_options['solar_group'] = solar_group_ids
            other_options['weather_stations'] = weather_station_source_keys

            other_options['raw_interval'] = interval

            data = fetch_data_from_druid(granularity, interval, plants, analysis_id, other_options)
            return Response(data=data, status=status.HTTP_200_OK)
        except Exception as exception:
            return Response("INTERNAL_SERVER_ERROR %s" % exception, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


'''
https://dataglen.com/api/v1/solar/analysis_dashboards/
'''
class AnalysisDashboardView(ProfileDataInAPIs, viewsets.ViewSet):
    authentication_classes = (authentication.TokenAuthentication, authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)
    lookup_field = 'dashboard_id'

    def list(self, request, **kwargs):
        try:
            user = self.request.user
            #if not user.role.enable_preference_edit:
            #    return Response("Not Authorized", status=status.HTTP_401_UNAUTHORIZED)
            client = self.request.user.role.dg_client
            all_analysis_dashboards = AnalysisDashboard.objects.filter(created_by=user).values('id','title','editable_by_others','enabled_for_admins')
            for dash in all_analysis_dashboards:
                dash['dashboard_id'] = dash.pop('id')

            return Response(data=all_analysis_dashboards, status=status.HTTP_200_OK)
        except Exception as exception:
            logger.debug("Error in list : %s" % exception)
            return Response("INTERNAL_SERVER_ERROR %s " % exception, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def retrieve(self, request, dashboard_id=None, **kwargs):
        '''
        Retrieves details of single dashboard with all analysis/widgets
        :param request:
        :param dashboard_id:
        :param kwargs:
        :return:
        '''
        try:
            user = self.request.user
            #if not user.role.enable_preference_edit:
            #    return Response("Not Authorized", status=status.HTTP_401_UNAUTHORIZED)
            payload_to_send = {}
            try:
                a_dashboard = AnalysisDashboard.objects.get(id=dashboard_id, created_by=user)
            except Exception as exception:
                return Response("INTERNAL_SERVER_ERROR  analysis dashboard not found with given id for this user: %s " % exception, \
                                status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            payload_to_send ={'dashboard_id':a_dashboard.id,'title':a_dashboard.title, \
                              'css': json.loads(a_dashboard.css.css),\
                              'editable_by_others':a_dashboard.editable_by_others,\
                              'enabled_for_admins':a_dashboard.enabled_for_admins}
            all_analysis_for_this_dashboard_objs = a_dashboard.analysis_configurations.all()
            l = []
            for analysis in all_analysis_for_this_dashboard_objs:
                if analysis.interval=='live':
                    # 2018-09-11/2018-09-12
                    interval = datetime.date.today().strftime("%Y-%m-%d") + "/" + \
                               (datetime.date.today()+datetime.timedelta(days=1)).strftime("%Y-%m-%d")
                else:
                    interval = analysis.interval

                l.append({ "analysis_id": analysis.analysis.id,
                                                "interval": interval,
                                                "col": analysis.col,
                                                "dashboard_id": analysis.dashboard.id,
                                                "size_x": analysis.size_x,
                                                "size_y": analysis.size_y,
                                                "granularity": analysis.granularity,
                                                "created_by_id": analysis.created_by_id,
                                                "dashboard_analysis_id": analysis.id,
                                                "row": analysis.row,
                                                "css": json.loads(analysis.css.css),
                                               "plant_slugs": analysis.plants.all().values_list('slug',flat=True)})
            payload_to_send["all_analysis_for_this_dashboard"] = l

            return Response(data=payload_to_send, status=status.HTTP_200_OK)
        except Exception as exception:
            logger.debug("Error in retrieve: %s" % exception)
            return Response("INTERNAL_SERVER_ERROR %s " % exception, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def interval_check(self,new_interval):
        '''
        :param new_interval:
        :return:
        '''
        # if interval is live just store string 'live'
        if new_interval == 'live':
            return 'live'
        # if interval is not live and is historic dates it should be in format "2018-09-11/2018-09-12"
        # and should not be future a timestamp
        else:
            try:
                t1, t2 = new_interval.split('/')
                dt1 = parser.parse(t1).date()
                dt2 = parser.parse(t2).date()
                today_date = datetime.date.today()
                # Check for future timestamps
                if (dt1 > today_date or dt2 > (today_date + datetime.timedelta(days=1))) and (dt1 < dt2):
                    logger.debug("time for interval is wrong = %s" % new_interval)
                    return False
                else:
                    return new_interval
            except Exception as exception:
                logger.debug("time format for interval is wrong = %s" % new_interval)
                return False
    def partial_update(self, request, dashboard_id=None, **kwargs):
        '''
        It will "Create, Edit, Update, Delete" analysis in a dashboard.
        :param request:
        :param dashboard_id:
        :param kwargs:
        :return:
        '''
        try:
            user = self.request.user
            client = user.role.dg_client
            all_slugs = list(SolarPlant.objects.filter(groupClient=client).values_list('slug',flat=True))
            if not user.role.enable_preference_edit:
                return Response("Not Authorized", status=status.HTTP_401_UNAUTHORIZED)
            try:
                payload = self.request.data
                # In case both dashboard and and analysis are being created at same time following distinction is required
                if "analysis_configs_list" in payload:
                    analysis_configs_list = payload['analysis_configs_list']
                    dashboard_id = self.request.data['dashboard_id']
                # If you want to delete existing analysis from the dashboard
                elif "delete_these_dashboard_analysis" in payload:
                    list_of_ids_to_delete_dashboard_analysis = payload["delete_these_dashboard_analysis"]
                # If you already have analysis and you want to edit existing analysis then...
                else:
                    analysis_configs_list = payload
            except Exception as exception:
                logger.debug("Payload problems in  partial update %s" % exception)
                return Response("Please specify payload in request body", status=status.HTTP_400_BAD_REQUEST)

            try:
                a_dashboard = AnalysisDashboard.objects.get(id=dashboard_id, created_by=user)
                list_of_all_analysis_ids_for_this_dashboard = a_dashboard.analysis_configurations.all().values_list('id',flat=True)
            except Exception as exception:
                logger.debug("No format found in %s" % exception)
                return Response("format is not found", status=status.HTTP_400_BAD_REQUEST)

            if "delete_these_dashboard_analysis" in payload:
                if set(list_of_ids_to_delete_dashboard_analysis).issubset(set(list_of_all_analysis_ids_for_this_dashboard)):
                    for id_to_delete in list_of_ids_to_delete_dashboard_analysis:
                        try:
                            existing_analysis_obj_to_delete = AnalysisConfiguration.objects.get(id=id_to_delete)
                            existing_analysis_obj_to_delete.delete()
                        except Exception as exception:
                            return Response(data="Analysis id not found %s " %exception, status=status.HTTP_400_BAD_REQUEST)
                    return Response(data="Analysis Deleted %s" %str(list_of_ids_to_delete_dashboard_analysis), status=status.HTTP_200_OK)
                else:
                    return Response(data="Dashboard Analysis Ids do not belong to this owner", status=status.HTTP_400_BAD_REQUEST)

            # get list of analysis configs, create or edit analysis objects and add/remove plants from it
            for analysis_config in analysis_configs_list:
                # update existing dashboard analysis. validate if the id belongs to the same dashboard
                if "dashboard_analysis_id" in analysis_config and analysis_config['dashboard_analysis_id'] in list_of_all_analysis_ids_for_this_dashboard:
                    existing_analysis_obj = AnalysisConfiguration.objects.get(id=analysis_config['dashboard_analysis_id'])
                    if 'col' in analysis_config:
                        existing_analysis_obj.col = analysis_config['col']
                    if 'row' in analysis_config:
                        existing_analysis_obj.row = analysis_config['row']
                    if 'size_x' in analysis_config:
                        existing_analysis_obj.size_x = analysis_config['size_x']
                    if 'size_y' in analysis_config:
                        existing_analysis_obj.size_y = analysis_config['size_y']
                    if 'granularity' in analysis_config:
                        existing_analysis_obj.granularity = analysis_config['granularity']
                    if 'interval' in analysis_config:
                        new_interval = self.interval_check(analysis_config['interval'])
                        if new_interval:
                            existing_analysis_obj.interval = new_interval
                        else:
                            logger.debug("time format for interval is wrong = %s" % new_interval)
                            return Response("Something went wrong while converting interval",
                                            status=status.HTTP_400_BAD_REQUEST)

                    if 'plant_slugs' in analysis_config:
                        if set(analysis_config["plant_slugs"]).issubset(set(all_slugs)):
                            # check for if you need to add the slugs
                            all_plants_already_added = set(existing_analysis_obj.plants.all().values_list('slug',flat=True))
                            new_plants_list = set(analysis_config["plant_slugs"])
                            plants_to_delete = all_plants_already_added - new_plants_list
                            plants_to_add = new_plants_list - all_plants_already_added
                            for slug in plants_to_add:
                                existing_analysis_obj.plants.add(SolarPlant.objects.get(slug=slug))
                            for slug in plants_to_delete:
                                existing_analysis_obj.plants.remove(SolarPlant.objects.get(slug=slug))
                        else:
                            logger.debug("**** unnkown plant slugs ####")
                    existing_analysis_obj.save()
                else:
                    analysis_id = analysis_config['analysis_id']
                    if "plant_slugs" in analysis_config:
                        # Check if all plant slugs belong to same client
                        if set(analysis_config["plant_slugs"]).issubset(set(all_slugs)):
                            col = analysis_config['col'] if 'col' in analysis_config else 0
                            row = analysis_config['row'] if 'row' in analysis_config else 0
                            size_x = analysis_config['size_x'] if 'size_x' in analysis_config else 0
                            size_y = analysis_config['size_y'] if 'size_y' in analysis_config else 0
                            granularity = analysis_config['granularity'] if 'granularity' in analysis_config else "hour"
                            new_interval = self.interval_check(analysis_config['interval'])
                            if not new_interval:
                                logger.debug("time format for interval is wrong = %s" % new_interval)
                                return Response("Something went wrong while converting interval",
                                                status=status.HTTP_400_BAD_REQUEST)
                            # Now everything looks fine Create a new object
                            new_analysis_config_obj = AnalysisConfiguration.objects.create(analysis_id=analysis_id, \
                                                                                           dashboard=a_dashboard,
                                                                                           created_by=user,\
                                                                                           interval = new_interval, \
                                                                                           granularity = granularity,\
                                                                                           col=col, row=row, \
                                                                                           size_x=size_x, size_y=size_y)
                            for slug in analysis_config["plant_slugs"]:
                                new_analysis_config_obj.plants.add(SolarPlant.objects.get(slug=slug))
                        else:
                            logger.debug("**** unnkown plant slugs ####")

            if "analysis_configs_list" in payload:
                return self.list(request, **kwargs)
            return Response(data={"dashboard_id":dashboard_id, "title":a_dashboard.title}, status=status.HTTP_200_OK)
        except Exception as exception:
            logger.debug("Error in partial update: %s" % exception)
            return Response("INTERNAL_SERVER_ERROR in partial update; %s " % exception, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def create(self, request, **kwargs):
        '''
        This creates new dashboard: either without any analysis or with list of analysis. List of analysis is then passed
        to partial_update to add in the dashboard.
        :param request:
        :param kwargs:
        :return:
        '''
        try:
            user = self.request.user
            if not user.role.enable_preference_edit:
                return Response("Not Authorized", status=status.HTTP_401_UNAUTHORIZED)
            try:
                payload = self.request.data
            except Exception as exc:
                logger.debug("Payload problems %s" % exc)
                return Response("Please specify payload in request body: %s" % exc, status=status.HTTP_400_BAD_REQUEST)
            if not 'title' in payload:
                logger.debug("Payload problems : specify title")
                return Response("Please specify payload in request body: specify title", \
                                status=status.HTTP_400_BAD_REQUEST)
            # empty css is just a placeholder
            csst = CssTemplate.objects.create(css="This is default css text for analysis dashboard", viz_type="line")
            editable_by_others = payload['editable_by_others'] if 'editable_by_others' in payload else False
            enabled_for_admins = payload['enabled_for_admins'] if 'enabled_for_admins' in payload else True
            dash1 = AnalysisDashboard.objects.create(title=payload['title'], created_by=user, \
                                                     css=csst,editable_by_others=editable_by_others, \
                                                     enabled_for_admins=enabled_for_admins)
            dashboard_id = dash1.id
            title = dash1.title
            if "analysis_configs_list" in payload:
                self.request.data['dashboard_id'] = dash1.id
                return self.partial_update(self, request,  **kwargs)
            else:
                return Response(data={"dashboard_id":dashboard_id, "title":title}, \
                                status=status.HTTP_200_OK)
        except Exception as exception:
            logger.debug("Error in list plant widget config: %s" % exception)
            return Response("INTERNAL_SERVER_ERROR %s " % exception, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

