import json
from django.http import Http404
from django.utils.translation import ugettext_lazy as _
from guardian.mixins import LoginRequiredMixin
from .utils import is_owner, is_employee, is_member, filter_owned_orgs, get_owned_group_details,\
    get_owned_group_and_solar_details, validate_groups
from django.contrib.auth.models import update_last_login
from django.conf import settings
from dataglen.models import Sensor

import logging
logger = logging.getLogger('rest.views')
logger.setLevel(logging.DEBUG)


class EntryPointMixin(LoginRequiredMixin):
    def dispatch(self, request, *args, **kwargs):
        self.request = request
        self.args = args
        self.kwargs = kwargs
        try:
            status, org = is_owner(self.request.user)
            if status is True:
                self.organization = org
                self.dataglenclient = self.organization.dataglenclient
                self.dataglengroup = None
                self.dashboard = self.dataglenclient.clientDashboard
                self.user_status = settings.USER_STATUS.OWNER
            else:
                # an employee can belong
                status, org = is_employee(self.request.user)
                if status is True:
                    self.organization = org
                    self.dataglenclient = self.organization.dataglenclient
                    self.dataglengroup = None
                    self.dashboard = self.dataglenclient.clientDashboard
                    self.user_status = settings.USER_STATUS.EMPLOYEE
                else:
                    status, orgs = is_member(self.request.user)

                    if status is True:
                        validated, dataglen_client, dataglen_groups = validate_groups(orgs)
                        if validated is True:
                            self.organization = dataglen_client.organization_ptr
                            self.dataglenclient = dataglen_client
                            self.dataglengroups = dataglen_groups
                            self.dashboard = self.dataglenclient.clientDashboard
                            self.user_status = settings.USER_STATUS.MEMBER
                        else:
                            self.organization = None
                            self.dataglengroups = None
                            self.dataglenclient = None
                            self.dashboard = None
                            self.user_status = settings.USER_STATUS.UNASSIGNED
                    else:
                        self.organization = None
                        self.dataglengroups = None
                        self.dataglenclient = None
                        self.dashboard = None
                        self.user_status = settings.USER_STATUS.UNASSIGNED
        except Exception as E:
            self.organization = None
            self.dataglengroup = None
            self.dataglenclient = None
            self.dashboard = None
            self.user_status = settings.USER_STATUS.UNASSIGNED

        self.object = self.organization
        return super(EntryPointMixin, self).dispatch(
                    request, *args, **kwargs)


class AddSensorsMixin(object):
    # RETURNS A LIST, NOT A QUERYSET, DO NOT CHANGE THAT!
    def dispatch(self, request, *args, **kwargs):
        if self.user_status is settings.USER_STATUS.OWNER:
            # sensors the owner owns, employees' own, and from the groups
            self.sources = self.dataglenclient.get_sensors()
        elif self.user_status is settings.USER_STATUS.EMPLOYEE:
            # sensors the employee owns
            sources = Sensor.objects.filter(user=request.user, isTemplate=False)
            sources = set(sources)
            # sensors from the groups the employee owns
            for dataglengroup_org in filter_owned_orgs(self.request.user, 'dataglengroup'):
                sources = sources.union(dataglengroup_org.dataglengroup.get_sensors())
            try:
                self.sources = list(sources)
            except TypeError:
                self.sources = []
        elif self.user_status is settings.USER_STATUS.MEMBER:
            # sensors the member owns
            sources = Sensor.objects.filter(user=request.user, isTemplate=False)
            # presently a member can belong to only one group
            if hasattr(self, 'dataglengroups'):
                group_sensors = []
                for g in self.dataglengroups:
                    for s in g.get_sensors():
                        group_sensors.append(s)
                self.sources = list(set(group_sensors).union(set(sources)))
            else:
                self.sources = list(set(sources))
        else :
            self.sources = list(Sensor.objects.filter(user=self.request.user))
        return super(AddSensorsMixin, self).dispatch(request, *args, **kwargs)


class OwnerRequiredMixin(EntryPointMixin):
    def dispatch(self, request, *args, **kwargs):
        dispatcher = super(OwnerRequiredMixin, self).dispatch(request, *args, **kwargs)
        if self.user_status is settings.USER_STATUS.OWNER:
            return dispatcher
        else:
            raise Http404(_("Only client owners are allowed to access this page."))


