import requests
import base64
import os
import calendar
from dashboards.mixins import EntryPointMixin, AddSensorsMixin
from braces.views import JSONResponseMixin
from django.views.generic.base import TemplateView
from django.views.generic.edit import FormView, UpdateView
from django.views.generic import CreateView
from django.http import Http404, HttpResponseBadRequest, HttpResponseServerError, HttpResponse
from django.core.urlresolvers import reverse_lazy
from django.db import IntegrityError
from .models import EnergyGenerationTable, PerformanceRatioTable, CUFTable
import datetime, pytz
from dashboards.mixins import ProfileDataMixin, ContextDataMixin
from monitoring.views import get_user_data_monitoring_status

from .models import IndependentInverter, SolarPlant, Feeder, Inverter, AJB, PlantPowerTable, PlantMetaSource, \
    PlantSummaryDetails, EnergyMeter
from .forms import IndependentInverterForm, SolarPlantAddForm, FeederForm, AJBForm, InverterForm
from .solarutils import get_inverter_data, filter_solar_plants, sync_values, calculate_total_plant_generation, \
    get_power_irradiation

from monitoring.models import SourceMonitoring
from kutbill import settings
import logging, json
from django.utils import timezone
from dataglen.models import ValidDataStorageByStream
from solarutils import get_aggregated_energy, get_energy_meter_values
from datetime import timedelta
from api_views import inverter_order, string_order, fix_co2_savings, fix_generation_units
from helpdesk.models import Ticket
from screamshot.utils import render_template
from solarrms2.models import EnergyContract
from rest_framework.response import Response
from solarrms.api_views import update_tz
from dateutil import parser

logger = logging.getLogger('dataglen.views')
logger.setLevel(logging.DEBUG)


class SolarPlantCreate(ProfileDataMixin, CreateView):
    form_class = SolarPlantAddForm
    model = SolarPlant

    def get_success_url(self):
        return self.success_url

    def get_form_kwargs(self):
        kwargs = super(SolarPlantCreate, self).get_form_kwargs()
        kwargs.update({'request': self.request})
        kwargs.update({'dataglenclient': self.dataglenclient})
        kwargs.update({'sensors': self.get_profile_data()['sensors']})
        return kwargs

    def get_context_data(self, **kwargs):
        tcontext = super(SolarPlantCreate, self).get_context_data(**kwargs)
        context = self.get_profile_data(**kwargs)
        solar_plants = filter_solar_plants(context)
        tcontext['groups'] = solar_plants
        return tcontext


class InvertersStatusPage(ProfileDataMixin, TemplateView):
    template_name = "solarmonitoring/niftyinverterstatus.html"

    def get_context_data(self, **kwargs):
        context = super(InvertersStatusPage, self).get_context_data()
        profile_data = self.get_profile_data()
        for key in profile_data.keys():
            context[key] = profile_data[key]
        plant_slug = self.kwargs.get('plant_slug')
        try:
            plant = SolarPlant.objects.get(slug=plant_slug)
            solar_plants = filter_solar_plants(context)
            assert (plant in solar_plants)
        except:
            raise Http404

        context['plant'] = plant
        # prepare inverter generation
        ts = datetime.datetime.now(pytz.timezone('Asia/Kolkata')).replace(hour=0, minute=0,
                                                                          second=0, microsecond=0).astimezone(pytz.UTC)

        inverters_status = {}
        plot_data = {}
        all_data = {'x': [], 'y': []}
        for orientation in ["NORTH", "SOUTH", "EAST", "WEST", "SOUTH-WEST"]:
            values = []
            plot_data_x = []
            plot_data_y = []
            for independent_inverter in plant.independent_inverter_units.filter(orientation=orientation):
                status = None
                try:
                    stats = get_user_data_monitoring_status(
                        IndependentInverter.objects.filter(sourceKey=independent_inverter.sourceKey))
                    if stats is not None:
                        active_alive_valid, active_alive_invalid, active_dead, deactivated_alive, deactivated_dead, unmonitored = stats
                        if len(active_alive_valid) > 0:
                            status = "CONNECTED"
                        else:
                            status = "DISCONNECTED"
                    else:
                        status = "ERROR"

                    generation = EnergyGenerationTable.objects.get(
                        timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                        count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                        identifier=independent_inverter.sourceKey,
                        ts__gte=ts)
                    # get inverter's status
                    values.append({"name": str(independent_inverter.name),
                                   "energy": generation.energy,
                                   "status": status})
                    plot_data_x.append(float(generation.energy))
                    plot_data_y.append(str(independent_inverter.name))
                    all_data['x'].append(float(generation.energy))
                    all_data['y'].append(str(independent_inverter.name))
                except EnergyGenerationTable.DoesNotExist:
                    plot_data_x.append(float(0.0))
                    plot_data_y.append(str(independent_inverter.name))
                    all_data['x'].append(0.0)
                    all_data['y'].append(str(independent_inverter.name))
                    values.append({"name": str(independent_inverter.name),
                                   "energy": 0.0,
                                   "status": status})
                except Exception as exc:
                    logger.debug("exception" + str(exc))
                    logger.debug(str(exc))
                    continue
            plot_data[orientation] = {'x': plot_data_x, 'y': plot_data_y}
            inverters_status[orientation] = values
        logger.debug(inverters_status)
        context['plot_data'] = plot_data
        context['all_data'] = all_data
        context['status'] = inverters_status

        # Get the number of tickets assigned.
        tickets = Ticket.objects.filter(assigned_to=self.request.user, status=1)
        tickets = len(tickets)
        context['tickets'] = tickets
        return context


class SolarPlantView(ProfileDataMixin, TemplateView):
    template_name = "solarmonitoring/summary_page_v4.html"

    def get_context_data(self, **kwargs):
        context = super(SolarPlantView, self).get_context_data()
        profile_data = self.get_profile_data()
        for key in profile_data.keys():
            context[key] = profile_data[key]
        plant_slug = self.kwargs.get('plant_slug')
        try:
            plant = SolarPlant.objects.get(slug=plant_slug)
            solar_plants = filter_solar_plants(context)
            assert (plant in solar_plants)
        except AssertionError:
            raise Http404("Assertion error - Plant Not Found")
        except:
            logger.debug(plant_slug)
            logger.debug("Plant not found")
            raise Http404("Plant Not Found")

        user = self.request.user
        try:
            webdyn_client = user.organizations_organization.all()[0].dataglengroup.groupClient.webdynClient
        except:
            webdyn_client = False
        context['webdyn_client'] = webdyn_client

        context['plant'] = plant
        context['updated'] = datetime.datetime.now(pytz.timezone('Asia/Kolkata')).strftime("%H:%M:%S %d-%m-%Y")
        # get hourly energy value for today
        ts = datetime.datetime.now(pytz.timezone('Asia/Kolkata')).replace(hour=0, minute=0,
                                                                          second=0, microsecond=0).astimezone(pytz.UTC)
        try:
            # check if the inverters connected have DAILY_YIELD
            logger.debug(ts)
            today_generation = EnergyGenerationTable.objects.get(
                timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                identifier=str(plant.owner.organization_user.user_id) + "_" + plant.slug,
                ts=ts)
            today_generation = today_generation.energy
        except Exception as exc:
            today_generation = 0.0
        context['today_generation'] = today_generation

        try:
            hour_generation = EnergyGenerationTable.objects.filter(
                timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                count_time_period=settings.DATA_COUNT_PERIODS.FIVE_MINTUES,
                identifier=str(plant.owner.organization_user.user_id) + "_" + plant.slug,
                ts__gte=ts).values_list('ts', 'energy')
        except:
            hour_generation = []
        context['hour_generation'] = [{"key": "Entire Plant Generation", "color": "#00cc66",
                                       "values": [[int(entry[0].strftime("%s")) * 1000,
                                                   entry[1]] for entry in reversed(hour_generation)]}]

        # prepare inverter generation
        inverters_generation = []
        for independent_inverter in plant.independent_inverter_units.all():
            try:
                generation = EnergyGenerationTable.objects.filter(
                    timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                    count_time_period=settings.DATA_COUNT_PERIODS.FIVE_MINTUES,
                    identifier=independent_inverter.sourceKey,
                    ts__gte=ts).values_list('ts', 'energy')
                inverters_generation.append({"key": str(independent_inverter.name),
                                             "values": [[int(entry[0].strftime("%s")) * 1000,
                                                         entry[1]] for entry in generation]})
            except:
                continue
        context['inverters_generation'] = sync_values(inverters_generation)

        inverters_today_generation = []
        for independent_inverter in plant.independent_inverter_units.all():
            try:
                # today's generation
                tg_inverter = EnergyGenerationTable.objects.get(
                    timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                    count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                    identifier=independent_inverter.sourceKey,
                    ts__gte=ts)

                inverters_today_generation.append({"label": str(independent_inverter.name),
                                                   "value": float(tg_inverter.energy)})
            except Exception as exc:
                logger.debug(exc)
                continue

        context['inverters_today_generation'] = [{"key": "Energy Generation for today",
                                                  "color": "#4f99b4",
                                                  "values": inverters_today_generation}]

        # get hourly energy value for last week
        tz = pytz.timezone('Asia/Kolkata')
        ts = timezone.now()
        ts = ts.astimezone(tz)
        ts = ts - datetime.timedelta(days=15)
        ts = ts.replace(hour=0, minute=0, second=0, microsecond=0)
        try:
            week_generation = EnergyGenerationTable.objects.filter(
                timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                identifier=str(plant.owner.organization_user.user_id) + "_" + plant.slug,
                ts__gte=ts).values_list('ts', 'energy')
        except:
            week_generation = []

        context['month_generation_per_day'] = [
            {"key": "Past one month generation per day", "values": [[int(entry[0].strftime("%s")) * 1000,
                                                                     float(entry[1]) / float(1000)] for entry in
                                                                    reversed(week_generation)]}]

        monthly_generation = 0.0
        try:
            daily_generation = EnergyGenerationTable.objects.filter(
                timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                identifier=str(plant.owner.organization_user.user_id) + "_" + plant.slug,
                ts__gte=ts.replace(day=1, hour=0, minute=0, second=0, microsecond=0)).values_list('ts', 'energy')
            for entry in daily_generation:
                monthly_generation += float(entry[1])
        except:
            pass
        context['monthly_generation'] = monthly_generation / 1000.0

        ts = timezone.now()

        try:
            '''for independent_inverter in plant.independent_inverter_units.all():
                power = ValidDataStorageByStream.objects.filter(source_key=independent_inverter.sourceKey,
                                                                stream_name='ACTIVE_POWER').limit(1)
                if len(power) > 0:
                    power_values.append(power[0])
            current_power = 0.0

            for value in power_values:
                delta = ts - value.timestamp_in_data.replace(tzinfo=pytz.UTC)
                if abs(delta.total_seconds()) < 300:
                    current_power += float(value.stream_value)'''
            power = PlantPowerTable.objects.filter(plant_slug=plant_slug,
                                                   ts__lte=ts - datetime.timedelta(minutes=3),
                                                   ts__gte=ts - datetime.timedelta(seconds=60 * 30)).limit(1)
            if len(power) > 0:
                current_power = float(power[0].power)
            else:
                current_power = 0.0
        except Exception as exc:
            logger.debug(exc)
            current_power = 0.0

        context['current_power'] = current_power

        # get total generation so far
        try:
            weeks_generation = EnergyGenerationTable.objects.filter(
                timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                identifier=str(plant.owner.organization_user.user_id) + "_" + plant.slug,
                ts__gte=plant.commissioned_date).values_list('energy')
            total_generation = 0.0
            for week in weeks_generation:
                total_generation += float(week[0])
            context['total_generation'] = total_generation / 1000.0
        except:
            context['total_generation'] = None

        try:
            context['total_revenue'] = context['total_generation'] * plant.feed_in_tariff
        except:
            context['total_revenue'] = None
        context['date'] = timezone.now().astimezone(pytz.timezone("Asia/Kolkata")).strftime("%d %h %I:%M %p")

        # get inverter's status
        stats = get_user_data_monitoring_status(plant.independent_inverter_units)
        if stats is not None:
            active_alive_valid, active_alive_invalid, active_dead, deactivated_alive, deactivated_dead, unmonitored = stats
            try:
                context['inverters_status'] = {
                    'stable': IndependentInverter.objects.filter(sourceKey__in=active_alive_valid),
                    'errors': IndependentInverter.objects.filter(sourceKey__in=active_dead),
                    'warnings': IndependentInverter.objects.filter(sourceKey__in=active_alive_invalid)}
            except:
                pass

        # Code to get the performance ratio
        try:
            plant_meta = PlantMetaSource.objects.get(plant=plant)
        except PlantMetaSource.DoesNotExist:
            plant_meta = None

        # Get the number of tickets assigned.
        tickets = Ticket.objects.filter(assigned_to=self.request.user, status=1)
        tickets = len(tickets)
        context['tickets'] = tickets

        return context


