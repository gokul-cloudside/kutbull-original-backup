from rest_framework import serializers
from solarrms2.models import BillingEntity, BankAccount, EnergyOffTaker, EnergyContract, SolarEventsPriorityMapping
from dashboards.models import DataglenGroup
from dashboards.mixins import ProfileDataInAPIs
from rest_framework import status, viewsets, authentication, permissions
from rest_framework.response import Response
from dashboards.models import DataglenClient
from solarrms.models import SolarPlant
from solarrms2.settings import currency_list
from organizations.models import Organization,OrganizationUser
from eventsframework.models import Company, MaintenanceContract
from solarrms.solarutils import filter_solar_plants
from datetime import datetime
from solarrms.api_views import update_tz
from dateutil import parser


import logging
logger = logging.getLogger('dataglen.rest_views')
logger.setLevel(logging.DEBUG)


event_types_all = ['GATEWAY_POWER_OFF',
                   'GATEWAY_DISCONNECTED',
                   'INVERTERS_DISCONNECTED',
                   'AJBS_DISCONNECTED',
                   'INVERTERS_NOT_GENERATING',
                   'INVERTERS_ALARMS',
                   'AJB_STRING_CURRENT_ZERO_ALARM',
                   'PANEL_CLEANING',
                   'INVERTERS_UNDERPERFORMING',
                   'MPPT_UNDERPERFORMING',
                   'AJB_UNDERPERFORMING']
priority_types_all = ['LOW', 'MEDIUM', 'HIGH', 'URGENT', 'COMMUNICATION ERROR', 'INFORMATION', 'NO ALERT']


class DataGlenClientSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(label='id', read_only=True)
    name = serializers.CharField(max_length=200, label='client_name')

    class Meta:
        model = DataglenClient
        fields = ('id', 'name')


class BillingEntitySerializer(serializers.ModelSerializer):
    dataglen_client = DataGlenClientSerializer(label="client_profile")
    id = serializers.IntegerField(label='id', read_only=True)

    class Meta:
        model = BillingEntity
        fields = ('id', 'dataglen_client', 'registered_office_address', 'cin_number', 'email', 'tel_number',
                  'website_address', 'tax_details_primary', 'tax_details_secondary')

    def create(self, validated_data):
        dg = self.context['request'].user.role.dg_client
        billing_entity = BillingEntity.objects.create(dataglen_client=dg, **validated_data)
        return billing_entity