class EmployeeRequiredMixin(EntryPointMixin):
    def dispatch(self, request, *args, **kwargs):
        dispatcher = super(EmployeeRequiredMixin, self).dispatch(request, *args, **kwargs)
        if self.user_status is settings.USER_STATUS.OWNER \
                or self.user_status is settings.USER_STATUS.EMPLOYEE:
            return dispatcher
        else:
            raise Http404(_("Only client owners or employees are allowed to access this page."))


class MemberRequiredMixin(EntryPointMixin):
    def dispatch(self, request, *args, **kwargs):
        dispatcher = super(MemberRequiredMixin, self).dispatch(request, *args, **kwargs)
        if self.user_status is settings.USER_STATUS.OWNER\
                or self.user_status is settings.USER_STATUS.EMPLOYEE\
                or self.user_status is settings.USER_STATUS.MEMBER:
            return dispatcher
        else:
            raise Http404(_("Only client owners, employees or members are allowed to access this page."))



class ProfileDataMixin(EntryPointMixin):
    def get_profile_data(self, **kwargs):
        context = {}#super(ProfileDataMixin, self).get_context_data(**kwargs)

        user = self.request.user
        try:
            webdyn_client = user.organizations_organization.all()[0].dataglengroup.groupClient.webdynClient
        except:
            webdyn_client = False
        context['webdyn_client'] = webdyn_client

        if self.user_status is settings.USER_STATUS.OWNER:
            context['dataglenclient'] = self.dataglenclient
            context['employees'] = self.dataglenclient.get_employees()
            context['groups'] = self.dataglenclient.dataglen_groups.all()
            context['groups_details'] = get_owned_group_details(context['groups'])
            total_members = set([])
            for group in self.dataglenclient.get_groups():
                total_members = total_members.union(set(group.get_members()))
            context['members'] = list(total_members)
            context['sensors'] = Sensor.objects.filter(isTemplate=False, user=self.request.user)
            context['user_access'] = "OWNER"
            try:
                context['contents'] = json.dumps(self.dataglenclient.contents_enabled.all()[0].contents)
            except Exception as exc:
                context['contents'] = None

        elif self.user_status is settings.USER_STATUS.EMPLOYEE:
            context['dataglenclient'] = self.dataglenclient
            owned_groups = self.dataglenclient.get_groups() #filter_owned_orgs(self.request.user, 'dataglengroup')
            context['groups'] = [org.dataglengroup for org in owned_groups]
            context['groups_details'] = get_owned_group_details(context['groups'])
            context['sensors'] = Sensor.objects.filter(isTemplate=False, user=self.request.user)
            context['user_access'] = "EMPLOYEE"
            try:
                context['contents'] = json.dumps(self.dataglenclient.contents_enabled.all()[0].contents)
            except:
                context['contents'] = None

        elif self.user_status is settings.USER_STATUS.MEMBER:
            # organisation and dataglenclient params
            context['dataglenclient'] = self.dataglenclient
            #TODO - members own sensors
            context['groups'] = self.dataglengroups
            context['groups_details'] = get_owned_group_details(context['groups'])
            context['user_access'] = "MEMBER"
            try:
                context['contents'] = json.dumps(self.dataglenclient.contents_enabled.all()[0].contents)
            except:
                context['contents'] = None

        elif self.user_status is settings.USER_STATUS.UNASSIGNED:
            context['sensors'] = Sensor.objects.filter(isTemplate=False, user=self.request.user)

        return context


class ContextDataMixin(ProfileDataMixin):
    def get_context_data(self, **kwargs):
        context = super(ContextDataMixin, self).get_context_data(**kwargs)
        tcontext = self.get_profile_data()
        for key in tcontext.keys():
            context[key] = tcontext[key]
        return context


