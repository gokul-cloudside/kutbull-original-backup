from django.test import TestCase
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework import permissions
from rest_framework.authentication import TokenAuthentication
from rest_framework.test import APIRequestFactory
from django.core.urlresolvers import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.test import Client
import unittest
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient
import json


class SensorListTest(unittest.TestCase):
    def setUp(self):
        self.user = User.objects.create_user('nishant@dataglen.com', 'nishant@dataglen.com', 'nishant')
        self.user.save()
        self.token = Token.objects.get(user=self.user).key
        self.data = { "name": "nishant-test","dataFormat": "JSON","dataReportingInterval": 0,"textMessageWithHTTP200": "string","textMessageWithError": "string","isActive": True,"isMonitored": True,"csvDataKeyName": "string","timeoutInterval": 0,"dataTimezone": "Africa/Abidjan" }
        self.auth_header = {'HTTP_AUTHORIZATION': 'Token {}'.format(self.token)}
        self.client = Client()
        self.token_improper = self.token + '1!2@3#'
        self.auth_header_improper = {'HTTP_AUTHORIZATION': 'Token {}'.format(self.token_improper)}

    def tearDown(self):
        self.user.delete()
        self.client = None

    def test_source_get_authenticated(self):
        c = Client()
        response = c.get('/api/sources/', {}, **self.auth_header)
        self.assertEqual(response.status_code, 200)

    def test_source_get_unauthenticated(self):
        c = Client()
        response = c.get('/api/sources/')
        self.assertEqual(response.status_code, 401)

    def test_source_get_token_improper(self):
        c = Client()
        response = c.get('/api/sources/', {}, **self.auth_header_improper)
        self.assertEqual(response.status_code, 401)

    def test_source_post_authenticated(self):
        c = Client()
        response = c.post('/api/sources/', {"name": "nishant-test",
                                            "dataFormat": "CSV",
                                            "dataReportingInterval": 0,
                                            "isActive": True,
                                            "isMonitored": True,
                                            "timeoutInterval": 0,
                                            "dataTimezone": "Africa/Abidjan"},
                          **self.auth_header)
        self.assertEqual(response.status_code, 201)

    def test_source_post_authenticated_json(self):
        c = Client()
        response = c.post('/api/sources/', {"name": "nishant-test",
                                            "dataFormat": "JSON",
                                            "dataReportingInterval": 0,
                                            "isActive": True,
                                            "isMonitored": True,
                                            "timeoutInterval": 0,
                                            "dataTimezone": "Africa/Abidjan" }, 
                          **self.auth_header)
        self.assertEqual(response.status_code, 201)

    def test_source_post_authenticated_improper_dataFormat(self):
        c = Client()
        response = c.post('/api/sources/', {"name": "nishant-test",
                                            "dataFormat": "CS",
                                            "dataReportingInterval": 0,
                                            "isActive": True,
                                            "isMonitored": True,
                                            "timeoutInterval": 0,
                                            "dataTimezone": "Africa/Abidjan"}, 
                          **self.auth_header)
        self.assertEqual(response.status_code, 400)

    def test_source_post_duplicate_source(self):
        c = Client()
        response_initial = c.post('/api/sources/', {"name": "nishant-test",
                                                    "dataFormat": "CSV",
                                                    "dataReportingInterval": 0,
                                                    "isActive": True,
                                                    "isMonitored": True,
                                                    "timeoutInterval": 0,
                                                    "dataTimezone": "Africa/Abidjan" }, 
                                 **self.auth_header)
        response_final = c.post('/api/sources/', {"name": "nishant-test",
                                                  "dataFormat": "CSV",
                                                  "dataReportingInterval": 0,
                                                  "isActive": True,
                                                  "isMonitored": True,
                                                  "timeoutInterval": 0,
                                                  "dataTimezone": "Africa/Abidjan" }, 
                                **self.auth_header)
        self.assertEqual(response_final.status_code, 409)

    def test_source_post_unauthenticated(self):
        c = Client()
        response = c.post('/api/sources/', {"name": "nishant-test",
                                            "dataFormat": "CSV",
                                            "dataReportingInterval": 0,
                                            "isActive": True,
                                            "isMonitored": True,
                                            "timeoutInterval": 0,
                                            "dataTimezone": "Africa/Abidjan" })
        self.assertEqual(response.status_code, 401)

    def test_source_post_token_improper(self):
        c = Client()
        response = c.post('/api/sources/', {"name": "nishant-test",
                                            "dataFormat": "CSV",
                                            "dataReportingInterval": 0,
                                            "isActive": True,
                                            "isMonitored": True,
                                            "timeoutInterval": 0,
                                            "dataTimezone": "Africa/Abidjan" }, 
                         **self.auth_header_improper)
        self.assertEqual(response.status_code, 401)

    def test_source_post_authenticated_mandatory_not_given(self):
        c = Client()
        response = c.post('/api/sources/', {"dataFormat": "CSV",
                                            "dataReportingInterval": 0,
                                            "isActive": True,
                                            "isMonitored": True,
                                            "timeoutInterval": 0,
                                            "dataTimezone": "Africa/Abidjan" }, 
                          **self.auth_header)
        self.assertEqual(response.status_code, 400)

    def test_source_delete_authenticated(self):
        c = Client()
        response_post = c.post('/api/sources/', {"name": "nishant-test",
                                                 "dataFormat": "CSV",
                                                 "dataReportingInterval": 0,
                                                 "isActive": True,
                                                 "isMonitored": True,
                                                 "timeoutInterval": 0,
                                                 "dataTimezone": "Africa/Abidjan" }, 
                              **self.auth_header)
        resp_dict = json.loads(response_post.content)
        if('sourceKey' in resp_dict):
            key = resp_dict['sourceKey']
        else:
            print('No Source key found in response')
        url = '/api/sources/' + key + '/'
        response = c.delete(url, {}, **self.auth_header)
        self.assertEqual(response_post.status_code, 201)
        self.assertEqual(response.status_code, 204)

    def test_source_delete_unauthenticated(self):
        c = Client()
        response_post = c.post('/api/sources/', {"name": "nishant-test",
                                                 "dataFormat": "CSV",
                                                 "dataReportingInterval": 0,
                                                 "isActive": True,
                                                 "isMonitored": True,
                                                 "timeoutInterval": 0,
                                                 "dataTimezone": "Africa/Abidjan" }, 
                              **self.auth_header)
        resp_dict = json.loads(response_post.content)
        if('sourceKey' in resp_dict):
            key = resp_dict['sourceKey']
        else:
            print('No Source key found in response')
        url = '/api/sources/' + key + '/'
        response = c.delete(url, {})
        self.assertEqual(response_post.status_code, 201)
        self.assertEqual(response.status_code, 401)

    def test_source_delete_unauthenticated_token_improper(self):
        c = Client()
        response_post = c.post('/api/sources/', {"name": "nishant-test",
                                                 "dataFormat": "CSV",
                                                 "dataReportingInterval": 0,
                                                 "isActive": True,
                                                 "isMonitored": True,
                                                 "timeoutInterval": 0,
                                                 "dataTimezone": "Africa/Abidjan" },
                              **self.auth_header)
        resp_dict = json.loads(response_post.content)
        if('sourceKey' in resp_dict):
            key = resp_dict['sourceKey']
        else:
            print('No Source key found in response')
        url = '/api/sources/' + key + '/'
        response = c.delete(url, {}, **self.auth_header_improper)
        self.assertEqual(response_post.status_code, 201)
        self.assertEqual(response.status_code, 401)

    def test_source_delete_authenticated_sourceKey_improper(self):
        c = Client()
        response_post = c.post('/api/sources/', {"name": "nishant-test",
                                                "dataFormat": "CSV",
                                                "dataReportingInterval": 0,
                                                "isActive": True,
                                                "isMonitored": True,
                                                "timeoutInterval": 0,
                                                "dataTimezone": "Africa/Abidjan" },
                              **self.auth_header)
        resp_dict = json.loads(response_post.content)
        if('sourceKey' in resp_dict):
            key = resp_dict['sourceKey']
        else:
            print('No Source key found in response')
        key_improper = key + 'xsdgffdhg'
        url = '/api/sources/' + key_improper + '/'
        response = c.delete(url, {}, **self.auth_header)
        self.assertEqual(response_post.status_code, 201)
        self.assertEqual(response.status_code, 400)

    def test_source_get_mentioned_key_authenticated(self):
        c = Client()
        response_post = c.post('/api/sources/', {"name": "nishant-test",
                                                 "dataFormat": "CSV",
                                                 "dataReportingInterval": 0,
                                                 "isActive": True,
                                                 "isMonitored": True,
                                                 "timeoutInterval": 0,
                                                 "dataTimezone": "Africa/Abidjan" },
                              **self.auth_header)
        resp_dict = json.loads(response_post.content)
        if('sourceKey' in resp_dict):
            key = resp_dict['sourceKey']
        else:
            print('No Source key found in response')
        url = '/api/sources/' + key + '/'
        response = c.get(url, {}, **self.auth_header)
        self.assertEqual(response_post.status_code, 201)
        self.assertEqual(response.status_code, 200)

    def test_source_get_mentioned_key_unauthenticated(self):
        c = Client()
        response_post = c.post('/api/sources/', {"name": "nishant-test",
                                                 "dataFormat": "CSV",
                                                 "dataReportingInterval": 0,
                                                 "isActive": True,
                                                 "isMonitored": True,
                                                 "timeoutInterval": 0,
                                                 "dataTimezone": "Africa/Abidjan" }, 
                               **self.auth_header)
        resp_dict = json.loads(response_post.content)
        if('sourceKey' in resp_dict):
            key = resp_dict['sourceKey']
        else:
            print('No Source key found in response')
        url = '/api/sources/' + key + '/'
        response = c.get(url, {})
        self.assertEqual(response_post.status_code, 201)
        self.assertEqual(response.status_code, 401)

    def test_source_get_mentioned_key_unauthenticated_token_improper(self):
        c = Client()
        response_post = c.post('/api/sources/', {"name": "nishant-test",
                                                 "dataFormat": "CSV",
                                                 "dataReportingInterval": 0,
                                                 "isActive": True,
                                                 "isMonitored": True,
                                                 "timeoutInterval": 0,
                                                 "dataTimezone": "Africa/Abidjan" }, 
                              **self.auth_header)
        resp_dict = json.loads(response_post.content)
        if('sourceKey' in resp_dict):
            key = resp_dict['sourceKey']
        else:
            print('No Source key found in response')
        url = '/api/sources/' + key + '/'
        response = c.get(url, {}, **self.auth_header_improper)
        self.assertEqual(response_post.status_code, 201)
        self.assertEqual(response.status_code, 401)

    def test_source_get_mentioned_key_authenticated_sourceKey_improper(self):
        c = Client()
        response_post = c.post('/api/sources/', {"name": "nishant-test",
                                                 "dataFormat": "CSV",
                                                 "dataReportingInterval": 0,
                                                 "isActive": True,
                                                 "isMonitored": True,
                                                 "timeoutInterval": 0,
                                                 "dataTimezone": "Africa/Abidjan" }, 
                              **self.auth_header)
        resp_dict = json.loads(response_post.content)
        if('sourceKey' in resp_dict):
            key = resp_dict['sourceKey']
        else:
            print('No Source key found in response')
        key_improper = key + 'afdgf'
        url = '/api/sources/' + key_improper +  '/'
        response = c.get(url, {}, **self.auth_header)
        self.assertEqual(response_post.status_code, 201)
        self.assertEqual(response.status_code, 400)

    def test_source_update_unauthenticated(self):
        c = Client()
        response_post = c.post('/api/sources/', {"name": "nishant-test",
                                                 "dataFormat": "CSV",
                                                 "dataReportingInterval": 0,
                                                 "isActive": True,
                                                 "isMonitored": True,
                                                 "timeoutInterval": 0,
                                                 "dataTimezone": "Africa/Abidjan" },
                              **self.auth_header)
        resp_dict = json.loads(response_post.content)
        if('sourceKey' in resp_dict):
            key = resp_dict['sourceKey']
        else:
            print('No Source key found in response')
        url = '/api/sources/' + key + '/'
        response = c.patch(url, {"name": "nishant-test",
                                 "dataFormat": "CSV",
                                 "dataReportingInterval": 0,
                                 "isActive": True,
                                 "isMonitored": True,
                                 "timeoutInterval": 0,
                                 "dataTimezone": "Africa/Abidjan" })
        self.assertEqual(response_post.status_code, 201)
        self.assertEqual(response.status_code, 401)

    def test_source_update_unauthenticated_token_improper(self):
        c = Client()
        response_post = c.post('/api/sources/', {"name": "nishant-test",
                                                 "dataFormat": "CSV",
                                                 "dataReportingInterval": 0,
                                                 "isActive": True,
                                                 "isMonitored": True,
                                                 "timeoutInterval": 0,
                                                 "dataTimezone": "Africa/Abidjan" },
                              **self.auth_header)
        resp_dict = json.loads(response_post.content)
        if('sourceKey' in resp_dict):
            key = resp_dict['sourceKey']
        else:
            print('No Source key found in response')
        url = '/api/sources/' + key + '/'
        response = c.patch(url, {"name": "nishant-test",
                                 "dataFormat": "JSON",
                                 "dataReportingInterval": 0,
                                 "isActive": True,
                                 "isMonitored": True,
                                 "timeoutInterval": 0,
                                 "dataTimezone": "Africa/Abidjan" },
                          **self.auth_header_improper)
        self.assertEqual(response_post.status_code, 201)
        self.assertEqual(response.status_code, 401)

    def test_source_update_authenticated_sourceKey_improper(self):
        c = Client()
        response_post = c.post('/api/sources/', {"name": "nishant-test",
                                                 "dataFormat": "CSV",
                                                 "dataReportingInterval": 0,
                                                 "isActive": True,
                                                 "isMonitored": True,
                                                 "timeoutInterval": 0,
                                                 "dataTimezone": "Africa/Abidjan" },
                              **self.auth_header)
        resp_dict = json.loads(response_post.content)
        if('sourceKey' in resp_dict):
            key = resp_dict['sourceKey']
        else:
            print('No Source key found in response')
        key_improper = key + 'sbcgnc'
        url = '/api/sources/' + key_improper + '/'
        response = c.patch(url, {"name": "nishant-test",
                                 "dataFormat": "JSON",
                                 "dataReportingInterval": 0,
                                 "isActive": True,
                                 "isMonitored": True,
                                 "timeoutInterval": 0,
                                 "dataTimezone": "Africa/Abidjan" },
                          **self.auth_header)
        self.assertEqual(response_post.status_code, 201)
        self.assertEqual(response.status_code, 400)

    """
    def test_source_update_authenticated_body_empty(self):
        c = Client()
        response_post = c.post('/api/sources/', {"name": "nishant-test",
                                                 "dataFormat": "XML",
                                                 "dataReportingInterval": 0,
                                                 "isActive": True,
                                                 "isMonitored": True,
                                                 "timeoutInterval": 0,
                                                 "dataTimezone": "Africa/Abidjan" },
                              **self.auth_header)
        resp_dict = json.loads(response_post.content)
        if('sourceKey' in resp_dict):
            key = resp_dict['sourceKey']
        else:
            print('No Source key found in response')
        print('key: ' + key)
        url = '/api/sources/' + key + '/'
        print('url: ' + url)
        response = c.patch(url, {}, **self.auth_header)
        self.assertEqual(response_post.status_code,201)
        self.assertEqual(response.status_code,201)

    """

    """
    def test_source_update_authenticated(self):
        c = Client()
        response_post = c.post('/api/sources/', {"name": "nishant-test",
                                                 "dataFormat": "CSV",
                                                 "dataReportingInterval": 0,
                                                 "isActive": True,
                                                 "isMonitored": True,
                                                 "timeoutInterval": 0,
                                                 "dataTimezone": "Africa/Abidjan" }, 
                              **self.auth_header)
        resp_dict = json.loads(response_post.content)
        if('sourceKey' in resp_dict):
            key = resp_dict['sourceKey']
        else:
            print('No Source key found in response')
        url = '/api/sources/' + key + '/'
        print(url)
        request_body = {"name": "nishant-test-update",
                        "dataFormat": "CSV",
                        "dataReportingInterval": 0,
                        "isActive": True,
                        "isMonitored": True,
                        "timeoutInterval": 0,
                        "dataTimezone": "Africa/Abidjan" }
        response = c.patch(url, content_type = 'text/plain', data = json.dumps(request_body), **self.auth_header)
        self.assertEqual(response.status_code,201)
    """

    def test_stream_get_authenticated(self):
        c = Client()
        response_post = c.post('/api/sources/', {"name": "nishant-test",
                                                 "dataFormat": "CSV",
                                                 "dataReportingInterval": 0,
                                                 "isActive": True,
                                                 "isMonitored": True,
                                                 "timeoutInterval": 0,
                                                 "dataTimezone": "Africa/Abidjan" }, 
                              **self.auth_header)
        resp_dict = json.loads(response_post.content)
        if('sourceKey' in resp_dict):
            key = resp_dict['sourceKey']
        else:
            print('No Source key found in response')
        url = '/api/sources/' + key + '/streams/'
        response = c.get(url, {}, **self.auth_header)
        self.assertEqual(response_post.status_code, 201)
        self.assertEqual(response.status_code, 200)

    def test_stream_get_unauthenticated(self):
        c = Client()
        response_post = c.post('/api/sources/', {"name": "nishant-test",
                                                 "dataFormat": "CSV",
                                                 "dataReportingInterval": 0,
                                                 "isActive": True,
                                                 "isMonitored": True,
                                                 "timeoutInterval": 0,
                                                 "dataTimezone": "Africa/Abidjan" },
                              **self.auth_header)
        resp_dict = json.loads(response_post.content)
        if('sourceKey' in resp_dict):
            key = resp_dict['sourceKey']
        else:
            print('No Source key found in response')
        url = '/api/sources/' + key + '/streams/'
        response = c.get(url)
        self.assertEqual(response_post.status_code, 201)
        self.assertEqual(response.status_code, 401)

    def test_stream_get_token_improper(self):
        c = Client()
        response_post = c.post('/api/sources/', {"name": "nishant-test",
                                                 "dataFormat": "JSON",
                                                 "dataReportingInterval": 0,
                                                 "isActive": True,
                                                 "isMonitored": True,
                                                 "timeoutInterval": 0,
                                                 "dataTimezone": "Africa/Abidjan" },

                              **self.auth_header)
        resp_dict = json.loads(response_post.content)
        if('sourceKey' in resp_dict):
            key = resp_dict['sourceKey']
        else:
            print('No Source key found in response')
        url = '/api/sources/' + key + '/streams/'
        response = c.get(url, {}, **self.auth_header_improper)
        self.assertEqual(response_post.status_code, 201)
        self.assertEqual(response.status_code, 401)

    def test_stream_get_sourceKey_improper(self):
        c = Client()
        response_post = c.post('/api/sources/', {"name": "nishant-test",
                                                 "dataFormat": "CSV",
                                                 "dataReportingInterval": 0,
                                                 "isActive": True,
                                                 "isMonitored": True,
                                                 "timeoutInterval": 0,
                                                 "dataTimezone": "Africa/Abidjan" },
                              **self.auth_header)
        resp_dict = json.loads(response_post.content)
        if('sourceKey' in resp_dict):
            key = resp_dict['sourceKey']
        else:
            print('No Source key found in response')
        key_improper = key + 'afdgf'
        url = '/api/sources/' + key_improper + '/streams/'
        response = c.get(url, {}, **self.auth_header)
        self.assertEqual(response_post.status_code, 201)
        self.assertEqual(response.status_code, 400)

    def test_stream_create_authenticated(self):
        c = Client()
        response_post = c.post('/api/sources/', {"name": "nishant-test",
                                                 "dataFormat": "CSV",
                                                 "dataReportingInterval": 0,
                                                 "isActive": True,
                                                 "isMonitored": True,
                                                 "timeoutInterval": 0,
                                                 "dataTimezone": "Africa/Abidjan" },
                              **self.auth_header)
        resp_dict = json.loads(response_post.content)
        if('sourceKey' in resp_dict):
            key = resp_dict['sourceKey']
        else:
            print('No Source key found in response')
        url = '/api/sources/' + key + '/streams/'
        response_stream = c.post(url, {"name": "stream1",
                                       "streamDataType": "INTEGER",
                                       "streamDataUnit": "INTEGER",
                                       "streamPositionInCSV": 1 }, 
                                **self.auth_header)
        self.assertEqual(response_post.status_code, 201)
        self.assertEqual(response_stream.status_code, 201)

    def test_stream_create_unauthenticated(self):
        c = Client()
        response_post = c.post('/api/sources/', {"name": "nishant-test",
                                                 "dataFormat": "CSV",
                                                 "dataReportingInterval": 0,
                                                 "isActive": True,
                                                 "isMonitored": True,
                                                 "timeoutInterval": 0,
                                                 "dataTimezone": "Africa/Abidjan" }, 
                              **self.auth_header)
        resp_dict = json.loads(response_post.content)
        if('sourceKey' in resp_dict):
            key = resp_dict['sourceKey']
        else:
            print('No Source key found in response')
        url = '/api/sources/' + key + '/streams/'
        response_stream = c.post(url, {"name": "stream1",
                                       "streamDataType": "INTEGER",
                                       "streamDataUnit": "INTEGER",
                                       "streamPositionInCSV": 1 } )
        self.assertEqual(response_post.status_code, 201)
        self.assertEqual(response_stream.status_code, 401)

    def test_stream_create_unauthenticated_token_improper(self):
        c = Client()
        response_post = c.post('/api/sources/', {"name": "nishant-test",
                                                 "dataFormat": "CSV",
                                                 "dataReportingInterval": 0,
                                                 "isActive": True,
                                                 "isMonitored": True,
                                                 "timeoutInterval": 0,
                                                 "dataTimezone": "Africa/Abidjan" }, 
                              **self.auth_header)
        resp_dict = json.loads(response_post.content)
        if('sourceKey' in resp_dict):
            key = resp_dict['sourceKey']
        else:
            print('No Source key found in response')
        url = '/api/sources/' + key + '/streams/'
        response_stream = c.post(url, {"name": "stream1",
                                       "streamDataType": "INTEGER",
                                       "streamDataUnit": "INTEGER",
                                       "streamPositionInCSV": 1 }, 
                                **self.auth_header_improper)
        self.assertEqual(response_post.status_code, 201)
        self.assertEqual(response_stream.status_code, 401)

    def test_stream_create_duplicate_stream(self):
        c = Client()
        response_post = c.post('/api/sources/', {"name": "nishant-test",
                                                 "dataFormat": "JSON",
                                                 "dataReportingInterval": 0,
                                                 "isActive": True,
                                                 "isMonitored": True,
                                                 "timeoutInterval": 0,
                                                 "dataTimezone": "Africa/Abidjan" },
                              **self.auth_header)
        resp_dict = json.loads(response_post.content)
        if('sourceKey' in resp_dict):
            key = resp_dict['sourceKey']
        else:
            print('No Source key found in response')
        url = '/api/sources/' + key + '/streams/'
        response_stream = c.post(url, {"name": "stream1",
                                       "streamDataType": "INTEGER",
                                       "streamDataUnit": "string",
                                       "streamPositionInCSV": 1 }, 
                                **self.auth_header)
        response_stream_duplicate = c.post(url, {"name": "stream1",
                                                 "streamDataType": "INTEGER",
                                                 "streamDataUnit": "INTEGER",
                                                 "streamPositionInCSV": 1 }, 
                                          **self.auth_header)
        self.assertEqual(response_post.status_code, 201)
        self.assertEqual(response_stream.status_code, 201)
        self.assertEqual(response_stream_duplicate.status_code, 409)

    def test_stream_create_mandatory_field_missing(self):
        c = Client()
        response_post = c.post('/api/sources/', {"name": "nishant-test",
                                                 "dataFormat": "CSV",
                                                 "dataReportingInterval": 0,
                                                 "isActive": True,
                                                 "isMonitored": True,
                                                 "timeoutInterval": 0,
                                                 "dataTimezone": "Africa/Abidjan" },
                              **self.auth_header)
        resp_dict = json.loads(response_post.content)
        if('sourceKey' in resp_dict):
            key = resp_dict['sourceKey']
        else:
            print('No Source key found in response')
        url = '/api/sources/' + key + '/streams/'
        response_stream = c.post(url, {"streamDataType": "INTEGER",
                                       "streamPositionInCSV": 0 },
                                 **self.auth_header)
        self.assertEqual(response_post.status_code, 201)
        self.assertEqual(response_stream.status_code, 400)


    """
    def test_stream_create_json_improper(self):
        c = Client()
        response_post = c.post('/api/sources/', {"name": "nishant-test",
                                                 "dataFormat": "CSV",
                                                 "dataReportingInterval": 0,
                                                 "isActive": True,
                                                 "isMonitored": True,
                                                 "timeoutInterval": 0,
                                                 "dataTimezone": "Africa/Abidjan" }, 
                               **self.auth_header)
        resp_dict = json.loads(response_post.content)
        if('sourceKey' in resp_dict):
            key = resp_dict['sourceKey']
        else:
            print('No Source key found in response')
        url = '/api/sources/' + key + '/streams/'
        request_body = {"name" "stream1",
                        "streamDataType": "INTEGER",
                        "streamDataUnit": "INTEGER"
                        "streamPositionInCSV": 1 }
        response_stream = c.post(url, json.loads(request_body), 
                                 **self.auth_header)
        self.assertEqual(response_post.status_code,201)
        self.assertEqual(response_stream.status_code,500)
    """
    

    def test_stream_delete_authenticated(self):
        c = Client()
        response_post = c.post('/api/sources/', {"name": "nishant-test",
                                                 "dataFormat": "CSV",
                                                 "dataReportingInterval": 0,
                                                 "isActive": True,
                                                 "isMonitored": True,
                                                 "timeoutInterval": 0,
                                                 "dataTimezone": "Africa/Abidjan" },
                              **self.auth_header)
        resp_dict = json.loads(response_post.content)
        if('sourceKey' in resp_dict):
            key = resp_dict['sourceKey']
        else:
            print('No Source key found in response')
        url = '/api/sources/' + key + '/streams/'
        response_stream = c.post(url, {"name": "stream1",
                                       "streamDataType": "INTEGER",
                                       "streamDataUnit": "INTEGER",
                                       "streamPositionInCSV": 1 }, 
                                **self.auth_header)
        resp_dict_stream = json.loads(response_stream.content)
        if('name' in resp_dict_stream):
            stream_name = resp_dict_stream['name']
        else:
            print('No stream found in response')
        url = '/api/sources/' + key + '/streams/' + stream_name + '/'
        response = c.delete(url, {}, **self.auth_header)
        self.assertEqual(response_post.status_code, 201)
        self.assertEqual(response.status_code, 204)


    def test_stream_delete_unautheticated(self):
        c = Client()
        response_post = c.post('/api/sources/', {"name": "nishant-test",
                                                 "dataFormat": "CSV",
                                                 "dataReportingInterval": 10,
                                                 "isActive": True,
                                                 "isMonitored": True,
                                                 "timeoutInterval": 10,
                                                 "dataTimezone": "Africa/Abidjan" },
                              **self.auth_header)
        resp_dict = json.loads(response_post.content)
        if('sourceKey' in resp_dict):
            key = resp_dict['sourceKey']
        else:
            print('No Source key found in response')
        url = '/api/sources/' + key + '/streams/'
        response_stream = c.post(url, {"name": "stream1",
                                       "streamDataType": "INTEGER",
                                       "streamDataUnit": "INTEGER",
                                       "streamPositionInCSV": 1 }, 
                                **self.auth_header)
        resp_dict_stream = json.loads(response_stream.content)
        if('name' in resp_dict_stream):
            stream_name = resp_dict_stream['name']
        else:
            print('No stream found in response')
        url = '/api/sources/' + key + '/streams/' + stream_name + '/'
        response = c.delete(url, {})
        self.assertEqual(response_post.status_code, 201)
        self.assertEqual(response.status_code, 401)

    def test_stream_delete_unautheticated_token_improper(self):
        c = Client()
        response_post = c.post('/api/sources/', {"name": "nishant-test",
                                                 "dataFormat": "CSV",
                                                 "dataReportingInterval": 0,
                                                 "isActive": True,
                                                 "isMonitored": True,
                                                 "csvDataKeyName": "dataKey",
                                                 "timeoutInterval": 0,
                                                 "dataTimezone": "Africa/Abidjan" }, 
                              **self.auth_header)
        resp_dict = json.loads(response_post.content)
        if('sourceKey' in resp_dict):
            key = resp_dict['sourceKey']
        else:
            print('No Source key found in response')
        url = '/api/sources/' + key + '/streams/'
        response_stream = c.post(url, {"name": "stream1",
                                       "streamDataType": "INTEGER",
                                       "streamDataUnit": "INTEGER",
                                       "streamPositionInCSV": 1 },
                                 **self.auth_header)
        resp_dict_stream = json.loads(response_stream.content)
        if('name' in resp_dict_stream):
            stream_name = resp_dict_stream['name']
        else:
            print('No stream found in response')
        url = '/api/sources/' + key + '/streams/' + stream_name + '/'
        response = c.delete(url, {}, **self.auth_header_improper)
        self.assertEqual(response_post.status_code, 201)
        self.assertEqual(response.status_code, 401)

    def test_stream_delete_invalid_source_key(self):
        c = Client()
        response_post = c.post('/api/sources/', {"name": "nishant-test",
                                                 "dataFormat": "JSON",
                                                 "dataReportingInterval": 0,
                                                 "isActive": True,
                                                 "isMonitored": True,
                                                 "timeoutInterval": 0,
                                                 "dataTimezone": "Africa/Abidjan" }, 
                              **self.auth_header)
        resp_dict = json.loads(response_post.content)
        if('sourceKey' in resp_dict):
            key = resp_dict['sourceKey']
        else:
            print('No Source key found in response')
        key_improper = key + 'sdvdsv'
        url = '/api/sources/' + key + '/streams/'
        response_stream = c.post(url, {"name": "stream1",
                                       "streamDataType": "INTEGER",
                                       "streamDataUnit": "INTEGER",
                                       "streamPositionInCSV": 1 }, 
                                 **self.auth_header)
        resp_dict_stream = json.loads(response_stream.content)
        if('name' in resp_dict_stream):
            stream_name = resp_dict_stream['name']
        else:
            print('No stream found in response')
        url = '/api/sources/' + key_improper + '/streams/' + stream_name + '/'
        response = c.delete(url, {}, **self.auth_header)
        self.assertEqual(response_post.status_code, 201)
        self.assertEqual(response.status_code, 400)

    def test_stream_delete_invalid_stream_name(self):
        c = Client()
        response_post = c.post('/api/sources/', {"name": "nishant-test",
                                                 "dataFormat": "JSON",
                                                 "dataReportingInterval": 10,
                                                 "isActive": True,
                                                 "isMonitored": True,
                                                 "timeoutInterval": 0,
                                                 "dataTimezone": "Africa/Abidjan" }, 
                              **self.auth_header)
        resp_dict = json.loads(response_post.content)
        if('sourceKey' in resp_dict):
            key = resp_dict['sourceKey']
        else:
            print('No Source key found in response')
        url = '/api/sources/' + key + '/streams/'
        response_stream = c.post(url, {"name": "stream1",
                                       "streamDataType": "INTEGER",
                                       "streamDataUnit": "INTEGER",
                                       "streamPositionInCSV": 1 },
                                 **self.auth_header)
        resp_dict_stream = json.loads(response_stream.content)
        if('name' in resp_dict_stream):
            stream_name = resp_dict_stream['name']
        else:
            print('No stream found in response')
        stream_name_improper = stream_name + 'adfgfhg'
        url = '/api/sources/' + key + '/streams/' + stream_name_improper + '/'
        response = c.delete(url, {}, **self.auth_header)
        self.assertEqual(response_post.status_code, 201)
        self.assertEqual(response.status_code, 400)

    def test_stream_get_with_mentioned_key_and_name_authenticated(self):
        c = Client()
        response_post = c.post('/api/sources/', {"name": "nishant-test",
                                                 "dataFormat": "JSON",
                                                 "dataReportingInterval": 0,
                                                 "isActive": True,
                                                 "isMonitored": True,
                                                 "timeoutInterval": 0,
                                                 "dataTimezone": "Africa/Abidjan" },
                             **self.auth_header)
        resp_dict = json.loads(response_post.content)
        if('sourceKey' in resp_dict):
            key = resp_dict['sourceKey']
        else:
            print('No Source key found in response')
        url = '/api/sources/' + key + '/streams/'
        response_stream = c.post(url, {"name": "stream1",
                                       "streamDataType": "INTEGER",
                                       "streamDataUnit": "INTEGER",
                                       "streamPositionInCSV": 1 }, 
                                 **self.auth_header)
        resp_dict_stream = json.loads(response_stream.content)
        if('name' in resp_dict_stream):
            stream_name = resp_dict_stream['name']
        else:
            print('No stream found in response')
        url = '/api/sources/' + key + '/streams/' + stream_name + '/'
        response_get = c.get(url, {}, **self.auth_header)
        self.assertEqual(response_post.status_code, 201)
        self.assertEqual(response_stream.status_code, 201)
        self.assertEqual(response_get.status_code, 200)

    def test_stream_get_with_mentioned_key_and_name_unauthenticated(self):
        c = Client()
        response_post = c.post('/api/sources/', {"name": "nishant-test",
                                                 "dataFormat": "JSON",
                                                 "dataReportingInterval": 0,
                                                 "isActive": True,
                                                 "isMonitored": True,
                                                 "timeoutInterval": 0,
                                                 "dataTimezone": "Africa/Abidjan" },
                               **self.auth_header)
        resp_dict = json.loads(response_post.content)
        if('sourceKey' in resp_dict):
            key = resp_dict['sourceKey']
        else:
            print('No Source key found in response')
        url = '/api/sources/' + key + '/streams/'
        response_stream = c.post(url, {"name": "stream1",
                                       "streamDataType": "INTEGER",
                                       "streamDataUnit": "INTEGER",
                                       "streamPositionInCSV": 1 },
                                 **self.auth_header)
        resp_dict_stream = json.loads(response_stream.content)
        if('name' in resp_dict_stream):
            stream_name = resp_dict_stream['name']
        else:
            print('No stream found in response')
        url = '/api/sources/' + key + '/streams/' + stream_name + '/'
        response_get = c.get(url, {})
        self.assertEqual(response_post.status_code, 201)
        self.assertEqual(response_stream.status_code, 201)
        self.assertEqual(response_get.status_code, 401)

    def test_stream_get_with_mentioned_key_and_name_token_key_improper(self):
        c = Client()
        response_post = c.post('/api/sources/', {"name": "nishant-test",
                                                 "dataFormat": "CSV",
                                                 "dataReportingInterval": 0,
                                                 "isActive": True,
                                                 "isMonitored": True,
                                                 "timeoutInterval": 0,
                                                 "dataTimezone": "Africa/Abidjan" }, 
                              **self.auth_header)
        resp_dict = json.loads(response_post.content)
        if('sourceKey' in resp_dict):
            key = resp_dict['sourceKey']
        else:
            print('No Source key found in response')
        url = '/api/sources/' + key + '/streams/'
        response_stream = c.post(url, {"name": "stream1",
                                       "streamDataType": "INTEGER",
                                       "streamDataUnit": "INTEGER",
                                       "streamPositionInCSV": 1 }, 
                                **self.auth_header)
        resp_dict_stream = json.loads(response_stream.content)
        if('name' in resp_dict_stream):
            stream_name = resp_dict_stream['name']
        else:
            print('No stream found in response')
        url = '/api/sources/' + key + '/streams/' + stream_name + '/'
        response_get = c.get(url, {}, **self.auth_header_improper)
        self.assertEqual(response_post.status_code, 201)
        self.assertEqual(response_stream.status_code, 201)
        self.assertEqual(response_get.status_code, 401)

    def test_stream_get_with_mentioned_key_and_name_source_key_improper(self):
        c = Client()
        response_post = c.post('/api/sources/', {"name": "nishant-test",
                                                 "dataFormat": "CSV",
                                                 "dataReportingInterval": 10,
                                                 "isActive": True,
                                                 "isMonitored": True,
                                                 "timeoutInterval": 0,
                                                 "dataTimezone": "Africa/Abidjan" },
                              **self.auth_header)
        resp_dict = json.loads(response_post.content)
        if('sourceKey' in resp_dict):
            key = resp_dict['sourceKey']
        else:
            print('No Source key found in response')
        key_improper = key + 'dfds'
        url = '/api/sources/' + key + '/streams/'
        response_stream = c.post(url, {"name": "stream1",
                                       "streamDataType": "INTEGER",
                                       "streamDataUnit": "INTEGER",
                                       "streamPositionInCSV": 1 },
                                 **self.auth_header)
        resp_dict_stream = json.loads(response_stream.content)
        if('name' in resp_dict_stream):
            stream_name = resp_dict_stream['name']
        else:
            print('No stream found in response')
        url = '/api/sources/' + key_improper + '/streams/' + stream_name + '/'
        response_get = c.get(url, {}, **self.auth_header)
        self.assertEqual(response_post.status_code, 201)
        self.assertEqual(response_stream.status_code, 201)
        self.assertEqual(response_get.status_code, 400)

    def test_stream_get_with_mentioned_key_and_name_stream_name_improper(self):
        c = Client()
        response_post = c.post('/api/sources/', {"name": "nishant-test",
                                                 "dataFormat": "CSV",
                                                 "dataReportingInterval": 0,
                                                 "isActive": True,
                                                 "isMonitored": True,
                                                 "timeoutInterval": 0,
                                                 "dataTimezone": "Africa/Abidjan" },
                               **self.auth_header)
        resp_dict = json.loads(response_post.content)
        if('sourceKey' in resp_dict):
            key = resp_dict['sourceKey']
        else:
            print('No Source key found in response')
        url = '/api/sources/' + key + '/streams/'
        response_stream = c.post(url, {"name": "stream1",
                                       "streamDataType": "INTEGER",
                                       "streamDataUnit": "INTEGER",
                                       "streamPositionInCSV": 1 },
                                 **self.auth_header)
        resp_dict_stream = json.loads(response_stream.content)
        if('name' in resp_dict_stream):
            stream_name = resp_dict_stream['name']
        else:
            print('No stream found in response')
        stream_name_improper = stream_name + 'dfsdg'
        url = '/api/sources/' + key + '/streams/' + stream_name_improper + '/'
        response_get = c.get(url, {}, **self.auth_header)
        self.assertEqual(response_post.status_code, 201)
        self.assertEqual(response_stream.status_code, 201)
        self.assertEqual(response_get.status_code, 400)

    def test_data_get_authenticated(self):
        c = Client()
        response_post = c.post('/api/sources/', {"name": "nishant-test",
                                                 "dataFormat": "CSV",
                                                 "dataReportingInterval": 0,
                                                 "isActive": True,
                                                 "isMonitored": True,
                                                 "timeoutInterval": 0,
                                                 "dataTimezone": "Africa/Abidjan" },
                              **self.auth_header)
        resp_dict = json.loads(response_post.content)
        if('sourceKey' in resp_dict):
            key = resp_dict['sourceKey']
        else:
            print('No Source key found in response')
        url = '/api/sources/' + key + '/streams/'
        response_stream = c.post(url, {"name": "stream1",
                                       "streamDataType": "INTEGER",
                                       "streamDataUnit": "INTEGER",
                                       "streamPositionInCSV": 1 },
                                 **self.auth_header)
        resp_dict_stream = json.loads(response_stream.content)
        if('name' in resp_dict_stream):
            stream_name = resp_dict_stream['name']
        else:
            print('No stream found in response')
        start_time = '2015-11-01T12:11:01Z'
        end_time = '2015-11-01T12:11:01Z'
        url_data = '/api/sources/' + key + '/data/' + '?startTime=' + start_time + '&endTime=' + end_time
        response_data = c.get(url_data, {}, **self.auth_header)
        self.assertEqual(response_post.status_code, 201)
        self.assertEqual(response_stream.status_code, 201)
        self.assertEqual(response_data.status_code, 200)

    def test_data_get_unauthenticated(self):
        c = Client()
        response_post = c.post('/api/sources/', {"name": "nishant-test",
                                                 "dataFormat": "CSV",
                                                 "dataReportingInterval": 0,
                                                 "isActive": True,
                                                 "isMonitored": True,
                                                 "timeoutInterval": 0,
                                                 "dataTimezone": "Africa/Abidjan" },
                               **self.auth_header)
        resp_dict = json.loads(response_post.content)
        if('sourceKey' in resp_dict):
            key = resp_dict['sourceKey']
        else:
            print('No Source key found in response')
        url = '/api/sources/' + key + '/streams/'
        response_stream = c.post(url, {"name": "stream1",
                                       "streamDataType": "INTEGER",
                                       "streamDataUnit": "INTEGER",
                                       "streamPositionInCSV": 1 },
                                 **self.auth_header)
        resp_dict_stream = json.loads(response_stream.content)
        if('name' in resp_dict_stream):
            stream_name = resp_dict_stream['name']
        else:
            print('No stream found in response')
        start_time = '2015-11-01T12:11:01Z'
        end_time = '2015-11-01T12:11:01Z'
        url_data = '/api/sources/' + key + '/data/' + '?startTime=' + start_time + '&endTime=' + end_time
        response_data = c.get(url_data, {})
        self.assertEqual(response_post.status_code, 201)
        self.assertEqual(response_stream.status_code, 201)
        self.assertEqual(response_data.status_code, 401)

    def test_data_get_improper_token(self):
        c = Client()
        response_post = c.post('/api/sources/', {"name": "nishant-test",
                                                 "dataFormat": "CSV",
                                                 "dataReportingInterval": 10,
                                                 "isActive": True,
                                                 "isMonitored": True,
                                                 "timeoutInterval": 0,
                                                 "dataTimezone": "Africa/Abidjan" }, 
                              **self.auth_header)
        resp_dict = json.loads(response_post.content)
        if('sourceKey' in resp_dict):
            key = resp_dict['sourceKey']
        else:
            print('No Source key found in response')
        url = '/api/sources/' + key + '/streams/'
        response_stream = c.post(url, {"name": "stream1",
                                       "streamDataType": "INTEGER",
                                       "streamDataUnit": "string",
                                       "streamPositionInCSV": 1 },
                                 **self.auth_header)
        resp_dict_stream = json.loads(response_stream.content)
        if('name' in resp_dict_stream):
            stream_name = resp_dict_stream['name']
        else:
            print('No stream found in response')
        start_time = '2015-11-01T12:11:01Z'
        end_time = '2015-11-01T12:11:01Z'
        url_data = '/api/sources/' + key + '/data/' + '?startTime=' + start_time + '&endTime=' + end_time
        response_data = c.get(url_data, {}, **self.auth_header_improper)
        self.assertEqual(response_post.status_code, 201)
        self.assertEqual(response_stream.status_code, 201)
        self.assertEqual(response_data.status_code, 401)

    def test_data_get_authenticated_source_key_improper(self):
        c = Client()
        response_post = c.post('/api/sources/', {"name": "nishant-test",
                                                 "dataFormat": "CSV",
                                                 "dataReportingInterval": 0,
                                                 "isActive": True,
                                                 "isMonitored": True,
                                                 "timeoutInterval": 0,
                                                 "dataTimezone": "Africa/Abidjan" },
                             **self.auth_header)
        resp_dict = json.loads(response_post.content)
        if('sourceKey' in resp_dict):
            key = resp_dict['sourceKey']
        else:
            print('No Source key found in response')
        key_improper = key + 'sfghgj'
        url = '/api/sources/' + key + '/streams/'
        response_stream = c.post(url, {"name": "stream1",
                                       "streamDataType": "INTEGER",
                                       "streamDataUnit": "INTEGER",
                                       "streamPositionInCSV": 1 },
                                 **self.auth_header)
        resp_dict_stream = json.loads(response_stream.content)
        if('name' in resp_dict_stream):
            stream_name = resp_dict_stream['name']
        else:
            print('No stream found in response')
        start_time = '2015-11-01T12:11:01Z'
        end_time = '2015-11-01T12:11:01Z'
        url_data = '/api/sources/' + key_improper + '/data/' + '?startTime=' + start_time + '&endTime=' + end_time
        response_data = c.get(url_data, {}, **self.auth_header)
        self.assertEqual(response_post.status_code, 201)
        self.assertEqual(response_stream.status_code, 201)
        self.assertEqual(response_data.status_code, 400)

    def test_data_get_authenticated_with_proper_stream_name(self):
        c = Client()
        response_post = c.post('/api/sources/', {"name": "nishant-test",
                                                 "dataFormat": "CSV",
                                                 "dataReportingInterval": 0,
                                                 "isActive": True,
                                                 "isMonitored": True,
                                                 "timeoutInterval": 0,
                                                 "dataTimezone": "Africa/Abidjan" },
                               **self.auth_header)
        resp_dict = json.loads(response_post.content)
        if('sourceKey' in resp_dict):
            key = resp_dict['sourceKey']
        else:
            print('No Source key found in response')
        url = '/api/sources/' + key + '/streams/'
        response_stream = c.post(url, {"name": "stream1",
                                       "streamDataType": "INTEGER",
                                       "streamDataUnit": "INTEGER",
                                       "streamPositionInCSV": 1 },
                                 **self.auth_header)
        resp_dict_stream = json.loads(response_stream.content)
        if('name' in resp_dict_stream):
            stream_name = resp_dict_stream['name']
        else:
            print('No stream found in response')
        start_time = '2015-11-01T12:11:01Z'
        end_time = '2015-11-01T12:11:01Z'
        url_data = '/api/sources/' + key + '/data/' + '?startTime=' + start_time + '&endTime=' + end_time + '&streamNames=' + stream_name
        response_data = c.get(url_data, {}, **self.auth_header)
        self.assertEqual(response_post.status_code, 201)
        self.assertEqual(response_stream.status_code, 201)
        self.assertEqual(response_data.status_code, 200)

    def test_data_get_authenticated_with_improper_stream_name(self):
        c = Client()
        response_post = c.post('/api/sources/', {"name": "nishant-test",
                                                 "dataFormat": "CSV",
                                                 "dataReportingInterval": 0,
                                                 "isActive": True,
                                                 "isMonitored": True,
                                                 "timeoutInterval": 0,

                                                 "dataTimezone": "Africa/Abidjan" }, **self.auth_header)
        resp_dict = json.loads(response_post.content)
        if('sourceKey' in resp_dict):
            key = resp_dict['sourceKey']
        else:
            print('No Source key found in response')
        url = '/api/sources/' + key + '/streams/'
        response_stream = c.post(url, {"name": "stream1",
                                       "streamDataType": "INTEGER",
                                       "streamDataUnit": "INTEGER",
                                       "streamPositionInCSV": 1 }, 
                                 **self.auth_header)
        resp_dict_stream = json.loads(response_stream.content)
        if('name' in resp_dict_stream):
            stream_name = resp_dict_stream['name']
        else:
            print('No stream found in response')
        stream_name_improper = stream_name + 'sdvsfg'
        start_time = '2015-11-01T12:11:01Z'
        end_time = '2015-11-01T12:11:01Z'
        url_data = '/api/sources/' + key + '/data/' + '?startTime=' + start_time + '&endTime=' + end_time + '&streamNames=' + stream_name_improper
        response_data = c.get(url_data, {}, **self.auth_header)
        self.assertEqual(response_post.status_code, 201)
        self.assertEqual(response_stream.status_code, 201)
        self.assertEqual(response_data.status_code, 400)

    def test_data_write_unauthenticated(self):
        c = Client()
        response_post = c.post('/api/sources/', {"name": "nishant-test",
                                                 "dataFormat": "CSV",
                                                 "dataReportingInterval": 10,
                                                 "isActive": True,
                                                 "isMonitored": True,
                                                 "timeoutInterval":5,
                                                 "dataTimezone": "Africa/Abidjan" },
                               **self.auth_header)
        resp_dict = json.loads(response_post.content)
        if('sourceKey' in resp_dict):
            key = resp_dict['sourceKey']
        else:
            print('No Source key found in response')
        url = '/api/sources/' + key + '/streams/'
        response_stream1 = c.post(url, {"name": "stream1",
                                        "streamDataType": "INTEGER",
                                        "streamDataUnit": "INTEGER",
                                        "streamPositionInCSV": 1 },
                                 **self.auth_header)
        response_stream2 = c.post(url, {"name": "stream2",
                                        "streamDataType": "INTEGER",
                                        "streamDataUnit": "INTEGER",
                                        "streamPositionInCSV": 2 },
                                 **self.auth_header)
        url_data = '/api/sources/' + key + '/data/'
        response_data = c.post(url_data, content_type = "text/plain", data='1,2')
        self.assertEqual(response_data.status_code, 401)

    def test_data_write_unauthenticated_token_improper(self):
        c = Client()
        response_post = c.post('/api/sources/', {"name": "nishant-test",
                                                 "dataFormat": "CSV",
                                                 "dataReportingInterval": 0,
                                                 "isActive": True,
                                                 "isMonitored": True,
                                                 "timeoutInterval": 0,
                                                 "dataTimezone": "Africa/Abidjan" }, 
                               **self.auth_header)
        resp_dict = json.loads(response_post.content)
        if('sourceKey' in resp_dict):
            key = resp_dict['sourceKey']
        else:
            print('No Source key found in response')
        url = '/api/sources/' + key + '/streams/'
        response_stream1 = c.post(url, {"name": "stream1",
                                        "streamDataType": "INTEGER",
                                        "streamDataUnit": "INTEGER",
                                        "streamPositionInCSV": 0 },
                                  **self.auth_header)
        response_stream2 = c.post(url, {"name": "stream2",
                                        "streamDataType": "INTEGER",
                                        "streamDataUnit": "INTEGER",
                                        "streamPositionInCSV": 2 },
                                  **self.auth_header)
        key_improper = key + 'sdvfsd'
        url_data = '/api/sources/' + key + '/data/'
        response_data = c.post(url_data, content_type = "text/plain", data='1,2', **self.auth_header_improper)
        self.assertEqual(response_data.status_code, 401)

    def test_data_write_unauthenticated_source_key_improper(self):
        c = Client()
        response_post = c.post('/api/sources/', {"name": "nishant-test",
                                                 "dataFormat": "CSV",
                                                 "dataReportingInterval": 0,
                                                 "isActive": True,
                                                 "isMonitored": True,
                                                 "timeoutInterval": 0,
                                                 "dataTimezone": "Africa/Abidjan" },
                               **self.auth_header)
        resp_dict = json.loads(response_post.content)
        if('sourceKey' in resp_dict):
            key = resp_dict['sourceKey']
        else:
            print('No Source key found in response')
        url = '/api/sources/' + key + '/streams/'
        response_stream1 = c.post(url, {"name": "stream1",
                                        "streamDataType": "INTEGER",
                                        "streamPositionInCSV": 1 },
                                  **self.auth_header)
        response_stream2 = c.post(url, {"name": "stream2",
                                        "streamDataType": "INTEGER",
                                        "streamPositionInCSV": 2 }, 
                                  **self.auth_header)
        key_improper = key + 'sdvfsd'
        url_data = '/api/sources/' + key_improper + '/data/'
        response_data = c.post(url_data, content_type = "text/plain", data='1,2', **self.auth_header)
        self.assertEqual(response_post.status_code, 201)
        self.assertEqual(response_stream1.status_code, 201)
        self.assertEqual(response_stream2.status_code, 201)
        self.assertEqual(response_data.status_code, 400)

    def test_data_write_authenticated_csv(self):
        c = Client()
        response_post = c.post('/api/sources/', {"name": "nishant-test",
                                                 "dataFormat": "CSV",
                                                 "dataReportingInterval": 10,
                                                 "isActive": True,
                                                 "isMonitored": True,
                                                 "dataTimezone": "Africa/Abidjan" },
                               **self.auth_header)
        resp_dict = json.loads(response_post.content)
        if('sourceKey' in resp_dict):
            key = resp_dict['sourceKey']
        else:
            print('No Source key found in response')
        url = '/api/sources/' + key + '/streams/'
        response_stream1 = c.post(url, {"name": "stream1",
                                        "streamDataType": "INTEGER",
                                        "streamPositionInCSV": 1 },
                                  **self.auth_header)
        response_stream2 = c.post(url, {"name": "stream2",
                                        "streamDataType": "INTEGER",
                                        "streamPositionInCSV": 2 },
                                  **self.auth_header)
        url_data = '/api/sources/' + key + '/data/'
        request_body = {'datapoint':'1,2'}
        response_data = c.post(url_data, content_type = "text/plain", data='1,2', **self.auth_header)
        self.assertEqual(response_post.status_code, 201)
        self.assertEqual(response_stream1.status_code, 201)
        self.assertEqual(response_stream2.status_code, 201)
        self.assertEqual(response_data.status_code, 200)

    def test_data_write_authenticated_json(self):
        c = Client()
        response_post = c.post('/api/sources/', {"name": "nishant-test",
                                                 "dataFormat": "JSON",
                                                 "dataReportingInterval": 10,
                                                 "isActive": True,
                                                 "isMonitored": True,
                                                 "dataTimezone": "Africa/Abidjan" }, 
                               **self.auth_header)
        resp_dict = json.loads(response_post.content)
        if('sourceKey' in resp_dict):
            key = resp_dict['sourceKey']
        else:
            print('No Source key found in response')
        url = '/api/sources/' + key + '/streams/'
        response_stream1 = c.post(url, {"name": "stream1",
                                        "streamDataType": "INTEGER",
                                        "streamPositionInCSV": 1 }, 
                                  **self.auth_header)
        response_stream2 = c.post(url, {"name": "stream2",
                                        "streamDataType": "INTEGER",
                                        "streamPositionInCSV": 2 },
                                  **self.auth_header)
        url_data = '/api/sources/' + key + '/data/'
        request_body = [{"stream1" : 10, "stream2" : 20}]
        response_data = c.post(url_data, content_type = "text/plain", data = json.dumps(request_body), **self.auth_header)
        self.assertEqual(response_post.status_code, 201)
        self.assertEqual(response_stream1.status_code, 201)
        self.assertEqual(response_stream2.status_code, 201)
        self.assertEqual(response_data.status_code, 200)


    """
    def test_data_write_authenticated_json2(self):
        c = Client()
        response_post = c.post('/api/sources/', {"name": "nishant-test",
                                                 "dataFormat": "JSON",
                                                 "dataReportingInterval": 10,
                                                 "isActive": True,
                                                 "isMonitored": True,
                                                 "dataTimezone": "Africa/Abidjan" }, 
                               **self.auth_header)
        resp_dict = json.loads(response_post.content)
        if('sourceKey' in resp_dict):
            key = resp_dict['sourceKey']
        else:
            print('No Source key found in response')
        url = '/api/sources/' + key + '/streams/'
        response_stream1 = c.post(url, {"name": "stream1",
                                        "streamDataType": "INTEGER",
                                        "streamPositionInCSV": 1 }, 
                                  **self.auth_header)
        response_stream2 = c.post(url, {"name": "stream2",
                                        "streamDataType": "INTEGER",
                                        "streamPositionInCSV": 2 }, 
                                  **self.auth_header)
        url_data = '/api/sources/' + key + '/data/'
        request_body = [{"stream1" : 10, "stream2" : 20}]
        response_data = c.post(url_data, content_type = "application/json", data = request_body, **self.auth_header)
        print("response new data: " + response_data.content)
        self.assertEqual(response_post.status_code,201)
        self.assertEqual(response_stream1.status_code,201)
        self.assertEqual(response_stream2.status_code,201)
        self.assertEqual(response_data.status_code, 200)
    """








