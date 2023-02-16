import sys
import os
import django
import configparser
#sys.path.append("/Dataglen/template-integration/kutbill-django")
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
from django.contrib.sites.models import Site

CONFIG_FILE = "client_creation.cfg"

class ClientCreation(object):
    api_token = None
    def get_config_parameters(self):
        config_dict = {}
        try:
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

        except configparser.Error:
            config_dict = None
        return config_dict

    def __init__(self):

        self.config_dict = self.get_config_parameters()
        if not self.config_dict:
            sys.exit()

    def add_user(self):
        try:
            user = User.objects.get(username=self.config_dict["USER_NAME"])
            return user
        except:
            try:
                user = User.objects.create_user(self.config_dict["USER_NAME"],
                                                self.config_dict["EMAIL"],
                                                self.config_dict["PASSWORD"],
                                                first_name=self.config_dict["FIRST_NAME"],
                                                last_name=self.config_dict["LAST_NAME"])
                user.save()
                print("New user created")
                return user
            except IntegrityError as exception:
                print(str(exception))
            except Exception as exception:
                print(str(exception))


    def add_email(self,user=None):
        try:
            email_address = EmailAddress.objects.get(user=user)
        except:
            try:
                email_address = EmailAddress.objects.create(user=user,
                                                            email=self.config_dict["EMAIL"],
                                                            verified=True,
                                                            primary=True)
                email_address.save()
                print("Email address added")
            except IntegrityError as exception:
                print(str(exception))
            except Exception as exception:
                print(str(exception))

    def add_client(self):
        try:
            client = DataglenClient.objects.get(name=self.config_dict["CLIENT_NAME"])
            return client
        except:
            try:
                try:
                    dashboard = Dashboard.objects.get(name=self.config_dict["CLIENT_DASHBOARD"])
                except Exception as exception:
                    print("Client Dashboard instance not found")
                client = DataglenClient.objects.create(name=self.config_dict["CLIENT_NAME"],
                                                       is_active=self.config_dict["CLIENT_ACTIVE"],
                                                       slug=self.config_dict["CLIENT_SLUG"],
                                                       clientWebsite=self.config_dict["CLIENT_WEBSITE"],
                                                       clientDashboard=dashboard,
                                                       canCreateGroups=self.config_dict["CLIENT_CAN_CREATE_GROUPS"])
                client.save()
                print("Client Created")
                return client
            except IntegrityError as exception:
                print(str(exception))
            except Exception as exception:
                print(str(exception))

    def create_organization_user(self,user=None,client=None):
        try:
            organization_user = OrganizationUser.objects.get(user=user,
                                                             organization=client)
        except:
            try:
                organization_user = OrganizationUser.objects.create(user=user,
                                                                    organization=client)
                organization_user.save()
                print("Organization User Created")
                return organization_user
            except IntegrityError as exception:
                print(str(exception))
            except Exception as exception:
                print(str(exception))


    def create_organization_owner(self,client=None,organization_user=None):
        try:
            organization_owner = OrganizationOwner.objects.get(organization=client,
    														   organization_user=organization_user)
            return organization_owner
        except:
            try:
                organization_owner = OrganizationOwner.objects.create(organization=client,
                                                                      organization_user=organization_user)
                organization_owner.save()
                print("Organization Owner Created")
                return organization_owner
            except IntegrityError as exception:
                print(str(exception))
            except Exception as exception:
                print(str(exception))

    def get_auth_token(self, user):
        try:
            token = Token.objects.get(user=user)
            api_token = token
            return token
        except IntegrityError as exception:
            print(str(exception))
        except Exception as exception:
            print(str(exception))    

    def email_send(self,token, send_email):
        email = ['nishant@dataglen.com', 'dpseetharam@dataglen.com', 'tanuja@dataglen.com', 'sunilkrghai@dataglen.com']
        subject = 'New Client Created'
        description = 'A new Client has been created on dataglen.com with following details \n\nClient Name ' + self.config_dict["CLIENT_NAME"] + '\n'+'User Name: ' + self.config_dict["USER_NAME"] + '\n' + 'Email: '+ self.config_dict["EMAIL"] + '\n' + 'Password: ' + self.config_dict["PASSWORD"] + '\n' + 'Dashboard: ' + self.config_dict['CLIENT_DASHBOARD'] + '\n' + 'API-KEY: '+ token.key
        try:
            if send_email:
                send_mail(subject,description,'admin@dataglen.com',email,fail_silently=False)
                print("email sent")
        except Exception as exception:
            print(str(exception))
        return description

def create_dataglen_client(send_email=False):
    clientCreation = ClientCreation()
    user = clientCreation.add_user()
    clientCreation.add_email(user)
    client = clientCreation.add_client()
    organization_user = clientCreation.create_organization_user(user,client)
    organization_owner = clientCreation.create_organization_owner(client,organization_user)
    token = clientCreation.get_auth_token(user)
    email_content = clientCreation.email_send(token, send_email)
    return email_content