class ProfileDataInSolarAPIs(object):
    def get_profile_data(self, **kwargs):
        context = {}
        try:
            status, org = is_owner(self.request.user)
            if status is True:
                self.organization = org
                self.dataglenclient = self.organization.dataglenclient
                self.dataglengroup = None
                self.dashboard = self.dataglenclient.clientDashboard
                self.user_status = settings.USER_STATUS.OWNER
                context['dataglenclient'] = self.dataglenclient
                context['groups'] = self.dataglenclient.dataglen_groups.all()
                context['solar_plants'] = get_owned_group_and_solar_details(context['groups'])

            else:
                # an employee can belong
                status, org = is_employee(self.request.user)
                if status is True:
                    self.organization = org
                    self.dataglenclient = self.organization.dataglenclient
                    self.dataglengroup = None
                    self.dashboard = self.dataglenclient.clientDashboard
                    self.user_status = settings.USER_STATUS.EMPLOYEE
                    context['dataglenclient'] = self.dataglenclient
                    owned_groups = self.dataglenclient.get_groups() #filter_owned_orgs(self.request.user, 'dataglengroup')
                    context['solar_plants'] = []
                    for org in owned_groups:
                        try:
                            context['solar_plants'].push(org.dataglengroup.solarplant)
                        except:
                            continue
                    #context['groups'] = [org.dataglengroup for org in owned_groups]
                    #context['solar_plants'] = get_owned_group_and_solar_details(context['groups'])
                else:
                    status, orgs = is_member(self.request.user)
                    if status is True:
                        validated, dataglen_client, dataglen_groups = validate_groups(orgs)
                        if validated is True:
                            self.organization = dataglen_client.organization_ptr
                            self.dataglenclient = dataglen_client
                            self.dataglengroups = dataglen_groups
                            self.dashboard = self.dataglenclient.clientDashboard
                            self.user_status = settings.USER_STATUS.MEMBER
                            context['dataglenclient'] = self.dataglenclient
                            #TODO - members own sensors
                            context['groups'] = self.dataglengroups
                            context['solar_plants'] = get_owned_group_and_solar_details(context['groups'])
                    else:
                        self.organization = None
                        self.dataglengroups = None
                        self.dataglenclient = None
                        self.dashboard = None
                        self.user_status = settings.USER_STATUS.UNASSIGNED
                        context['sensors'] = Sensor.objects.filter(isTemplate=False, user=self.request.user)
                        context['contents'] = None
        except Exception as E:
            logger.debug(E)
            self.organization = None
            self.dataglengroup = None
            self.dataglenclient = None
            self.dashboard = None
            self.user_status = settings.USER_STATUS.UNASSIGNED

        return context


class ProfileDataInAPIs(object):
    def get_profile_data(self, **kwargs):
        context = {}
        try:
            update_last_login(None, self.request.user)
            status, org = is_owner(self.request.user)
            if status is True:
                self.organization = org
                self.dataglenclient = self.organization.dataglenclient
                self.dataglengroup = None
                self.dashboard = self.dataglenclient.clientDashboard
                self.user_status = settings.USER_STATUS.OWNER
                context['dataglenclient'] = self.dataglenclient
                context['employees'] = self.dataglenclient.get_employees()
                context['groups'] = self.dataglenclient.dataglen_groups.all()
                context['groups_details'] = get_owned_group_details(context['groups'])
                total_members = set([])
                for group in self.dataglenclient.get_groups():
                    total_members = total_members.union(set(group.get_members()))
                context['members'] = list(total_members)
                context['sensors'] = Sensor.objects.filter(isTemplate=False, user=self.request.user)

            else:
                # an employee can belong
                status, org = is_employee(self.request.user)
                if status is True:
                    self.organization = org
                    self.dataglenclient = self.organization.dataglenclient
                    self.dataglengroup = None
                    self.dashboard = self.dataglenclient.clientDashboard
                    self.user_status = settings.USER_STATUS.EMPLOYEE
                    context['dataglenclient'] = self.dataglenclient
                    owned_groups = self.dataglenclient.get_groups() #filter_owned_orgs(self.request.user, 'dataglengroup')
                    context['groups'] = [org.dataglengroup for org in owned_groups]
                    context['groups_details'] = get_owned_group_details(context['groups'])
                    context['sensors'] = Sensor.objects.filter(isTemplate=False, user=self.request.user)
                else:
                    status, orgs = is_member(self.request.user)
                    if status is True:
                        validated, dataglen_client, dataglen_groups = validate_groups(orgs)
                        if validated is True:
                            self.organization = dataglen_client.organization_ptr
                            self.dataglenclient = dataglen_client
                            self.dataglengroups = dataglen_groups
                            self.dashboard = self.dataglenclient.clientDashboard
                            self.user_status = settings.USER_STATUS.MEMBER
                            context['dataglenclient'] = self.dataglenclient
                            #TODO - members own sensors
                            context['groups'] = self.dataglengroups
                            context['groups_details'] = get_owned_group_details(context['groups'])
                    else:
                        self.organization = None
                        self.dataglengroups = None
                        self.dataglenclient = None
                        self.dashboard = None
                        self.user_status = settings.USER_STATUS.UNASSIGNED
                        context['sensors'] = Sensor.objects.filter(isTemplate=False, user=self.request.user)
                        context['contents'] = None
        except Exception as E:
            logger.debug(E)
            self.organization = None
            self.dataglengroup = None
            self.dataglenclient = None
            self.dashboard = None
            self.user_status = settings.USER_STATUS.UNASSIGNED

        return context
