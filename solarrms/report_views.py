from easy_pdf.views import PDFTemplateView
from dataglen.models import Sensor
from events.models import Events, AlertManagement, UserEventAlertsPreferences
from solarrms.models import SolarPlant
from dataglen.models import ValidDataStorageByStream, InvalidDataStorageBySource
from solarrms.models import EnergyGenerationTable
from dashboards.mixins import AddSensorsMixin, EntryPointMixin
from braces.views import JSONResponseMixin
from utils.errors import generate_exception_comments, log_and_return_error, log_and_return_independent_error,log_and_return_bad_data_write_request

from django.utils import timezone
from django.conf import settings
import sys, dateutil, logging
import pytz
from django.http import Http404

logger = logging.getLogger('dataglen.rest_views')
logger.setLevel(logging.DEBUG)


class GenerateInverterLevelPDFReportView(EntryPointMixin, AddSensorsMixin,
                                         JSONResponseMixin, PDFTemplateView):
    template_name = "/solarmonitoring/generate_inverter_pdf.html"

    def get(self, request, *args, **kwargs):
        try:
            source = Sensor.objects.get(sourceKey=self.kwargs.get('source_key'))
            if source not in self.sources:
                raise Http404
        except Sensor.DoesNotExist:
            raise Http404

        return self.render_to_response(self.get_context_data())

    def get_context_data(self, **kwargs):
        try:
            plant = SolarPlant.objects.get(slug=self.kwargs.get('plant_slug'))
        except SolarPlant.DoesNotExist:
            raise Http404
        try:
            source = Sensor.objects.get(sourceKey=self.kwargs.get('source_key'))
            if source not in self.sources:
                raise Http404
        except Sensor.DoesNotExist:
            raise Http404
        
        context = super(GenerateInverterLevelPDFReportView, self).get_context_data(
            pagesize="A4",
            title="_".join(["Performance Report for inverter:", source.sourceKey,
                            "installed at the", plant.name, "plant."]),
            **kwargs
        )

        request_arrival_time = timezone.now()
        try:
            st = self.request.GET.get("startTime")
            et = self.request.GET.get("endTime")
            try:
                tz = pytz.timezone(source.dataTimezone)
            except Exception as exception:
                logger.debug(str(exception))
                comments = generate_exception_comments(sys._getframe().f_code.co_name)
                return log_and_return_error(self.request.user.id, self.request, request_arrival_time,
                                            settings.ERRORS.SOURCE_CONFIGURATION_ISSUE, settings.RESPONSE_TYPES.DRF,
                                            False, comments)

            # convert into datetime objects
            st = dateutil.parser.parse(st)
            if st.tzinfo is None:
                st = tz.localize(st)
            et = dateutil.parser.parse(et)
            if et.tzinfo is None:
                et = tz.localize(et)

        except Exception as exception:
            logger.debug(exception)
            comments = generate_exception_comments(sys._getframe().f_code.co_name)
            return log_and_return_error(self.request.user.id, self.request, request_arrival_time,
                                        settings.ERRORS.BAD_REQUEST, settings.RESPONSE_TYPES.DRF,
                                        False, comments)

        identifier = str(self.kwargs.get('source_key'))
        alerts = AlertManagement.objects.filter(identifier=identifier,
                                                alert_time__gte=st,
                                                alert_time__lte=et).order_by('alert_time')
        alerts_size = len(alerts)

        #valid_records = ValidDataStorageByStream.objects.filter(source_key=identifier,
        #                                                        stream_name='ACTIVE_POWER',
        #                                                        timestamp_in_data__gte=st,
        #                                                        timestamp_in_data__lte=et).limit(1000)
        #valid_records_size = len(valid_records)

        hourly_inverter_energy_generations = EnergyGenerationTable.objects.filter(identifier=identifier,
                                                                                  timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                                  count_time_period=3600,
                                                                                  ts__gte=st,
                                                                                  ts__lte=et)
        hourly_inverter_energy_generations_size = len(hourly_inverter_energy_generations)

        total_inverter_energy = 0.0
        for entry in hourly_inverter_energy_generations:
            total_inverter_energy += float(entry.energy)

        context['alerts'] = alerts
        context['alerts_size'] = alerts_size
        context['startTime'] = st
        context['endTime'] = et
        context['source'] = source
        #context['valid_records'] = valid_records
        #context['valid_records_size'] = valid_records_size
        context['daily_inverter_energy_generations'] = hourly_inverter_energy_generations
        context['daily_inverter_energy_generations_size'] = hourly_inverter_energy_generations_size
        context['total_inverter_energy'] = total_inverter_energy
        return context


