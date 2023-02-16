from django.test import TestCase
from dashboards.models import DataglenClient, DataglenGroup, Dashboard
from dataglen.models import Sensor
from dashboards.utils import create_a_group, delete_a_group, add_a_sensor, remove_a_sensor, \
    add_a_member, remove_a_member
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist

class NewGroupTestCase(TestCase):
    user = None
    user_name = "TEST USER"
    user_email = "admin@dataglen.com"

    sensor1 = None
    sensor1_name = "TEST SENSOR 1"
    sensor2 = None
    sensor2_name = "TEST SENSOR 2"
    member_email = "sunilkrghai@gmail.com"

    dashboard = None
    dashboard_name = "DATAGLEN"

    dataglenclient = None
    dataglenclient_name = "TEST CLIENT"

    dataglengroup = None
    dataglengroup_name = "TEST GROUP"

    def setUp(self):
        # create a test user, sensor(s), dashboard, and a client
        self.user = User.objects.create(username=self.user_name, email=self.user_email)

        self.dashboard = Dashboard.objects.create(name=self.dashboard_name, slug="dataglen", active=True,
                                                  allowGroups=True, ownerViewURL="dataglen:index",
                                                  employeeViewURL="dataglen:index", groupViewURL="dataglen:index")

        self.dataglenclient = DataglenClient.objects.create(name=self.dataglenclient_name,
                                                            slug="test-client", clientWebsite="http://radiostudio.co.in",
                                                            clientDashboard=self.dashboard)

        self.sensor1 = Sensor.objects.create(name=self.sensor1_name, user=self.user,
                                             dataFormat="CSV", timeoutInterval=60)
        self.sensor2 = Sensor.objects.create(name=self.sensor2_name, user=self.user,
                                             dataFormat="JSON", timeoutInterval=60)

    def test_new_group_with_invalid_owner_email(self):
        try:
            group = create_a_group(self.dataglenclient_name, 'invalid@dataglen.com',
                                   self.dataglengroup_name, True, [self.sensor1])
        except ObjectDoesNotExist:
            pass

    def test_new_group_addition_and_deletion(self):
        assert(len(self.dataglenclient.get_groups()) == 0)
        self.dataglengroup = create_a_group(self.dataglenclient_name, self.user_email,
                                            self.dataglengroup_name, True, [self.sensor1])
        assert(len(self.dataglenclient.get_groups()) == 1)
        delete_a_group(self.dataglengroup_name)
        self.dataglengroup = None
        assert(len(self.dataglenclient.get_groups()) == 0)

    def test_sensor_addition_and_deletion(self):
        self.dataglengroup = create_a_group(self.dataglenclient_name, self.user_email,
                                            self.dataglengroup_name, True, [self.sensor1])
        assert(len(self.dataglengroup.get_sensors()) == 1)
        add_a_sensor(self.dataglengroup_name, self.sensor2)
        assert(len(self.dataglengroup.get_sensors()) == 2)
        remove_a_sensor(self.dataglengroup_name, self.sensor2)
        assert(len(self.dataglengroup.get_sensors()) == 1)
        delete_a_group(self.dataglengroup_name)
        self.dataglengroup = None

    # TODO : Fix this test case 
    '''
    def test_inviting_member_and_deletion(self):
        self.dataglengroup = create_a_group(self.dataglenclient_name, self.user_email,
                                            self.dataglengroup_name, True,  [self.sensor1])
        assert(len(self.dataglengroup.get_members()) == 1)
        # owner is always a member
        organization_user = add_a_member(self.dataglengroup_name, self.member_email, True)
        # also check if the email is received
        assert(len(self.dataglengroup.get_members()) == 2)
        remove_a_member(self.dataglengroup_name, self.member_email)
        assert(len(self.dataglengroup.get_members()) == 1)
    '''