class SolarPlantViewNew(ProfileDataMixin, TemplateView):
    template_name = "solarmonitoring/summary_page_v4.html"

    def get_context_data(self, **kwargs):
        context = super(SolarPlantViewNew, self).get_context_data()
        profile_data = self.get_profile_data()
        for key in profile_data.keys():
            context[key] = profile_data[key]
        plant_slug = self.kwargs.get('plant_slug')
        try:
            plant = SolarPlant.objects.get(slug=plant_slug)
            solar_plants = filter_solar_plants(context)
            assert (plant in solar_plants)
        except AssertionError:
            raise Http404("Assertion error - Plant Not Found")
        except:
            logger.debug(plant_slug)
            logger.debug("Plant not found")
            raise Http404("Plant Not Found")

        context['plant'] = plant
        context['updated'] = datetime.datetime.now(pytz.timezone('Asia/Kolkata')).strftime("%H:%M:%S %d-%m-%Y")
        # get hourly energy value for today
        ts = datetime.datetime.now(pytz.timezone('Asia/Kolkata')).replace(hour=0, minute=0,
                                                                          second=0, microsecond=0).astimezone(pytz.UTC)
        try:
            # check if the inverters connected have DAILY_YIELD
            logger.debug(ts)
            today_generation = EnergyGenerationTable.objects.get(
                timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                identifier=str(plant.owner.organization_user.user_id) + "_" + plant.slug,
                ts=ts)
            today_generation = today_generation.energy
        except Exception as exc:
            today_generation = 0.0
        context['today_generation'] = today_generation

        try:
            hour_generation = EnergyGenerationTable.objects.filter(
                timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                count_time_period=settings.DATA_COUNT_PERIODS.FIVE_MINTUES,
                identifier=str(plant.owner.organization_user.user_id) + "_" + plant.slug,
                ts__gte=ts).values_list('ts', 'energy')
        except:
            hour_generation = []
        context['hour_generation'] = [{"key": "Entire Plant Generation", "color": "#00cc66",
                                       "values": [[int(entry[0].strftime("%s")) * 1000,
                                                   entry[1]] for entry in reversed(hour_generation)]}]

        # prepare inverter generation
        inverters_generation = []
        for independent_inverter in plant.independent_inverter_units.all():
            try:
                generation = EnergyGenerationTable.objects.filter(
                    timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                    count_time_period=settings.DATA_COUNT_PERIODS.FIVE_MINTUES,
                    identifier=independent_inverter.sourceKey,
                    ts__gte=ts).values_list('ts', 'energy')
                inverters_generation.append({"key": str(independent_inverter.name),
                                             "values": [[int(entry[0].strftime("%s")) * 1000,
                                                         entry[1]] for entry in generation]})
            except:
                continue
        context['inverters_generation'] = sync_values(inverters_generation)

        inverters_today_generation = []
        for independent_inverter in plant.independent_inverter_units.all():
            try:
                # today's generation
                tg_inverter = EnergyGenerationTable.objects.get(
                    timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                    count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                    identifier=independent_inverter.sourceKey,
                    ts__gte=ts)

                inverters_today_generation.append({"label": str(independent_inverter.name),
                                                   "value": float(tg_inverter.energy)})
            except Exception as exc:
                logger.debug(exc)
                continue

        context['inverters_today_generation'] = [{"key": "Energy Generation for today",
                                                  "color": "#4f99b4",
                                                  "values": inverters_today_generation}]

        # get hourly energy value for last week
        tz = pytz.timezone('Asia/Kolkata')
        ts = timezone.now()
        ts = ts.astimezone(tz)
        ts = ts - datetime.timedelta(days=15)
        ts = ts.replace(hour=0, minute=0, second=0, microsecond=0)
        try:
            week_generation = EnergyGenerationTable.objects.filter(
                timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                identifier=str(plant.owner.organization_user.user_id) + "_" + plant.slug,
                ts__gte=ts).values_list('ts', 'energy')
        except:
            week_generation = []

        context['month_generation_per_day'] = [
            {"key": "Past one month generation per day", "values": [[int(entry[0].strftime("%s")) * 1000,
                                                                     float(entry[1]) / float(1000)] for entry in
                                                                    reversed(week_generation)]}]

        monthly_generation = 0.0
        try:
            daily_generation = EnergyGenerationTable.objects.filter(
                timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                identifier=str(plant.owner.organization_user.user_id) + "_" + plant.slug,
                ts__gte=ts.replace(day=1, hour=0, minute=0, second=0, microsecond=0)).values_list('ts', 'energy')
            for entry in daily_generation:
                monthly_generation += float(entry[1])
        except:
            pass
        context['monthly_generation'] = monthly_generation / 1000.0

        ts = timezone.now()

        try:
            '''for independent_inverter in plant.independent_inverter_units.all():
                power = ValidDataStorageByStream.objects.filter(source_key=independent_inverter.sourceKey,
                                                                stream_name='ACTIVE_POWER').limit(1)
                if len(power) > 0:
                    power_values.append(power[0])
            current_power = 0.0

            for value in power_values:
                delta = ts - value.timestamp_in_data.replace(tzinfo=pytz.UTC)
                if abs(delta.total_seconds()) < 300:
                    current_power += float(value.stream_value)'''
            power = PlantPowerTable.objects.filter(plant_slug=plant_slug,
                                                   ts__lte=ts - datetime.timedelta(minutes=3),
                                                   ts__gte=ts - datetime.timedelta(seconds=60 * 30)).limit(1)
            if len(power) > 0:
                current_power = float(power[0].power)
            else:
                current_power = 0.0
        except Exception as exc:
            logger.debug(exc)
            current_power = 0.0

        context['current_power'] = current_power

        # get total generation so far
        try:
            weeks_generation = EnergyGenerationTable.objects.filter(
                timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                count_time_period=settings.DATA_COUNT_PERIODS.DAILY,
                identifier=str(plant.owner.organization_user.user_id) + "_" + plant.slug,
                ts__gte=plant.commissioned_date).values_list('energy')
            total_generation = 0.0
            for week in weeks_generation:
                total_generation += float(week[0])
            context['total_generation'] = total_generation / 1000.0
        except:
            context['total_generation'] = None

        try:
            context['total_revenue'] = context['total_generation'] * plant.feed_in_tariff
        except:
            context['total_revenue'] = None
        context['date'] = timezone.now().astimezone(pytz.timezone("Asia/Kolkata")).strftime("%d %h %I:%M %p")

        # get inverter's status
        stats = get_user_data_monitoring_status(plant.independent_inverter_units)
        if stats is not None:
            active_alive_valid, active_alive_invalid, active_dead, deactivated_alive, deactivated_dead, unmonitored = stats
            try:
                context['inverters_status'] = {
                    'stable': IndependentInverter.objects.filter(sourceKey__in=active_alive_valid),
                    'errors': IndependentInverter.objects.filter(sourceKey__in=active_dead),
                    'warnings': IndependentInverter.objects.filter(sourceKey__in=active_alive_invalid)}
            except:
                pass

        # Code to get the performance ratio
        try:
            plant_meta = PlantMetaSource.objects.get(plant=plant)
        except PlantMetaSource.DoesNotExist:
            plant_meta = None

        # Get the number of tickets assigned.
        tickets = Ticket.objects.filter(assigned_to=self.request.user, status=1)
        tickets = len(tickets)
        context['tickets'] = tickets

        return context


class IndependentInverterCreate(FormView):
    template_name = "solarmonitoring/independent_inverter_add.html"
    form_class = IndependentInverterForm

    def get_success_url(self):
        return reverse_lazy('solar:devices-list', kwargs={'plant_slug': self.kwargs.get('plant_slug')})

    def form_valid(self, form, *args, **kwargs):
        try:
            independentInverter = form.save(commit=False)
            independentInverter.user = self.request.user
            independentInverter.plant = SolarPlant.objects.get(slug=self.kwargs.get('plant_slug'))
            independentInverter.save()
            self.key = independentInverter.sourceKey
            return super(IndependentInverterCreate, self).form_valid(form)
        except IntegrityError:
            return HttpResponseBadRequest("The name of a source should be unique")
        except SolarPlant.DoesNotExist:
            return HttpResponseBadRequest(
                "There is no solar plant with the name: " + str(self.kwargs.get('plant_slug')))
        except:
            return HttpResponseServerError("INTERNAL SERVER ERROR. Please contact your us at contact@dataglen.com")


class ViewSolarPlants(ContextDataMixin, JSONResponseMixin, TemplateView):
    template_name = "solarmonitoring/niftyclient.html"
    json_include = []

    def get_context_data(self, **kwargs):
        context = super(ViewSolarPlants, self).get_context_data(**kwargs)


class IndependentInverterCompareAndDownloadValues(ContextDataMixin, AddSensorsMixin, TemplateView):

    def get(self, request, *args, **kwargs):
        try:
            inverter_key = self.kwargs.get('inverter_key')
            inverter = IndependentInverter.objects.get(sourceKey=inverter_key)
            plant_slug = self.kwargs.get('plant_slug')
            plant = SolarPlant.objects.get(slug=plant_slug)
            assert (inverter.plant.slug == plant_slug)
        except KeyError:
            return HttpResponseBadRequest("Plant slug or inverter key not mentioned")
        except IndependentInverter.DoesNotExist:
            return HttpResponseBadRequest("Invalid inverter key")
        except SolarPlant.DoesNotExist:
            return HttpResponseBadRequest("Invalid plant slug")
        except AssertionError:
            raise Http404

        self.plant_slug = plant_slug
        self.inverter_key = inverter_key

        return self.render_to_response(context=self.get_context_data())

    def get_context_data(self, **kwargs):
        context = super(IndependentInverterCompareAndDownloadValues, self).get_context_data(**kwargs)
        context['plant_slug'] = self.plant_slug
        context['inverter_key'] = self.inverter_key

        # Get the number of tickets assigned.
        tickets = Ticket.objects.filter(assigned_to=self.request.user, status=1)
        tickets = len(tickets)
        context['tickets'] = tickets

        return context


class PlantIndependentInverterCompareValues(ContextDataMixin, TemplateView):

    def get(self, request, *args, **kwargs):
        try:
            plant_slug = self.kwargs.get('plant_slug')
            plant = SolarPlant.objects.get(slug=plant_slug)
            self.plant_slug = plant_slug
            self.plant = plant
            return self.render_to_response(context=self.get_context_data())
        except KeyError:
            return HttpResponseBadRequest("Plant slug or inverter key not mentioned")
        except SolarPlant.DoesNotExist:
            return HttpResponseBadRequest("Invalid plant slug")
        except Exception as exc:
            logger.debug(exc)
            raise Http404

    def get_context_data(self, **kwargs):
        try:
            context = super(PlantIndependentInverterCompareValues, self).get_context_data(**kwargs)
            context['plant_slug'] = self.plant_slug
            context['plant'] = self.plant

            # Get the number of tickets assigned.
            tickets = Ticket.objects.filter(assigned_to=self.request.user, status=1)
            tickets = len(tickets)
            context['tickets'] = tickets
            return context
        except Exception as exc:
            logger.debug(exc)
            raise Http404


class SolarClientLinks(ProfileDataMixin, TemplateView):
    template_name = "solarmonitoring/plant_preferences.html"

    def get_context_data(self, **kwargs):
        context = super(SolarClientLinks, self).get_context_data(**kwargs)
        data = self.get_profile_data(**kwargs)
        for key in data.keys():
            context[key] = data[key]
        return context


class SolarClientAddPlantLinks(ProfileDataMixin, TemplateView):
    template_name = "solarmonitoring/add_plant.html"

    def get_context_data(self, **kwargs):
        context = super(SolarClientAddPlantLinks, self).get_context_data(**kwargs)
        data = self.get_profile_data(**kwargs)
        for key in data.keys():
            context[key] = data[key]
        return context


class SolarClientCompareClientParametersLinks(ProfileDataMixin, TemplateView):
    template_name = "solarmonitoring/compare_client_parameters.html"

    def get_context_data(self, **kwargs):
        context = super(SolarClientCompareClientParametersLinks, self).get_context_data(**kwargs)
        data = self.get_profile_data(**kwargs)
        for key in data.keys():
            context[key] = data[key]

        solar_plants = []
        try:
            for group in context['groups_details']:
                try:
                    solar_plant = group['instance'].solarplant
                    solar_plants.append({"plant_name": str(solar_plant.name),
                                         "plant_slug": str(solar_plant.slug)})
                except:
                    continue
        except Exception:
            pass

        context["plants"] = json.dumps(solar_plants)
        return context


class SolarClient(ProfileDataMixin, TemplateView):
    template_name = "solarmonitoring/client_page_v3.html"

    def get_context_data(self, **kwargs):
        context = super(SolarClient, self).get_context_data(**kwargs)
        data = self.get_profile_data(**kwargs)
        for key in data.keys():
            context[key] = data[key]
        user = self.request.user
        try:
            webdyn_client = user.organizations_organization.all()[0].dataglengroup.groupClient.webdynClient
        except:
            webdyn_client = False
        context['webdyn_client'] = webdyn_client

        try:
            if (user.organizations_organization.all()[
                0].dataglengroup.groupClient.owner.organization_user.user == user):
                add_user = True
            else:
                add_user = False
        except:
            add_user = False
        context['add_user'] = add_user

        try:
            if webdyn_client is True and add_user is True and user.organizations_organization.all()[
                0].dataglengroup.groupClient.name != "Chemtrols Solar":
                compare_plants = True
            else:
                compare_plants = False
        except:
            compare_plants = False
        context['compare_plants'] = compare_plants
        return context


class FeederAdd(FormView):
    template_name = 'solarmonitoring/feeder_add.html'
    form_class = FeederForm

    def get_success_url(self):
        return reverse_lazy('solar:devices-list', kwargs={'plant_slug': self.kwargs.get('plant_slug')})

    def form_valid(self, form, *args, **kwargs):
        try:
            feeder = form.save(commit=False)
            feeder.user = self.request.user
            feeder.plant = SolarPlant.objects.get(slug=self.kwargs.get('plant_slug'))
            feeder.save()
            self.key = feeder.sourceKey
            return super(FeederAdd, self).form_valid(form)
        except IntegrityError:
            return HttpResponseBadRequest("The name of a source should be unique")
        except SolarPlant.DoesNotExist:
            return HttpResponseBadRequest(
                "There is no solar plant with the name: " + str(self.kwargs.get('plant_slug')))
        except:
            return HttpResponseServerError("INTERNAL SERVER ERROR. Please contact your us at contact@dataglen.com")


class SolarPlantDevicesList(EntryPointMixin, AddSensorsMixin, TemplateView):
    template_name = "solarmonitoring/list_devices.html"

    def get_context_data(self, **kwargs):
        context = super(SolarPlantDevicesList, self).get_context_data()
        try:
            self.plant = SolarPlant.objects.get(slug=self.kwargs.get('plant_slug'))
        except SolarPlant.DoesNotExist:
            HttpResponseBadRequest("There is no solar plant with the name: " + str(self.kwargs.get('plant_slug')))
        context['feeders'] = self.plant.feeder_units.all()
        context['inverters'] = self.plant.inverter_units.all()
        context['independentInverters'] = self.plant.independent_inverter_units.all()
        context['ajbs'] = self.plant.ajb_units.all()
        return context


class FeederUpdate(UpdateView):
    template_name = "solarmonitoring/feeder_update.html"
    form_class = FeederForm
    model = Feeder
    slug_url_kwarg = 'feeder_key'
    slug_field = 'sourceKey'

    def get_success_url(self):
        return reverse_lazy('solar:devices-list', kwargs={'plant_slug': self.kwargs.get('plant_slug')})


class AJBAdd(FormView):
    template_name = 'solarmonitoring/ajb_add.html'
    form_class = AJBForm

    def get_success_url(self):
        return reverse_lazy('solar:devices-list', kwargs={'plant_slug': self.kwargs.get('plant_slug')})

    def form_valid(self, form, *args, **kwargs):
        try:
            ajb = form.save(commit=False)
            ajb.user = self.request.user
            ajb.plant = SolarPlant.objects.get(slug=self.kwargs.get('plant_slug'))
            ajb.inverter = Inverter.objects.get(sourceKey=self.kwargs.get('inverter_key'))
            ajb.save()
            self.key = ajb.sourceKey
            return super(AJBAdd, self).form_valid(form)
        except IntegrityError:
            return HttpResponseBadRequest("The name of a source should be unique")
        except SolarPlant.DoesNotExist:
            return HttpResponseBadRequest(
                "There is no solar plant with the name: " + str(self.kwargs.get('plant_slug')))
        except Exception as exe:
            return HttpResponseServerError(
                str(exe) + "INTERNAL SERVER ERROR. Please contact your us at contact@dataglen.com")


class AJBUpdate(UpdateView):
    template_name = "solarmonitoring/ajb_update.html"
    form_class = AJBForm
    model = AJB
    slug_url_kwarg = 'ajb_key'
    slug_field = 'sourceKey'

    def get_success_url(self):
        return reverse_lazy('solar:devices-list', kwargs={'plant_slug': self.kwargs.get('plant_slug')})


class InverterAdd(FormView):
    template_name = 'solarmonitoring/inverter_add.html'
    form_class = InverterForm

    def get_success_url(self):
        return reverse_lazy('solar:devices-list', kwargs={'plant_slug': self.kwargs.get('plant_slug')})

    def form_valid(self, form, *args, **kwargs):
        try:
            inverter = form.save(commit=False)
            inverter.user = self.request.user
            inverter.plant = SolarPlant.objects.get(slug=self.kwargs.get('plant_slug'))
            inverter.feeder = Feeder.objects.get(sourceKey=self.kwargs.get('feeder_key'))
            inverter.save()
            self.key = inverter.sourceKey
            return super(InverterAdd, self).form_valid(form)
        except IntegrityError:
            return HttpResponseBadRequest("The name of a source should be unique")
        except SolarPlant.DoesNotExist:
            return HttpResponseBadRequest(
                "There is no solar plant with the name: " + str(self.kwargs.get('plant_slug')))
        except Exception as exe:
            return HttpResponseServerError(
                str(exe) + "INTERNAL SERVER ERROR. Please contact your us at contact@dataglen.com")


