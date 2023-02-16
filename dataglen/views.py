from django.views.generic.base import View, TemplateView
from django.views.generic.list import ListView
from django.views.generic.edit import CreateView, FormView, UpdateView
from django.conf import settings
from django.db import IntegrityError
from django.shortcuts import redirect
from django.utils import timezone
from django.http import Http404, HttpResponseBadRequest, HttpResponseServerError, HttpResponse
from django.shortcuts import get_object_or_404
from django.core.urlresolvers import reverse_lazy
from utils.utils import get_sensor_data_in_utc
from dataglen.models import ValidDataStorageByStream
from braces.views import JSONResponseMixin
from rest_framework.authtoken.models import Token
import datetime
import logging

from .forms import SensorForm, TemplateForm, FieldForm
from .models import InvalidDataStorageBySource, Field, Sensor
from action.models import ActionField
from config.models import ConfigField
from errors.models import ErrorField

from logger.models import DataCountTable
from dashboards.mixins import AddSensorsMixin, EntryPointMixin, ContextDataMixin
from monitoring.views import get_user_data_monitoring_status
from utils.views import get_live_chart_data
import pytz
from action.models import ActionField


logger = logging.getLogger('dataglen.views')
logger.setLevel(logging.DEBUG)


class DashboardData(EntryPointMixin, AddSensorsMixin,
                    JSONResponseMixin, TemplateView):
    template_name = 'dataglen/index.html'
    json_include = ['sources_len', 'valid_records', 'invalid_records',
                    'live_data_chart',
                    'stable', 'errors', 'warnings', 'unmonitored']

    def get(self, request, *args, **kwargs):
        if self.request.is_ajax() is False:
            return self.render_to_response(self.get_context_data())
        else:
            context = self.get_context_data()
            context_dict = {}
            for key in self.json_include:
                context_dict[key] = context[key]
            return self.render_json_response(context_dict)

    def get_context_data(self, **kwargs):
        context = super(DashboardData, self).get_context_data(**kwargs)
        source_keys = [source.sourceKey for source in self.sources]

        stats = get_user_data_monitoring_status(Sensor.objects.filter(sourceKey__in=source_keys))
        if stats is not None:
            active_alive_valid, active_alive_invalid, active_dead, deactivated_alive, deactivated_dead, unmonitored = stats
            stable_len = len(active_alive_valid) + len(deactivated_dead)
            warnings_len = len(active_alive_invalid)
            errors_len = len(active_dead) + len(deactivated_alive)
            unmonitored_len = len(unmonitored)
        else:
            stable_len = None
            warnings_len = None
            errors_len = None
            unmonitored_len = None

        try:
            source_details = {'valid_records': 0, 'invalid_records': 0}
            source_data_counts = DataCountTable.objects.filter(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                               count_time_period=settings.DATA_COUNT_PERIODS.AGGREGATED,
                                                               identifier__in=source_keys)
            for source_data_count in source_data_counts:
                source_details['valid_records'] += getattr(source_data_count, 'valid_records', 0)
                source_details['invalid_records'] += getattr(source_data_count, 'invalid_records', 0)
        except:
            source_details = {'valid_records': None, 'invalid_records': None}

        # metadata on volume
        context['sources_len'] = len(self.sources)
        context['user'] = self.request.user
        context['valid_records'] = source_details['valid_records']
        context['invalid_records'] = source_details['invalid_records']
        # monitoring status
        context['stable'] = stable_len
        context['warnings'] = warnings_len
        context['errors'] = errors_len
        context['unmonitored'] = unmonitored_len

        if self.request.is_ajax():
            context['live_data_chart'] = get_live_chart_data([source.sourceKey for source in self.sources])
        return context


