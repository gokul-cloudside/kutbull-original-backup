from features.models import Feature, SubscriptionPlan, DGClientSubscription, RoleAccess
from features.models import SOLAR_USER_ROLE
from features.setup_features import SUBSCRIPTION_PLANS
from django.core.mail import send_mail

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
        print ra
        if role[0].startswith("CLIENT"):
            for feature in Feature.objects.filter(name__in=SUBSCRIPTION_PLANS['BASIC']):
                ra.features.add(feature)
                print feature

        else:
            for feature in Feature.objects.all():
                ra.features.add(feature)


def send_email(plant, desc, plant_meta_source_name, plant_meta_source_key):
    """

    :param plant:
    :param desc:
    :param plant_meta_source_key:
    :return:
    """
    email = ['narsing@dataglen.com',
             'sunilkrghai@dataglen.com']
    subject = 'New Plant Created : ' + str(plant.slug)
    description = str(
        desc) + '\n\nA new Plant has been created on dataglen.com with following details \n\nPlant Name ' \
                  + str(plant.name) + '\n' + 'Plant Slug: ' + str(plant.slug) + '\n\n' + "\n\nPlant Meta Source Details:\n" + str(plant_meta_source_name) + " : " + str(plant_meta_source_key) +\
                  '\n\n\n' + 'Best Wishes,\n' + 'Team Dataglen'
    send_mail(subject, description, 'admin@dataglen.com', email, fail_silently=False)
    print
    "email sent"