class InverterUpdate(UpdateView):
    template_name = "solarmonitoring/inverter_update.html"
    form_class = InverterForm
    model = Inverter
    slug_url_kwarg = 'finverter_key'
    slug_field = 'sourceKey'

    def get_success_url(self):
        return reverse_lazy('solar:devices-list', kwargs={'plant_slug': self.kwargs.get('plant_slug')})


class IndependentInverterUpdate(UpdateView):
    template_name = "solarmonitoring/independent_inverter_update.html"
    form_class = IndependentInverterForm
    model = IndependentInverter
    slug_url_kwarg = 'inverter_key'
    slug_field = 'sourceKey'

    def get_success_url(self):
        return reverse_lazy('solar:devices-list', kwargs={'plant_slug': self.kwargs.get('plant_slug')})


class PlantMetaView(ProfileDataMixin, TemplateView):
    template_name = "solarmonitoring/plant_meta.html"

    def get(self, request, *args, **kwargs):
        try:
            self.solar_plant = SolarPlant.objects.get(slug=self.kwargs.get('plant_slug'))
        except SolarPlant.DoesNotExist:
            return HttpResponseBadRequest("There is no solar plat with name: " + str(self.kwargs.get('plant_slug')))
        return self.render_to_response(context=self.get_context_data())

    def get_context_data(self, **kwargs):
        context = super(PlantMetaView, self).get_context_data(**kwargs)
        try:
            plant_meta = PlantMetaSource.objects.get(plant=self.solar_plant)
        except PlantMetaSource.DoesNotExist:
            plant_meta = None
        profile_data = self.get_profile_data()
        for key in profile_data.keys():
            context[key] = profile_data[key]
        context['plant_meta'] = plant_meta
        context['plant'] = self.solar_plant
        # Get the number of tickets assigned.
        tickets = Ticket.objects.filter(assigned_to=self.request.user, status=1)
        tickets = len(tickets)
        context['tickets'] = tickets
        return context


class PlantMetaDownloadView(ProfileDataMixin, TemplateView):
    template_name = "solarmonitoring/plant_meta_download.html"

    def get(self, request, *args, **kwargs):
        try:
            self.solar_plant = SolarPlant.objects.get(slug=self.kwargs.get('plant_slug'))
        except SolarPlant.DoesNotExist:
            return HttpResponseBadRequest("There is no solar plat with name: " + str(self.kwargs.get('plant_slug')))
        return self.render_to_response(context=self.get_context_data())

    def get_context_data(self, **kwargs):
        context = super(PlantMetaDownloadView, self).get_context_data(**kwargs)
        try:
            plant_meta = PlantMetaSource.objects.get(plant=self.solar_plant)
        except PlantMetaSource.DoesNotExist:
            plant_meta = None
        profile_data = self.get_profile_data()
        for key in profile_data.keys():
            context[key] = profile_data[key]
        context['plant_meta'] = plant_meta
        context['plant'] = self.solar_plant
        # Get the number of tickets assigned.
        tickets = Ticket.objects.filter(assigned_to=self.request.user, status=1)
        tickets = len(tickets)
        context['tickets'] = tickets
        return context


class PerformanceRatioView(ProfileDataMixin, TemplateView):
    template_name = "solarmonitoring/performance_ratio.html"

    def get(self, request, *args, **kwargs):
        try:
            plant_slug = self.kwargs.get('plant_slug')
            plant = SolarPlant.objects.get(slug=plant_slug)
            self.plant_slug = plant_slug
            self.plant = plant
            return self.render_to_response(context=self.get_context_data())
        except KeyError:
            return HttpResponseBadRequest("Plant slug or inverter key not mentioned")
        except SolarPlant.DoesNotExist:
            return HttpResponseBadRequest("Invalid plant slug")
        except Exception as exc:
            logger.debug(exc)
            raise Http404

    def get_context_data(self, **kwargs):
        try:
            context = super(PerformanceRatioView, self).get_context_data(**kwargs)
            context['plant_slug'] = self.plant_slug
            context['plant'] = self.plant
            profile_data = self.get_profile_data()
            for key in profile_data.keys():
                context[key] = profile_data[key]
            solar_plants = filter_solar_plants(context)
            assert (self.plant in solar_plants)
            # Get the number of tickets assigned.
            tickets = Ticket.objects.filter(assigned_to=self.request.user, status=1)
            tickets = len(tickets)
            context['tickets'] = tickets
            return context
        except Exception as exc:
            logger.debug(exc)
            raise Http404


class CompareTableView(ProfileDataMixin, TemplateView):
    template_name = "solarmonitoring/compare_table.html"

    def get(self, request, *args, **kwargs):
        try:
            plant_slug = self.kwargs.get('plant_slug')
            plant = SolarPlant.objects.get(slug=plant_slug)
            self.plant_slug = plant_slug
            self.plant = plant
            return self.render_to_response(context=self.get_context_data())
        except KeyError:
            return HttpResponseBadRequest("Plant slug or inverter key not mentioned")
        except SolarPlant.DoesNotExist:
            return HttpResponseBadRequest("Invalid plant slug")
        except Exception as exc:
            logger.debug(exc)
            raise Http404

    def get_context_data(self, **kwargs):
        try:
            context = super(CompareTableView, self).get_context_data(**kwargs)
            try:
                plant_meta = PlantMetaSource.objects.get(plant=self.plant)
            except PlantMetaSource.DoesNotExist:
                plant_meta = None
            context['plant_slug'] = self.plant_slug
            context['plant'] = self.plant
            context['plant_meta'] = plant_meta
            profile_data = self.get_profile_data()
            for key in profile_data.keys():
                context[key] = profile_data[key]
            solar_plants = filter_solar_plants(context)
            assert (self.plant in solar_plants)
            # Get the number of tickets assigned.
            tickets = Ticket.objects.filter(assigned_to=self.request.user, status=1)
            tickets = len(tickets)
            context['tickets'] = tickets
            return context
        except Exception as exc:
            logger.debug(exc)
            raise Http404


class ReportSummaryView(ProfileDataMixin, TemplateView):
    template_name = "solarmonitoring/report_summary.html"

    def get(self, request, *args, **kwargs):
        try:
            plant_slug = self.kwargs.get('plant_slug')
            plant = SolarPlant.objects.get(slug=plant_slug)
            self.plant_slug = plant_slug
            self.plant = plant
            return self.render_to_response(context=self.get_context_data())
        except KeyError:
            return HttpResponseBadRequest("Plant slug or inverter key not mentioned")
        except SolarPlant.DoesNotExist:
            return HttpResponseBadRequest("Invalid plant slug")
        except Exception as exc:
            logger.debug(exc)
            raise Http404

    def get_context_data(self, **kwargs):
        try:
            context = super(ReportSummaryView, self).get_context_data(**kwargs)
            try:
                plant_meta = PlantMetaSource.objects.get(plant=self.plant)
            except PlantMetaSource.DoesNotExist:
                plant_meta = None
            context['plant_slug'] = self.plant_slug
            context['plant'] = self.plant
            context['plant_meta'] = plant_meta
            profile_data = self.get_profile_data()
            for key in profile_data.keys():
                context[key] = profile_data[key]
            solar_plants = filter_solar_plants(context)
            assert (self.plant in solar_plants)
            # Get the number of tickets assigned.
            tickets = Ticket.objects.filter(assigned_to=self.request.user, status=1)
            tickets = len(tickets)
            context['tickets'] = tickets
            return context
        except Exception as exc:
            logger.debug(exc)
            raise Http404


class ComparePlantTableView(ProfileDataMixin, TemplateView):
    template_name = "solarmonitoring/compare_plant_table_jq.html"

    def get(self, request, *args, **kwargs):
        try:
            plant_slug = self.kwargs.get('plant_slug')
            plant = SolarPlant.objects.get(slug=plant_slug)
            self.plant_slug = plant_slug
            self.plant = plant
            final_nodes = []
            inverters_nodes = []
            if hasattr(plant, 'metadata'):
                nodes = []
                for node in plant.metadata.fields.filter(isActive=True):
                    nodes.append({'text': str(node.name),
                                  'source_key': str(plant.metadata.sourceKey)})
                final_nodes.append({'text': "Plant Level Information", "selectable": False, "nodes": nodes})

            if plant.slug == 'rrkabel':
                inverters_unordered = plant.independent_inverter_units.all().order_by('name')
                inverters = sorted(inverters_unordered, key=inverter_order)
            else:
                inverters = plant.independent_inverter_units.all().order_by('id')

            for inverter in inverters:
                data_point = {}
                data_point["text"] = str(inverter.name)
                data_point["selectable"] = False
                nodes = []
                for node in inverter.fields.filter(isActive=True):
                    nodes.append({'text': str(node.name),
                                  'source_key': str(inverter.sourceKey)})
                data_point['nodes'] = nodes
                inverters_nodes.append(data_point)
            final_nodes.append({'text': "Inverters", "selectable": False, "nodes": inverters_nodes})
            context = self.get_context_data()
            context['options'] = json.dumps(final_nodes)
            return self.render_to_response(context=context)
        except KeyError:
            return HttpResponseBadRequest("Plant slug or inverter key not mentioned")
        except SolarPlant.DoesNotExist:
            return HttpResponseBadRequest("Invalid plant slug")
        except Exception as exc:
            logger.debug(exc)
            raise Http404

    def get_context_data(self, **kwargs):
        try:
            context = super(ComparePlantTableView, self).get_context_data(**kwargs)
            try:
                plant_meta = PlantMetaSource.objects.get(plant=self.plant)
            except PlantMetaSource.DoesNotExist:
                plant_meta = None
            context['plant_slug'] = self.plant_slug
            context['plant'] = self.plant
            context['plant_meta'] = plant_meta
            profile_data = self.get_profile_data()
            for key in profile_data.keys():
                context[key] = profile_data[key]
            solar_plants = filter_solar_plants(context)
            assert (self.plant in solar_plants)
            # Get the number of tickets assigned.
            tickets = Ticket.objects.filter(assigned_to=self.request.user, status=1)
            tickets = len(tickets)
            context['tickets'] = tickets
            return context
        except Exception as exc:
            logger.debug(exc)
            raise Http404


class InverterDeviceComparisonsView(ProfileDataMixin, TemplateView):
    template_name = "solarmonitoring/inverter_device_comparisons.html"

    def get(self, request, *args, **kwargs):
        try:
            plant_slug = self.kwargs.get('plant_slug')
            plant = SolarPlant.objects.get(slug=plant_slug)
            self.plant_slug = plant_slug
            self.plant = plant
            final_nodes = []

            if plant.slug == 'rrkabel':
                inverters_unordered = plant.independent_inverter_units.all().order_by('name')
                inverters = sorted(inverters_unordered, key=inverter_order)
            else:
                inverters = plant.independent_inverter_units.all().order_by('id')

            for inverter in inverters:
                inverters_nodes = []
                if len(inverter.ajb_units.all()) > 0:
                    for ajb in inverter.ajb_units.all().order_by('id'):
                        data_point = {}
                        data_point["text"] = str(ajb.name)
                        data_point["selectable"] = False
                        data_point["showCheckbox"] = True
                        nodes = []
                        for node in ajb.fields.filter(isActive=True).order_by('id'):
                            if "S" in node.name or "VOLTAGE" in node.name:
                                nodes.append({'text': str(node.name),
                                              'showCheckbox': True,
                                              'source_key': str(ajb.sourceKey)})
                        data_point['nodes'] = nodes
                        inverters_nodes.append(data_point)
                    final_nodes.append(
                        {'text': inverter.name, "selectable": False, "showCheckbox": False, "nodes": inverters_nodes})
            context = self.get_context_data()
            context['options'] = json.dumps(final_nodes)
            return self.render_to_response(context=context)
        except KeyError:
            return HttpResponseBadRequest("Plant slug or inverter key not mentioned")
        except SolarPlant.DoesNotExist:
            return HttpResponseBadRequest("Invalid plant slug")
        except Exception as exc:
            logger.debug(exc)
            raise Http404

    def get_context_data(self, **kwargs):
        try:
            context = super(InverterDeviceComparisonsView, self).get_context_data(**kwargs)
            try:
                plant_meta = PlantMetaSource.objects.get(plant=self.plant)
            except PlantMetaSource.DoesNotExist:
                plant_meta = None
            context['plant_slug'] = self.plant_slug
            context['plant'] = self.plant
            context['plant_meta'] = plant_meta
            profile_data = self.get_profile_data()
            for key in profile_data.keys():
                context[key] = profile_data[key]
            solar_plants = filter_solar_plants(context)
            assert (self.plant in solar_plants)
            return context
        except Exception as exc:
            logger.debug(exc)
            raise Http404


class TicketsListView(ProfileDataMixin, TemplateView):
    template_name = "solarmonitoring/ticketlist.html"

    def get(self, request, *args, **kwargs):
        try:
            plant_slug = self.kwargs.get('plant_slug')
            plant = SolarPlant.objects.get(slug=plant_slug)
            self.plant_slug = plant_slug
            self.plant = plant
            final_nodes = []
            inverters_nodes = []
            if hasattr(plant, 'metadata'):
                nodes = []
                for node in plant.metadata.fields.filter(isActive=True):
                    nodes.append({'text': str(node.name),
                                  'source_key': str(plant.metadata.sourceKey)})
                final_nodes.append({'text': "Plant Level Information", "selectable": False, "nodes": nodes})

            if plant.slug == 'rrkabel':
                inverters_unordered = plant.independent_inverter_units.all().order_by('name')
                inverters = sorted(inverters_unordered, key=inverter_order)
            else:
                inverters = plant.independent_inverter_units.all().order_by('id')

            for inverter in inverters:
                data_point = {}
                data_point["text"] = str(inverter.name)
                data_point["selectable"] = False
                nodes = []
                for node in inverter.fields.filter(isActive=True):
                    nodes.append({'text': str(node.name),
                                  'source_key': str(inverter.sourceKey)})
                data_point['nodes'] = nodes
                inverters_nodes.append(data_point)
            final_nodes.append({'text': "Inverters", "selectable": False, "nodes": inverters_nodes})
            context = self.get_context_data()
            context['options'] = json.dumps(final_nodes)
            return self.render_to_response(context=context)
        except KeyError:
            return HttpResponseBadRequest("Plant slug or inverter key not mentioned")
        except SolarPlant.DoesNotExist:
            return HttpResponseBadRequest("Invalid plant slug")
        except Exception as exc:
            logger.debug(exc)
            raise Http404

    def get_context_data(self, **kwargs):
        try:
            context = super(TicketsListView, self).get_context_data(**kwargs)
            try:
                plant_meta = PlantMetaSource.objects.get(plant=self.plant)
            except PlantMetaSource.DoesNotExist:
                plant_meta = None
            context['plant_slug'] = self.plant_slug
            context['plant'] = self.plant
            context['plant_meta'] = plant_meta
            profile_data = self.get_profile_data()
            for key in profile_data.keys():
                context[key] = profile_data[key]
            solar_plants = filter_solar_plants(context)
            assert (self.plant in solar_plants)
            # Get the number of tickets assigned.
            tickets = Ticket.objects.filter(assigned_to=self.request.user, status=1)
            tickets = len(tickets)
            context['tickets'] = tickets
            return context
        except Exception as exc:
            logger.debug(exc)
            raise Http404