class SourceData(EntryPointMixin, AddSensorsMixin,
                 JSONResponseMixin, TemplateView):
    template_name = "dataglen/source_profile.html"
    json_include = ['valid_records', 'invalid_records', 'live_data_chart']

    def get(self, request, *args, **kwargs):
        try:
            source = Sensor.objects.get(sourceKey=self.kwargs.get('source_key'))
            if source not in self.sources:
                raise Http404
        except Sensor.DoesNotExist:
            raise Http404

        if self.request.is_ajax():
            context = self.get_context_data()
            context_dict = {}
            for key in self.json_include:
                context_dict[key] = context[key]
            return self.render_json_response(context_dict)
        else:
            return self.render_to_response(self.get_context_data())

    def get_context_data(self, **kwargs):
        context = super(SourceData, self).get_context_data(**kwargs)
        try:
            source = Sensor.objects.get(sourceKey=self.kwargs.get('source_key'))
            if source not in self.sources:
                raise Http404
        except Sensor.DoesNotExist:
            raise Http404

        try:
            source_details = DataCountTable.objects.get(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                        count_time_period=settings.DATA_COUNT_PERIODS.AGGREGATED,
                                                        identifier=source.sourceKey)
        except:
            source_details = {'valid_records': 0, 'invalid_records': 0}

        try:
            streams = Field.objects.filter(source=source).order_by('id')
        except Field.DoesNotExist:
            streams = []
        try:
            action_streams = ActionField.objects.filter(source=source).order_by('id')
        except ActionField.DoesNotExist:
            action_streams = []
        try:
            config_streams = ConfigField.objects.filter(source=source).order_by('id')
        except ConfigField.DoesNotExist:
            config_streams = []

        try:
            error_streams = ErrorField.objects.filter(source=source).order_by('id')
        except ErrorField.DoesNotExist:
            error_streams = []

        context['valid_records'] = source_details['valid_records']
        context['invalid_records'] = source_details['invalid_records']
        context['source'] = source
        context['streams'] = streams
        context['action_streams'] = action_streams
        context['config_streams'] = config_streams
        context['error_streams'] = error_streams

        if self.request.is_ajax():
            context['live_data_chart'] = get_live_chart_data([source.sourceKey])

        return context


class SourceListView(EntryPointMixin, AddSensorsMixin, ListView):
    model = Sensor
    context_object_name = 'sources'
    template_name = 'dataglen/list_sources.html'

    def get_queryset(self):
        return self.sources


class SourceCreateView(FormView):
    template_name = "dataglen/add_source.html"
    form_class = SensorForm

    def get_success_url(self):
        return reverse_lazy('dataglen:source-detail', kwargs={'source_key': self.key})

    def form_valid(self, form):
        try:
            data_source = form.save(commit=False)
            data_source.user = self.request.user
            data_source.save()
            self.key = data_source.sourceKey
            return super(SourceCreateView, self).form_valid(form)
        except IntegrityError:
            return HttpResponseBadRequest("The name of a source should be unique")
        except:
            return HttpResponseServerError("INTERNAL SERVER ERROR. Please contact us at contact@dataglen.com")


class SourceUpdateView(UpdateView):
    template_name = "dataglen/edit_source.html"
    form_class = SensorForm
    model = Sensor
    slug_url_kwarg = 'source_key'
    slug_field = 'sourceKey'


class StreamUpdateView(UpdateView):
    template_name = "dataglen/edit_stream.html"
    form_class = FieldForm
    model = Field
    slug_url_kwarg = 'stream_id'
    slug_field = 'id'

    def get_success_url(self):
        return reverse_lazy('dataglen:source-detail',
                            kwargs={'source_key': self.kwargs.get('source_key')})

# TODO improve these functions later (as per the DeleteView)
class SourceDeleteView(EntryPointMixin, AddSensorsMixin, View):
    model = Sensor
    success_url = reverse_lazy("dataglen:source-list")

    def get(self, request, *args, **kwargs):
        self.object = get_object_or_404(Sensor, sourceKey=self.kwargs.get('source_key'))
        if self.object.isActive:
            return HttpResponseBadRequest("Sensor should be deactivated before deleting")
        if self.object not in self.sources:
            raise Http404
        else:
            try:
                self.object.delete()
                return redirect(self.success_url)
            except:
                return HttpResponseServerError()


