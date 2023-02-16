from django.test import Client
from django.test import TestCase
import requests
import random

from django.conf import settings

BASE_URL = "http://127.0.0.1"

class TestSensorGETAPIs(TestCase):
    SENSORS_URL = BASE_URL + "/dataglen/sensors/"

    # check authentication for GET
    def test_missing_token(self):
        # miss a token
        response = requests.get(self.SENSORS_URL)
        assert(response.status_code == 401)

    def test_invalid_token(self):
        # provide an invalid token
        response = requests.get(self.SENSORS_URL,
                                headers = {'Authorization': 'Token invalidTokenKey'})
        assert(response.status_code == 401)

    # test variations of GET call
    def test_get_all(self):
        # successful request
        response = requests.get(self.SENSORS_URL,
                                headers = {'Authorization': 'Token c81b99751ea730d84dfa8c92be7a9a41a52e90cc'})
        assert(len(response.json()) >= 1)
        assert(response.status_code == 200)

    def test_get_valid_key(self):
        # provide a valid key
        response = requests.get(self.SENSORS_URL,
                                headers = {'Authorization': 'Token c81b99751ea730d84dfa8c92be7a9a41a52e90cc'},
                                params = {'sourceKey': '54WdKMmULZ2xFgY'})
        assert(len(response.json()) == 12)
        assert(response.status_code == 200)

    def test_get_invalid_key(self):
        # mention an invalid key
        response = requests.get(self.SENSORS_URL,
                                headers = {'Authorization': 'Token c81b99751ea730d84dfa8c92be7a9a41a52e90cc'},
                                params = {'sourceKey': 'invalidSourceKey'})
        assert(response.status_code == settings.ERRORS.INVALID_SOURCE_KEY.code)
        assert(response.json()['error'] == settings.ERRORS.INVALID_SOURCE_KEY.description)

class TestSensorPOSTAPIs(TestCase):
    SENSORS_URL = BASE_URL + "/dataglen/sensors/"
    KEY = ''
    # check authentication for GET
    def test_missing_token(self):
        # miss a token
        response = requests.post(self.SENSORS_URL)
        assert(response.status_code == 401)

    def test_invalid_token(self):
        # provide an invalid token
        response = requests.post(self.SENSORS_URL,
                                headers = {'Authorization': 'Token invalidTokenKey'})
        assert(response.status_code == 401)

    def test_valid_data(self):
        response = requests.post(self.SENSORS_URL,
                                 headers = {'Authorization': 'Token c81b99751ea730d84dfa8c92be7a9a41a52e90cc'},
                                 data = {'name': str(random.random()),
                                         'dataFormat': 'CSV'
                                        })
        assert(response.status_code == 201)
        assert(len(response.json()) == 12)
        self.KEY = response.json()['sourceKey']

    def test_invalid_data(self):
        # same name
        response = requests.post(self.SENSORS_URL,
                                 headers={'Authorization': 'Token c81b99751ea730d84dfa8c92be7a9a41a52e90cc'},
                                 data={'name': 'useless_name',
                                      })
        assert(response.status_code == 400)
        assert(response.json()['sourceKey'] == self.KEY)


    def test_delete_sensor(self):
        print self.KEY
        response = requests.delete(self.SENSORS_URL,
                                   headers = {'Authorization': 'Token c81b99751ea730d84dfa8c92be7a9a41a52e90cc'},
                                   data = {'sourceKey': self.KEY})
        print response.content
        assert(response.status_code == 204)