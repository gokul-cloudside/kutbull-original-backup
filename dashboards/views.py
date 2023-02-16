from django.views.generic.base import View, TemplateView
from django.views.generic.edit import CreateView, FormView, UpdateView
from django.shortcuts import redirect
from django.core.urlresolvers import reverse
from kutbill import settings
from .mixins import EntryPointMixin, ContextDataMixin
import logging
from .forms import EmployeeAddForm, DataglenGroupAddForm, MemberAddForm
from .models import DataglenGroup
from django.http import HttpResponseBadRequest, HttpResponse, JsonResponse
from rest_framework.views import APIView
from django.contrib.auth import authenticate
logger = logging.getLogger('dataglen.views')
logger.setLevel(logging.DEBUG)
from .mixins import ProfileDataInAPIs
from .utils import is_owner
from rest_framework.authtoken.models import Token

class ErrorView(EntryPointMixin, TemplateView):
    template_name = "dataglen/500.html"


class EntryPointPostLogin(EntryPointMixin, View):
    def dispatch(self, request, *args, **kwargs):
        super(EntryPointPostLogin, self).dispatch(request, *args, **kwargs)
        if self.user_status is settings.USER_STATUS.OWNER:
            return redirect(reverse(self.dashboard.ownerViewURL))
        elif self.user_status is settings.USER_STATUS.EMPLOYEE:
            return redirect(reverse(self.dashboard.employeeViewURL))
        elif self.user_status is settings.USER_STATUS.MEMBER:
            return redirect(reverse(self.dashboard.groupViewURL))
        elif self.user_status is settings.USER_STATUS.UNASSIGNED:
            return redirect(reverse("dataglen:dashboard"))
        else:
            return redirect(reverse("dataglen:dashboard"))


class OrganizationEmployeeCreate(ContextDataMixin, CreateView):
    form_class = EmployeeAddForm

    def get_success_url(self):
        return self.success_url

    def get_form_kwargs(self):
        kwargs = super(OrganizationEmployeeCreate, self).get_form_kwargs()
        kwargs.update({'organization': self.dataglenclient.organization_ptr,
                       'request': self.request})
        return kwargs

    def get(self, request, *args, **kwargs):
        self.organization = self.dataglenclient.organization_ptr
        return super(OrganizationEmployeeCreate, self).get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.organization = self.dataglenclient.organization_ptr
        return super(OrganizationEmployeeCreate, self).post(request, *args, **kwargs)


class GroupMemberCreate(ContextDataMixin, CreateView):
    form_class = MemberAddForm

    def get_success_url(self):
        return self.success_url

    def get_form_kwargs(self):
        kwargs = super(GroupMemberCreate, self).get_form_kwargs()
        kwargs.update({'organization': self.dataglenclient.organization_ptr,
                       'groups': self.get_profile_data()['groups'],
                       'request': self.request})
        return kwargs

    def get(self, request, *args, **kwargs):
        self.organization = self.dataglenclient.organization_ptr
        return super(GroupMemberCreate, self).get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.organization = self.dataglenclient.organization_ptr
        return super(GroupMemberCreate, self).post(request, *args, **kwargs)


class DataglenGroupCreate(ContextDataMixin, CreateView):
    form_class = DataglenGroupAddForm
    model = DataglenGroup

    def get_success_url(self):
        return self.success_url

    def get_form_kwargs(self):
        kwargs = super(DataglenGroupCreate, self).get_form_kwargs()
        kwargs.update({'request': self.request})
        kwargs.update({'dataglenclient': self.dataglenclient})
        kwargs.update({'sensors': self.get_profile_data()['sensors']})
        return kwargs


class DataglenGroupUpdate(ContextDataMixin, UpdateView):
    model = DataglenGroup
    fields = ['name', 'is_active', 'groupSensors']
    slug_url_kwarg = 'slug'
    slug_field = 'slug'

    def get_context_data(self, **kwargs):
        context = super(DataglenGroupUpdate, self).get_context_data(**kwargs)
        context['members'] = self.object.get_members()
        return context

    def get_success_url(self):
        return self.success_url

    def get_form(self, form_class=None):
        form = super(DataglenGroupUpdate, self).get_form()
        form.fields['groupSensors'].queryset = self.get_context_data()['sensors']
        return form


class DataGlenLoginView(APIView):
    def post(self, request, format=None):
        try:
            username = request.data["username"]
            password = request.data["password"]
        except:
            return JsonResponse({"detail": "Bad request"})
        user = authenticate(username=username, password=password)
        try:
            if user is None:
                return JsonResponse({"detail": "Invalid username or password"})
            else:
                status, org = is_owner(user)
                if status is True:
                    return JsonResponse({"token": user.auth_token.key,
                                         "admin": "true",
                                         "first_name": user.first_name,
                                         "last_name": user.last_name})
                else:
                    return JsonResponse({"token": user.auth_token.key,
                                         "admin": "false",
                                         "first_name": user.first_name,
                                         "last_name": user.last_name})
        except Exception as exc:
            return JsonResponse({"detail": str(exc)})

