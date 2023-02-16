from datetime import datetime, timedelta
from django.utils import timezone
import datetime
import requests
import json
import sys

def copy_alpine_data():
    try:
        print("alpine data copy cronjob started")
        from_inverters = ['aKhB7G4OKaeu1QZ','kk13E8AUlbGKnfz','24OtYMV6MYIStar', 'sshACDtQmndgx22','FaXbAEnqc1D8TUa', 'SNAaefRWYVCdAjZ', 'tFE5TQ39lRuq5i4', 'tR7WDcmD6ChCur1', 'RzQXyDOMsuJttiP', 'YgrE1UiA3snWeP7']
        to_inverters = ['qzDBYp6CxuMtuv7', 'cH5fsJt46x5NFQZ', 'LQSjr1XE7RVWVek', 'cVFBehixE5TWqDP', 'UA0xFLO1UrIu8gR', 'tCkyv8uwzDJFlfM','0LUQOnL8aOPpTIG','qFdellZTqUnqINi', '1egtaG3QT5C5JfD', 'zDGrYE1AJO2XWl2']
        from_gateway = 'PsUuKYYbi2JNKkY'
        to_gateway = 'Ua9uVs2jIJCBM18'
        from_meta = '82ADfYzxEXIy4f2'
        to_meta = '5U36bUziOQ9acnm'
        from_API_key = '13fcd7319bb9ae25bf7ea290f9f2ba8eca2e41bc'
        to_API_key = '6991d6c406a9d7f60428e255a8def0deec50c1ec'
        from_server_address = 'https://dataglen.com'
        sources_url = '/api/sources/'
        to_server_address = 'http://kafka.dataglen.org'
        current_time = timezone.now()
        initial_time = current_time - datetime.timedelta(minutes=10)
        from_token = 'Token ' + from_API_key
        to_token = 'Token ' + to_API_key
        from_auth_header = {'Authorization': from_token}
        params = {'startTime': str(initial_time), 'endTime': str(current_time)}


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


        # Copy the inverter data
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
                    length = sys.getsizeof(post_body)
                    to_auth_header = {'Authorization': to_token, 'content-length': length, 'content-type': 'application/json'}
                    response_post = requests.post(to_url , data = json.dumps(post_body) , headers = to_auth_header)
                    print(response_post.status_code)
            except Exception as exception:
                print(str(exception))
                pass
    except Exception as exception:
        print(str(exception))


dgc_server = 'http://dataglen.com/' 
dgc_header = {'Authorization': 'Token 1971e093c790edb3fd5c38dc93029c317f5fe396',
              'Content-Type' : 'application/json'}

dgk_server = 'http://kafka.dataglen.org/' 
dgk_header = {'Authorization': 'Token 29be146a882cff0701598a64643db422e5251c28',
              'Content-Type' : 'application/json'}

def DG_get_dataSourceList(dg_server, dg_header):
    dg_get_url = dg_server + 'api/sources/'
    r = requests.get(dg_get_url, headers=dg_header)
    return r

dgc_dsList = DG_get_dataSourceList(dgc_server, dgc_header).json()
dgk_dsList = DG_get_dataSourceList(dgk_server, dgk_header).json()

smb_dict = {} 
for dgk_source in dgk_dsList:
    dgk_name = dgk_source['name']
    dgk_key = dgk_source['sourceKey']
    #if False == dgk_name.startswith('TATA_SMB_'):
    #    continue

    #dgk_name1 = dgk_name.replace('TATA_', '')
    dgc_source_found = None
    for dgc_source in dgc_dsList:
        if dgc_source['name'] == dgk_name:
            dgc_source_found = dgc_source
    if dgc_source_found == None:
        continue

    dgc_name = dgc_source_found['name']
    dgc_key = dgc_source_found['sourceKey']
    key_dict = {'from': dgc_key, 'to': dgk_key}
    smb_dict[dgk_name] = key_dict
    #print dgk_name, dgc_name, dgk_key, dgc_key, key_dict

with open('./waaree_smb_data.json', 'w') as outfile:
    json.dump(smb_dict, outfile, indent=3, sort_keys=True)