class TicketViewView(ProfileDataMixin, TemplateView):
    template_name = "solarmonitoring/ticket_view.html"

    def get(self, request, *args, **kwargs):
        try:
            plant_slug = self.kwargs.get('plant_slug')
            plant = SolarPlant.objects.get(slug=plant_slug)
            self.plant_slug = plant_slug
            self.plant = plant
            final_nodes = []
            inverters_nodes = []
            if hasattr(plant, 'metadata'):
                nodes = []
                for node in plant.metadata.fields.filter(isActive=True):
                    nodes.append({'text': str(node.name),
                                  'source_key': str(plant.metadata.sourceKey)})
                final_nodes.append({'text': "Plant Level Information", "selectable": False, "nodes": nodes})

            if plant.slug == 'rrkabel':
                inverters_unordered = plant.independent_inverter_units.all().order_by('name')
                inverters = sorted(inverters_unordered, key=inverter_order)
            else:
                inverters = plant.independent_inverter_units.all().order_by('id')

            for inverter in inverters:
                inverters_nodes = []
                if len(inverter.ajb_units.all()) > 0:
                    for ajb in inverter.ajb_units.all().order_by('id'):
                        data_point = {}
                        data_point["text"] = str(ajb.name)
                        data_point["selectable"] = False
                        data_point["showCheckbox"] = True
                        nodes = []
                        for node in ajb.fields.filter(isActive=True).order_by('id'):
                            if "S" in node.name or "VOLTAGE" in node.name:
                                nodes.append({'text': str(node.name),
                                              'showCheckbox': True,
                                              'source_key': str(ajb.sourceKey)})
                        data_point['nodes'] = nodes
                        inverters_nodes.append(data_point)
                    final_nodes.append(
                        {'text': inverter.name, "selectable": False, "showCheckbox": False, "nodes": inverters_nodes})
                data_point = {}
                data_point["text"] = str(inverter.name)
                data_point["selectable"] = False
                nodes = []
                for node in inverter.fields.filter(isActive=True):
                    nodes.append({'text': str(node.name),
                                  'source_key': str(inverter.sourceKey)})
                data_point['nodes'] = nodes
                inverters_nodes.append(data_point)
            final_nodes.append({'text': "Inverters", "selectable": False, "nodes": inverters_nodes})

            context = self.get_context_data()
            context['options'] = json.dumps(final_nodes)
            return self.render_to_response(context=context)
        except KeyError:
            return HttpResponseBadRequest("Plant slug or inverter key not mentioned")
        except SolarPlant.DoesNotExist:
            return HttpResponseBadRequest("Invalid plant slug")
        except Exception as exc:
            logger.debug(exc)
            raise Http404

    def get_context_data(self, **kwargs):
        try:
            context = super(TicketViewView, self).get_context_data(**kwargs)
            try:
                plant_meta = PlantMetaSource.objects.get(plant=self.plant)
            except PlantMetaSource.DoesNotExist:
                plant_meta = None
            context['plant_slug'] = self.plant_slug
            context['plant'] = self.plant
            context['plant_meta'] = plant_meta
            profile_data = self.get_profile_data()
            for key in profile_data.keys():
                context[key] = profile_data[key]
            solar_plants = filter_solar_plants(context)
            assert (self.plant in solar_plants)
            # Get the number of tickets assigned.
            tickets = Ticket.objects.filter(assigned_to=self.request.user, status=1)
            tickets = len(tickets)
            context['tickets'] = tickets
            return context
        except Exception as exc:
            logger.debug(exc)
            raise Http404


class CUFView(ProfileDataMixin, TemplateView):
    template_name = "solarmonitoring/cuf.html"

    def get(self, request, *args, **kwargs):
        try:
            plant_slug = self.kwargs.get('plant_slug')
            plant = SolarPlant.objects.get(slug=plant_slug)
            self.plant_slug = plant_slug
            self.plant = plant
            return self.render_to_response(context=self.get_context_data())
        except KeyError:
            return HttpResponseBadRequest("Plant slug or inverter key not mentioned")
        except SolarPlant.DoesNotExist:
            return HttpResponseBadRequest("Invalid plant slug")
        except Exception as exc:
            logger.debug(exc)
            raise Http404

    def get_context_data(self, **kwargs):
        try:
            context = super(CUFView, self).get_context_data(**kwargs)
            context['plant_slug'] = self.plant_slug
            context['plant'] = self.plant
            profile_data = self.get_profile_data()
            for key in profile_data.keys():
                context[key] = profile_data[key]
            solar_plants = filter_solar_plants(context)
            assert (self.plant in solar_plants)
            # Get the number of tickets assigned.
            tickets = Ticket.objects.filter(assigned_to=self.request.user, status=1)
            tickets = len(tickets)
            context['tickets'] = tickets
            return context
        except Exception as exc:
            logger.debug(exc)
            raise Http404


class SummaryViewView(ProfileDataMixin, TemplateView):
    template_name = "solarmonitoring/summary_report.html"

    def get(self, request, *args, **kwargs):
        try:
            plant_slug = self.kwargs.get('plant_slug')
            plant = SolarPlant.objects.get(slug=plant_slug)
            self.plant_slug = plant_slug
            self.plant = plant
            final_nodes = []
            inverters_nodes = []
            if hasattr(plant, 'metadata'):
                nodes = []
                for node in plant.metadata.fields.filter(isActive=True):
                    nodes.append({'text': str(node.name),
                                  'source_key': str(plant.metadata.sourceKey)})
                final_nodes.append({'text': "Plant Level Information", "selectable": False, "nodes": nodes})

            if plant.slug == 'rrkabel':
                inverters_unordered = plant.independent_inverter_units.all().order_by('name')
                inverters = sorted(inverters_unordered, key=inverter_order)
            else:
                inverters = plant.independent_inverter_units.all().order_by('id')

            for inverter in inverters:
                inverters_nodes = []
                if len(inverter.ajb_units.all()) > 0:
                    for ajb in inverter.ajb_units.all().order_by('id'):
                        data_point = {}
                        data_point["text"] = str(ajb.name)
                        data_point["selectable"] = False
                        data_point["showCheckbox"] = True
                        nodes = []
                        for node in ajb.fields.filter(isActive=True).order_by('id'):
                            if "S" in node.name or "VOLTAGE" in node.name:
                                nodes.append({'text': str(node.name),
                                              'showCheckbox': True,
                                              'source_key': str(ajb.sourceKey)})
                        data_point['nodes'] = nodes
                        inverters_nodes.append(data_point)
                    final_nodes.append(
                        {'text': inverter.name, "selectable": False, "showCheckbox": False, "nodes": inverters_nodes})
                data_point = {}
                data_point["text"] = str(inverter.name)
                data_point["selectable"] = False
                nodes = []
                for node in inverter.fields.filter(isActive=True):
                    nodes.append({'text': str(node.name),
                                  'source_key': str(inverter.sourceKey)})
                data_point['nodes'] = nodes
                inverters_nodes.append(data_point)
            final_nodes.append({'text': "Inverters", "selectable": False, "nodes": inverters_nodes})

            context = self.get_context_data()
            context['options'] = json.dumps(final_nodes)
            return self.render_to_response(context=context)
        except KeyError:
            return HttpResponseBadRequest("Plant slug or inverter key not mentioned")
        except SolarPlant.DoesNotExist:
            return HttpResponseBadRequest("Invalid plant slug")
        except Exception as exc:
            logger.debug(exc)
            raise Http404

    def get_context_data(self, **kwargs):
        try:
            context = super(SummaryViewView, self).get_context_data(**kwargs)
            try:
                plant_meta = PlantMetaSource.objects.get(plant=self.plant)
            except PlantMetaSource.DoesNotExist:
                plant_meta = None
            context['plant_slug'] = self.plant_slug
            context['plant'] = self.plant
            context['plant_meta'] = plant_meta
            profile_data = self.get_profile_data()
            for key in profile_data.keys():
                context[key] = profile_data[key]
            solar_plants = filter_solar_plants(context)
            assert (self.plant in solar_plants)
            # Get the number of tickets assigned.
            tickets = Ticket.objects.filter(assigned_to=self.request.user, status=1)
            tickets = len(tickets)
            context['tickets'] = tickets
            return context
        except Exception as exc:
            logger.debug(exc)
            raise Http404


class ClientSummaryViewView(ProfileDataMixin, TemplateView):
    template_name = "solarmonitoring/summary_client.html"

    def get(self, request, *args, **kwargs):
        try:
            plant_slug = self.kwargs.get('plant_slug')
            plant = SolarPlant.objects.get(slug=plant_slug)
            self.plant_slug = plant_slug
            self.plant = plant
            final_nodes = []
            inverters_nodes = []
            if hasattr(plant, 'metadata'):
                nodes = []
                for node in plant.metadata.fields.filter(isActive=True):
                    nodes.append({'text': str(node.name),
                                  'source_key': str(plant.metadata.sourceKey)})
                final_nodes.append({'text': "Plant Level Information", "selectable": False, "nodes": nodes})

            if plant.slug == 'rrkabel':
                inverters_unordered = plant.independent_inverter_units.all().order_by('name')
                inverters = sorted(inverters_unordered, key=inverter_order)
            else:
                inverters = plant.independent_inverter_units.all().order_by('id')

            for inverter in inverters:
                inverters_nodes = []
                if len(inverter.ajb_units.all()) > 0:
                    for ajb in inverter.ajb_units.all().order_by('id'):
                        data_point = {}
                        data_point["text"] = str(ajb.name)
                        data_point["selectable"] = False
                        data_point["showCheckbox"] = True
                        nodes = []
                        for node in ajb.fields.filter(isActive=True).order_by('id'):
                            if "S" in node.name or "VOLTAGE" in node.name:
                                nodes.append({'text': str(node.name),
                                              'showCheckbox': True,
                                              'source_key': str(ajb.sourceKey)})
                        data_point['nodes'] = nodes
                        inverters_nodes.append(data_point)
                    final_nodes.append(
                        {'text': inverter.name, "selectable": False, "showCheckbox": False, "nodes": inverters_nodes})
                data_point = {}
                data_point["text"] = str(inverter.name)
                data_point["selectable"] = False
                nodes = []
                for node in inverter.fields.filter(isActive=True):
                    nodes.append({'text': str(node.name),
                                  'source_key': str(inverter.sourceKey)})
                data_point['nodes'] = nodes
                inverters_nodes.append(data_point)
            final_nodes.append({'text': "Inverters", "selectable": False, "nodes": inverters_nodes})

            context = self.get_context_data()
            context['options'] = json.dumps(final_nodes)
            return self.render_to_response(context=context)
        except KeyError:
            return HttpResponseBadRequest("Plant slug or inverter key not mentioned")
        except SolarPlant.DoesNotExist:
            return HttpResponseBadRequest("Invalid plant slug")
        except Exception as exc:
            logger.debug(exc)
            raise Http404

    def get_context_data(self, **kwargs):
        try:
            context = super(ClientSummaryViewView, self).get_context_data(**kwargs)
            try:
                plant_meta = PlantMetaSource.objects.get(plant=self.plant)
            except PlantMetaSource.DoesNotExist:
                plant_meta = None
            context['plant_slug'] = self.plant_slug
            context['plant'] = self.plant
            context['plant_meta'] = plant_meta
            profile_data = self.get_profile_data()
            for key in profile_data.keys():
                context[key] = profile_data[key]
            solar_plants = filter_solar_plants(context)
            assert (self.plant in solar_plants)
            # Get the number of tickets assigned.
            tickets = Ticket.objects.filter(assigned_to=self.request.user, status=1)
            tickets = len(tickets)
            context['tickets'] = tickets
            return context
        except Exception as exc:
            logger.debug(exc)
            raise Http404


class InverterResidualsViewView(ProfileDataMixin, TemplateView):
    template_name = "solarmonitoring/inverter_residuals.html"

    def get(self, request, *args, **kwargs):
        try:
            plant_slug = self.kwargs.get('plant_slug')
            plant = SolarPlant.objects.get(slug=plant_slug)
            self.plant_slug = plant_slug
            self.plant = plant
            final_nodes = []
            inverters_nodes = []
            if hasattr(plant, 'metadata'):
                nodes = []
                for node in plant.metadata.fields.filter(isActive=True):
                    nodes.append({'text': str(node.name),
                                  'source_key': str(plant.metadata.sourceKey)})
                final_nodes.append({'text': "Plant Level Information", "selectable": False, "nodes": nodes})

            if plant.slug == 'rrkabel':
                inverters_unordered = plant.independent_inverter_units.all().order_by('name')
                inverters = sorted(inverters_unordered, key=inverter_order)
            else:
                inverters = plant.independent_inverter_units.all().order_by('id')

            for inverter in inverters:
                inverters_nodes = []
                if len(inverter.ajb_units.all()) > 0:
                    for ajb in inverter.ajb_units.all().order_by('id'):
                        data_point = {}
                        data_point["text"] = str(ajb.name)
                        data_point["selectable"] = False
                        data_point["showCheckbox"] = True
                        nodes = []
                        for node in ajb.fields.filter(isActive=True).order_by('id'):
                            if "S" in node.name or "VOLTAGE" in node.name:
                                nodes.append({'text': str(node.name),
                                              'showCheckbox': True,
                                              'source_key': str(ajb.sourceKey)})
                        data_point['nodes'] = nodes
                        inverters_nodes.append(data_point)
                    final_nodes.append(
                        {'text': inverter.name, "selectable": False, "showCheckbox": False, "nodes": inverters_nodes})
                data_point = {}
                data_point["text"] = str(inverter.name)
                data_point["selectable"] = False
                nodes = []
                for node in inverter.fields.filter(isActive=True):
                    nodes.append({'text': str(node.name),
                                  'source_key': str(inverter.sourceKey)})
                data_point['nodes'] = nodes
                inverters_nodes.append(data_point)
            final_nodes.append({'text': "Inverters", "selectable": False, "nodes": inverters_nodes})

            context = self.get_context_data()
            context['options'] = json.dumps(final_nodes)
            return self.render_to_response(context=context)
        except KeyError:
            return HttpResponseBadRequest("Plant slug or inverter key not mentioned")
        except SolarPlant.DoesNotExist:
            return HttpResponseBadRequest("Invalid plant slug")
        except Exception as exc:
            logger.debug(exc)
            raise Http404

    def get_context_data(self, **kwargs):
        try:
            context = super(InverterResidualsViewView, self).get_context_data(**kwargs)
            try:
                plant_meta = PlantMetaSource.objects.get(plant=self.plant)
            except PlantMetaSource.DoesNotExist:
                plant_meta = None
            context['plant_slug'] = self.plant_slug
            context['plant'] = self.plant
            context['plant_meta'] = plant_meta
            profile_data = self.get_profile_data()
            for key in profile_data.keys():
                context[key] = profile_data[key]
            solar_plants = filter_solar_plants(context)
            assert (self.plant in solar_plants)
            # Get the number of tickets assigned.
            tickets = Ticket.objects.filter(assigned_to=self.request.user, status=1)
            tickets = len(tickets)
            context['tickets'] = tickets
            return context
        except Exception as exc:
            logger.debug(exc)
            raise Http404