class BillingEntityView(ProfileDataInAPIs, viewsets.ModelViewSet):
    authentication_classes = (authentication.TokenAuthentication, authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = BillingEntitySerializer

    def get_queryset(self):
        if not self.request.user.role.enable_preference_edit:
            return Response("Not Authorized", status=status.HTTP_401_UNAUTHORIZED)

        return BillingEntity.objects.filter(dataglen_client=self.request.user.role.dg_client)


class BankAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = BankAccount
        fields = ('id', 'account_bank', 'beneficiary_name', 'account_number', 'account_ifsc_code', \
                  'bank_address', 'account_micr_code', 'account_branch_code')

    def create(self, validated_data):
        dg = self.context['request'].user.role.dg_client
        billing_entity = BillingEntity.objects.get(dataglen_client=dg)

        bank_account = BankAccount.objects.create(billing_entity=billing_entity, **validated_data)
        return bank_account


class BankAccountView(ProfileDataInAPIs, viewsets.ModelViewSet):
    authentication_classes = (authentication.TokenAuthentication, authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = BankAccountSerializer

    def get_queryset(self):
        if not self.request.user.role.enable_preference_edit:
            return Response("Not Authorized", status=status.HTTP_401_UNAUTHORIZED)
        dg = self.request.user.role.dg_client
        billing_entity = BillingEntity.objects.filter(dataglen_client=dg)
        return BankAccount.objects.filter(billing_entity=billing_entity)


class EnergyOffTakerSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(label='id', read_only=True)

    class Meta:
        model = EnergyOffTaker
        fields = (
        'id', 'name', 'groupLogo', 'registered_name', 'registered_office_address', 'cin_number', 'email', 'tel_number',
        'website_address', 'tax_details_primary', 'tax_details_secondary')

    def create(self, validated_data):
        dgc = self.context['request'].user.role.dg_client
        off_taker = EnergyOffTaker.objects.create(groupClient=dgc, **validated_data)
        return off_taker


class EnergyOffTakerView(ProfileDataInAPIs, viewsets.ModelViewSet):
    authentication_classes = (authentication.TokenAuthentication, authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = EnergyOffTakerSerializer

    def get_queryset(self):
        if not self.request.user.role.enable_preference_edit:
            return Response("Not Authorized", status=status.HTTP_401_UNAUTHORIZED)
        return EnergyOffTaker.objects.filter(groupClient=self.request.user.role.dg_client)


class SolarPlantSerializer(serializers.ModelSerializer):
    # id = serializers.IntegerField(label='id', read_only=True)
    # location = serializers.CharField(max_length=250, label='location')
    class Meta:
        model = SolarPlant
        fields = ('id', 'location', 'name')


class SolarEventsPriorityMappingSerialiser(serializers.ModelSerializer):
    all_event_types = serializers.SerializerMethodField('event_types_all')

    def event_types_all(self, SolarEventsPriorityMapping):
        l = event_types_all
        return l

    class Meta:
        model = SolarEventsPriorityMapping
        fields = ('id', 'client', 'event_type', 'priority', 'html_color_code', 'all_event_types')

    def create(self, validated_data):
        user_role = self.context['request'].user.role
        if not user_role.enable_preference_edit:
            return Response("Not Authorized", status=status.HTTP_401_UNAUTHORIZED)
        # dg_client = user_role.dg_client
        event = validated_data['event_type']
        priority = validated_data['priority']

        if not event in event_types_all and priority in priority_types_all:
            logger.debug("event or priority not valid")
            return Response("INTERNAL_SERVER_ERROR: event or priority not valid",
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        else:
            priority_mapping = SolarEventsPriorityMapping.objects.create(**validated_data)
            return priority_mapping


class SolarEventsPriorityMappingView(ProfileDataInAPIs, viewsets.ModelViewSet):
    authentication_classes = (authentication.TokenAuthentication, authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = SolarEventsPriorityMappingSerialiser

    def get_queryset(self):
        if not self.request.user.role.enable_preference_edit:
            return Response("Not Authorized", status=status.HTTP_401_UNAUTHORIZED)
        return SolarEventsPriorityMapping.objects.filter(client=self.request.user.role.dg_client)


class EnergyContractView(ProfileDataInAPIs, viewsets.ViewSet):
    authentication_classes = (authentication.TokenAuthentication, authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)
    lookup_field = 'id'

    def list(self, request, id=None,**kwargs):
        """

        :param request:
        :param kwargs:
        :return:
        """
        try:
            if not self.request.user.role.enable_preference_edit:
                return Response("Not Authorized", status=status.HTTP_401_UNAUTHORIZED)
            dg_client = self.request.user.role.dg_client
            plant_slug = request.query_params.get("plant_slug", None)
            if plant_slug:
                plants = SolarPlant.objects.filter(slug=plant_slug).values('id', 'name')
            else:
                plants = SolarPlant.objects.filter(groupClient=dg_client).values('id', 'name')
            plant_ids = []
            for plant in plants:
                plant_ids.append(plant['id'])
            energy_contracts = EnergyContract.objects.filter(plant_id__in=plant_ids) \
                .values('id', 'contact_name','start_date', 'end_date', 'plant__id','plant__name', 'off_taker__id','off_taker__name',
                        'ppa_price', 'currency', 'late_payment_penalty_clause', 'early_payment_offset_days',
                        'early_payment_discount_factor')

            master_payload = {}
            for contract in energy_contracts:
                start_date = contract.pop('start_date')
                end_date = contract.pop('end_date')
                try:
                    start_date = datetime.combine(start_date, datetime.min.time())
                    end_date = datetime.combine(end_date, datetime.min.time())
                except:
                    return Response("please specify start and end time in correct format",
                                    status=status.HTTP_400_BAD_REQUEST)
                contract['start_date'] = start_date
                contract['end_date'] = end_date
                contract['plant_id'] = contract.pop('plant__id')
                contract['contract_name'] = contract.pop('contact_name')
                contract['plant_name'] = contract.pop('plant__name')
                contract['off_taker_id'] = contract.pop('off_taker__id')
                contract['off_taker_name'] = contract.pop('off_taker__name')
            master_payload['all_energy_contracts'] = energy_contracts
            master_payload['all_plants'] = plants
            all_offtakers = EnergyOffTaker.objects.filter(groupClient=self.request.user.role.dg_client).values('id', 'name','registered_name')
            master_payload['all_offtakers'] = all_offtakers
            master_payload['currency_list'] = currency_list


            return Response(data=master_payload, status=status.HTTP_200_OK)
        except Exception as exception:
            logger.debug("Error in list EnergyContract: %s" % exception)
            return Response("INTERNAL_SERVER_ERROR", status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def retrieve(self, request, id=None, **kwargs):
        """

        :param request:
        :param user_id:
        :param kwargs:
        :return:
        """
        try:
            if not self.request.user.role.enable_preference_edit:
                return Response("Not Authorized", status=status.HTTP_401_UNAUTHORIZED)

            dg_client = self.request.user.role.dg_client
            plants = SolarPlant.objects.filter(groupClient=dg_client).values('id','name')
            plant_ids = []
            for plant in plants:
                plant_ids.append(plant['id'])
            energy_contracts = EnergyContract.objects.filter(plant_id__in=plant_ids).values_list('id',flat=True)
            if int(id) in energy_contracts:
                energy_contract = EnergyContract.objects.filter(id=int(id)).\
                    values('id','contact_name', 'start_date', 'end_date', 'plant__id','plant__name',
                           'off_taker__id','off_taker__name', 'ppa_price', 'currency',
                           'late_payment_penalty_clause', 'early_payment_offset_days',
                           'early_payment_discount_factor')[0]
            else:
                return Response("Not Authorized", status=status.HTTP_401_UNAUTHORIZED)
            master_payload = {}
            energy_contract['plant_id'] = energy_contract.pop('plant__id')
            energy_contract['contract_name'] = energy_contract.pop('contact_name')
            energy_contract['plant_name'] = energy_contract.pop('plant__name')
            energy_contract['off_taker_id'] = energy_contract.pop('off_taker__id')
            energy_contract['off_taker_name'] = energy_contract.pop('off_taker__name')
            master_payload['all_energy_contracts'] = energy_contract
            master_payload['all_plants'] = plants
            all_offtakers = EnergyOffTaker.objects.filter(groupClient=self.request.user.role.dg_client).values('id', 'name','registered_name')
            master_payload['all_offtakers'] = all_offtakers

            return Response(data=master_payload, status=status.HTTP_200_OK)
        except Exception as exception:
            logger.debug("Error in list EnergyContract: %s" % exception)
            return Response("INTERNAL_SERVER_ERROR", status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def partial_update(self, request, id=None, **kwargs):
        """

        :param request:
        :param kwargs:
        :return:
        """
        try:
            if not self.request.user.role.enable_preference_edit:
                return Response("Not Authorized", status=status.HTTP_401_UNAUTHORIZED)

            dg_client = self.request.user.role.dg_client
            plants = SolarPlant.objects.filter(groupClient=dg_client).values('id', 'name')
            plant_ids = []
            for plant in plants:
                plant_ids.append(plant['id'])
            energy_contracts = EnergyContract.objects.filter(plant_id__in=plant_ids).values_list('id', flat=True)
            if int(id) in energy_contracts:
                energy_contract = EnergyContract.objects.get(id=int(id))
            else:
                return Response("Not Authorized", status=status.HTTP_401_UNAUTHORIZED)

            payload = self.request.data

            if "start_date" in payload:
                energy_contract.start_date = payload['start_date']
            if "end_date" in payload:
                energy_contract.end_date = payload['end_date']
            if "ppa_price" in payload:
                energy_contract.ppa_price = payload['ppa_price']
            if "currency" in payload:
                energy_contract.currency = payload['currency']
            if "late_payment_penalty_clause" in payload:
                energy_contract.late_payment_penalty_clause = payload['late_payment_penalty_clause']
            if "early_payment_offset_days" in payload:
                energy_contract.early_payment_offset_days = payload['early_payment_offset_days']
            if "early_payment_discount_factor" in payload:
                energy_contract.early_payment_discount_factor = payload['early_payment_discount_factor']
            if "contract_name" in payload:
                energy_contract.contact_name = payload['contract_name']
            if "plant_id" in payload:
                if payload['plant_id'] in plant_ids:
                    try:
                        change_plant = SolarPlant.objects.get(id=payload['plant_id'])
                    except Exception as e:
                        logger.debug("plant not found")
                    energy_contract.plant = change_plant
            energy_contract.save()

            return Response(data="EnergyContract Updated", status=status.HTTP_200_OK)
        except Exception as exception:
            logger.debug("Error in list EnergyContract: %s" % exception)
            return Response("INTERNAL_SERVER_ERROR %s"% exception, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def create(self, request, id=None, **kwargs):
        """

        :param request:
        :param user_id:
        :param kwargs:
        :return:
        """
        try:
            if not self.request.user.role.enable_preference_edit:
                return Response("Not Authorized", status=status.HTTP_401_UNAUTHORIZED)

            dg_client = self.request.user.role.dg_client
            plants = SolarPlant.objects.filter(groupClient=dg_client).values_list('id',flat=True)

            payload = self.request.data

            plant_id = payload.pop('plant')
            if plant_id in plants:
                plant = SolarPlant.objects.get(id=plant_id)
            all_offtakers = EnergyOffTaker.objects.filter(groupClient=self.request.user.role.dg_client).values_list('id', flat=True)
            off_taker_id = payload.pop('off_taker')
            if off_taker_id in all_offtakers:
                off_taker = EnergyOffTaker.objects.get(id=off_taker_id)
            start_date = payload.pop('start_date')
            end_date = payload.pop('end_date')
            payload['contact_name'] = payload.pop('contract_name')
            try:
                st = parser.parse(start_date)
                et = parser.parse(end_date)
                start_date = update_tz(st, plant.metadata.plantmetasource.dataTimezone)
                end_date = update_tz(et, plant.metadata.plantmetasource.dataTimezone)
            except:
                return Response("please specify start and end time in correct format",
                                status=status.HTTP_400_BAD_REQUEST)
            EnergyContract.objects.create(plant=plant,off_taker=off_taker,start_date = start_date, end_date= end_date, **payload)

            return Response(data="Done", status=status.HTTP_200_OK)
        except Exception as exception:
            logger.debug("Error in list EnergyContract: %s" % exception)
            return Response("INTERNAL_SERVER_ERROR", status=status.HTTP_500_INTERNAL_SERVER_ERROR)
