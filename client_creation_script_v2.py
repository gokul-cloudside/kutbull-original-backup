import sys
import os
import django
import configparser
os.environ["DJANGO_SETTINGS_MODULE"] = "kutbill.settings"
django.setup()
from django.db import IntegrityError
from django.contrib.auth.models import User
from allauth.account.models import EmailAddress
from dashboards.models import DataglenClient
from dashboards.models import Dashboard
from organizations.models import OrganizationOwner
from organizations.models import OrganizationUser
from django.core.mail import send_mail
from rest_framework.authtoken.models import Token
from features.models import Feature, SubscriptionPlan, DGClientSubscription, RoleAccess
from dashboards.models import Dashboard, DataglenClient
from features.models import SOLAR_USER_ROLE
from features.setup_features import SUBSCRIPTION_PLANS

__version__ = '2.0'
CONFIG_FILE = "client_creation.cfg"


class ClientCreation(object):

    api_token = None

    def __init__(self):
        """
            read config parameters
        """

        self.config_dict = self.get_config_parameters()
        if not self.config_dict:
            sys.exit()

    def get_config_parameters(self):
        """
        get config parameter from .cfg file
        :return:
        """

        config_dict = {}
        config = configparser.ConfigParser()
        config.read(CONFIG_FILE)
        config_dict['USER_NAME'] = config['USER']['USER_NAME']
        config_dict['PASSWORD'] = config['USER']['PASSWORD']
        config_dict['EMAIL'] = config['USER']['EMAIL']
        config_dict['FIRST_NAME'] = config['USER']['FIRST_NAME']
        config_dict['LAST_NAME'] = config['USER']['LAST_NAME']
        config_dict['CLIENT_NAME'] = config['CLIENT']['NAME']
        config_dict['CLIENT_ACTIVE'] = config['CLIENT']['IS_ACTIVE']
        config_dict['CLIENT_SLUG'] = config['CLIENT']['SLUG']
        config_dict['CLIENT_WEBSITE'] = config['CLIENT']['WEBSITE']
        config_dict['CLIENT_DASHBOARD'] = config['CLIENT']['DASHBOARD']
        config_dict['CLIENT_CAN_CREATE_GROUPS'] = config['CLIENT']['CAN_CREATE_GROUPS']
        return config_dict

    def add_user(self):
        """

        :return:
        """

        user = User.objects.filter(username=self.config_dict["USER_NAME"])
        if not user:
            user = User.objects.create_user(self.config_dict["USER_NAME"],
                                            self.config_dict["EMAIL"],
                                            self.config_dict["PASSWORD"],
                                            first_name=self.config_dict["FIRST_NAME"],
                                            last_name=self.config_dict["LAST_NAME"])
            user.save()
            print "New user created"
            return user
        return user[0]

    def add_email(self,user=None):
        """

        :param user:
        :return:
        """

        email_address, created = EmailAddress.objects.get_or_create(user=user,
                                                        email=self.config_dict["EMAIL"],
                                                        verified=True,
                                                        primary=True)
        if created:
            print "Email address added"
        print "Organization Owner is %s" % email_address
        return email_address

    def add_client(self):
        """

        :return:
        """

        client = DataglenClient.objects.filter(name=self.config_dict["CLIENT_NAME"])
        if not client:
            dashboard = Dashboard.objects.get(name=self.config_dict["CLIENT_DASHBOARD"])
            client = DataglenClient.objects.create(name=self.config_dict["CLIENT_NAME"],
                                                   is_active=self.config_dict["CLIENT_ACTIVE"],
                                                   slug=self.config_dict["CLIENT_SLUG"],
                                                   clientWebsite=self.config_dict["CLIENT_WEBSITE"],
                                                   clientDashboard=dashboard,
                                                   canCreateGroups=self.config_dict["CLIENT_CAN_CREATE_GROUPS"])
            print "Client Created"
            return client
        return client[0]

    def create_organization_user(self,user=None,client=None):
        """

        :param user:
        :param client:
        :return:
        """

        organization_user, created = OrganizationUser.objects.get_or_create(user=user, organization=client)
        if created:
            print "Organization User Created"
        print "Organization User is %s" % organization_user
        return organization_user

    def create_organization_owner(self,client=None,organization_user=None):
        """

        :param client:
        :param organization_user:
        :return:
        """

        organization_owner, created = OrganizationOwner.objects.get_or_create(organization=client,\
                                                               organization_user=organization_user)
        if created:
            print "Organization Owner Created"
        print "Organization Owner is %s" % organization_owner
        return organization_owner

    def get_auth_token(self, user):
        """

        :param user:
        :return:
        """

        token = Token.objects.get(user=user)
        return token

    def email_send(self,token, send_email):
        """

        :param token:
        :param send_email:
        :return:
        """

        email = ['lavanya@dataglen.com']
        subject = 'New Client Created'
        description = 'A new Client has been created on dataglen.com with following details \n\nClient Name ' + str(self.config_dict["CLIENT_NAME"]) + '\n'+'User Name: ' + str(self.config_dict["USER_NAME"]) + '\n' + 'Email: '+ str(self.config_dict["EMAIL"]) + '\n' + 'Password: ' + str(self.config_dict["PASSWORD"]) + '\n' + 'Dashboard: ' + str(self.config_dict['CLIENT_DASHBOARD']) + '\n' + 'API-KEY: '+ str(token.key)
        if send_email:
            send_mail(subject, description, 'admin@dataglen.com', email, fail_silently=False)
            print "email sent"
        return description


def create_dataglen_client(send_email=False):
    """

    :return:
    """

    clientCreation = ClientCreation()
    user = clientCreation.add_user()
    clientCreation.add_email(user)
    client = clientCreation.add_client()
    organization_user = clientCreation.create_organization_user(user, client)
    organization_owner = clientCreation.create_organization_owner(client, organization_user)
    token = clientCreation.get_auth_token(user)
    email_content = clientCreation.email_send(token, send_email)
    return email_content


def define_client_subscription_plan(client):
    """

    :param client:
    :return:
    """
    subscription = SubscriptionPlan.objects.get(name="PREMIUM")
    DGClientSubscription.objects.create(dg_client=client, subscription_plan=subscription)


def define_roles_access_for_client(client):
    """

    :param client:
    :return:
    """
    for role in SOLAR_USER_ROLE:
        ra = RoleAccess.objects.create(dg_client=client,
                                               role=role[0])
        if role[0].startswith("CLIENT"):
            for feature in Feature.objects.filter(name__in=SUBSCRIPTION_PLANS['BASIC']):
                ra.features.add(feature)
        else:
            for feature in Feature.objects.all():
                ra.features.add(feature)