class MultipleParametersViewView(ProfileDataMixin, TemplateView):
    template_name = "solarmonitoring/plant_multiple_parameters.html"

    def get(self, request, *args, **kwargs):
        try:
            plant_slug = self.kwargs.get('plant_slug')
            plant = SolarPlant.objects.get(slug=plant_slug)
            self.plant_slug = plant_slug
            self.plant = plant
            final_nodes = []
            inverters_nodes = []
            if hasattr(plant, 'metadata'):
                nodes = []
                for node in plant.metadata.fields.filter(isActive=True):
                    nodes.append({'text': str(node.name),
                                  'source_key': str(plant.metadata.sourceKey)})
                final_nodes.append({'text': "Plant Level Information", "selectable": False, "nodes": nodes})

            if plant.slug == 'rrkabel':
                inverters_unordered = plant.independent_inverter_units.all().order_by('name')
                inverters = sorted(inverters_unordered, key=inverter_order)
            else:
                inverters = plant.independent_inverter_units.all().order_by('id')

            for inverter in inverters:
                inverters_nodes = []
                if len(inverter.ajb_units.all()) > 0:
                    for ajb in inverter.ajb_units.all().order_by('id'):
                        data_point = {}
                        data_point["text"] = str(ajb.name)
                        data_point["selectable"] = False
                        data_point["showCheckbox"] = True
                        nodes = []
                        for node in ajb.fields.filter(isActive=True).order_by('id'):
                            if "S" in node.name or "VOLTAGE" in node.name:
                                nodes.append({'text': str(node.name),
                                              'showCheckbox': True,
                                              'source_key': str(ajb.sourceKey)})
                        data_point['nodes'] = nodes
                        inverters_nodes.append(data_point)
                    final_nodes.append(
                        {'text': inverter.name, "selectable": False, "showCheckbox": False, "nodes": inverters_nodes})
                data_point = {}
                data_point["text"] = str(inverter.name)
                data_point["selectable"] = False
                nodes = []
                for node in inverter.fields.filter(isActive=True):
                    nodes.append({'text': str(node.name),
                                  'source_key': str(inverter.sourceKey)})
                data_point['nodes'] = nodes
                inverters_nodes.append(data_point)
            final_nodes.append({'text': "Inverters", "selectable": False, "nodes": inverters_nodes})

            context = self.get_context_data()
            context['options'] = json.dumps(final_nodes)
            return self.render_to_response(context=context)
        except KeyError:
            return HttpResponseBadRequest("Plant slug or inverter key not mentioned")
        except SolarPlant.DoesNotExist:
            return HttpResponseBadRequest("Invalid plant slug")
        except Exception as exc:
            logger.debug(exc)
            raise Http404

    def get_context_data(self, **kwargs):
        try:
            context = super(MultipleParametersViewView, self).get_context_data(**kwargs)
            try:
                plant_meta = PlantMetaSource.objects.get(plant=self.plant)
            except PlantMetaSource.DoesNotExist:
                plant_meta = None
            context['plant_slug'] = self.plant_slug
            context['plant'] = self.plant
            context['plant_meta'] = plant_meta
            profile_data = self.get_profile_data()
            for key in profile_data.keys():
                context[key] = profile_data[key]
            solar_plants = filter_solar_plants(context)
            assert (self.plant in solar_plants)
            # Get the number of tickets assigned.
            tickets = Ticket.objects.filter(assigned_to=self.request.user, status=1)
            tickets = len(tickets)
            context['tickets'] = tickets
            return context
        except Exception as exc:
            logger.debug(exc)
            raise Http404


class AddPlantsViewView(ProfileDataMixin, TemplateView):
    template_name = "solarmonitoring/add_plant.html"

    def get(self, request, *args, **kwargs):
        try:
            plant_slug = self.kwargs.get('plant_slug')
            plant = SolarPlant.objects.get(slug=plant_slug)
            self.plant_slug = plant_slug
            self.plant = plant
            final_nodes = []
            inverters_nodes = []
            if hasattr(plant, 'metadata'):
                nodes = []
                for node in plant.metadata.fields.filter(isActive=True):
                    nodes.append({'text': str(node.name),
                                  'source_key': str(plant.metadata.sourceKey)})
                final_nodes.append({'text': "Plant Level Information", "selectable": False, "nodes": nodes})

            if plant.slug == 'rrkabel':
                inverters_unordered = plant.independent_inverter_units.all().order_by('name')
                inverters = sorted(inverters_unordered, key=inverter_order)
            else:
                inverters = plant.independent_inverter_units.all().order_by('id')

            for inverter in inverters:
                inverters_nodes = []
                if len(inverter.ajb_units.all()) > 0:
                    for ajb in inverter.ajb_units.all().order_by('id'):
                        data_point = {}
                        data_point["text"] = str(ajb.name)
                        data_point["selectable"] = False
                        data_point["showCheckbox"] = True
                        nodes = []
                        for node in ajb.fields.filter(isActive=True).order_by('id'):
                            if "S" in node.name or "VOLTAGE" in node.name:
                                nodes.append({'text': str(node.name),
                                              'showCheckbox': True,
                                              'source_key': str(ajb.sourceKey)})
                        data_point['nodes'] = nodes
                        inverters_nodes.append(data_point)
                    final_nodes.append(
                        {'text': inverter.name, "selectable": False, "showCheckbox": False, "nodes": inverters_nodes})
                data_point = {}
                data_point["text"] = str(inverter.name)
                data_point["selectable"] = False
                nodes = []
                for node in inverter.fields.filter(isActive=True):
                    nodes.append({'text': str(node.name),
                                  'source_key': str(inverter.sourceKey)})
                data_point['nodes'] = nodes
                inverters_nodes.append(data_point)
            final_nodes.append({'text': "Inverters", "selectable": False, "nodes": inverters_nodes})

            context = self.get_context_data()
            context['options'] = json.dumps(final_nodes)
            return self.render_to_response(context=context)
        except KeyError:
            return HttpResponseBadRequest("Plant slug or inverter key not mentioned")
        except SolarPlant.DoesNotExist:
            return HttpResponseBadRequest("Invalid plant slug")
        except Exception as exc:
            logger.debug(exc)
            raise Http404

    def get_context_data(self, **kwargs):
        try:
            context = super(AddPlantsViewView, self).get_context_data(**kwargs)
            try:
                plant_meta = PlantMetaSource.objects.get(plant=self.plant)
            except PlantMetaSource.DoesNotExist:
                plant_meta = None
            context['plant_slug'] = self.plant_slug
            context['plant'] = self.plant
            context['plant_meta'] = plant_meta
            profile_data = self.get_profile_data()
            for key in profile_data.keys():
                context[key] = profile_data[key]
            solar_plants = filter_solar_plants(context)
            assert (self.plant in solar_plants)
            # Get the number of tickets assigned.
            tickets = Ticket.objects.filter(assigned_to=self.request.user, status=1)
            tickets = len(tickets)
            context['tickets'] = tickets
            return context
        except Exception as exc:
            logger.debug(exc)
            raise Http404


class PlantMetricsViewView(ProfileDataMixin, TemplateView):
    template_name = "solarmonitoring/plant_metrics.html"

    def get(self, request, *args, **kwargs):
        try:
            plant_slug = self.kwargs.get('plant_slug')
            plant = SolarPlant.objects.get(slug=plant_slug)
            self.plant_slug = plant_slug
            self.plant = plant
            final_nodes = []
            inverters_nodes = []
            if hasattr(plant, 'metadata'):
                nodes = []
                for node in plant.metadata.fields.filter(isActive=True):
                    nodes.append({'text': str(node.name),
                                  'source_key': str(plant.metadata.sourceKey)})
                final_nodes.append({'text': "Plant Level Information", "selectable": False, "nodes": nodes})

            if plant.slug == 'rrkabel':
                inverters_unordered = plant.independent_inverter_units.all().order_by('name')
                inverters = sorted(inverters_unordered, key=inverter_order)
            else:
                inverters = plant.independent_inverter_units.all().order_by('id')

            for inverter in inverters:
                inverters_nodes = []
                if len(inverter.ajb_units.all()) > 0:
                    for ajb in inverter.ajb_units.all().order_by('id'):
                        data_point = {}
                        data_point["text"] = str(ajb.name)
                        data_point["selectable"] = False
                        data_point["showCheckbox"] = True
                        nodes = []
                        for node in ajb.fields.filter(isActive=True).order_by('id'):
                            if "S" in node.name or "VOLTAGE" in node.name:
                                nodes.append({'text': str(node.name),
                                              'showCheckbox': True,
                                              'source_key': str(ajb.sourceKey)})
                        data_point['nodes'] = nodes
                        inverters_nodes.append(data_point)
                    final_nodes.append(
                        {'text': inverter.name, "selectable": False, "showCheckbox": False, "nodes": inverters_nodes})
                data_point = {}
                data_point["text"] = str(inverter.name)
                data_point["selectable"] = False
                nodes = []
                for node in inverter.fields.filter(isActive=True):
                    nodes.append({'text': str(node.name),
                                  'source_key': str(inverter.sourceKey)})
                data_point['nodes'] = nodes
                inverters_nodes.append(data_point)
            final_nodes.append({'text': "Inverters", "selectable": False, "nodes": inverters_nodes})

            context = self.get_context_data()
            context['options'] = json.dumps(final_nodes)
            return self.render_to_response(context=context)
        except KeyError:
            return HttpResponseBadRequest("Plant slug or inverter key not mentioned")
        except SolarPlant.DoesNotExist:
            return HttpResponseBadRequest("Invalid plant slug")
        except Exception as exc:
            logger.debug(exc)
            raise Http404

    def get_context_data(self, **kwargs):
        try:
            context = super(PlantMetricsViewView, self).get_context_data(**kwargs)
            try:
                plant_meta = PlantMetaSource.objects.get(plant=self.plant)
            except PlantMetaSource.DoesNotExist:
                plant_meta = None
            context['plant_slug'] = self.plant_slug
            context['plant'] = self.plant
            context['plant_meta'] = plant_meta
            profile_data = self.get_profile_data()
            for key in profile_data.keys():
                context[key] = profile_data[key]
            solar_plants = filter_solar_plants(context)
            assert (self.plant in solar_plants)
            # Get the number of tickets assigned.
            tickets = Ticket.objects.filter(assigned_to=self.request.user, status=1)
            tickets = len(tickets)
            context['tickets'] = tickets
            return context
        except Exception as exc:
            logger.debug(exc)
            raise Http404


class AlarmsListViewView(ProfileDataMixin, TemplateView):
    template_name = "solarmonitoring/alarms_list.html"

    def get(self, request, *args, **kwargs):
        try:
            plant_slug = self.kwargs.get('plant_slug')
            plant = SolarPlant.objects.get(slug=plant_slug)
            self.plant_slug = plant_slug
            self.plant = plant
            final_nodes = []
            inverters_nodes = []
            if hasattr(plant, 'metadata'):
                nodes = []
                for node in plant.metadata.fields.filter(isActive=True):
                    nodes.append({'text': str(node.name),
                                  'source_key': str(plant.metadata.sourceKey)})
                final_nodes.append({'text': "Plant Level Information", "selectable": False, "nodes": nodes})

            if plant.slug == 'rrkabel':
                inverters_unordered = plant.independent_inverter_units.all().order_by('name')
                inverters = sorted(inverters_unordered, key=inverter_order)
            else:
                inverters = plant.independent_inverter_units.all().order_by('id')

            for inverter in inverters:
                inverters_nodes = []
                if len(inverter.ajb_units.all()) > 0:
                    for ajb in inverter.ajb_units.all().order_by('id'):
                        data_point = {}
                        data_point["text"] = str(ajb.name)
                        data_point["selectable"] = False
                        data_point["showCheckbox"] = True
                        nodes = []
                        for node in ajb.fields.filter(isActive=True).order_by('id'):
                            if "S" in node.name or "VOLTAGE" in node.name:
                                nodes.append({'text': str(node.name),
                                              'showCheckbox': True,
                                              'source_key': str(ajb.sourceKey)})
                        data_point['nodes'] = nodes
                        inverters_nodes.append(data_point)
                    final_nodes.append(
                        {'text': inverter.name, "selectable": False, "showCheckbox": False, "nodes": inverters_nodes})
                data_point = {}
                data_point["text"] = str(inverter.name)
                data_point["selectable"] = False
                nodes = []
                for node in inverter.fields.filter(isActive=True):
                    nodes.append({'text': str(node.name),
                                  'source_key': str(inverter.sourceKey)})
                data_point['nodes'] = nodes
                inverters_nodes.append(data_point)
            final_nodes.append({'text': "Inverters", "selectable": False, "nodes": inverters_nodes})

            context = self.get_context_data()
            context['options'] = json.dumps(final_nodes)
            return self.render_to_response(context=context)
        except KeyError:
            return HttpResponseBadRequest("Plant slug or inverter key not mentioned")
        except SolarPlant.DoesNotExist:
            return HttpResponseBadRequest("Invalid plant slug")
        except Exception as exc:
            logger.debug(exc)
            raise Http404

    def get_context_data(self, **kwargs):
        try:
            context = super(AlarmsListViewView, self).get_context_data(**kwargs)
            try:
                plant_meta = PlantMetaSource.objects.get(plant=self.plant)
            except PlantMetaSource.DoesNotExist:
                plant_meta = None
            context['plant_slug'] = self.plant_slug
            context['plant'] = self.plant
            context['plant_meta'] = plant_meta
            profile_data = self.get_profile_data()
            for key in profile_data.keys():
                context[key] = profile_data[key]
            solar_plants = filter_solar_plants(context)
            assert (self.plant in solar_plants)
            # Get the number of tickets assigned.
            tickets = Ticket.objects.filter(assigned_to=self.request.user, status=1)
            tickets = len(tickets)
            context['tickets'] = tickets
            return context
        except Exception as exc:
            logger.debug(exc)
            raise Http404


class InvertersAjbsSecondViewView(ProfileDataMixin, TemplateView):
    template_name = "solarmonitoring/inverter_ajb_second.html"

    def get(self, request, *args, **kwargs):
        try:
            plant_slug = self.kwargs.get('plant_slug')
            plant = SolarPlant.objects.get(slug=plant_slug)
            self.plant_slug = plant_slug
            self.plant = plant
            final_nodes = []
            inverters_nodes = []
            if hasattr(plant, 'metadata'):
                nodes = []
                for node in plant.metadata.fields.filter(isActive=True):
                    nodes.append({'text': str(node.name),
                                  'source_key': str(plant.metadata.sourceKey)})
                final_nodes.append({'text': "Plant Level Information", "selectable": False, "nodes": nodes})

            if plant.slug == 'rrkabel':
                inverters_unordered = plant.independent_inverter_units.all().order_by('name')
                inverters = sorted(inverters_unordered, key=inverter_order)
            else:
                inverters = plant.independent_inverter_units.all().order_by('id')

            for inverter in inverters:
                inverters_nodes = []
                if len(inverter.ajb_units.all()) > 0:
                    for ajb in inverter.ajb_units.all().order_by('id'):
                        data_point = {}
                        data_point["text"] = str(ajb.name)
                        data_point["selectable"] = False
                        data_point["showCheckbox"] = True
                        nodes = []
                        for node in ajb.fields.filter(isActive=True).order_by('id'):
                            if "S" in node.name or "VOLTAGE" in node.name:
                                nodes.append({'text': str(node.name),
                                              'showCheckbox': True,
                                              'source_key': str(ajb.sourceKey)})
                        data_point['nodes'] = nodes
                        inverters_nodes.append(data_point)
                    final_nodes.append(
                        {'text': inverter.name, "selectable": False, "showCheckbox": False, "nodes": inverters_nodes})
                data_point = {}
                data_point["text"] = str(inverter.name)
                data_point["selectable"] = False
                nodes = []
                for node in inverter.fields.filter(isActive=True):
                    nodes.append({'text': str(node.name),
                                  'source_key': str(inverter.sourceKey)})
                data_point['nodes'] = nodes
                inverters_nodes.append(data_point)
            final_nodes.append({'text': "Inverters", "selectable": False, "nodes": inverters_nodes})

            context = self.get_context_data()
            context['options'] = json.dumps(final_nodes)
            return self.render_to_response(context=context)
        except KeyError:
            return HttpResponseBadRequest("Plant slug or inverter key not mentioned")
        except SolarPlant.DoesNotExist:
            return HttpResponseBadRequest("Invalid plant slug")
        except Exception as exc:
            logger.debug(exc)
            raise Http404

    def get_context_data(self, **kwargs):
        try:
            context = super(InvertersAjbsSecondViewView, self).get_context_data(**kwargs)
            try:
                plant_meta = PlantMetaSource.objects.get(plant=self.plant)
            except PlantMetaSource.DoesNotExist:
                plant_meta = None
            context['plant_slug'] = self.plant_slug
            context['plant'] = self.plant
            context['plant_meta'] = plant_meta
            profile_data = self.get_profile_data()
            for key in profile_data.keys():
                context[key] = profile_data[key]
            solar_plants = filter_solar_plants(context)
            assert (self.plant in solar_plants)
            # Get the number of tickets assigned.
            tickets = Ticket.objects.filter(assigned_to=self.request.user, status=1)
            tickets = len(tickets)
            context['tickets'] = tickets
            return context
        except Exception as exc:
            logger.debug(exc)
            raise Http404