class StreamDeleteView(EntryPointMixin, View):

    def get_success_url(self):
        return reverse_lazy('dataglen:source-detail',
                            kwargs={'source_key': self.kwargs.get('source_key')})

    def get(self, request, *args, **kwargs):
        self.source = get_object_or_404(Sensor, sourceKey=self.kwargs.get('source_key'))
        self.object = get_object_or_404(Field, source=self.source, name=self.kwargs.get('stream_name'))
        try:
            self.object.delete()
            return redirect(self.get_success_url())
        except:
            return HttpResponseServerError()

class ApplyTemplate(EntryPointMixin, AddSensorsMixin, FormView):
    form_class = TemplateForm
    template_name = "dataglen/apply_template.html"

    def get_success_url(self):
        return reverse_lazy('dataglen:source-detail', kwargs={'source_key': self.key})

    def form_valid(self, form):
        try:
            self.key = self.kwargs.get("source_key")
            sensor = Sensor.objects.get(sourceKey=self.key, isTemplate=False)
            id = form.cleaned_data['template_id']
            # look for template
            template = Sensor.objects.get(isTemplate=True,
                                          id=id)
            # copy fields
            fields = Field.objects.filter(source=template)
            # copy all the fields
            #TODO copy all action fields and config fields
            for field in fields:
                new_field = Field()
                new_field.source = sensor
                new_field.name = field.name
                new_field.streamDataType = field.streamDataType
                new_field.streamPositionInCSV = field.streamPositionInCSV
                new_field.streamDataUnit = field.streamDataUnit
                new_field.streamDateTimeFormat = field.streamDateTimeFormat
                # save the field
                new_field.save()
            # update the sensor details
            sensor.templateName = template.templateName
            sensor.textMessageWithHTTP200 = template.textMessageWithHTTP200
            sensor.textMessageWithError = template.textMessageWithError
            sensor.csvDataKeyName = template.csvDataKeyName
            sensor.save()
            return super(ApplyTemplate, self).form_valid(form)
        except Sensor.DoesNotExist:
            raise Http404
        except Exception:
            return HttpResponseServerError("Something went wrong. Sorry. Please try again later.")


class StreamCreateView(EntryPointMixin, AddSensorsMixin, CreateView):
    form_class = FieldForm
    template_name = "dataglen/add_stream.html"

    def get_success_url(self):
        return reverse_lazy('dataglen:source-detail', kwargs={'source_key': self.kwargs.get('source_key')})

    def form_valid(self, form):
        try:
            source = get_object_or_404(Sensor, isTemplate=False, sourceKey = self.kwargs.get('source_key'))
            new_stream = form.save(commit=False)
            new_stream.source = source
            new_stream.save()
            return super(StreamCreateView, self).form_valid(form)
        except IntegrityError:
            return HttpResponseBadRequest("The stream name should be unique.")
        except:
            return HttpResponseServerError("Something went wrong, please contact us at contact@datalen.com")


# TODO add stream - update, list and delete
class MonitoringStatus(EntryPointMixin, AddSensorsMixin, TemplateView):
    template_name = "dataglen/monitoring_status.html"

    def get_context_data(self, **kwargs):
        context = super(MonitoringStatus, self).get_context_data()
        source_keys = [source.sourceKey for source in self.sources]
        stats = get_user_data_monitoring_status(Sensor.objects.filter(sourceKey__in=source_keys))
        stats_dict = {}
        if stats is not None:
            active_alive_valid, active_alive_invalid, active_dead, deactivated_alive, deactivated_dead, unmonitored = stats
            stats_dict = {'active_alive_valid': Sensor.objects.filter(sourceKey__in=active_alive_valid).values("name", "sourceKey"),
                          'active_alive_invalid': Sensor.objects.filter(sourceKey__in=active_alive_invalid).values('name', 'sourceKey'),
                          'active_dead': Sensor.objects.filter(sourceKey__in=active_dead).values('name', 'sourceKey'),
                          'deactivated_alive': Sensor.objects.filter(sourceKey__in=deactivated_alive).values('name', 'sourceKey'),
                          'deactivated_dead': Sensor.objects.filter(sourceKey__in=deactivated_dead).values('name', 'sourceKey')}
        for key in stats_dict.keys():
            context[key] = stats_dict[key]
        return context