# this fun is obsolete now. see copy_live_data_waaneep.py        
def copy_waaneep_data():
    try:
        print("waaneep data copy cronjob started", datetime.datetime.now().isoformat(), len(smb_dict) )
        #          
        from_inverters = ['KxkVfuaDbAiA3Xg', '9cNsxyWxQMQrpMK', 'mourZhJAJdKqV39', 'AM21XTY6Mn14idI', 
                          'GW4mdfs5lo0rBEb', 'OJkgKULGDZEq8Xx', 'ijsqwfMo5fm4iYm', '5DDWfdQMBK3sH8k', 
                          'wNnYEMHe8CIh9hq', 'Z0RYdU5ROMgxM4H', 'ApA7bYDit1t8Z0J', 'S5EhrWYxv9MWdOs']  # Inverter_1.x, 2.x, 3.x
        to_inverters   = ['aQmjwzhuh4VrESz', '7hMvJ426ttQyj8z', 'bBk5wJRgbIRjdsG', 'L1bEINBcluUsi8k', 
                          'nTdCrhphVr1KnFW', 'jeFbmJ2r0N5eiDV', '3qz1lh3iJhSqzrC', 'dZehF4kvc5jFcm0', 
                          'ZmWGn8BH53uzqz5', '8oJ8LuzGcMci8Id', 'D8Y4WUFsIjEBaip', 'yXtGnoS6eSMDoKR']
          # smb_1.* and smb_2.*
        from_smbs = ['MCAv347WBmMDYzB', 'euxxWUP9ft1vXBK', '5FqdM22QIQHjA6w', 'wSCEHBH8oNhe1XG', 'XmH5a99XwZ2HG39', 'RVYz0Ik5D2Fqvht',
                     'e9rKSTMToewRdVL', '0U5R8MiaHESIvRc', '14gbiu3EtzwxUcS', 'Qq323Sen99hOrIa', 'l5ziQSy21uHoMZ8', 'NHKAYfmf8CPVcYc',
                     'Kvi4C7437LTG3T3', 'NPYm4PiWKHQK5Op', 'HpRhvR0kFr0He6K', 'N9PTxWLuAa50jGI', 'st68vLOgARQ3Lvb', '6xK5BYhqhBPmkg9',
                     'zKmecs1fGJQdX6m', 'aXrIQpYEhuR0mwl', 'W9bye9Jzbim4XBI', 'T12SVuYcdxja9d2', 'fIhrwDfusAnjmNX', 'QOrXZFWmQI3hy7A',
                     'oLOtYUTr0OTXVqw', 'vVRkBnnQBQDaD1W', 'hdNwjHs8ac9vvew', '5s1SCu7dhuO2phX', 'VRllKfXsWMwOwk5', 'cgs68jQzpYGDvKc',
                     '1KZsMYQYCsqvnIc', '32Rr8rvX5udmmP9', 'kVOVuxuEJTMZOwx', 'j6wPk1TvxoBUldt', 'hFMxNAzDV5G6OY2', 'EKopcPY0KbNYygz',
                     'woDZEcYmnrA2fxv', 'mwI6UeaQ4JeEixy', 'UPqpJx6vFQArjaz', '9M9l7Hr6udF2thu', 'pBBuBtaVPES9q5l', 'H5ogtUD5PulSF5y',
                     'oDrt8JOhG6uWHjx', 'SAVUmSGmLpXU6Tl', '8NRZP6lcZaQsBx2', '2IrqAZ7m4dChksd', 'N5Cl9fA46IF9LKm', 'R9hzDGUdWz9VNEN']

        to_smbs =   ['55ANtZJ58LRpO8H', 'SgBtXYM3idaETLx', 'GTAq3VKped4P3Yc', 'DuVIiik8hSRG9Ex', 'ejeFfwZ4PFmEsX7', 'rqssfsMJXs2dWk1',
                     '93cf2xfW3bIbqof', 'fiIt8ALAqAPr130', '6KFQSaRBSJMpALP', '61UNLv42qswe1D7', 'D3oDWkpfUSssbnX', 'xeGsIRYb2jZaEqv',
                     'zWHnoGJSFhqhojp', 'mC6DoCJzrPQKryC', 'pxJ6yZW2mzVHlDA', 'aMA8DKVeAZJGUiL', 'dDBagVhQBoMa9Wf', 'zUAstet11nGATwN',
                     'AnZC2GG3iA1heCc', 'vP6H0QoK7aeahzm', 'xOuj9Qqqzu6sYCM', '66VKo3YfoyzzytR', 'vkDL7Moi73MiUJF', 'zFOSIlr1fN35NEW',
                     'tn1X3cyGuaje6GL', 'UvId6XDxT9NaI6Z', '6rHcSznHZ16pbf7', 'QD7puDqDXpXGz7S', 'dJVBtRFV1KzqDkw', 'kuiMctUydr2ZsHM',
                     'kKO1ZLWRZc8cZAA', 'fJkoY4kR3m9bWhw', 'qX3vNeV7p2vrjSj', '65HCnorECCEyeGJ', 'DyKiRRaaASE4a8g', 'bE3K5P014VuG7qY',
                     'eCOWUr10l3pOWDW', 'mUcOWq2Zpu6Jnp6', 'KXtVdbbq4OsjgGR', 'k36KLEL872CcKa0', '5UjR416lgkxVOhh', '9LNiE07PG93DXZK',
                     'KUIzmfjTeTD3OHH', 'wxITmVPdqZSh5av', 'rylpSVR6CF4LyB1', '0CxMI2oOEwWB8j8', '2zYGMVioGJMOA6p', 'p24bVhhVpJqp3Ro']

        #from_smbs = ["e9rKSTMToewRdVL", "0U5R8MiaHESIvRc", "14gbiu3EtzwxUcS", "Qq323Sen99hOrIa", "l5ziQSy21uHoMZ8", "NHKAYfmf8CPVcYc"] # SMB_1.2.*
        #to_smbs =   ["93cf2xfW3bIbqof", "fiIt8ALAqAPr130", "6KFQSaRBSJMpALP", "61UNLv42qswe1D7", "D3oDWkpfUSssbnX", "xeGsIRYb2jZaEqv"]        
        from_gateway = 'n0d29HN0ExXTEOR'  # Waaneep_Gateway
        to_gateway = 'T8p2JjllPjwhpnV'
        from_meta = 'O9SkB6yuxo63uBs'  # Waaneep_Plant_Meta
        to_meta = 'fsm2Xn14vwsXStj'
        from_API_key = '1971e093c790edb3fd5c38dc93029c317f5fe396'
        to_API_key = '29be146a882cff0701598a64643db422e5251c28'
        from_server_address = 'https://dataglen.com'
        sources_url = '/api/sources/'
        to_server_address = 'http://kafka.dataglen.org'
        current_time = timezone.now()
        initial_time = current_time - datetime.timedelta(minutes=20)
        from_token = 'Token ' + from_API_key
        to_token = 'Token ' + to_API_key
        from_auth_header = {'Authorization': from_token}
        params = {'startTime': str(initial_time), 'endTime': str(current_time)}


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


        # Copy the inverter data
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
                    print(post_body)
                    length = sys.getsizeof(post_body)
                    to_auth_header = {'Authorization': to_token, 'content-length': length, 'content-type': 'application/json'}
                    response_post = requests.post(to_url , data = json.dumps(post_body) , headers = to_auth_header)
                    print(response_post.status_code)
            except Exception as exception:
                print(str(exception))
                pass

        # Copy the SMBr data
        #for index in range(len(from_smbs)):
        #    from_url = from_server_address + sources_url + str(from_smbs[index]) + '/data/'
        #    to_url = to_server_address + sources_url + str(to_smbs[index]) + '/data/'
        for (smbname,smbkeys) in smb_dict.items():
            #print smbname, smbkeys
            from_smb = smbkeys['from']
            to_smb = smbkeys['to']
            from_url = from_server_address + sources_url + str(from_smb) + '/data/'
            to_url = to_server_address + sources_url + str(to_smb) + '/data/'

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
                    #print(post_body)
                    length = sys.getsizeof(post_body)
                    to_auth_header = {'Authorization': to_token, 'content-length': length, 'content-type': 'application/json'}
                    response_post = requests.post(to_url , data = json.dumps(post_body) , headers = to_auth_header)
                    print datetime.datetime.now().isoformat(), smbname, response_post.status_code
            except Exception as exception:
                print datetime.datetime.now().isoformat(), smbname, str(exception)
                pass

        print("waaneep data copy cronjob stopped", datetime.datetime.now().isoformat() )
    except Exception as exception:
        print(str(exception))
