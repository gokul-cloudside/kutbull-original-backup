from django.utils import timezone
import datetime
import requests
import json
import sys

from_inverters = ['BzrHE4UdAk0uHPn','40vUT72mrB16fKK','QEnXQPUjLavwdpm','3klk15PkzALckD5','8RpSsaF77A9P8zi','67R10ayrsLEII8b',
                  'rK71TioXn3EvDlI','oSADDPlHUZXVqdA','o1cUvU82ZaXFrIc','llkvzBRDrUWamW3','aSYFJ4iVqbqExQ6','uAuiQafsdt52JUX',
                  'QLDDcvkvZqIiVf5','eXDwDQIZ62PmUpm','TNmebneZN9plrot','Bc3GvR2GsY6UX7T']

to_inverters = ['2yrRPgXXTKM2pzY','oH0HqsvYlsS440C','b3hu0SqNNsbJewT','ax6FRDdUlaYc9DZ','jEhtvMIB3Rw8bLD','WpHOeH9IJZQ03oC',
                'z0kWpe0Pi2eTw0c','c9GqU32xIfHooW7','RZDtHY4jtzJYpWo','GD7fdnmpSRTVd8J','YKTf9yua0iXDb97','eZbkt96GpmzuLkB',
                'qCoKS6PDORdrE7j','aaniAxuoIBuyhvl','BurRt0M9cnrKfqN','uoVqfRACRykrBQg']

from_API_key = '540becf583a19f49672968c6b76789e414ac95ca'
to_API_key = 'd1579eddece24742df3063de2b7c482937cd67c1'

from_gateway = 'USS8Ff463UCpNJk'
to_gateway = 'mNUGTwZBJbx3z56'
from_meta = 'MCeJjp00uvLaxas'
to_meta = 'XdHlBLCUSy6Avo7'

from_server_address = 'https://dataglen.com'
sources_url = '/api/sources/'
to_server_address = 'http://104.200.23.242'
current_time = timezone.now()
initial_time = current_time - datetime.timedelta(minutes=10)
from_token = 'Token ' + from_API_key
to_token = 'Token ' + to_API_key
from_auth_header = {'Authorization': from_token}
params = {'startTime': str(initial_time), 'endTime': str(current_time)}

def test_balancer():
    try:
        # copy the gateway data
        from_gateway_url = from_server_address + sources_url + str(from_gateway) + '/data/'
        to_gateway_url = to_server_address + sources_url + str(to_gateway) + '/data/'
        response = requests.get(from_gateway_url, headers=from_auth_header, params=params)
        response_json = json.loads(response.content)
        stream_values = []
        stream_values_count = []
        for i in range(len(response_json['streams'])):
            if int(str(response_json['streams'][i]['count'])) != 0:
                stream_values.append(response_json['streams'][i])
                stream_values_count.append(response_json['streams'][i]['count'])
        try:
            for i in range(max(stream_values_count)):
                post_body = {}
                for j in range(len(stream_values)):
                    if str(stream_values[j]['name']) == 'TIMESTAMP' and stream_values[j]['values'][i]:
                        post_body[str(stream_values[j]['name'])] = str(stream_values[j]['values'][i])
                    elif str(stream_values[j]['name']) != 'TIMESTAMP' and stream_values[j]['values'][i]:
                        post_body[str(stream_values[j]['name'])] = float(stream_values[j]['values'][i])
                    else:
                        pass
                print(post_body)
                length = sys.getsizeof(post_body)
                to_auth_header = {'Authorization': to_token, 'content-length': length, 'content-type': 'application/json'}
                response_post = requests.post(to_gateway_url , data = json.dumps(post_body) , headers = to_auth_header)
                print(response_post.status_code)
        except Exception as exception:
            print(str(exception))
            pass


        #copy the plant meta data
        from_meta_url = from_server_address + sources_url + str(from_meta) + '/data/'
        to_meta_url = to_server_address + sources_url + str(to_meta) + '/data/'
        response = requests.get(from_meta_url, headers=from_auth_header, params=params)
        response_json = json.loads(response.content)
        stream_values = []
        stream_values_count = []
        for i in range(len(response_json['streams'])):
            if int(str(response_json['streams'][i]['count'])) != 0:
                stream_values.append(response_json['streams'][i])
                stream_values_count.append(response_json['streams'][i]['count'])
        try:
            for i in range(max(stream_values_count)):
                post_body = {}
                for j in range(len(stream_values)):
                    if str(stream_values[j]['name']) == 'TIMESTAMP' and stream_values[j]['values'][i]:
                        post_body[str(stream_values[j]['name'])] = str(stream_values[j]['values'][i])
                    elif str(stream_values[j]['name']) != 'TIMESTAMP' and stream_values[j]['values'][i]:
                        post_body[str(stream_values[j]['name'])] = float(stream_values[j]['values'][i])
                    else:
                        pass
                print(post_body)
                length = sys.getsizeof(post_body)
                to_auth_header = {'Authorization': to_token, 'content-length': length, 'content-type': 'application/json'}
                response_post = requests.post(to_meta_url , data = json.dumps(post_body) , headers = to_auth_header)
                print(response_post.status_code)
        except Exception as exception:
            print(str(exception))
            pass

        #copy inverters data
        for index in range(len(from_inverters)):
            from_url = from_server_address + sources_url + str(from_inverters[index]) + '/data/'
            to_url = to_server_address + sources_url + str(to_inverters[index]) + '/data/'
            response = requests.get(from_url, headers=from_auth_header, params=params)
            response_json = json.loads(response.content)
            stream_values = []
            stream_values_count = []
            for i in range(len(response_json['streams'])):
                if int(str(response_json['streams'][i]['count'])) != 0:
                    stream_values.append(response_json['streams'][i])
                    stream_values_count.append(response_json['streams'][i]['count'])
            try:
                for i in range(max(stream_values_count)):
                    post_body = {}
                    for j in range(len(stream_values)):
                        if str(stream_values[j]['name']) == 'TIMESTAMP' and stream_values[j]['values'][i]:
                            post_body[str(stream_values[j]['name'])] = str(stream_values[j]['values'][i])
                        elif str(stream_values[j]['name']) != 'TIMESTAMP' and stream_values[j]['values'][i]:
                            post_body[str(stream_values[j]['name'])] = float(stream_values[j]['values'][i])
                        else:
                            pass
                    print post_body
                    length = sys.getsizeof(post_body)
                    to_auth_header = {'Authorization': to_token, 'content-length': length, 'content-type': 'application/json'}
                    response_post = requests.post(to_url , data = json.dumps(post_body) , headers = to_auth_header)
                    print(response_post.status_code)
            except Exception as exception:
                print(str(exception))
                pass
    except Exception as exception:
        print str(exception)