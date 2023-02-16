from rest_framework.response import Response
from rest_framework import status
from rest_framework import viewsets
from rest_framework import authentication, permissions
from django.contrib.auth.models import User, update_last_login
from dgusers.serializers import UserCreateValues, UserViewValues, OrganizationUserCreateValues
from dgusers.models import UserRole, AlertsCategory
from dashboards.utils import is_owner
from allauth.account.models import EmailAddress
from solarrms.models import SolarPlant
from organizations.models import OrganizationUser
from solarrms.solarutils import filter_solar_plants
from dashboards.mixins import ProfileDataInAPIs
import logging
from rest_framework import parsers, renderers
from rest_framework.authtoken.models import Token
from rest_framework.authtoken.serializers import AuthTokenSerializer
from rest_framework.response import Response
from rest_framework.views import APIView
from features.models import DGClientSubscription, RoleAccess, SubscriptionPlan, Feature


logger = logging.getLogger('dataglen.rest_views')
logger.setLevel(logging.DEBUG)


class UserView(viewsets.ViewSet):
    authentication_classes = (authentication.TokenAuthentication, authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)
    lookup_field = 'id'

    def create(self, request):
        try:
            data = self.request.data
            serializer = UserCreateValues(data=data)
            user_id = User.objects.filter(email=data['email']).values_list('id', flat=True)
            if len(user_id) > 0:
                return Response("User already exist with this email.", status=status.HTTP_403_FORBIDDEN)
            if serializer.is_valid():
                try:
                    owner, client = is_owner(self.request.user)
                    if owner:
                        dataglen_client = client.dataglenclient
                    else:
                        dataglen_client = self.request.user.organizations_organization.all()[0].dataglengroup.groupClient
                except Exception as exception:
                    logger.debug(str(exception))
                    return Response("You do not have access rights to add new user.", status=status.HTTP_403_FORBIDDEN)

                try:
                    daily_report = self.request.data.get('daily_report', 0)
                    gateway_alerts = self.request.data.get('gateway_alerts', 0)
                    inverters_alerts = self.request.data.get('inverters_alerts', 0)
                    other_alerts = self.request.data.get('other_alerts', 0)
                    sms = self.request.data.get('sms', 0)
                    phone_no = self.request.data.get('phone_no', 0)
                    # donot allow any user without plant slug with new UI
                    plant_slug = self.request.data.get('plant_slug', None)
                    try:
                        password = self.request.data.get('password')
                        confirm_password = self.request.data.get('confirm_password')
                    except:
                        return Response("Please provide password and confirm passwords",status=status.HTTP_400_BAD_REQUEST)

                    if sms is 1 and phone_no is 0:
                        return Response("Please provide phone number as you have opted for sms alerts", status=status.HTTP_400_BAD_REQUEST)
                    if not (str(password) == str(confirm_password)):
                        return Response("Password and confirm password do not match", status=status.HTTP_400_BAD_REQUEST)

                    else:
                        try:
                            # Add user
                            # split with @ and use 0th element of list as username
                            username_from_email = str(data['email'])[0:29]
                            user = User.objects.create_user(str(username_from_email),
                                                            str(data['email']),
                                                            str(password),
                                                            first_name=str(data['first_name']),
                                                            last_name=str(data['last_name']))
                            user.save()

                            # Add Email address
                            user_email = EmailAddress.objects.create(user=user,
                                                                     email=str(data['email']),
                                                                     primary=True,
                                                                     verified=True)
                            user_email.save()

                            # Add user role
                            user_role = UserRole.objects.create(role=data['user_role'],
                                                                user=user,
                                                                dg_client=dataglen_client,
                                                                daily_report=daily_report,
                                                                gateway_alerts_notifications=gateway_alerts,
                                                                inverters_alerts_notifications=inverters_alerts,
                                                                other_alerts=other_alerts,
                                                                sms=sms,
                                                                phone_number=phone_no)
                            user_role.save()
                            # donot allow any user without plant slug with new UI
                            if plant_slug:
                                if str(user_role).upper().startswith("CLIENT"):
                                    admin = False
                                else:
                                    admin = True
                                splants = SolarPlant.objects.filter(slug__in=plant_slug)
                                for plant in splants:
                                    organization_user = OrganizationUser.objects.create(user=user,
                                                                                    organization=plant,
                                                                                    is_admin=admin)

                            #OrganizationUser.objects.create(user=user, organization=dataglen_client)
                            return Response("User created successfully", status=status.HTTP_201_CREATED)
                        except Exception as exception:
                            logger.debug(str(exception))
                            return Response("A user with this email already exists.", status=status.HTTP_400_BAD_REQUEST)

                except Exception as exception:
                    logger.debug(str(exception))
                    return Response("Please provide password and confirm password", status=status.HTTP_400_BAD_REQUEST)

            else:
                logger.debug(serializer.errors)
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as exception:
            logger.debug(str(exception))
            return Response("INTERNAL_SERVER_ERROR", status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def list(self, request):
        try:
            try:
                owner, client = is_owner(self.request.user)
                if owner:
                    dataglen_client = client.dataglenclient
                else:
                    dataglen_client = self.request.user.organizations_organization.all()[0].dataglengroup.groupClient
            except Exception as exception:
                logger.debug(str(exception))
                return Response("You do not have access rights to view users.", status=status.HTTP_403_FORBIDDEN)

            response_data= {}
            user_array = []
            try:
                associated_users = UserRole.objects.filter(dg_client=dataglen_client)
                for associated_user in associated_users:
                    user_dict = {}
                    user = associated_user.user
                    user_dict["user_id"] = user.id
                    user_dict["user_name"] = user.username
                    user_dict["email"] = user.email
                    user_dict["first_name"] = user.first_name
                    user_dict["last_name"] = user.last_name
                    try:
                        user_dict["role"] = user.role.role
                    except:
                        user_dict["role"] = None
                    user_array.append(user_dict)
                response_data["users"] = user_array
                serializer = UserViewValues(response_data)
                return Response(serializer.data, status=status.HTTP_200_OK)
            except Exception as exception:
                logger.debug(str(exception))
                return Response("BAD_REQUEST", status=status.HTTP_400_BAD_REQUEST)

        except Exception as exception:
            logger.debug(str(exception))
            return Response("INTERNAL_SERVER_ERROR", status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def partial_update(self, request, id=None):
        try:
            try:
                user = User.objects.get(id=id)
            except:
                return Response("Invalid User", status=status.HTTP_400_BAD_REQUEST)
            try:
                user_role = self.request.data.get('user_role', user.role.role)
            except Exception as exception:
                return Response("Please provide a role for the user", status=status.HTTP_400_BAD_REQUEST)
            logger.debug(user_role)
            daily_report = self.request.data.get('daily_report', user.role.daily_report)
            gateway_alerts = self.request.data.get('gateway_alerts', user.role.gateway_alerts_notifications)
            inverters_alerts = self.request.data.get('inverters_alerts', user.role.inverters_alerts_notifications)
            other_alerts = self.request.data.get('other_alerts', user.role.other_alerts)
            sms = self.request.data.get('sms', user.role.sms)
            phone_no = self.request.data.get('phone_no', user.role.phone_number)
            if sms is 1 and phone_no is 0:
                return Response("Please provide phone number as you have opted for sms alerts", status=status.HTTP_400_BAD_REQUEST)
            preferences = self.request.data.get('preferences', None)
            slugs = self.request.query_params.get('slugs', None)
            if preferences and len(preferences)>0:
                for preference in preferences:
                    try:
                        logger.debug(preference)
                        event_type = str(preference['event_type']).replace(" ","_").upper()
                        alert_category = AlertsCategory.objects.get(user_role=user.role, event_type=event_type)
                        enabled = True if str(preference['enabled']) is 'True' else False
                        email_notifications = True if str(preference['email_notifications']) is 'True' else False
                        alert_on_close = True if str(preference['alert_on_close']) is 'True' else False
                        sms_notifications = True if str(preference['sms_notifications']) is 'True' else False
                        email_aggregation_minutes = int(preference['email_aggregation_minutes'])
                        sms_aggregation_minutes = int(preference['sms_aggregation_minutes'])
                        alert_category.enabled = enabled
                        alert_category.email_notifications = email_notifications
                        alert_category.alert_on_close = alert_on_close
                        alert_category.sms_notifications = sms_notifications
                        alert_category.email_aggregation_minutes = email_aggregation_minutes
                        alert_category.sms_aggregation_minutes = sms_aggregation_minutes
                        alert_category.save()
                    except Exception as exception:
                        logger.debug(str(exception))
                        return Response("Alert Preferences can not be updated", status=status.HTTP_400_BAD_REQUEST)
            try:
                user_role_table = user.role
                user_role_table.role=user_role
                user_role_table.daily_report=daily_report
                user_role_table.gateway_alerts_notifications=gateway_alerts
                user_role_table.inverters_alerts_notifications=inverters_alerts
                user_role_table.other_alerts=other_alerts
                user_role_table.sms=sms
                user_role_table.phone_number=phone_no
                user_role_table.save()
            except Exception as exception:
                logger.debug(str(exception))
                return Response("User details can not be updated", status=status.HTTP_400_BAD_REQUEST)

            logger.debug(slugs)
            if slugs is not None:
                try:
                    slugs = slugs.split(",")
                except:
                    return Response("Please send comma separated plant slugs")
                try:
                    user.role.alerts_preferences_plants.all()[0].set_preferences(slugs)
                except:
                    return Response("plant alert preference can not be updated", status=status.HTTP_400_BAD_REQUEST)

            return Response("User details updated successfully.", status=status.HTTP_201_CREATED)
        except Exception as exception:
            logger.debug(str(exception))
            return Response("INTERNAL_SERVER_ERROR", status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def retrieve(self, request, id=None):
        try:
            try:
                user = User.objects.get(id=id)
            except:
                return Response("Invalid User", status=status.HTTP_400_BAD_REQUEST)
            try:
                data = {}
                data['user_id'] = user.id
                data['user_name'] = user.username
                data['email'] = user.email
                data['first_name'] = user.first_name
                data['last_name'] = user.last_name
                data['role'] = user.role.role
                data['daily_report'] = user.role.daily_report
                data['gateway_alerts'] = user.role.gateway_alerts_notifications
                data['inverters_alerts'] = user.role.inverters_alerts_notifications
                data['other_alerts'] = user.role.other_alerts
                data['sms'] = user.role.sms
                data['phone_no'] = user.role.phone_number
                data['preferences'] = user.role.list_accessible_alerts()
                try:
                    data['plant_preferences'] = user.role.alerts_preferences_plants.all()[0].get_preferences()[0]
                    data['enabled_plants'] = user.role.alerts_preferences_plants.all()[0].get_preferences()[1]
                    data['total_plants'] = user.role.alerts_preferences_plants.all()[0].get_preferences()[2]
                except:
                    pass
            except:
                return Response("User has no role", status=status.HTTP_400_BAD_REQUEST)
            return Response(data=data, status=status.HTTP_200_OK)
        except Exception as exception:
            logger.debug(str(exception))



class OrganizationUserView(ProfileDataInAPIs, viewsets.ViewSet):
    authentication_classes = (authentication.TokenAuthentication, authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)
    lookup_field = 'id'

    def create(self, request):
        try:
            data = self.request.data
            serializer = OrganizationUserCreateValues(data=data)
            if serializer.is_valid():
                try:
                    user = User.objects.get(email=str(data['email']))
                    plant = SolarPlant.objects.get(slug=str(data['plant_slug']))
                except Exception as exception:
                    logger.debug(str(exception))
                    return Response("Invalid email or plant slug", status=status.HTTP_400_BAD_REQUEST)
                try:
                    try:
                        user_role = user.role.role
                    except Exception as exception:
                        logger.debug(str(exception))
                        return Response("Role is not set for the user. Please set role of the user first.")
                    if str(user_role).upper().startswith("CLIENT"):
                        admin = False
                    else:
                        admin = True
                    organization_user = OrganizationUser.objects.create(user=user,
                                                                        organization=plant,
                                                                        is_admin=admin)
                    organization_user.save()
                    return Response("User added to the plant successfully.", status=status.HTTP_201_CREATED)
                except Exception as exception:
                    logger.debug(str(exception))
                    return Response("This user is already added to this plant", status=status.HTTP_400_BAD_REQUEST)
            else:
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as exception:
            logger.debug(str(exception))
            return Response("INTERNAL_SERVER_ERROR", status=status.HTTP_500_INTERNAL_SERVER_ERROR)


    def list(self, request):
        try:
            try:
                profile_data = self.get_profile_data()
                solar_plants = filter_solar_plants(profile_data)
                response_data= {}
                for plant in solar_plants:
                    user_array = []
                    organization_users = plant.organization_users.all()
                    for organization_user in organization_users:
                        user = organization_user.user
                        user_dict = {}
                        user_dict["organization_user_id"] = organization_user.id
                        user_dict["user_name"] = user.username
                        user_dict["email"] = user.email
                        user_dict["first_name"] = user.first_name
                        user_dict["last_name"] = user.last_name
                        try:
                            user_dict["role"] = user.role.role
                        except:
                            user_dict["role"] = None
                        user_array.append(user_dict)
                    response_data[str(plant.slug)] = user_array
                return Response(data=response_data, status=status.HTTP_200_OK)
            except Exception as exception:
                logger.debug(str(exception))
                return Response("You do not have access rights to view the users.", status=status.HTTP_403_FORBIDDEN)
        except Exception as exception:
            logger.debug(str(exception))
            return Response("INTERNAL_SERVER_ERROR", status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def destroy(self, request, id=None):
        try:
            try:
                organization_user = OrganizationUser.objects.get(id=id)
            except Exception as exception:
                logger.debug(str(exception))
                return Response("Invalid Organization User Id", status=status.HTTP_400_BAD_REQUEST)
            try:
                organization_user.delete()
            except Exception as exception:
                logger.debug(str(exception))
                return Response("User's access removed from the plant successfully.", status=status.HTTP_403_FORBIDDEN)
            return Response("User removed from the plant successfully", status=status.HTTP_202_ACCEPTED)

        except Exception as exception:
            logger.debug(str(exception))
            return Response("INTERNAL_SERVER_ERROR", status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class DataGlenObtainAuthToken(APIView):
    throttle_classes = ()
    permission_classes = ()
    parser_classes = (parsers.FormParser, parsers.MultiPartParser, parsers.JSONParser,)
    renderer_classes = (renderers.JSONRenderer,)
    serializer_class = AuthTokenSerializer

    def post(self, request, *args, **kwargs):
        try:
            serializer = self.serializer_class(data=request.data)
            serializer.is_valid(raise_exception=True)
            user = serializer.validated_data['user']
            token, created = Token.objects.get_or_create(user=user)
            # add the role
            try:
                user_role = str(user.role.role)
                viewOnly = user.role.viewOnly
                # allow user to edit user,plant preferences
                preference_flag = user.role.enable_preference_edit
                suspended_flag = user.role.account_suspended
            except:
                user_role = "CLIENT_SITE_ENGINEER"
                viewOnly = False
            # suspend user account
            if suspended_flag:
                return Response("Not Authorized!", status=status.HTTP_401_UNAUTHORIZED)
            #update last login of user
            update_last_login(None, user)
            # dgclient id
            client = user.role.dg_client_id
            return Response({'token': token.key, 'role':user_role, 'id':user.id, 'viewOnly':viewOnly,
                             'admin':preference_flag, 'client':client})
        except Exception as exception:
            logger.debug(str(exception))
            return Response("INTERNAL_SERVER_ERROR", status=status.HTTP_500_INTERNAL_SERVER_ERROR)



class RoleMatrixView(viewsets.ViewSet):
    authentication_classes = (authentication.TokenAuthentication, authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def list(self, request):
        try:
            result = {}
            user = self.request.user
            try:
                dg_client = user.role.dg_client
            except:
                return Response("Logged in user has no role assigned", status=status.HTTP_400_BAD_REQUEST)

            user_role = self.request.query_params.get("role", None)
            if user_role == None:
                return Response("Please specify the role to view role matrix", status=status.HTTP_400_BAD_REQUEST)
            try:
                client_subscription = dg_client.subscription.all()[0]
                subscription_plan = client_subscription.subscription_plan
                subscription_plan_features = subscription_plan.features.all()
            except:
                return Response("Client has not subscribed to any of the plans.", status=status.HTTP_400_BAD_REQUEST)

            try:
                role_access = RoleAccess.objects.get(dg_client=dg_client, role=user_role)
                role_access_features = role_access.features.all()
            except:
                return Response("Invalid role or No access has been given to this role", status=status.HTTP_400_BAD_REQUEST)

            unsubscribed_features = []
            enabled_features = []
            disabled_features = []
            if str(subscription_plan.name) is not'PREMIUM':
                premium_subscription = SubscriptionPlan.objects.get(name='PREMIUM')
                premium_features = premium_subscription.features.all()
                for feature in premium_features:
                    if feature not in subscription_plan_features:
                        unsubscribed_features.append(str(feature.name))
            for feature in role_access_features:
                enabled_features.append(str(feature.name))
            for feature in subscription_plan_features:
                if feature not in role_access_features:
                    disabled_features.append(str(feature.name))
            result['unsubscribed_features'] = unsubscribed_features
            result['enabled_features'] = enabled_features
            result['disabled_features']= disabled_features
            return Response(data=result, status=status.HTTP_200_OK)
        except Exception as exception:
            logger.debug(str(exception))
            return Response("INTERVAL_SERVER_ERROR", status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def create(self, request):
        try:
            user = self.request.user
            data = self.request.data
            try:
                dg_client = user.role.dg_client
            except:
                return Response("Logged in user has no role assigned", status=status.HTTP_400_BAD_REQUEST)

            role = self.request.query_params.get("role", None)
            if role == None:
                return Response("Please specify the role to view role matrix", status=status.HTTP_400_BAD_REQUEST)
            for key in data.keys():
                try:
                    feature = Feature.objects.get(name=key)
                except:
                    return Response("Invalid feature name - " + str(key), status=status.HTTP_400_BAD_REQUEST)

            try:
                role_access = RoleAccess.objects.get(dg_client=dg_client, role=role)
            except Exception as exception:
                logger.debug(str(exception))
                return Response("Invalid Role", status=status.HTTP_400_BAD_REQUEST)

            for key in data.keys():
                feature = Feature.objects.get(name=key)
                logger.debug(key)
                if int(data[key]) == 1:
                    role_access.features.add(feature)
                elif int(data[key]) == 0:
                    role_access.features.remove(feature)
                else:
                    pass
            return Response("Features updated successfully", status=status.HTTP_201_CREATED)
        except Exception as exception:
            logger.debug(str(exception))
            return Response("INTERVAL_SERVER_ERROR", status=status.HTTP_500_INTERNAL_SERVER_ERROR)
