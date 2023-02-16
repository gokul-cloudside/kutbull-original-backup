from organizations.models import OrganizationOwner
from django.contrib.auth.models import User
from .models import DataglenClient, DataglenGroup
from organizations.utils import create_organization
from organizations.models import OrganizationUser
from django.db import IntegrityError
from django.http import HttpResponseServerError, HttpResponseBadRequest
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from kutbill import settings
from organizations.backends import invitation_backend
from django.contrib.sites.models import Site


"""def filter_owned_orgs(user, attr):
    filtered_list = []
    org_user_instances = user.organizations_organizationuser.all()
    owners = OrganizationOwner.objects.all()
    for owner in owners:
        if owner.organization_user in org_user_instances and hasattr(owner.organization, attr):
            filtered_list.append(owner.organization)
        else:
            continue
    return filtered_list"""


def filter_owned_orgs(user, attr):
    """
    modified above function to reduce the query of mysql
    :param user:
    :param attr:
    :return:
    """
    filtered_list = []
    org_user_instances = user.organizations_organizationuser.all().values_list('id', flat=True)
    owners = OrganizationOwner.objects.filter(organization_user_id__in=org_user_instances)
    for owner in owners:
        if hasattr(owner.organization, attr):
            filtered_list.append(owner.organization)
        else:
            continue
    return filtered_list


def filter_memberships(user, attr):
    filtered_list = []
    org_instances = user.organizations_organization.all()
    for org in org_instances:
        try:
            if hasattr(org, attr):
                filtered_list.append(org)
        except:
            pass
    return filtered_list


def is_owner(user):
    try:
        owned_client = filter_owned_orgs(user, 'dataglenclient')
        assert(len(owned_client) == 1)
        return True, owned_client[0]
    except AssertionError:
        return False, None


def is_employee(user):
    try:
        member_client = filter_memberships(user, 'dataglenclient')
        assert(len(member_client) == 1)
        return True, member_client[0]
    except AssertionError:
        return False, None


def is_member(user):
    try:
        member_groups = filter_memberships(user, 'dataglengroup')
        #assert(len(member_group) == 1)
        return True, member_groups
    except AssertionError:
        return False, None

def validate_groups(orgs):
    try:
        dataglen_groups = []
        dataglen_client = orgs[0].dataglengroup.get_client()
        for org in orgs:
            assert(org.dataglengroup.get_client() == dataglen_client)
            dataglen_groups.append(org.dataglengroup)
        return True, dataglen_client, dataglen_groups
    except :
        return False, None

def get_owned_group_details(dataglengroups):
    members = []
    for grp in dataglengroups:
        grp_details = {}
        grp_details['instance'] = grp
        grp_details['members'] = grp.get_members()
        grp_details['sensors'] = grp.get_sensors()
        members.append(grp_details)
    return members


def get_owned_group_and_solar_details(dataglengroups):
    solar_plants = []
    try:
        for group in dataglengroups:
            try:
                solar_plant = group.solarplant
                solar_plants.append(solar_plant)
            except:
                continue
        return solar_plants
    except KeyError:
        return solar_plants

# Not to be used directly
def create_dataglen_group_internal(dataglen_client, owner, name, is_active, sensors):
    try:
        org_kwargs = {'org_model': DataglenGroup}
        org_defaults = {'groupClient': dataglen_client}
        dataglen_group = create_organization(user=owner, name=name,
                                             is_active=is_active,
                                             org_defaults=org_defaults, **org_kwargs)
        # since there's a dataglen_group instance now, we can save many to many relations as well
        for sensor in sensors:
            dataglen_group.groupSensors.add(sensor)
        dataglen_group.save()
        return dataglen_group
    except Exception as exc:
        raise Exception(settings.INTERNAL_ERRORS.INTERNAL_UNKNOWN_ERROR.description + str(exc))


'''
    Functions for managing DataglenGroups and Users
'''


def create_a_group(client_name, owner_email, group_name, is_active, sensors):
    try:
        dataglen_client = DataglenClient.objects.get(name=client_name)
        owner = User.objects.get(email__iexact=owner_email)
        return create_dataglen_group_internal(dataglen_client, owner, group_name, is_active, sensors)
    except DataglenClient.DoesNotExist:
        raise ObjectDoesNotExist(settings.INTERNAL_ERRORS.DATAGLEN_CLIENT_DOES_NOT_EXIST.description)
    except User.DoesNotExist:
        raise ObjectDoesNotExist(settings.INTERNAL_ERRORS.DATAGLEN_USER_DOES_NOT_EXIST.description)


def delete_a_group(group_name):
    try:
        group = DataglenGroup.objects.get(name=group_name)
        group.delete()
    except DataglenGroup.DoesNotExist:
        return ObjectDoesNotExist(settings.INTERNAL_ERRORS.DATAGLEN_GROUP_DOES_NOT_EXIST.description)


def add_a_sensor(group_name,
                 sensor):
    # get a group first
    try:
        group = DataglenGroup.objects.get(name=group_name)
        group.groupSensors.add(sensor)
        return True
    except DataglenGroup.DoesNotExist:
        raise Exception(settings.INTERNAL_ERRORS.DATAGLEN_GROUP_DOES_NOT_EXIST.description)
    except :
        raise Exception(settings.INTERNAL_ERRORS.INTERNAL_UNKNOWN_ERROR.description)


def remove_a_sensor(group_name,
                    sensor):
    # get a group first
    try:
        group = DataglenGroup.objects.get(name=group_name)
        group.groupSensors.remove(sensor)
        return True
    except DataglenGroup.DoesNotExist:
        raise Exception(settings.INTERNAL_ERRORS.DATAGLEN_GROUP_DOES_NOT_EXIST.description)
    except Exception as exc:
        raise Exception(settings.INTERNAL_ERRORS.INTERNAL_UNKNOWN_ERROR.description + str(exc))


def add_a_member(group_name, user_email, is_admin):
    # get a group first
    try:
        group = DataglenGroup.objects.get(name=group_name)
    except DataglenGroup.DoesNotExist:
        raise Exception(settings.INTERNAL_ERRORS.DATAGLEN_GROUP_DOES_NOT_EXIST.description)

    # invite or add a user if needed
    try:
        user = User.objects.get(email__iexact=user_email)
    except User.MultipleObjectsReturned:
        raise ValidationError("This email address has been used multiple times.")
    except User.DoesNotExist:
        # we're using django organization's invitation backend itself
        user = invitation_backend().invite_by_email(user_email,
                                                    **{'domain': Site.objects.get_current(),
                                                       'organization': group.organization_ptr,
                                                       'sender': group.owner.organization_user.user})
    return OrganizationUser.objects.create(user=user,
                                           organization=group,
                                           is_admin=is_admin)


def remove_a_member(group_name, user_email):
    # get a group first
    try:
        group = DataglenGroup.objects.get(name=group_name)
        user = User.objects.get(email__iexact=user_email)
        return group.remove_user(user)
    except DataglenGroup.DoesNotExist:
        raise Exception(settings.INTERNAL_ERRORS.DATAGLEN_GROUP_DOES_NOT_EXIST.description)
    except User.DoesNotExist:
        raise Exception(settings.INTERNAL_ERRORS.DATAGLEN_USER_DOES_NOT_EXIST)