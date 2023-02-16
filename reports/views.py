from easy_pdf.views import PDFTemplateView
from dataglen.models import Sensor
from events.models import AlertManagement
from dataglen.models import ValidDataStorageByStream, InvalidDataStorageBySource
from dashboards.mixins import AddSensorsMixin, EntryPointMixin
from braces.views import JSONResponseMixin
from utils.errors import generate_exception_comments, log_and_return_error
from django.http import Http404, HttpResponseBadRequest

from django.utils import timezone
from django.conf import settings
import sys, dateutil, logging
import pytz

logger = logging.getLogger('dataglen.rest_views')
logger.setLevel(logging.DEBUG)


class GeneratePDFReportView(EntryPointMixin, AddSensorsMixin,
                            JSONResponseMixin,PDFTemplateView):

    template_name = "/reports/generate_pdf.html"

    def get(self, request, *args, **kwargs):
        try:
            source = Sensor.objects.get(sourceKey=self.kwargs.get('source_key'),
                                        user=self.request.user)
            if source not in self.sources:
                raise Http404
        except Sensor.DoesNotExist:
            raise Http404
        return self.render_to_response(self.get_context_data())

    def get_context_data(self, **kwargs):
        try:
            source = Sensor.objects.get(sourceKey=self.kwargs.get('source_key'),
                                        user=self.request.user)
            if source not in self.sources:
                raise Http404
        except Sensor.DoesNotExist:
            raise Http404

        context = super(GeneratePDFReportView, self).get_context_data(
            pagesize="A4",
            title=source.name,
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
            # TODO why this is not being returned?
            return log_and_return_error(self.request.user.id, self.request, request_arrival_time,
                                        settings.ERRORS.BAD_REQUEST, settings.RESPONSE_TYPES.DRF,
                                        False, comments)

        identifier = str(self.kwargs.get('source_key'))
        alerts = AlertManagement.objects.filter(identifier=identifier,
                                                alert_time__gte=st,
                                                alert_time__lte=et).order_by('alert_time')
        alerts_size = len(alerts)

        valid_records = ValidDataStorageByStream.objects.filter(source_key=identifier,
                                                                stream_name='ACTIVE_POWER',
                                                                timestamp_in_data__gte=st,
                                                                timestamp_in_data__lte=et).limit(1000)
        valid_records_size = len(valid_records)

        invalid_records = InvalidDataStorageBySource.objects.filter(source_key=identifier,
                                                                    insertion_time__gte=st,
                                                                    insertion_time__lte=et).limit(1000)
        invalid_records_size = len(invalid_records)

        context['alerts'] = alerts
        context['alerts_size'] = alerts_size
        context['startTime'] = st
        context['endTime'] = et
        context['source'] = source
        context['valid_records'] = valid_records
        context['valid_records_size'] = valid_records_size
        context['invalid_records'] = invalid_records
        context['invalid_records_size'] = invalid_records_size

        return context