class AddPlantOptionsViewView(ProfileDataMixin, TemplateView):
    template_name = "solarmonitoring/add_plant_options.html"

    def get(self, request, *args, **kwargs):
        try:
            plant_slug = self.kwargs.get('plant_slug')
            plant = SolarPlant.objects.get(slug=plant_slug)
            self.plant_slug = plant_slug
            self.plant = plant
            final_nodes = []
            inverters_nodes = []
            if hasattr(plant, 'metadata'):
                nodes = []
                for node in plant.metadata.fields.filter(isActive=True):
                    nodes.append({'text': str(node.name),
                                  'source_key': str(plant.metadata.sourceKey)})
                final_nodes.append({'text': "Plant Level Information", "selectable": False, "nodes": nodes})

            if plant.slug == 'rrkabel':
                inverters_unordered = plant.independent_inverter_units.all().order_by('name')
                inverters = sorted(inverters_unordered, key=inverter_order)
            else:
                inverters = plant.independent_inverter_units.all().order_by('id')

            for inverter in inverters:
                inverters_nodes = []
                if len(inverter.ajb_units.all()) > 0:
                    for ajb in inverter.ajb_units.all().order_by('id'):
                        data_point = {}
                        data_point["text"] = str(ajb.name)
                        data_point["selectable"] = False
                        data_point["showCheckbox"] = True
                        nodes = []
                        for node in ajb.fields.filter(isActive=True).order_by('id'):
                            if "S" in node.name or "VOLTAGE" in node.name:
                                nodes.append({'text': str(node.name),
                                              'showCheckbox': True,
                                              'source_key': str(ajb.sourceKey)})
                        data_point['nodes'] = nodes
                        inverters_nodes.append(data_point)
                    final_nodes.append(
                        {'text': inverter.name, "selectable": False, "showCheckbox": False, "nodes": inverters_nodes})
                data_point = {}
                data_point["text"] = str(inverter.name)
                data_point["selectable"] = False
                nodes = []
                for node in inverter.fields.filter(isActive=True):
                    nodes.append({'text': str(node.name),
                                  'source_key': str(inverter.sourceKey)})
                data_point['nodes'] = nodes
                inverters_nodes.append(data_point)
            final_nodes.append({'text': "Inverters", "selectable": False, "nodes": inverters_nodes})

            context = self.get_context_data()
            context['options'] = json.dumps(final_nodes)
            return self.render_to_response(context=context)
        except KeyError:
            return HttpResponseBadRequest("Plant slug or inverter key not mentioned")
        except SolarPlant.DoesNotExist:
            return HttpResponseBadRequest("Invalid plant slug")
        except Exception as exc:
            logger.debug(exc)
            raise Http404

    def get_context_data(self, **kwargs):
        try:
            context = super(AddPlantOptionsViewView, self).get_context_data(**kwargs)
            try:
                plant_meta = PlantMetaSource.objects.get(plant=self.plant)
            except PlantMetaSource.DoesNotExist:
                plant_meta = None
            context['plant_slug'] = self.plant_slug
            context['plant'] = self.plant
            context['plant_meta'] = plant_meta
            profile_data = self.get_profile_data()
            for key in profile_data.keys():
                context[key] = profile_data[key]
            solar_plants = filter_solar_plants(context)
            assert (self.plant in solar_plants)
            # Get the number of tickets assigned.
            tickets = Ticket.objects.filter(assigned_to=self.request.user, status=1)
            tickets = len(tickets)
            context['tickets'] = tickets
            return context
        except Exception as exc:
            logger.debug(exc)
            raise Http404


class PlantPreferencesViewView(ProfileDataMixin, TemplateView):
    template_name = "solarmonitoring/plant_preferences.html"

    def get(self, request, *args, **kwargs):
        try:
            plant_slug = self.kwargs.get('plant_slug')
            plant = SolarPlant.objects.get(slug=plant_slug)
            self.plant_slug = plant_slug
            self.plant = plant
            final_nodes = []
            inverters_nodes = []
            if hasattr(plant, 'metadata'):
                nodes = []
                for node in plant.metadata.fields.filter(isActive=True):
                    nodes.append({'text': str(node.name),
                                  'source_key': str(plant.metadata.sourceKey)})
                final_nodes.append({'text': "Plant Level Information", "selectable": False, "nodes": nodes})

            if plant.slug == 'rrkabel':
                inverters_unordered = plant.independent_inverter_units.all().order_by('name')
                inverters = sorted(inverters_unordered, key=inverter_order)
            else:
                inverters = plant.independent_inverter_units.all().order_by('id')

            for inverter in inverters:
                inverters_nodes = []
                if len(inverter.ajb_units.all()) > 0:
                    for ajb in inverter.ajb_units.all().order_by('id'):
                        data_point = {}
                        data_point["text"] = str(ajb.name)
                        data_point["selectable"] = False
                        data_point["showCheckbox"] = True
                        nodes = []
                        for node in ajb.fields.filter(isActive=True).order_by('id'):
                            if "S" in node.name or "VOLTAGE" in node.name:
                                nodes.append({'text': str(node.name),
                                              'showCheckbox': True,
                                              'source_key': str(ajb.sourceKey)})
                        data_point['nodes'] = nodes
                        inverters_nodes.append(data_point)
                    final_nodes.append(
                        {'text': inverter.name, "selectable": False, "showCheckbox": False, "nodes": inverters_nodes})
                data_point = {}
                data_point["text"] = str(inverter.name)
                data_point["selectable"] = False
                nodes = []
                for node in inverter.fields.filter(isActive=True):
                    nodes.append({'text': str(node.name),
                                  'source_key': str(inverter.sourceKey)})
                data_point['nodes'] = nodes
                inverters_nodes.append(data_point)
            final_nodes.append({'text': "Inverters", "selectable": False, "nodes": inverters_nodes})

            context = self.get_context_data()
            context['options'] = json.dumps(final_nodes)
            return self.render_to_response(context=context)
        except KeyError:
            return HttpResponseBadRequest("Plant slug or inverter key not mentioned")
        except SolarPlant.DoesNotExist:
            return HttpResponseBadRequest("Invalid plant slug")
        except Exception as exc:
            logger.debug(exc)
            raise Http404

    def get_context_data(self, **kwargs):
        try:
            context = super(PlantPreferencesViewView, self).get_context_data(**kwargs)
            try:
                plant_meta = PlantMetaSource.objects.get(plant=self.plant)
            except PlantMetaSource.DoesNotExist:
                plant_meta = None
            context['plant_slug'] = self.plant_slug
            context['plant'] = self.plant
            context['plant_meta'] = plant_meta
            profile_data = self.get_profile_data()
            for key in profile_data.keys():
                context[key] = profile_data[key]
            solar_plants = filter_solar_plants(context)
            assert (self.plant in solar_plants)
            # Get the number of tickets assigned.
            tickets = Ticket.objects.filter(assigned_to=self.request.user, status=1)
            tickets = len(tickets)
            context['tickets'] = tickets
            return context
        except Exception as exc:
            logger.debug(exc)
            raise Http404

