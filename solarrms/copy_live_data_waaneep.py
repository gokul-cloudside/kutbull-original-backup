from datetime import datetime, timedelta
from django.utils import timezone
import datetime
import requests
import json
import sys
from multiprocessing.dummy import Pool as ThreadPool

dgc_server = 'http://dataglen.com/'
dgc_header = {'Authorization': 'Token 1971e093c790edb3fd5c38dc93029c317f5fe396',
              'Content-Type' : 'application/json'}

dgk_server = 'http://trial.dataglen.com/'
dgk_header = {'Authorization': 'Token 616dbf31f8c4050555d52733178c0aaa5a6e5822',
              'Content-Type' : 'application/json'}

def DG_get_dataSourceList(dg_server, dg_header):
    dg_get_url = dg_server + 'api/sources/'
    r = requests.get(dg_get_url, headers=dg_header)
    return r

def get_smb_keys():
    print datetime.datetime.now().isoformat(), 'getting data from ', dgc_server
    dgc_dsList = DG_get_dataSourceList(dgc_server, dgc_header).json()
    print datetime.datetime.now().isoformat(), 'getting data from ', dgk_server
    dgk_dsList = DG_get_dataSourceList(dgk_server, dgk_header).json()

    smb_dict = {}
    smb_list = list()
    index = 0
    for dgk_source in dgk_dsList:
        dgk_name = dgk_source['name']
        dgk_key = dgk_source['sourceKey']
        #if False == dgk_name.startswith('TATA_SMB_'):
        #        continue

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
        
        key_dict = {'name': dgk_name, 'from': dgc_key, 'to': dgk_key}        
        smb_list.insert(index, key_dict)
        index = index + 1
        #print dgk_name, dgc_name, dgk_key, dgc_key, key_dict

    return (smb_dict, smb_list)

def copy_smb_data(smbkeys):
    from_API_key = '1971e093c790edb3fd5c38dc93029c317f5fe396'
    to_API_key = '616dbf31f8c4050555d52733178c0aaa5a6e5822'
    from_server_address = 'https://dataglen.com'
    sources_url = '/api/sources/'
    to_server_address = 'http://trial.dataglen.com'
    #current_time = datetime.datetime.now()
    current_time = timezone.now()
    initial_time = current_time - datetime.timedelta(minutes=5)
    from_token = 'Token ' + from_API_key
    to_token = 'Token ' + to_API_key
    from_auth_header = {'Authorization': from_token}
    params = {'startTime': str(initial_time), 'endTime': str(current_time)}
    #print datetime.datetime.now().isoformat(), "params ", params

    smbname = smbkeys['name']
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
         # for i in range(max(stream_values_count)):
        for i in sorted(range(max(stream_values_count)), reverse=True):  # post the older value first
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
        print datetime.datetime.now().isoformat(), smbname, 'Exception ', str(exception)
        pass

def copy_waaneep_data():
    try:
        print datetime.datetime.now().isoformat(), "copy_waaneep_data CRONJOB STARTED"

        (smb_dict, smb_list) = get_smb_keys()

        print datetime.datetime.now().isoformat(), 'storing dict'
        with open('./waaree_smb_data.json', 'w') as outfile:
            json.dump(smb_dict, outfile, indent=3, sort_keys=True)

        #tstart = datetime.datetime.now()
        #print datetime.datetime.now().isoformat(), 'SEQUENTIAL START'
        #for smb in smb_list:
        #    print datetime.datetime.now().isoformat(), 'processing ', smb['name']
        #    copy_smb_data(smb)
        #print datetime.datetime.now().isoformat(), 'SEQUENTIAL END'    
        #tend = datetime.datetime.now()
        #print datetime.datetime.now().isoformat(), 'DURATION ', (tend-tstart)

        tstart = datetime.datetime.now()
        print datetime.datetime.now().isoformat(), "UPLOADING STARTED"
        threads = 5
        pool = ThreadPool(threads)
        results = pool.map(copy_smb_data, smb_list)
        pool.close()
        pool.join()
        #print results
        tend = datetime.datetime.now()
        print datetime.datetime.now().isoformat(), 'DURATION ', (tend-tstart)
        print datetime.datetime.now().isoformat(), "UPLOADING STOPPTED"
        print datetime.datetime.now().isoformat(), "copy_waaneep_data CRONJOB STOPPTED"        
    except Exception as exception:
        print datetime.datetime.now().isoformat(), "copy_waaneep_data CRONJOB Exception ", str(exception)

#copy_waaneep_data()


