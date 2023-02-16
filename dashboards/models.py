from organizations.models import Organization, OrganizationUser
from django.db import models
from dataglen.models import Sensor
from django.contrib.auth.models import Permission
import os

# Define skeleton models
class Dashboard(Organization):

    active = models.BooleanField(default=True)
    allowGroups = models.BooleanField(default=True)

    ownerViewURL = models.CharField(blank=False, max_length=50)
    employeeViewURL = models.CharField(blank=False, max_length=50)
    groupViewURL = models.CharField(blank=False, max_length=50)

    def __unicode__(self):
        return self.name

    class Meta:
        permissions = (
            ('client_view', 'Allowed to access client view of this dashboard'),
            ('employee_view', 'Allowed to access employee view of this dashboard'),
            ('group_view', 'Allowed to access group view of this dashboard'),
            ('can_create_groups', 'This employee is allowed to create groups of this dashboard'),
        )


class DataglenClient(Organization):
    clientWebsite = models.URLField(blank=False)
    clientLogo = models.URLField(blank=True, null=True)
    clientMobileLogo = models.URLField(blank=True, null=True)
    clientDomain = models.CharField(max_length=50, blank=True, null=True)
    clientContactAddress = models.EmailField(blank=True, null=True)
    clientDashboard = models.ForeignKey(Dashboard,
                                        related_name="dataglen_clients")
    canCreateGroups = models.BooleanField(default=False)
    webdynClient = models.BooleanField(default=False)
    #client_address = models.TextField(default="", blank=True)
    #client_phone_no = models.CharField(default="", blank=True, max_length=13)

    def is_employee(self, user):
        return self.is_admin(user)

    def get_employees(self):
        try:
            return self.organization_users.all().exclude(id=self.owner.organization_user.id)
        except:
            # if there's no owner associated
            return []

    def get_members(self):
        members = set
        groups = self.dataglen_groups.all()
        for group in groups:
            members.union(set(group.get_members()))
        return members

    def get_sensors(self):
        # add employees
        users = [employee.user for employee in self.get_employees()]
        # add the owner's user instance
        users.append(self.owner.organization_user.user)
        # add groups' sensors
        sources = set(Sensor.objects.filter(user__in=users, isTemplate=False))
        for group in self.get_groups():
            sources = sources.union(group.get_sensors())
        try:
            return list(sources)
        except TypeError:
            return []

    def get_groups(self):
        return self.dataglen_groups.all()

    def generate_solar_plant_reports(self, filename):
        try:
            if os.path.exists(filename):
                fd = open(filename, "a")
            else:
                fd = open(filename, "w")
        except Exception as exc:
            print exc
            return

        for group in self.get_groups():
            try:
                plant = group.solarplant
                text = "#".join([str(self.name),
                                 str(plant.name),
                                 str(plant.capacity),
                                 str(str(plant.independent_inverter_units.all()[0].get_last_write_ts().date())),
                                 str(plant.independent_inverter_units.all()[0].get_last_write_ts(first_ts=True).date()),
                                 str(len(plant.independent_inverter_units.all())),
                                 "\n"])
                fd.write(text)
            except:
                continue
        fd.close()

    def __unicode__(self):
        return self.name


class DataglenGroup(Organization):
    groupClient = models.ForeignKey(DataglenClient, related_name="dataglen_groups")
    groupLogo = models.URLField(blank=True, null=True)
    groupMobileLogo = models.URLField(blank=True, null=True)
    groupSensors = models.ManyToManyField(Sensor, blank=True, null=True, related_name="dataglen_groups")
    groupPermissions = models.ManyToManyField(Permission, blank=True, null=True, related_name="dataglen_groups")

    def get_client(self):
        return self.groupClient

    def get_members(self):
        try:
            return self.organization_users.all().exclude(id=self.owner.organization_user.id)
        except:
            return []

    def get_sensors(self):
        return self.groupSensors.all()

    def __unicode__(self):
        return "_".join([self.name, str(self.groupClient.id)])