class PDFReportSummary1(ProfileDataMixin, TemplateView):
    template_name = "solarmonitoring/pdf_report.html"

    def get(self, request, *args, **kwargs):
        try:
            plant_slug = self.kwargs.get('plant_slug')
            self.plant = SolarPlant.objects.get(slug=plant_slug)
            self.plant_slug = self.plant.slug
            st = request.GET.get('st', '')
            context_data = self.get_pdf_content(st)
            return self.render_to_response(context=context_data)
        except KeyError:
            return HttpResponseBadRequest("Plant slug or inverter key not mentioned")
        except SolarPlant.DoesNotExist:
            return HttpResponseBadRequest("Invalid plant slug")
        except Exception as exc:
            logger.debug(exc)
            raise Http404

    def get_pdf_content(self, st, plant=None):
        if plant:
            self.plant = plant
            self.plant_slug = plant.slug
        datetime_dict = dict()
        datetime_dict['st'] = st
        pdf_report_save_folder = 'pdf_report/'
        if not os.path.exists(pdf_report_save_folder):
            os.makedirs(pdf_report_save_folder, 0777)
        self.file_name = "%s/%s-%s.pdf" % (pdf_report_save_folder, self.plant_slug, datetime_dict['st'])
        datetime_parameter = st.split("-")
        self.report_type = None
        try:
            if len(datetime_parameter) == 3:
                datetime_dict['st_day'], datetime_dict['st_month'], datetime_dict['st_year'] = datetime_parameter
                _, last_day_of_month = calendar.monthrange(int(datetime_dict['st_year']),
                                                           int(datetime_dict['st_month']))
                datetime_dict['st'] = datetime.datetime.strptime(datetime_dict['st'], "%d-%m-%Y")
                datetime_dict['et'] = datetime_dict['st'] + datetime.timedelta(days=1)
                datetime_dict['dmy_st'] = datetime.datetime.strptime(
                    "01-%s-%s" % (datetime_dict['st_month'], datetime_dict['st_year']), "%d-%m-%Y")
                datetime_dict['dmy_et'] = datetime_dict['dmy_st'] + datetime.timedelta(last_day_of_month)
                self.report_type = 'daily'
            if len(datetime_parameter) == 2:
                datetime_dict['st_day'] = "01"
                datetime_dict['st_month'], datetime_dict['st_year'] = datetime_parameter
                _, last_day_of_month = calendar.monthrange(int(datetime_dict['st_year']),
                                                           int(datetime_dict['st_month']))
                datetime_dict['st'] = "01-%s-%s" % (datetime_dict['st_month'], datetime_dict['st_year'])
                datetime_dict['st'] = datetime.datetime.strptime(datetime_dict['st'], "%d-%m-%Y")
                datetime_dict['et'] = datetime_dict['st'] + datetime.timedelta(last_day_of_month)
                datetime_dict['dmy_st'] = datetime_dict['st']
                datetime_dict['dmy_et'] = datetime_dict['et']
                self.report_type = 'monthly'
            datetime_dict['my_st'] = datetime.datetime.strptime("01-01-%s" % (datetime_dict['st_year']), "%d-%m-%Y")
            datetime_dict['my_et'] = datetime_dict['my_st'] + datetime.timedelta(days=365)
            try:
                tz = pytz.timezone(self.plant.metadata.plantmetasource.dataTimezone)
                datetime_dict['st'] = tz.localize(datetime_dict['st'])
                datetime_dict['st'] = datetime_dict['st'].astimezone(tz)
                datetime_dict['et'] = tz.localize(datetime_dict['et'])
                datetime_dict['et'] = datetime_dict['et'].astimezone(tz)
                datetime_dict['my_st'] = tz.localize(datetime_dict['my_st'])
                datetime_dict['my_st'] = datetime_dict['my_st'].astimezone(tz)
                datetime_dict['my_et'] = tz.localize(datetime_dict['my_et'])
                datetime_dict['my_et'] = datetime_dict['my_et'].astimezone(tz)
                datetime_dict['dmy_st'] = tz.localize(datetime_dict['dmy_st'])
                datetime_dict['dmy_st'] = datetime_dict['dmy_st'].astimezone(tz)
                datetime_dict['dmy_et'] = tz.localize(datetime_dict['dmy_et'])
                datetime_dict['dmy_et'] = datetime_dict['dmy_et'].astimezone(tz)
            except:
                tz = pytz.timezone("UTC")
        except Exception as exception:
            logger.debug("invalid input %s", exception)
            return {}

        self.tz = tz
        self.st = datetime_dict['st']
        self.et = datetime_dict['et']
        self.my_st = datetime_dict['my_st']
        self.my_et = datetime_dict['my_et']
        self.dmy_st = datetime_dict['dmy_st']
        self.dmy_et = datetime_dict['dmy_et']
        self.st_day = datetime_dict['st_day']
        self.st_month = datetime_dict['st_month']
        self.st_year = datetime_dict['st_year']
        context_data = dict()
        context_data['splant_latitude'] = self.plant.latitude
        context_data['splant_longitude'] = self.plant.longitude
        context_data['splant_group_client_logo'] = self.plant.dataglengroup.groupLogo \
            if self.plant.dataglengroup.groupLogo else self.plant.groupClient.clientLogo
        # fetch file extension and conver it to base64
        image_file_extension = context_data['splant_group_client_logo'].split(".")[-1]
        response = requests.get(context_data['splant_group_client_logo'])
        context_data['splant_group_client_logo'] = " data:image/%s;base64,%s" % (
            image_file_extension, base64.b64encode(response.content))
        context_data['splant_name'] = self.plant.name
        context_data['splant_location'] = self.plant.location
        context_data['splant_capacity'] = self.plant.capacity
        context_data['splant_elevation'] = self.plant.elevation
        context_data['report_type'] = self.report_type
        context_data['splant_client_name'] = self.plant.groupClient.name
        context_data['splant_client_address'] = str("Address Here")
        context_data['splant_client_phoneno'] = str("phone no")
        context_data['splant_client_contact_address'] = self.plant.groupClient.clientContactAddress
        context_data['start_date'] = datetime.datetime.strftime(self.st, "%d-%m-%Y")
        context_data['end_date'] = self.et - datetime.timedelta(days=1)
        context_data['end_date'] = datetime.datetime.strftime(context_data['end_date'], "%d-%m-%Y")
        context_data['splant_data'] = self.get_plant_summary_date_wise()
        context_data['inverter_data'] = self.get_plant_inverters()
        context_data['plant_meta_data'] = self.get_plant_meta_data()
        context_data['base64_for_icons'] = PDFReportSummary.get_base64_for_icons_images()
        try:
            context_data['till_date_generation'] = calculate_total_plant_generation(self.plant)
            context_data['till_date_generation'] = round(context_data['till_date_generation'], 2)
        except Exception as exce:
            context_data['till_date_generation'] = 0.0
            logger.debug("%s", exce)
        context_data['monthly_generation'], context_data['yearly_generation'] = self.get_plant_summary_month_year_wise()
        context_data['month_co2_saving'] = fix_co2_savings(float(context_data['monthly_generation']) * 0.7) if \
        context_data[
            'monthly_generation'] else 0.0
        context_data['power_irradiation'] = self.get_plant_power_irradiation()
        context_data['daily_monthly_generation'] = self.get_daily_montly_generation_and_insolation()
        # convert to units
        context_data['monthly_generation'] = fix_generation_units(float(context_data['monthly_generation']))
        context_data['yearly_generation'] = fix_generation_units(float(context_data['yearly_generation']))
        context_data['till_date_generation'] = fix_generation_units(float(context_data['till_date_generation']))
        if self.report_type == "monthly":
            context_data['ac_dc_conversion_monthly'], context_data[
                'availability_monthly'] = self.get_ac_dc_conversion_monthly_availability()
            context_data['cuf_monthly_data'] = self.get_month_cuf()
        render_template('solarmonitoring/pdf_report.html', context_data, output=self.file_name, width="11in",
                        height="17in",
                        format="pdf", waitfor="#jscompleted", wait="25000")
        if plant:
            return self.file_name
        return context_data

    def get_plant_summary_date_wise(self):
        try:
            plant_values = {}
            plant_values['generation'] = 0.0
            plant_values['performance_ratio'] = 0.0
            plant_values['cuf'] = 0.0
            plant_values['specific_yield'] = 0.0
            plant_values['dc_loss'] = 0.0
            plant_values['conversion_loss'] = 0.0
            plant_values['ac_loss'] = 0.0
            plant_values['grid_availability'] = 0.0
            plant_values['equipment_availability'] = 0.0
            plant_values['insolation'] = 0.0
            plant_values['plant_money_saving'] = 0.0
            count_time_period = settings.DATA_COUNT_PERIODS.DAILY
            if str(self.report_type) == "monthly":
                count_time_period = settings.DATA_COUNT_PERIODS.MONTH
            plant_summary_values = PlantSummaryDetails.objects.filter(timestamp_type='BASED_ON_REQUEST_ARRIVAL',
                                                                      count_time_period=count_time_period,
                                                                      identifier=self.plant_slug,
                                                                      ts__gte=self.st, ts__lt=self.et)
            if plant_summary_values:
                value = plant_summary_values[0]
                plant_values['generation'] = value.generation
                plant_values['plant_co2'] = fix_co2_savings(
                    float(plant_values['generation']) * 0.7) if value.generation else 0.0
                plant_values['generation'] = fix_generation_units(
                    plant_values['generation']) if value.generation else 0.0
                plant_values['performance_ratio'] = "{0:.2f}".format(
                    float(value.performance_ratio) * 100) if value.performance_ratio else 0.0
                plant_values['cuf'] = "{0:.2f}".format(float(value.cuf) * 100) if value.cuf else 0.0
                plant_values['specific_yield'] = "{0:.2f}".format(
                    float(value.specific_yield)) if value.specific_yield else 0.0
                plant_values['dc_loss'] = fix_generation_units(float(value.dc_loss)) if value.dc_loss else None
                plant_values['conversion_loss'] = fix_generation_units(
                    value.conversion_loss) if value.conversion_loss else None
                plant_values['ac_loss'] = fix_generation_units(value.ac_loss) if value.ac_loss else None
                plant_values['grid_availability'] = "{0:.2f}".format(
                    float(value.grid_availability)) if value.grid_availability else 100.0
                plant_values['equipment_availability'] = "{0:.2f}".format(
                    float(value.equipment_availability)) if value.equipment_availability else 100.0
                plant_values['insolation'] = "{0:.2f}".format(
                    float(value.average_irradiation)) if value.average_irradiation else 0.0
                plant_values['plant_money_saving'] = "{0:.2f}".format(
                    float(value.generation) * 3) if value.generation else 0.0
        except Exception as exception:
            logger.debug("%s", exception)
        return plant_values

    def get_plant_summary_month_year_wise(self):
        month_generation = 0.0
        year_generation = 0.0
        try:
            plant_summary_values = PlantSummaryDetails.objects.filter(timestamp_type='BASED_ON_REQUEST_ARRIVAL',
                                                                      count_time_period=2419200,
                                                                      identifier=self.plant_slug,
                                                                      ts__gte=self.my_st,
                                                                      ts__lt=self.my_et).order_by('ts')
            previous_month = int(self.st_month) - 1
            if previous_month == 0:
                previous_month = 12
            for psv in plant_summary_values:
                if int(psv.ts.strftime("%m")) == previous_month:
                    month_generation = psv.generation
                year_generation += psv.generation
        except Exception as exce:
            month_generation = 0.0
            year_generation = 0.0
            logger.debug("%s", exce)
        month_generation = "{0:.2f}".format(float(month_generation)) if month_generation > 0 else 0.0
        year_generation = "{0:.2f}".format(float(year_generation)) if year_generation > 0 else 0.0
        return month_generation, year_generation

    def get_plant_meta_data(self):
        plant_meta_data = dict()
        plant_meta_data['panel_technology'] = "%s" % self.plant.metadata.plantmetasource.panel_technology
        plant_meta_data['panel_capacity'] = float(self.plant.metadata.plantmetasource.panel_capacity)
        plant_meta_data['no_of_panels'] = "%s" % self.plant.metadata.plantmetasource.no_of_panels
        return plant_meta_data

    def get_plant_inverters(self):
        all_inverters = IndependentInverter.objects.filter(plant=self.plant)
        inverter_data = {'manufacturer': '', 'model': '', 'total_capacity': 0.0, 'actual_capacity': 0.0}
        for inv_data in all_inverters:
            inverter_data['manufacturer'] = inv_data.manufacturer
            inverter_data['model'] = inv_data.model
        inverter_data["total_capacity"] = self.plant.capacity
        return inverter_data

    def get_plant_power_irradiation(self):
        power_irradation = get_power_irradiation(self.st, self.et, self.plant)
        return power_irradation

    def get_daily_montly_generation_and_insolation(self):
        count_time_period = settings.DATA_COUNT_PERIODS.DAILY
        plant_summary_values_details = []
        try:
            plant_summary_values = PlantSummaryDetails.objects.filter(timestamp_type='BASED_ON_REQUEST_ARRIVAL',
                                                                      count_time_period=count_time_period,
                                                                      identifier=self.plant_slug,
                                                                      ts__gte=self.dmy_st,
                                                                      ts__lt=self.dmy_et).order_by('ts')
            for psv in plant_summary_values:
                plant_summary_values_data = dict()
                try:
                    timestamp_data = pytz.utc.localize(psv.ts)
                    timestamp_data = timestamp_data.astimezone(self.tz)
                except Exception as exception:
                    logger.debug(str(exception))
                plant_summary_values_data['timestamp'] = datetime.datetime.strftime(timestamp_data,
                                                                                    "%Y-%m-%dT%H:%M:%SZ")
                plant_summary_values_data['generation'] = float(psv.generation) if psv.generation else 0.0
                plant_summary_values_data['insolation'] = float(
                    psv.average_irradiation) if psv.average_irradiation else 0.0
                plant_summary_values_details.append(plant_summary_values_data)
        except Exception as exce:
            logger.debug("%s", exce)
        return json.dumps(plant_summary_values_details)

    def get_month_cuf(self):
        count_time_period = settings.DATA_COUNT_PERIODS.DAILY
        cuf_data_all = []
        try:
            cuf_data = CUFTable.objects.filter(timestamp_type=settings.TIMESTAMP_TYPES.BASED_ON_REQUEST_ARRIVAL,
                                               count_time_period=count_time_period,
                                               identifier=self.plant.metadata.plantmetasource.sourceKey,
                                               ts__gte=self.st,
                                               ts__lt=self.et).values_list('CUF', 'ts').order_by('ts')
            for cd in cuf_data:
                cufd = dict()
                cufd['cuf'] = float(cd[0])
                timestamp_data = cd[1]
                try:
                    timestamp_data = pytz.utc.localize(timestamp_data)
                    timestamp_data = timestamp_data.astimezone(self.tz)
                except Exception as exception:
                    logger.debug(str(exception))
                cufd['timestamp'] = datetime.datetime.strftime(timestamp_data, "%Y-%m-%dT%H:%M:%SZ")
                cuf_data_all.append(cufd)
        except Exception as exce:
            logger.debug(str(exce))
        return json.dumps(cuf_data_all)

    def get_ac_dc_conversion_monthly_availability(self):
        count_time_period = settings.DATA_COUNT_PERIODS.DAILY
        data_ac_dc_conversion = list()
        data_plant_availability = list()
        try:
            plant_summary_values = PlantSummaryDetails.objects.filter(timestamp_type='BASED_ON_REQUEST_ARRIVAL',
                                                                      count_time_period=count_time_period,
                                                                      identifier=self.plant_slug,
                                                                      ts__gte=self.st,
                                                                      ts__lt=self.et).order_by('ts')
            for adc in plant_summary_values:
                plant_losses_data = dict()
                plant_availability = dict()
                timestamp_data = adc.ts
                try:
                    timestamp_data = pytz.utc.localize(timestamp_data)
                    timestamp_data = timestamp_data.astimezone(self.tz)
                except Exception as exception:
                    logger.debug(str(exception))
                plant_losses_data['timestamp'] = datetime.datetime.strftime(timestamp_data, "%Y-%m-%dT%H:%M:%SZ")
                plant_losses_data['dc_loss'] = float(adc.dc_loss) if adc.dc_loss else 0.0
                plant_losses_data['ac_loss'] = float(adc.ac_loss) if adc.ac_loss else 0.0
                plant_losses_data['conversion_loss'] = float(adc.conversion_loss) if adc.conversion_loss else 0.0
                plant_availability['equipment_availability'] = float(
                    adc.equipment_availability) if adc.equipment_availability else 100.0
                plant_availability['grid_availability'] = float(
                    adc.grid_availability) if adc.grid_availability else 100.0
                plant_availability['avtimestamp'] = datetime.datetime.strftime(timestamp_data, "%Y-%m-%dT%H:%M:%SZ")
                data_plant_availability.append(plant_availability)
                data_ac_dc_conversion.append(plant_losses_data)
        except Exception as exce:
            logger.debug(str(exce))
        return json.dumps(data_ac_dc_conversion), json.dumps(data_plant_availability)

    @staticmethod
    def get_base64_for_icons_images():
        image_base64_data = dict()
        try:
            with open("solarrms/icons/plantalarm.png", "rb") as image_file:
                image_base64_data["plantalarm"] = " data:image/png;base64,%s" % base64.b64encode(image_file.read())
            with open("solarrms/icons/plantco2saving.png", "rb") as image_file:
                image_base64_data["plantco2saving"] = " data:image/png;base64,%s" % base64.b64encode(image_file.read())
            with open("solarrms/icons/plantgeneration.png", "rb") as image_file:
                image_base64_data["plantgeneration"] = " data:image/png;base64,%s" % base64.b64encode(image_file.read())
            with open("solarrms/icons/plantgridavailibility.png", "rb") as image_file:
                image_base64_data["plantgridavailibility"] = " data:image/png;base64,%s" % base64.b64encode(
                    image_file.read())
            with open("solarrms/icons/plantinverter.png", "rb") as image_file:
                image_base64_data["plantinverter"] = " data:image/png;base64,%s" % base64.b64encode(image_file.read())
            with open("solarrms/icons/plantlosses.png", "rb") as image_file:
                image_base64_data["plantlosses"] = " data:image/png;base64,%s" % base64.b64encode(image_file.read())
            with open("solarrms/icons/plantsaving.png", "rb") as image_file:
                image_base64_data["plantsaving"] = " data:image/png;base64,%s" % base64.b64encode(image_file.read())
            with open("solarrms/icons/plantpannel.png", "rb") as image_file:
                image_base64_data["plantpannel"] = " data:image/png;base64,%s" % base64.b64encode(image_file.read())
            with open("solarrms/icons/bannersolar.png", "rb") as image_file:
                image_base64_data["bannersolar"] = " data:image/png;base64,%s" % base64.b64encode(image_file.read())
        except Exception as exc:
            logger.debug("get_base64 for_icons_images %s" % exc)
        return image_base64_data


from solarrms.solar_reports import gen_daily_report_cleanmax
from django.core.exceptions import ObjectDoesNotExist
from rest_framework import status, viewsets, authentication, permissions

class PDFReportSummary_OldFunctioning(ProfileDataMixin, TemplateView):
    template_name = "solarmonitoring/pdf_cleanmax_daily.html"
    authentication_classes = (authentication.TokenAuthentication, authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)
    def get(self, request, plant_slug=None, **kwargs):
        logger.debug("inside geeeeeeeeeeeet request")
        try:
            context = self.get_profile_data(**kwargs)
            plants = filter_solar_plants(context)
            try:
                user_role = self.request.user.role.role
                user_client = self.request.user.role.dg_client
                if str(user_role) == 'CEO':
                    plants = SolarPlant.objects.filter(groupClient=user_client)
            except Exception as exception:
                logger.debug(str(exception))
                plants = filter_solar_plants(context)
            logger.debug(plants)
            try:
                plant = None
                for plant_instance in plants:
                    if plant_instance.slug == plant_slug:
                        plant = plant_instance
                if plant is None:
                    logger.debug("##############################No Plant found########################")
                    return HttpResponseBadRequest("Invalid plant slug")
            except ObjectDoesNotExist:
                return HttpResponseBadRequest("Invalid plant slug")
            except:
                return HttpResponseBadRequest("Internal Server Error")

            self.plant = SolarPlant.objects.get(slug=plant_slug)
            self.plant_slug = self.plant.slug
            st = request.GET.get('st', '')
            context_data = self.get_pdf_content(st)
            return self.render_to_response(context=context_data)
        except KeyError:
            return HttpResponseBadRequest("Plant slug or inverter key not mentioned")
        except SolarPlant.DoesNotExist:
            return HttpResponseBadRequest("Invalid plant slug")
        except Exception as exc:
            logger.debug(exc)
            raise Http404

    def get_pdf_content(self, st, plant=None):
        logger.debug("=-=-=-in get_pdf_content in views.py-=-=-=-=")
        if plant:
            self.plant = plant
            self.plant_slug = plant.slug
        logger.debug("======plant is ===="+self.plant_slug)
        datetime_dict = dict()
        datetime_dict['st'] = st
        pdf_report_save_folder = '/var/tmp/monthly_report/PDF_CleanMax_Daily/'
        if not os.path.exists(pdf_report_save_folder):
            os.makedirs(pdf_report_save_folder, 0777)
        self.file_name = "%s/%s-%s-%s.pdf" % (pdf_report_save_folder,(self.plant.groupClient.name).replace(' ','-')+"-Daily-Report-For", self.plant_slug, datetime_dict['st'])
        datetime_parameter = st.split("-")
        self.report_type = None
        try:
            if len(datetime_parameter) == 3:
                self.report_type = 'daily'
                logger.debug("3 datetime parameters")
                try:
                    datetime_dict['st'] = datetime.datetime.strptime(datetime_dict['st'], "%d-%m-%Y")
                    tz = pytz.timezone(self.plant.metadata.plantmetasource.dataTimezone)
                    datetime_dict['st'] = tz.localize(datetime_dict['st'])
                    logger.debug("Date received as :")
                    logger.debug(datetime_dict['st'])
                except:
                    logger.debug("Time exception")
                    tz = pytz.timezone("UTC")
        except Exception as exception:
            logger.debug("invalid input %s", exception)
            return {}

        self.tz = tz
        self.st = datetime_dict['st']
        #import pdb;pdb.set_trace()
        context_data = gen_daily_report_cleanmax(self.plant,datetime_dict['st'])
        # logger.debug("views.py got the context "+str(context_data))
        #import pdb;pdb.set_trace()
        try:
            render_template('solarmonitoring/pdf_cleanmax_daily.html', context_data, output=self.file_name, width="9.27in", height="11.69in",
                        format="pdf", waitfor="#jscompleted", wait="25000")
        except Exception as e:
            logger.debug("Exception in render_template in views.py")
        if plant:
            return self.file_name
        return context_data


