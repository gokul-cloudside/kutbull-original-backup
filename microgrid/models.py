from django.db import models
from django.conf import settings
from solarrms.models import IndependentInverter, SolarField, SolarPlant
from dataglen.models import Sensor

# Create your models here.

PANELSET_STREAMS = ('ACTIVE_POWER', 'DAILY_YIELD')
LOAD_STREAMS = ('ACTIVE_POWER', 'DAILY_YIELD')
BATTERY_STREAMS = ('DC_POWER', 'ACTIVE_POWER', 'DAILY_YIELD', 'TOTAL_YIELD')
CHARGE_CONTROLLER_STREAMS = ('TEMPERATURE', 'BATT_VOLTAGE', 'BATT_CURRENT', 'DC_VOLTAGE', \
                     'DC_CURRENT', 'LOAD_CURRENT')


class ChargeController(Sensor):

    is_master = models.BooleanField(default=False, null=False, blank=False)
    plant = models.ForeignKey(SolarPlant, related_name="charge_controllers")

    def save(self, *args, **kwargs):
        """

        :param args:
        :param kwargs:
        :return:
        """
        self.templateName = 'CC_SECONDARY'
        if self.is_master:
            self.templateName = 'CC_PRIMARY'
        super(ChargeController, self).save(*args, **kwargs)
        add_charge_controller_streams(self)


def add_charge_controller_streams(c_controller):
    """

    :param c_controller:
    :return:
    """
    for stream in CHARGE_CONTROLLER_STREAMS:
        sf = SolarField(source=c_controller, name=stream,
                        streamDataType='FLOAT', displayName=stream, fieldType='INPUT')
        sf.save()


class PanelSet(IndependentInverter):
    no_of_panels = models.IntegerField(default=1, null=False, blank=False)
    charge_controller = models.ForeignKey(ChargeController,
                                          related_name="panel_sets")

    def save(self, *args, **kwargs):
        """

        :param args:
        :param kwargs:
        :return:
        """
        self.templateName = settings.INVERTER_TEMPLATE
        self.name = "Panels_%s" % self.name
        super(PanelSet, self).save(*args, **kwargs)
        self.fields.all().exclude(name__in=PANELSET_STREAMS).update(isActive=False)


class ConnectedLoad(IndependentInverter):

    load_voltage = models.FloatField(null=False, blank=False)
    charge_controller = models.ForeignKey(ChargeController,
                                          related_name="connected_loads")

    def save(self, *args, **kwargs):
        """

        :param args:
        :param kwargs:
        :return:
        """
        self.templateName = settings.INVERTER_TEMPLATE
        self.name = "Load_%s" % self.name
        super(ConnectedLoad, self).save(*args, **kwargs)
        self.fields.all().exclude(name__in=LOAD_STREAMS).update(isActive=False)


class Battery(IndependentInverter):

    controllable = models.BooleanField(default=False, null=False, blank=False)
    charge_controller = models.ManyToManyField(ChargeController,
                                               related_name="batteries")

    def save(self, *args, **kwargs):
        """

        :param args:
        :param kwargs:
        :return:
        """
        self.templateName = settings.INVERTER_TEMPLATE
        self.name = "Battery_%s" % self.name
        super(Battery, self).save(*args, **kwargs)
        self.fields.all().exclude(name__in=BATTERY_STREAMS).update(isActive=False)


