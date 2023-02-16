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


class ActionAPITest(unittest.TestCase):
    def setUp(self):
        self.user = User.objects.create_user('nishant@dataglen.com', 'nishant@dataglen.com', 'nishant')
        self.user.save()
        self.token = Token.objects.get(user=self.user).key
        self.auth_header = {'HTTP_AUTHORIZATION': 'Token {}'.format(self.token)}
        self.client = Client()
        self.token_improper = self.token + '1!2@3#'
        self.auth_header_improper = {'HTTP_AUTHORIZATION': 'Token {}'.format(self.token_improper)}

    def tearDown(self):
        self.user.delete()
        self.client = None

    def test_action_stream_get_authenticated(self):
        c = Client()
        response_post = c.post('/api/sources/', {"name": "test_source",
                                                 "dataFormat": "CSV",
                                                 "dataReportingInterval": 0,
                                                 "isActive": True,
                                                 "isMonitored": True,
                                                  }, 
                              **self.auth_header)
        resp_dict = json.loads(response_post.content)
        if('sourceKey' in resp_dict):
            key = resp_dict['sourceKey']
        else:
            print('No Source key found in response')
        url = '/api/sources/' + key + '/action_streams/'
        response = c.get(url, {}, **self.auth_header)
        self.assertEqual(response_post.status_code, 201)
        self.assertEqual(response.status_code, 200)

    def test_action_stream_get_unauthenticated(self):
        c = Client()
        response_post = c.post('/api/sources/', {"name": "test_source",
                                                 "dataFormat": "CSV",
                                                 "dataReportingInterval": 0,
                                                 "isActive": True,
                                                 "isMonitored": True,
                                                  },
                              **self.auth_header)
        resp_dict = json.loads(response_post.content)
        if('sourceKey' in resp_dict):
            key = resp_dict['sourceKey']
        else:
            print('No Source key found in response')
        url = '/api/sources/' + key + '/action_streams/'
        response = c.get(url)
        self.assertEqual(response_post.status_code, 201)
        self.assertEqual(response.status_code, 401)

    def test_action_stream_get_token_improper(self):
        c = Client()
        response_post = c.post('/api/sources/', {"name": "test_source",
                                                 "dataFormat": "CSV",
                                                 "dataReportingInterval": 0,
                                                 "isActive": True,
                                                 "isMonitored": True,
                                                 },

                              **self.auth_header)
        resp_dict = json.loads(response_post.content)
        if('sourceKey' in resp_dict):
            key = resp_dict['sourceKey']
        else:
            print('No Source key found in response')
        url = '/api/sources/' + key + '/action_streams/'
        response = c.get(url, {}, **self.auth_header_improper)
        self.assertEqual(response_post.status_code, 201)
        self.assertEqual(response.status_code, 401)

    def test_action_stream_get_sourceKey_improper(self):
        c = Client()
        response_post = c.post('/api/sources/', {"name": "test_source",
                                                 "dataFormat": "CSV",
                                                 "dataReportingInterval": 0,
                                                 "isActive": True,
                                                 "isMonitored": True,
                                                  },
                              **self.auth_header)
        resp_dict = json.loads(response_post.content)
        if('sourceKey' in resp_dict):
            key = resp_dict['sourceKey']
        else:
            print('No Source key found in response')
        key_improper = key + 'afdgf'
        url = '/api/sources/' + key_improper + '/action_streams/'
        response = c.get(url, {}, **self.auth_header)
        self.assertEqual(response_post.status_code, 201)
        self.assertEqual(response.status_code, 400)

    def test_action_stream_create_authenticated(self):
        c = Client()
        response_post = c.post('/api/sources/', {"name": "test_source",
                                                 "dataFormat": "CSV",
                                                 "dataReportingInterval": 0,
                                                 "isActive": True,
                                                 "isMonitored": True,
                                                  },
                              **self.auth_header)
        resp_dict = json.loads(response_post.content)
        if('sourceKey' in resp_dict):
            key = resp_dict['sourceKey']
        else:
            print('No Source key found in response')
        url = '/api/sources/' + key + '/action_streams/'
        response_stream = c.post(url, {"name": "stream1",
                                       "streamDataType": "INTEGER",
                                       "streamDataUnit": "INTEGER",
                                       "streamPositionInCSV": 1 }, 
                                **self.auth_header)
        self.assertEqual(response_post.status_code, 201)
        self.assertEqual(response_stream.status_code, 201)

    def test_action_stream_create_unauthenticated(self):
        c = Client()
        response_post = c.post('/api/sources/', {"name": "test_source",
                                                 "dataFormat": "CSV",
                                                 "dataReportingInterval": 0,
                                                 "isActive": True,
                                                 "isMonitored": True,
                                                  }, 
                              **self.auth_header)
        resp_dict = json.loads(response_post.content)
        if('sourceKey' in resp_dict):
            key = resp_dict['sourceKey']
        else:
            print('No Source key found in response')
        url = '/api/sources/' + key + '/action_streams/'
        response_stream = c.post(url, {"name": "stream1",
                                       "streamDataType": "INTEGER",
                                       "streamDataUnit": "INTEGER",
                                       "streamPositionInCSV": 1 } )
        self.assertEqual(response_post.status_code, 201)
        self.assertEqual(response_stream.status_code, 401)

    def test_action_stream_create_unauthenticated_token_improper(self):
        c = Client()
        response_post = c.post('/api/sources/', {"name": "test_source",
                                                 "dataFormat": "CSV",
                                                 "dataReportingInterval": 0,
                                                 "isActive": True,
                                                 "isMonitored": True,
                                                  }, 
                              **self.auth_header)
        resp_dict = json.loads(response_post.content)
        if('sourceKey' in resp_dict):
            key = resp_dict['sourceKey']
        else:
            print('No Source key found in response')
        url = '/api/sources/' + key + '/action_streams/'
        response_stream = c.post(url, {"name": "stream1",
                                       "streamDataType": "INTEGER",
                                       "streamDataUnit": "INTEGER",
                                       "streamPositionInCSV": 1 }, 
                                **self.auth_header_improper)
        self.assertEqual(response_post.status_code, 201)
        self.assertEqual(response_stream.status_code, 401)

    def test_action_stream_create_duplicate_stream(self):
        c = Client()
        response_post = c.post('/api/sources/', {"name": "test_source",
                                                 "dataFormat": "CSV",
                                                 "dataReportingInterval": 0,
                                                 "isActive": True,
                                                 "isMonitored": True,
                                                  },
                              **self.auth_header)
        resp_dict = json.loads(response_post.content)
        if('sourceKey' in resp_dict):
            key = resp_dict['sourceKey']
        else:
            print('No Source key found in response')
        url = '/api/sources/' + key + '/action_streams/'
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

    def test_action_stream_create_mandatory_field_missing(self):
        c = Client()
        response_post = c.post('/api/sources/', {"name": "test_source",
                                                 "dataFormat": "CSV",
                                                 "dataReportingInterval": 0,
                                                 "isActive": True,
                                                 "isMonitored": True,
                                                  },
                              **self.auth_header)
        resp_dict = json.loads(response_post.content)
        if('sourceKey' in resp_dict):
            key = resp_dict['sourceKey']
        else:
            print('No Source key found in response')
        url = '/api/sources/' + key + '/action_streams/'
        response_stream = c.post(url, {"streamDataType": "INTEGER",
                                       "streamPositionInCSV": 0 },
                                 **self.auth_header)
        self.assertEqual(response_post.status_code, 201)
        self.assertEqual(response_stream.status_code, 400)


    def test_action_stream_delete_authenticated(self):
        c = Client()
        response_post = c.post('/api/sources/', {"name": "test_source",
                                                 "dataFormat": "CSV",
                                                 "dataReportingInterval": 0,
                                                 "isActive": True,
                                                 "isMonitored": True,
                                                  },
                              **self.auth_header)
        resp_dict = json.loads(response_post.content)
        if('sourceKey' in resp_dict):
            key = resp_dict['sourceKey']
        else:
            print('No Source key found in response')
        url = '/api/sources/' + key + '/action_streams/'
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
        url = '/api/sources/' + key + '/action_streams/' + stream_name + '/'
        response = c.delete(url, {}, **self.auth_header)
        self.assertEqual(response_post.status_code, 201)
        self.assertEqual(response.status_code, 204)


    def test_action_stream_delete_unautheticated(self):
        c = Client()
        response_post = c.post('/api/sources/', {"name": "test_source",
                                                 "dataFormat": "CSV",
                                                 "dataReportingInterval": 0,
                                                 "isActive": True,
                                                 "isMonitored": True,
                                                  },
                              **self.auth_header)
        resp_dict = json.loads(response_post.content)
        if('sourceKey' in resp_dict):
            key = resp_dict['sourceKey']
        else:
            print('No Source key found in response')
        url = '/api/sources/' + key + '/action_streams/'
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
        url = '/api/sources/' + key + '/action_streams/' + stream_name + '/'
        response = c.delete(url, {})
        self.assertEqual(response_post.status_code, 201)
        self.assertEqual(response.status_code, 401)

    def test_action_stream_delete_unautheticated_token_improper(self):
        c = Client()
        response_post = c.post('/api/sources/', {"name": "test_source",
                                                 "dataFormat": "CSV",
                                                 "dataReportingInterval": 0,
                                                 "isActive": True,
                                                 "isMonitored": True,
                                                  }, 
                              **self.auth_header)
        resp_dict = json.loads(response_post.content)
        if('sourceKey' in resp_dict):
            key = resp_dict['sourceKey']
        else:
            print('No Source key found in response')
        url = '/api/sources/' + key + '/action_streams/'
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
        url = '/api/sources/' + key + '/action_streams/' + stream_name + '/'
        response = c.delete(url, {}, **self.auth_header_improper)
        self.assertEqual(response_post.status_code, 201)
        self.assertEqual(response.status_code, 401)

    def test_action_stream_delete_invalid_source_key(self):
        c = Client()
        response_post = c.post('/api/sources/', {"name": "test_source",
                                                 "dataFormat": "CSV",
                                                 "dataReportingInterval": 0,
                                                 "isActive": True,
                                                 "isMonitored": True,
                                                  }, 
                              **self.auth_header)
        resp_dict = json.loads(response_post.content)
        if('sourceKey' in resp_dict):
            key = resp_dict['sourceKey']
        else:
            print('No Source key found in response')
        key_improper = key + 'sdvdsv'
        url = '/api/sources/' + key + '/action_streams/'
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
        url = '/api/sources/' + key_improper + '/action_streams/' + stream_name + '/'
        response = c.delete(url, {}, **self.auth_header)
        self.assertEqual(response_post.status_code, 201)
        self.assertEqual(response.status_code, 400)

    def test_action_stream_delete_invalid_stream_name(self):
        c = Client()
        response_post = c.post('/api/sources/', {"name": "test_source",
                                                 "dataFormat": "CSV",
                                                 "dataReportingInterval": 0,
                                                 "isActive": True,
                                                 "isMonitored": True,
                                                  }, 
                              **self.auth_header)
        resp_dict = json.loads(response_post.content)
        if('sourceKey' in resp_dict):
            key = resp_dict['sourceKey']
        else:
            print('No Source key found in response')
        url = '/api/sources/' + key + '/action_streams/'
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
        url = '/api/sources/' + key + '/action_streams/' + stream_name_improper + '/'
        response = c.delete(url, {}, **self.auth_header)
        self.assertEqual(response_post.status_code, 201)
        self.assertEqual(response.status_code, 400)

    def test_action_stream_get_with_mentioned_key_and_name_authenticated(self):
        c = Client()
        response_post = c.post('/api/sources/', {"name": "test_source",
                                                 "dataFormat": "CSV",
                                                 "dataReportingInterval": 0,
                                                 "isActive": True,
                                                 "isMonitored": True,
                                                  },
                             **self.auth_header)
        resp_dict = json.loads(response_post.content)
        if('sourceKey' in resp_dict):
            key = resp_dict['sourceKey']
        else:
            print('No Source key found in response')
        url = '/api/sources/' + key + '/action_streams/'
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
        url = '/api/sources/' + key + '/action_streams/' + stream_name + '/'
        response_get = c.get(url, {}, **self.auth_header)
        self.assertEqual(response_post.status_code, 201)
        self.assertEqual(response_stream.status_code, 201)
        self.assertEqual(response_get.status_code, 200)

    def test_action_stream_get_with_mentioned_key_and_name_unauthenticated(self):
        c = Client()
        response_post = c.post('/api/sources/', {"name": "test_source",
                                                 "dataFormat": "CSV",
                                                 "dataReportingInterval": 0,
                                                 "isActive": True,
                                                 "isMonitored": True,
                                                  },
                               **self.auth_header)
        resp_dict = json.loads(response_post.content)
        if('sourceKey' in resp_dict):
            key = resp_dict['sourceKey']
        else:
            print('No Source key found in response')
        url = '/api/sources/' + key + '/action_streams/'
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
        url = '/api/sources/' + key + '/action_streams/' + stream_name + '/'
        response_get = c.get(url, {})
        self.assertEqual(response_post.status_code, 201)
        self.assertEqual(response_stream.status_code, 201)
        self.assertEqual(response_get.status_code, 401)

    def test_action_stream_get_with_mentioned_key_and_name_token_key_improper(self):
        c = Client()
        response_post = c.post('/api/sources/', {"name": "test_source",
                                                 "dataFormat": "CSV",
                                                 "dataReportingInterval": 0,
                                                 "isActive": True,
                                                 "isMonitored": True,
                                                  }, 
                              **self.auth_header)
        resp_dict = json.loads(response_post.content)
        if('sourceKey' in resp_dict):
            key = resp_dict['sourceKey']
        else:
            print('No Source key found in response')
        url = '/api/sources/' + key + '/action_streams/'
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
        url = '/api/sources/' + key + '/action_streams/' + stream_name + '/'
        response_get = c.get(url, {}, **self.auth_header_improper)
        self.assertEqual(response_post.status_code, 201)
        self.assertEqual(response_stream.status_code, 201)
        self.assertEqual(response_get.status_code, 401)

    def test_action_stream_get_with_mentioned_key_and_name_source_key_improper(self):
        c = Client()
        response_post = c.post('/api/sources/', {"name": "test_source",
                                                 "dataFormat": "CSV",
                                                 "dataReportingInterval": 0,
                                                 "isActive": True,
                                                 "isMonitored": True,
                                                  },
                              **self.auth_header)
        resp_dict = json.loads(response_post.content)
        if('sourceKey' in resp_dict):
            key = resp_dict['sourceKey']
        else:
            print('No Source key found in response')
        key_improper = key + 'dfds'
        url = '/api/sources/' + key + '/action_streams/'
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
        url = '/api/sources/' + key_improper + '/action_streams/' + stream_name + '/'
        response_get = c.get(url, {}, **self.auth_header)
        self.assertEqual(response_post.status_code, 201)
        self.assertEqual(response_stream.status_code, 201)
        self.assertEqual(response_get.status_code, 400)

    def test_action_stream_get_with_mentioned_key_and_name_stream_name_improper(self):
        c = Client()
        response_post = c.post('/api/sources/', {"name": "test_source",
                                                 "dataFormat": "CSV",
                                                 "dataReportingInterval": 0,
                                                 "isActive": True,
                                                 "isMonitored": True,
                                                  },
                               **self.auth_header)
        resp_dict = json.loads(response_post.content)
        if('sourceKey' in resp_dict):
            key = resp_dict['sourceKey']
        else:
            print('No Source key found in response')
        url = '/api/sources/' + key + '/action_streams/'
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
        url = '/api/sources/' + key + '/action_streams/' + stream_name_improper + '/'
        response_get = c.get(url, {}, **self.auth_header)
        self.assertEqual(response_post.status_code, 201)
        self.assertEqual(response_stream.status_code, 201)
        self.assertEqual(response_get.status_code, 400)


    def test_action_get_authenticated(self):
        c = Client()
        response_post = c.post('/api/sources/', {"name": "test_source",
                                                 "dataFormat": "CSV",
                                                 "dataReportingInterval": 0,
                                                 "isActive": True,
                                                 "isMonitored": True,
                                                  }, 
                              **self.auth_header)
        resp_dict = json.loads(response_post.content)
        if('sourceKey' in resp_dict):
            key = resp_dict['sourceKey']
        else:
            print('No Source key found in response')
        url = '/api/sources/' + key + '/action/'
        response = c.get(url, {}, **self.auth_header)
        self.assertEqual(response_post.status_code, 201)
        self.assertEqual(response.status_code, 200)

    def test_action_get_unauthenticated(self):
        c = Client()
        response_post = c.post('/api/sources/', {"name": "test_source",
                                                 "dataFormat": "CSV",
                                                 "dataReportingInterval": 0,
                                                 "isActive": True,
                                                 "isMonitored": True,
                                                  },
                              **self.auth_header)
        resp_dict = json.loads(response_post.content)
        if('sourceKey' in resp_dict):
            key = resp_dict['sourceKey']
        else:
            print('No Source key found in response')
        url = '/api/sources/' + key + '/action/'
        response = c.get(url)
        self.assertEqual(response_post.status_code, 201)
        self.assertEqual(response.status_code, 401)

    def test_action_get_token_improper(self):
        c = Client()
        response_post = c.post('/api/sources/', {"name": "test_source",
                                                 "dataFormat": "CSV",
                                                 "dataReportingInterval": 0,
                                                 "isActive": True,
                                                 "isMonitored": True,
                                                 },

                              **self.auth_header)
        resp_dict = json.loads(response_post.content)
        if('sourceKey' in resp_dict):
            key = resp_dict['sourceKey']
        else:
            print('No Source key found in response')
        url = '/api/sources/' + key + '/action/'
        response = c.get(url, {}, **self.auth_header_improper)
        self.assertEqual(response_post.status_code, 201)
        self.assertEqual(response.status_code, 401)

    def test_action_get_sourceKey_improper(self):
        c = Client()
        response_post = c.post('/api/sources/', {"name": "test_source",
                                                 "dataFormat": "CSV",
                                                 "dataReportingInterval": 0,
                                                 "isActive": True,
                                                 "isMonitored": True,
                                                  },
                              **self.auth_header)
        resp_dict = json.loads(response_post.content)
        if('sourceKey' in resp_dict):
            key = resp_dict['sourceKey']
        else:
            print('No Source key found in response')
        key_improper = key + 'afdgf'
        url = '/api/sources/' + key_improper + '/action/'
        response = c.get(url, {}, **self.auth_header)
        self.assertEqual(response_post.status_code, 201)
        self.assertEqual(response.status_code, 400)


    def test_action_create_authenticated(self):
        c = Client()
        response_post = c.post('/api/sources/', {"name": "test_source",
                                                 "dataFormat": "JSON",
                                                 "dataReportingInterval": 0,
                                                 "isActive": True,
                                                 "isMonitored": True,
                                                  },
                               **self.auth_header)
        resp_dict = json.loads(response_post.content)
        if('sourceKey' in resp_dict):
            key = resp_dict['sourceKey']
        else:
            print('No Source key found in response')
        url = '/api/sources/' + key + '/action_streams/'
        response_stream1 = c.post(url, {"name": "action-stream1",
                                       "streamDataType": "INTEGER",
                                       "streamPositionInCSV": 1 }, 
                                **self.auth_header)
        response_stream2 = c.post(url, {"name": "action-stream2",
                                       "streamDataType": "INTEGER",
                                       "streamPositionInCSV": 2 }, 
                                **self.auth_header)
        url_action = '/api/sources/' + key + '/action/'
        request_body = {"action-stream1" : 10, "action-stream2" : 20}
        response = c.post(url_action , content_type = "application/json", 
                          data=json.dumps(request_body), **self.auth_header)
        self.assertEqual(response.status_code,201)

    def test_action_create_unauthenticated(self):
        c = Client()
        response_post = c.post('/api/sources/', {"name": "test_source",
                                                 "dataFormat": "JSON",
                                                 "dataReportingInterval": 0,
                                                 "isActive": True,
                                                 "isMonitored": True,
                                                  },
                               **self.auth_header)
        resp_dict = json.loads(response_post.content)
        if('sourceKey' in resp_dict):
            key = resp_dict['sourceKey']
        else:
            print('No Source key found in response')
        url = '/api/sources/' + key + '/action_streams/'
        response_stream1 = c.post(url, {"name": "action-stream1",
                                       "streamDataType": "INTEGER",
                                       "streamPositionInCSV": 1 }, 
                                **self.auth_header)
        response_stream2 = c.post(url, {"name": "action-stream2",
                                       "streamDataType": "INTEGER",
                                       "streamPositionInCSV": 2 }, 
                                **self.auth_header)
        url_action = '/api/sources/' + key + '/action/'
        request_body = {"action-stream1" : 10, "action-stream2" : 20}
        response = c.post(url_action , content_type = "application/json", 
                          data=json.dumps(request_body))
        self.assertEqual(response.status_code,401)


    def test_action_create_token_key_improper(self):
        c = Client()
        response_post = c.post('/api/sources/', {"name": "test_source",
                                                 "dataFormat": "JSON",
                                                 "dataReportingInterval": 0,
                                                 "isActive": True,
                                                 "isMonitored": True,
                                                  },
                               **self.auth_header)
        resp_dict = json.loads(response_post.content)
        if('sourceKey' in resp_dict):
            key = resp_dict['sourceKey']
        else:
            print('No Source key found in response')
        url = '/api/sources/' + key + '/action_streams/'
        response_stream1 = c.post(url, {"name": "action-stream1",
                                       "streamDataType": "INTEGER",
                                       "streamPositionInCSV": 1 }, 
                                **self.auth_header)
        response_stream2 = c.post(url, {"name": "action-stream2",
                                       "streamDataType": "INTEGER",
                                       "streamPositionInCSV": 2 }, 
                                **self.auth_header)
        url_action = '/api/sources/' + key + '/action/'
        request_body = {"action-stream1" : 10, "action-stream2" : 20}
        response = c.post(url_action , content_type = "application/json", 
                          data=json.dumps(request_body), **self.auth_header_improper)
        self.assertEqual(response.status_code,401)


    def test_action_create_authenticated_sourceKey_improper(self):
        c = Client()
        response_post = c.post('/api/sources/', {"name": "test_source",
                                                 "dataFormat": "JSON",
                                                 "dataReportingInterval": 0,
                                                 "isActive": True,
                                                 "isMonitored": True,
                                                  },
                               **self.auth_header)
        resp_dict = json.loads(response_post.content)
        if('sourceKey' in resp_dict):
            key = resp_dict['sourceKey']
        else:
            print('No Source key found in response')
        url = '/api/sources/' + key + '/action_streams/'
        response_stream1 = c.post(url, {"name": "action-stream1",
                                       "streamDataType": "INTEGER",
                                       "streamPositionInCSV": 1 }, 
                                **self.auth_header)
        response_stream2 = c.post(url, {"name": "action-stream2",
                                       "streamDataType": "INTEGER",
                                       "streamPositionInCSV": 2 }, 
                                **self.auth_header)
        key_improper = key + 'sdgfdhgjfh'
        url_action = '/api/sources/' + key_improper + '/action/'
        request_body = {"action-stream1" : 10, "action-stream2" : 20}
        response = c.post(url_action , content_type = "application/json", 
                          data=json.dumps(request_body), **self.auth_header)
        self.assertEqual(response.status_code,400)


    def test_action_create_authenticated_stream_name_improper(self):
        c = Client()
        response_post = c.post('/api/sources/', {"name": "test_source",
                                                 "dataFormat": "JSON",
                                                 "dataReportingInterval": 0,
                                                 "isActive": True,
                                                 "isMonitored": True,
                                                  },
                               **self.auth_header)
        resp_dict = json.loads(response_post.content)
        if('sourceKey' in resp_dict):
            key = resp_dict['sourceKey']
        else:
            print('No Source key found in response')
        url = '/api/sources/' + key + '/action_streams/'
        response_stream1 = c.post(url, {"name": "action-stream1",
                                       "streamDataType": "INTEGER",
                                       "streamPositionInCSV": 1 }, 
                                **self.auth_header)
        response_stream2 = c.post(url, {"name": "action-stream2",
                                       "streamDataType": "INTEGER",
                                       "streamPositionInCSV": 2 }, 
                                **self.auth_header)
        key_improper = key + 'sdgfdhgjfh'
        url_action = '/api/sources/' + key + '/action/'
        request_body = {"action-stream11" : 10, "action-stream2" : 20}
        response = c.post(url_action , content_type = "application/json", 
                          data=json.dumps(request_body), **self.auth_header)
        self.assertEqual(response.status_code,400)


    def test_action_patch_authenticated(self):
        c = Client()
        response_post = c.post('/api/sources/', {"name": "test_source",
                                                 "dataFormat": "JSON",
                                                 "dataReportingInterval": 0,
                                                 "isActive": True,
                                                 "isMonitored": True,
                                                  },
                               **self.auth_header)
        resp_dict = json.loads(response_post.content)
        if('sourceKey' in resp_dict):
            key = resp_dict['sourceKey']
        else:
            print('No Source key found in response')
        url = '/api/sources/' + key + '/action_streams/'
        response_stream1 = c.post(url, {"name": "action-stream1",
                                       "streamDataType": "INTEGER",
                                       "streamPositionInCSV": 1 }, 
                                **self.auth_header)
        response_stream2 = c.post(url, {"name": "action-stream2",
                                       "streamDataType": "INTEGER",
                                       "streamPositionInCSV": 2 }, 
                                **self.auth_header)
        url_action = '/api/sources/' + key + '/action/'
        request_body = {"action-stream1" : 10, "action-stream2" : 20}
        response_action = c.post(url_action , content_type = "application/json", 
                          data=json.dumps(request_body), **self.auth_header)
        response_action_get = c.get(url_action, **self.auth_header)
        resp_dict_action = json.loads(response_action_get.content)
        if('insertionTime' in resp_dict_action):
            time = resp_dict_action['insertionTime']
        else:
            print('No insertion time found in response')
        body_patch = {'acknowledgement':1,'insertionTime': time}
        response_patch = c.patch(url_action, content_type = "application/json", 
                          data=json.dumps(body_patch), **self.auth_header)
        response_get_after_patch = c.get(url_action, **self.auth_header)
        resp_dict_after_patch = json.dumps(response_get_after_patch.data)
        resp_dict_after_patch_loads = json.loads(resp_dict_after_patch)
        length_streams = len(resp_dict_after_patch_loads['streams'])
        self.assertEqual(length_streams,0)
        self.assertEqual(response_action.status_code,201)
        self.assertEqual(response_patch.status_code,200)


    def test_action_patch_unauthenticated(self):
        c = Client()
        response_post = c.post('/api/sources/', {"name": "test_source",
                                                 "dataFormat": "JSON",
                                                 "dataReportingInterval": 0,
                                                 "isActive": True,
                                                 "isMonitored": True,
                                                  },
                               **self.auth_header)
        resp_dict = json.loads(response_post.content)
        if('sourceKey' in resp_dict):
            key = resp_dict['sourceKey']
        else:
            print('No Source key found in response')
        url = '/api/sources/' + key + '/action_streams/'
        response_stream1 = c.post(url, {"name": "action-stream1",
                                       "streamDataType": "INTEGER",
                                       "streamPositionInCSV": 1 }, 
                                **self.auth_header)
        response_stream2 = c.post(url, {"name": "action-stream2",
                                       "streamDataType": "INTEGER",
                                       "streamPositionInCSV": 2 }, 
                                **self.auth_header)
        url_action = '/api/sources/' + key + '/action/'
        request_body = {"action-stream1" : 10, "action-stream2" : 20}
        response_action = c.post(url_action , content_type = "application/json", 
                          data=json.dumps(request_body), **self.auth_header)
        response_action_get = c.get(url_action, **self.auth_header)
        resp_dict_action = json.loads(response_action_get.content)
        if('insertionTime' in resp_dict_action):
            time = resp_dict_action['insertionTime']
        else:
            print('No insertion time found in response')
        body_patch = {'acknowledgement':1,'insertionTime': time}
        response_patch = c.patch(url_action, content_type = "application/json", 
                          data=json.dumps(body_patch))
        self.assertEqual(response_action.status_code,201)
        self.assertEqual(response_patch.status_code,401)

    def test_action_patch_token_improper(self):
        c = Client()
        response_post = c.post('/api/sources/', {"name": "test_source",
                                                 "dataFormat": "JSON",
                                                 "dataReportingInterval": 0,
                                                 "isActive": True,
                                                 "isMonitored": True,
                                                  },
                               **self.auth_header)
        resp_dict = json.loads(response_post.content)
        if('sourceKey' in resp_dict):
            key = resp_dict['sourceKey']
        else:
            print('No Source key found in response')
        url = '/api/sources/' + key + '/action_streams/'
        response_stream1 = c.post(url, {"name": "action-stream1",
                                       "streamDataType": "INTEGER",
                                       "streamPositionInCSV": 1 }, 
                                **self.auth_header)
        response_stream2 = c.post(url, {"name": "action-stream2",
                                       "streamDataType": "INTEGER",
                                       "streamPositionInCSV": 2 }, 
                                **self.auth_header)
        url_action = '/api/sources/' + key + '/action/'
        request_body = {"action-stream1" : 10, "action-stream2" : 20}
        response_action = c.post(url_action , content_type = "application/json", 
                          data=json.dumps(request_body), **self.auth_header)
        response_action_get = c.get(url_action, **self.auth_header)
        resp_dict_action = json.loads(response_action_get.content)
        if('insertionTime' in resp_dict_action):
            time = resp_dict_action['insertionTime']
        else:
            print('No insertion time found in response')
        body_patch = {'acknowledgement':1,'insertionTime': time}
        response_patch = c.patch(url_action, content_type = "application/json", 
                          data=json.dumps(body_patch), **self.auth_header_improper)
        self.assertEqual(response_action.status_code,201)
        self.assertEqual(response_patch.status_code,401)



    def test_action_patch_authenticated_insertionTime_improper(self):
        c = Client()
        response_post = c.post('/api/sources/', {"name": "test_source",
                                                 "dataFormat": "JSON",
                                                 "dataReportingInterval": 0,
                                                 "isActive": True,
                                                 "isMonitored": True,
                                                  },
                               **self.auth_header)
        resp_dict = json.loads(response_post.content)
        if('sourceKey' in resp_dict):
            key = resp_dict['sourceKey']
        else:
            print('No Source key found in response')
        url = '/api/sources/' + key + '/action_streams/'
        response_stream1 = c.post(url, {"name": "action-stream1",
                                       "streamDataType": "INTEGER",
                                       "streamPositionInCSV": 1 }, 
                                **self.auth_header)
        response_stream2 = c.post(url, {"name": "action-stream2",
                                       "streamDataType": "INTEGER",
                                       "streamPositionInCSV": 2 }, 
                                **self.auth_header)
        url_action = '/api/sources/' + key + '/action/'
        request_body = {"action-stream1" : 10, "action-stream2" : 20}
        response_action = c.post(url_action , content_type = "application/json", 
                          data=json.dumps(request_body), **self.auth_header)
        response_action_get = c.get(url_action, **self.auth_header)
        resp_dict_action = json.loads(response_action_get.content)
        if('insertionTime' in resp_dict_action):
            time = resp_dict_action['insertionTime']
        else:
            print('No insertion time found in response')
        body_patch = {'acknowledgement':1,'insertionTime': '2015-12-31T11:20:45.530816Z'}
        response_patch = c.patch(url_action, content_type = "application/json", 
                          data=json.dumps(body_patch), **self.auth_header)
        response_get_after_patch = c.get(url_action, **self.auth_header)
        resp_dict_after_patch = json.dumps(response_get_after_patch.data)
        resp_dict_after_patch_loads = json.loads(resp_dict_after_patch)
        length_streams = len(resp_dict_after_patch_loads['streams'])
        self.assertNotEqual(length_streams,0)
        self.assertEqual(response_action.status_code,201)
        self.assertEqual(response_patch.status_code,200)