class GeneratePlantLevelPDFReportView(EntryPointMixin, AddSensorsMixin,
                                      JSONResponseMixin,PDFTemplateView):
    template_name = "/solarmonitoring/generate_plant_pdf.html"

    def get(self, request, *args, **kwargs):
        try:
            self.plant = SolarPlant.objects.get(slug=self.kwargs.get('plant_slug'))
        except SolarPlant.DoesNotExist:
            raise Http404
        return self.render_to_response(self.get_context_data())

    def get_context_data(self, **kwargs):
        request_arrival_time = timezone.now()
        context = super(GeneratePlantLevelPDFReportView, self).get_context_data(
            pagesize="A4",
            title="Performance Report",
            **kwargs
        )
        try:
            self.plant = SolarPlant.objects.get(slug=self.kwargs.get('plant_slug'))
        except SolarPlant.DoesNotExist:
            raise Http404

        inverters = self.plant.independent_inverter_units.all()
        alerts_final = []
        valid_records_final = []
        invalid_records_final = []

        try:
            st = self.request.GET.get("startTime")
            et = self.request.GET.get("endTime")
        except Exception as exception:
            logger.debug(exception)
            comments = generate_exception_comments(sys._getframe().f_code.co_name)
            return log_and_return_error(self.request.user.id, self.request, request_arrival_time,
                                        settings.ERRORS.BAD_REQUEST, settings.RESPONSE_TYPES.DRF,
                                        False, comments)

        for inverter in inverters:
            try:
                source = Sensor.objects.get(sourceKey=inverter.sourceKey)
                if source not in self.sources:
                    raise Http404
            except Sensor.DoesNotExist:
                raise Http404
            try:
                st = self.request.GET.get("startTime")
                et = self.request.GET.get("endTime")
                try:
                    tz = pytz.timezone(source.dataTimezone)
                except Exception as exception:
                    logger.debug(str(exception))
                    comments = generate_exception_comments(sys._getframe().f_code.co_name)
                    return log_and_return_error(self.request.user.id, self.request, request_arrival_time,
                                                settings.ERRORS.SOURCE_CONFIGURATION_ISSUE, settings.RESPONSE_TYPES.DRF,
                                                False, comments)

                # convert into datetime objects
                st = dateutil.parser.parse(st)
                if st.tzinfo is None:
                    st = tz.localize(st)
                et = dateutil.parser.parse(et)
                if et.tzinfo is None:
                    et = tz.localize(et)

            except Exception as exception:
                logger.debug(exception)
                comments = generate_exception_comments(sys._getframe().f_code.co_name)
                return log_and_return_error(self.request.user.id, self.request, request_arrival_time,
                                            settings.ERRORS.BAD_REQUEST, settings.RESPONSE_TYPES.DRF,
                                            False, comments)

            try:
                identifier = str(inverter.sourceKey)
                alerts = AlertManagement.objects.filter(identifier=identifier,
                                                        alert_time__gte=st,
                                                        alert_time__lte=et).order_by('alert_time')
            except AlertManagement.DoesNotExist:
                alerts = []
            alerts_final.extend(alerts)

            try:
                source_key = inverter.sourceKey
                valid_records = ValidDataStorageByStream.objects.filter(source_key=source_key,
                                                                        stream_name='ACTIVE_POWER',
                                                                        timestamp_in_data__gte=st,
                                                                        timestamp_in_data__lte=et).limit(1000)
            except ValidDataStorageByStream.DoesNotExist:
                valid_records = []
            valid_records_final.extend(valid_records)

            try:
                source_key = inverter.sourceKey
                invalid_records = InvalidDataStorageBySource.objects.filter(source_key=source_key,
                                                                            insertion_time__gte=st,
                                                                            insertion_time__lte=et).limit(1000)
            except InvalidDataStorageBySource.DoesNotExist:
                invalid_records = []
            invalid_records_final.extend(invalid_records)

        # get plant level information now : st/et as per the last inverter's timezone
        plant_slug = self.kwargs.get('plant_slug')
        identifier = str(self.request.user.id) + '_' + str(plant_slug)
        total_plant_energy = 0.0
        try:
            daily_plant_energy_generations = EnergyGenerationTable.objects.filter(identifier=identifier,
                                                                                  timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                                  count_time_period=3600,
                                                                                  ts__gte=st,
                                                                                  ts__lte=et)
            for entry in daily_plant_energy_generations:
                total_plant_energy += float(entry.energy)
        except EnergyGenerationTable.DoesNotExist:
            daily_plant_energy_generations = []
        daily_plant_energy_generations_size = len(daily_plant_energy_generations)

        alerts_size_final = len(alerts_final)
        valid_records_size_final = len(valid_records_final)
        invalid_records_size_final = len(invalid_records_final)
        context['startTime'] = st
        context['endTime'] = et
        context['alerts_final'] = alerts_final
        context['alerts_size_final'] = alerts_size_final
        context['valid_records_final'] = valid_records_final
        context['valid_records_size_final'] = valid_records_size_final
        context['invalid_records_final'] = invalid_records_final
        context['invalid_records_size_final'] = invalid_records_size_final
        context['daily_plant_energy_generations'] = daily_plant_energy_generations
        context['daily_plant_energy_generations_size'] = daily_plant_energy_generations_size
        context['total_plant_energy'] = total_plant_energy
        context['plant_name'] = self.plant.name

        return context