class DiscardedRecordsForSource(EntryPointMixin, AddSensorsMixin, TemplateView):
    template_name = "dataglen/list_discarded.html"

    def get_context_data(self, **kwargs):
        source = get_object_or_404(Sensor, isTemplate=False, sourceKey = kwargs.get("source_key"))
        discarded_records = InvalidDataStorageBySource.objects.filter(source_key = kwargs.get("source_key")).limit(settings.DATAGLEN['DISCARDED_RECORDS_UI_WINDOW_NUMBERS'])
        context = super(DiscardedRecordsForSource, self).get_context_data()
        context['source'] = source
        context['discarded_records'] = discarded_records
        context['window_len'] = len(discarded_records)
        return context


class DiscardedRecordsStatsForSources(EntryPointMixin, AddSensorsMixin, TemplateView):
    template_name = "dataglen/list_discarded_stats.html"

    def get_context_data(self, **kwargs):
        discarded_stats = []
        keys = [source.sourceKey for source in self.sources]
        discarded_records_stats = DataCountTable.objects.filter(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                                count_time_period=settings.DATA_COUNT_PERIODS.AGGREGATED,
                                                                identifier__in=keys)
        for source_stat in discarded_records_stats:
            if source_stat.invalid_records > 0:
                discarded_record = InvalidDataStorageBySource.objects.filter(source_key=source_stat.identifier).limit(1)
                if len(discarded_record) > 0:
                    discarded_stats.append({'last_record': discarded_record[0].insertion_time,
                                            'key': source_stat.identifier,
                                            'invalid_records': source_stat.invalid_records,
                                            'valid_records': source_stat.valid_records})
                else:
                    discarded_stats.append({'last_record': "NA",
                                            'key': source_stat.identifier,
                                            'invalid_records': source_stat.invalid_records,
                                            'valid_records': source_stat.valid_records})

        context = super(DiscardedRecordsStatsForSources, self).get_context_data()
        try:
            context['discarded_stats'] = sorted(discarded_stats, key=lambda k:k['last_record'], reverse=True)
        except:
            context['discarded_stats'] = discarded_stats

        return context


class SourcesList(EntryPointMixin, AddSensorsMixin, TemplateView):
    template_name = "dataglen/list_data.html"

    def get_context_data(self, **kwargs):
        context = super(SourcesList, self).get_context_data()
        context['sources'] = self.sources
        return context