class GenerateElectricityBill(ProfileDataMixin, TemplateView):
    template_name = "solarmonitoring/bill.html"
    authentication_classes = (authentication.TokenAuthentication, authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)


    def get(self, request, plant_slug=None, **kwargs):
        try:
            context = self.get_profile_data(**kwargs)
            plants = filter_solar_plants(context)
            try:
                user_role = self.request.user.role.role
                user_client = self.request.user.role.dg_client
                if str(user_role) == 'CEO':
                    plants = SolarPlant.objects.filter(groupClient=user_client)
            except Exception as exception:
                logger.debug(str(exception))
                plants = filter_solar_plants(context)
            logger.debug(plants)
            try:
                plant = None
                for plant_instance in plants:
                    if plant_instance.slug == plant_slug:
                        plant = plant_instance
                if plant is None:
                    return HttpResponseBadRequest("Invalid plant slug")
            except ObjectDoesNotExist:
                return HttpResponseBadRequest("Invalid plant slug")
            except:
                return HttpResponseBadRequest("Internal Server Error")

            self.plant = SolarPlant.objects.get(slug=plant_slug)
            self.plant_slug = self.plant.slug
            st = request.GET.get('st', '')
            et = request.GET.get('et', '')
            logger.debug("going to get context........")
            get_request=True
            context_data = self.get_pdf_content(st,et,self.plant,get_request)
            return self.render_to_response(context=context_data)
        except KeyError:
            return HttpResponseBadRequest("Plant slug or inverter key not mentioned")
        except SolarPlant.DoesNotExist:
            return HttpResponseBadRequest("Invalid plant slug")
        except Exception as exc:
            logger.debug(exc)
            raise Http404

    def get_billing_units(self, starttime, endtime, plant):
        try:
            context = {}
            # below fields might be wrong. They should be filled with energy offtaker details
            context['payer_name'] = plant.name
            context['payer_address'] = plant.location
            context['client_short_name'] = plant.groupClient.name
            try:
                context['logo'] = plant.dataglengroup.groupLogo \
                    if plant.dataglengroup.groupLogo else plant.groupClient.clientLogo
                # fetch file extension and conver it to base64
                image_file_extension = context['logo'].split(".")[-1]
                response = requests.get(context['logo'])
                context['logo'] = " data:image/%s;base64,%s" % (
                    image_file_extension, base64.b64encode(response.content))
            except:
                context['logo'] = ""
            try:
                context['clint_GST'] = plant.groupClient.billing_entity.tax_details_primary
            except Exception as e:
                context['clint_GST'] = "N/A"
            context['plant_capacity'] = plant.capacity
            today = datetime.datetime.now()

            context['bill_date'] = today.strftime("%d-%B-%Y")
            start_date = starttime.strftime("%d-%B-%Y")
            end_date = endtime.strftime("%d-%B-%Y")
            context['bill_supplies'] = "%s to %s" % (start_date,end_date)
            return context
        except Exception as e:
            logger.debug(e)
            return context

    def get_pdf_content(self, st, et, plant, get_request=None):
        try:
            client = plant.groupClient
            # starttime = datetime.datetime(2018, 4, 1, 0, 0)
            # endtime = datetime.datetime(2018, 4, 30, 0, 0)
            try:
                st = parser.parse(st)
                et = parser.parse(et)
                st = st.replace(hour=0,minute=0,microsecond=0)
                et = et.replace(hour=23,minute=59,microsecond=0)
                starttime = update_tz(st, plant.metadata.plantmetasource.dataTimezone)
                endtime = update_tz(et, plant.metadata.plantmetasource.dataTimezone)
            except:
                logger.debug("exception in time in energy bill")
                return HttpResponseBadRequest("Wrong starttime endtime specified")

            context = self.get_billing_units(starttime, endtime, plant)

            energy_meters = plant.energy_meters.all()
            meter_readings_multiple_meter_for_single_plant = []
            if not energy_meters:
                return HttpResponseBadRequest("No Energy Meters Found. Can not Generate Energy Bill.")

            for meter in energy_meters:
                meter_readings = ValidDataStorageByStream.objects.filter(source_key=meter.sourceKey,
                                                                         stream_name='Wh_RECEIVED',
                                                                         timestamp_in_data__gte=starttime,
                                                                         timestamp_in_data__lte=endtime)
                meter_readings[0]
                new_reading = int(float(meter_readings[0]['stream_value']))
                old_reading = int(float(meter_readings[-1]['stream_value']))
                meter_readings_multiple_meter_for_single_plant.append(new_reading - old_reading)

            billed_units = sum(meter_readings_multiple_meter_for_single_plant)
            context['current_reading'] = new_reading
            context['previous_reading'] = old_reading
            context['billed_units'] = billed_units
            try:
                contract = EnergyContract.objects.get(plant=plant, start_date__lte=starttime.date(), end_date__gte=endtime.date())
            except:
                return HttpResponseBadRequest("No energy Contract found. Can not Generate Bill")

            context['tarrif_per_unit'] = contract.ppa_price
            context['currency'] = contract.currency
            context['solar_charges'] = billed_units * contract.ppa_price
            due_date = datetime.datetime.now().replace(day=25)
            context['due_date'] = due_date.strftime("%d-%B-%Y")
            early_date = due_date.replace(day=20)
            context['early_date'] = early_date.strftime("%d-%B-%Y")
            context['early_discount'] = contract.early_payment_discount_factor
            context['early_discount_factor'] = (100.0 - context['early_discount'])/100.0

            context['early_discount_ammount'] = context['solar_charges'] * context['early_discount_factor']
            context['benefit'] = context['solar_charges'] - context['early_discount_ammount']

            context['late_payment_penalty'] = contract.late_payment_penalty_clause

            try:
                bank_account = client.billing_entity.accounts.all()[0]
                bank_details = ("Bank : %s" % bank_account.account_bank) + \
                               (" Beneficiary Name: %s" % bank_account.beneficiary_name) + \
                               (" Account Number: %s" % bank_account.account_number) + \
                               (" IFSC Code: %s" % bank_account.account_ifsc_code) + \
                               (" Bank Address: %s" % bank_account.bank_address) + \
                               (" MICR Code : %s" % bank_account.account_micr_code) + \
                               (" Branch Code : %s" % bank_account.account_branch_code)

                context['client_bank_details'] = bank_details
            except Exception as e:
                bank_details = "N/A"
                context['client_bank_details'] = bank_details

            if get_request:
                return context
            file_name = '/var/tmp/monthly_report/bill_pdf/bill.pdf'
            try:
                render_template('solarmonitoring/bill.html', context, output=file_name,
                                width="9.27in", height="11.69in",
                                format="pdf", waitfor="#jscompleted", wait="25000")
            except Exception as e:
                logger.debug("Exception in energy bill / render_template in views.py")

            return file_name

        except Exception as exc:
            logger.debug(exc)
            return Response("INTERNAL_SERVER_ERROR == %s" % exc, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# trial.dataglen.com/solar/plant/omya/dyna_pdf/?st=2018-04-15
from features.models import RoleAccess
# Whenever you add new feature please add in following two dicts
feature_dynamic_pdf_ids_feature_ids = [1618, 1612, 1608, 1616, 1644, 1630]
feature_dynamic_pdf_ids_mapping = {'GEN_VS_IRR_BAR_GRAPH_30_DAYS':'POWER_CHART_GENERATION',
                                   'PLANT_PROD_STMT_ONE_DAY':'TOTAL_ENERGY_GENERATION',
                                   'SUMMARY_OF_PLANT_PROD_INVERTER':'INVERTER_ENERGY_GENERATION',
                                   'SUMMARY_OF_PLANT_PROD_ENERGY_METER':'METER_POWER_GENERATION',
                                   'SUMMARY_OF_PLANT_PR':'PR_METRICS',
                                   'PLANT_DESCRIPTION':'TOTAL_CAPACITY_PLANT_DETAILS'}

from features.models import CustomReportFormat
from django.http import StreamingHttpResponse


class PDFReportSummary(ProfileDataMixin, TemplateView):
    template_name = "solarmonitoring/pdf_report_daily_dynamic.html"
    # authentication_classes = (authentication.TokenAuthentication, authentication.SessionAuthentication,)
    # permission_classes = (permissions.IsAuthenticated,)

    def get(self, request, plant_slug=None, **kwargs):
        try:
            context = self.get_profile_data(**kwargs)
            plants = filter_solar_plants(context)
            try:
                user_role = self.request.user.role.role
                user_client = self.request.user.role.dg_client
                if str(user_role) == 'CEO':
                    plants = SolarPlant.objects.filter(groupClient=user_client)
            except Exception as exception:
                logger.debug(str(exception))
                plants = filter_solar_plants(context)
            logger.debug(plants)
            try:
                plant = None
                for plant_instance in plants:
                    if plant_instance.slug == plant_slug:
                        plant = plant_instance
                if plant is None:
                    return HttpResponseBadRequest("Invalid plant slug")
            except ObjectDoesNotExist:
                return HttpResponseBadRequest("Invalid plant slug")
            except:
                return HttpResponseBadRequest("Internal Server Error")

            self.plant = SolarPlant.objects.get(slug=plant_slug)
            self.plant_slug = self.plant.slug
            st = request.GET.get('st', '')
            logger.debug("going to get context........")
            get_request=True
            context_data = self.get_pdf_content(st,self.plant,self.request.user,get_request)
            return self.render_to_response(context=context_data)
        except KeyError:
            return HttpResponseBadRequest("Plant slug or inverter key not mentioned")
        except SolarPlant.DoesNotExist:
            return HttpResponseBadRequest("Invalid plant slug")
        except Exception as exc:
            logger.debug(exc)
            raise Http404

    # Find out if custom feature set exists for this user
    def get_custom_feature_set(self,user):

        custom_format_filter = CustomReportFormat.objects.filter(dg_client=user.role.dg_client, role=user.role.role, role_default=True)

        if len(custom_format_filter)>0:
            print "Default format is defined"
            custom_format = custom_format_filter[0]
        elif user.custom_report.all():
            custom_format = user.custom_report.all()[0]
        else:
            return None
        custom_features = custom_format.custom_features.all().values()
        restructured_custom_feaures_dict = {}
        for feature in custom_features:
            id = feature.pop('features_id')
            restructured_custom_feaures_dict[id] = feature
        # print restructured_custom_feaures_dict
        return restructured_custom_feaures_dict

    def get_pdf_content(self, st,plant,user,get_request=None):
        try:

            # plant_slug = self.kwargs.get('plant_slug')
            # plant = SolarPlant.objects.get(slug=plant_slug)
            # st = request.GET.get('st', '')
            if not st:
                return HttpResponseBadRequest("Date is not specified")
            try:
                st = parser.parse(st)
                starttime = update_tz(st, plant.metadata.plantmetasource.dataTimezone)
            except:
                logger.debug("something is wrong")
                return HttpResponseBadRequest("No date given")

            custom_feature_set = self.get_custom_feature_set(user)

            if not custom_feature_set:
                custom_feature_set = {}
                print "no custom formtas. shifting to defaults"
                try:
                    accessible_features = []
                    user_features_obj_list = RoleAccess.objects.get(role=user.role.role,\
                                                                    dg_client=user.role.dg_client).\
                                                                    features.all().values_list('id',flat=True)

                    if set(feature_dynamic_pdf_ids_feature_ids).issubset(set(user_features_obj_list)):
                        for item in feature_dynamic_pdf_ids_feature_ids:
                            custom_feature_set[item]={}
                        # custom_feature_set = dict(zip(feature_dynamic_pdf_ids_feature_ids,feature_dynamic_pdf_ids_feature_ids))
                    else:
                        sub_feature_set = set(feature_dynamic_pdf_ids_feature_ids).intersection(set(user_features_obj_list))
                        for item in sub_feature_set:
                            custom_feature_set[item]={}

                    logger.debug("Accessible features list when no custom formats found: " + str(custom_feature_set))
                except Exception as e:
                    accessible_features.append('PLANT_PROD_STMT_ONE_DAY')
                    logger.debug("Accessible features list after Exception : " + str(accessible_features))

            context = {}
            context = gen_daily_report_cleanmax(plant, starttime, custom_feature_set)
            if get_request:
                return context

            # If you want to see only HTML uncomment following line
            # return self.render_to_response(context=context)

            file_name = '/var/tmp/daily_pdf/Daily_PDF_Report_' + plant.slug + '_' + starttime.strftime("%d%b%Y") +'.pdf'
            try:
                render_template('solarmonitoring/pdf_report_daily_dynamic.html', context, output=file_name,
                                width="9.27in", height="13.69in",
                                format="pdf", waitfor="#jscompleted", wait="25000")
            except Exception as exception:
                logger.debug("Exception in render_template in views.py %s" % exception)
            return file_name
        except Exception as exc:
            logger.debug(exc)
            return ("Something is wrong: %s" % exc)

from solarrms.solar_reports import  gen_monthly_report_cleanmax

class PDFReportSummaryMonthly(ProfileDataMixin, TemplateView):
    template_name = "solarmonitoring/pdf_report_monthly_dynamic.html"

    def get(self, request, plant_slug=None, **kwargs):
        try:
            context = self.get_profile_data(**kwargs)
            plants = filter_solar_plants(context)
            try:
                user_role = self.request.user.role.role
                user_client = self.request.user.role.dg_client
                if str(user_role) == 'CEO':
                    plants = SolarPlant.objects.filter(groupClient=user_client)
            except Exception as exception:
                logger.debug(str(exception))
                plants = filter_solar_plants(context)
            logger.debug(plants)
            try:
                plant = None
                for plant_instance in plants:
                    if plant_instance.slug == plant_slug:
                        plant = plant_instance
                if plant is None:
                    return HttpResponseBadRequest("Invalid plant slug")
            except ObjectDoesNotExist:
                return HttpResponseBadRequest("Invalid plant slug")
            except:
                return HttpResponseBadRequest("Internal Server Error")
            self.plant = SolarPlant.objects.get(slug=plant_slug)
            self.plant_slug = self.plant.slug
            st = request.GET.get('st', '')
            logger.debug("going to get context........")
            get_request=True
            context_data = self.get_pdf_content(st,self.plant,self.request.user,get_request)
            return self.render_to_response(context=context_data)
        except KeyError:
            return HttpResponseBadRequest("Plant slug or inverter key not mentioned")
        except SolarPlant.DoesNotExist:
            return HttpResponseBadRequest("Invalid plant slug")
        except Exception as exc:
            logger.debug(exc)
            raise Http404

    def get_pdf_content(self, st,plant,user,get_request=None):
        try:

            if not st:
                return HttpResponseBadRequest("Date is not specified")
            try:
                st = parser.parse(st)
                starttime = update_tz(st, plant.metadata.plantmetasource.dataTimezone)
            except:
                logger.debug("something is wrong")
                return HttpResponseBadRequest("No date given")

            context = {}
            context = gen_monthly_report_cleanmax(plant, starttime)
            if get_request:
                return context

            file_name = '/var/tmp/monthly_report/pdfs/pdf_report_monthly_%s_%s_%s.pdf'%(plant.slug,starttime.month,starttime.year)
            try:
                render_template('solarmonitoring/pdf_report_monthly_dynamic.html', context, output=file_name,
                                width="9.27in", height="13.69in",
                                format="pdf", waitfor="#jscompleted", wait="25000")
            except Exception as exception:
                logger.debug("Exception in render_template in views.py %s" % exception)
            return file_name
        except Exception as exc:
            logger.debug(exc)
            return ("Something is wrong: %s" % exc)


class DynamicRenderingHTML(ProfileDataMixin, TemplateView):
    template_name = "solarmonitoring/pdf_report_daily_dynamic.html"

    authentication_classes = (authentication.TokenAuthentication, authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def current_datetime(self):
        now = datetime.datetime.now()
        html = "<html><body>It is now %s.</body></html>" % now
        return HttpResponse(html)

    def get(self, request, *args, **kwargs):
        try:
            html = "<html><body>In %s hour(s), it will be  %s.</body></html>"
            path = "/home/upendra/PycharmProjects/kutbill_staging/kutbill-django/solarrms/templates/solarmonitoring/dynamic_html.html"
            file = open(path, 'r')

            # return HttpResponse(file.read())
            # return self.render_to_response(context={})

        except Exception as exc:
            logger.debug(exc)
            return HttpResponseBadRequest("Something is wrong")