class HeatMapData(EntryPointMixin, AddSensorsMixin, View):

    def get(self, request, *args, **kwargs):

        try:
            source = Sensor.objects.get(sourceKey=kwargs.get('identifier'))
        except Sensor.DoesNotExist:
            raise Http404

        if source not in self.sources:
            raise Http404

        request_arrival_time = timezone.now()
        request_arrival_time = request_arrival_time.astimezone(pytz.timezone(source.dataTimezone))
        try:
            # heat map
            deadline = request_arrival_time - datetime.timedelta(days=6)
            heat_map_entries = DataCountTable.objects.filter(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                                             count_time_period=settings.DATA_COUNT_PERIODS.HOUR,
                                                             identifier=kwargs.get('identifier'),
                                                             ts__gte=deadline)
            heat_map_data = "day\thour\tvalue\n"
            append_zero_data = {}
            for day in range(1, 8):
                append_zero_data[day] = {}
                for hour in range(1, 25):
                    append_zero_data[day][hour] = 0

            for entry in heat_map_entries:
                if entry.valid_records is not None:
                    ts = entry.ts.replace(tzinfo=pytz.utc).astimezone(pytz.timezone(source.dataTimezone))
                    diff = request_arrival_time.date() - ts.date()
                    # due to future dates
                    if diff.days < 0:
                        continue
                    heat_map_data += "\t".join([str(diff.days+1),
                                                str(ts.hour+1),
                                                str(entry.valid_records)])
                    heat_map_data += "\n"
                    append_zero_data[diff.days+1][ts.hour+1] = entry.valid_records

            for day in range(1, 8):
                for hour in range(1, 25):
                    if append_zero_data[day][hour] == 0:
                        heat_map_data += "\t".join([str(day),
                                                    str(hour),
                                                    str(0)])
                        heat_map_data += "\n"

            response = HttpResponse(heat_map_data)
            return response
        except Exception as exc:
            logger.debug(str(exc))
            return HttpResponseServerError("Sorry, something went wrong, please try again later." + str(exc))


class UserProfile(ContextDataMixin, AddSensorsMixin,
                  TemplateView):
    def get_template_names(self):
        if self.user_status is settings.USER_STATUS.OWNER:
            return "dataglen/owner_profile.html"
        else :
            return "dataglen/profile.html"

    def get_context_data(self, **kwargs):
        context = super(UserProfile, self).get_context_data()
        try:
            token = Token.objects.get(user=self.request.user).key
        except:
            token = 'NOT APPLICABLE'
        context['token'] = token
        context['user'] = self.request.user
        context['total_sources'] = self.sources
        return context


class NebulaView(EntryPointMixin, AddSensorsMixin, JSONResponseMixin, TemplateView):
    template_name = "dataglen/nebula.html"
    CHART_LEN = 20
    json_include = ['data', 'adc_streams_data']

    status_params = ['OP1', 'OP2', 'OP3', 'MREL', 'PWM1_V1', 'PWM2_V1', 'PWM3_V1', 'PWM1_V2', 'PWM2_V2', 'PWM3_V2', 'PWM1_V3', 'PWM2_V3', 'PWM3_V3']

    def get(self, request, *args, **kwargs):
        if self.request.is_ajax() is False:
            return self.render_to_response(self.get_context_data())
        else:
            context = self.get_context_data()
            context_dict = {}
            for key in self.json_include:
                context_dict[key] = context[key]
            return self.render_json_response(context_dict)

    def status_data(self, key):
        status_data = {}
        for param in self.status_params:
            try:
                record = ValidDataStorageByStream.objects.filter(source_key=key, stream_name=param).limit(1)[0]
                status_data[param] = int(float(record.stream_value))
            except Exception as exc:
                logger.debug(exc)
                continue

        return status_data

    def get_context_data(self, **kwargs):
        try:
            source = Sensor.objects.get(sourceKey=self.kwargs.get('source_key'))
        except Sensor.DoesNotExist:
            raise Http404

        if source not in self.sources or source.templateName != "RS_IOELabKit":
            raise Http404

        context = super(NebulaView, self).get_context_data()
        context['nebula'] = source
        # get adc values
        adc_streams = ["ADC1_R", "ADC2_R", "ADC3_R"]
        adc_streams_data = []
        for stream in adc_streams:
            try:
                stream_object = Field.objects.get(source=source, name=stream)
                adc_streams_data.append({"name": stream, "mf": stream_object.multiplicationFactor})
            except:
                continue

        context['adc_streams_data'] = adc_streams_data

        # get the data
        streams = Field.objects.filter(source=source)
        streams_names = [stream.name for stream in streams]
        data = get_sensor_data_in_utc(source, streams_names, self.CHART_LEN)
        context['data'] = data

        # get boolean params
        context['status_data'] = self.status_data(source.sourceKey)
        return context