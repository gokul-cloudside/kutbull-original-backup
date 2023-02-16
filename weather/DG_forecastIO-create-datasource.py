
# coding: utf-8

# In[1]:

import os
import pandas as pd
import requests
import requests
import time
import json


# In[2]:

dg_server = 'http://192.168.63.136:8000/'
dg_header = {'Authorization': 'Token f9482341323906bd26aade901db5a24218d55caf',
             'Content-Type' : 'application/json'}


# In[3]:

def DG_get_dataSourceList():    
    dg_get_url = dg_server + 'api/sources/'
    r = requests.get(dg_get_url, headers=dg_header)
    return r

def DG_get_dataStreamList(dsKey):    
    dg_get_url = dg_server + 'api/sources/' + dsKey + '/streams/'
    r = requests.get(dg_get_url, headers=dg_header)
    return r

def DG_create_datasource(payload):
    dg_post_url = dg_server + 'api/sources/'
    r = requests.post(dg_post_url, headers=dg_header, data=json.dumps(payload))            
    return r

def DG_create_datastream(dskey, payload):    
    dg_post_url = dg_server + 'api/sources/' + dskey + '/streams/'
    r = requests.post(dg_post_url, headers=dg_header, data=json.dumps(payload))
    return r

def DG_delete_datasource(dsKey):
    dg_del_url = dg_server + 'api/sources/' + dsKey + '/'
    r = requests.delete(dg_del_url, headers=dg_header)            
    return r


# In[4]:

##################################################################################################################
############################## SUMMARY OF EXISTING DATASOURCE AND DATASTREAMS ####################################
##################################################################################################################
def SUMMARY_OF_DATASOURCES(source_prefix):
    dataSourceList = DG_get_dataSourceList().json()
    len(dataSourceList)

    for source in dataSourceList:
        if source['name'].startswith(source_prefix):
            print "\n", source['name'], source['sourceKey']
            dataStreamList = DG_get_dataStreamList (source['sourceKey']).json()    
            stList = []
            for stream in dataStreamList:
                stList.append(stream['name'])
            print "\t No. Streams ", len(stList)
            print "\t", stList


# In[5]:

##################################################################################################################
############################## DELETE DATASOURCE  ####################################
##################################################################################################################
def DELETE_ALL_DATASOURCES(source_prefix):
    dataSourceList = DG_get_dataSourceList().json()
    len(dataSourceList)

    for source in dataSourceList:
        if source['name'].startswith(source_prefix):
            print "Deleting ", source['name'], source['sourceKey']
            res = DG_delete_datasource (source['sourceKey'])
            if res.status_code != 204:
                print res.status_code, res.text


# In[6]:

##################################################################################################################
############################## CREATE NEW DATASOURCE ####################################
##################################################################################################################

# {"name":"ForecastIO-Palladam-Temperature1","dataReportingInterval":3600, "dataFormat":"JSON","isActive":true,"isMonitored":true,"timeoutInterval":7200}

ds_payload = { "name" : "",
               "dataReportingInterval": 3600,
               "dataFormat":"JSON",
               "isActive":True,
               "isMonitored":True,
               "timeoutInterval":7200 }

def CREATE_NEW_DATASOURCES(attributes):
    source_list = {}
    for atrib in attributes:
        if atrib == "time":
            continue        
        ds_payload["name"] =source_prefix + atrib
        #print ds_payload
        r = DG_create_datasource(ds_payload)
        
        if r.status_code == 201:
            source_list [source_prefix + atrib] = r.json()['sourceKey']
            print source_prefix + atrib + " = " + r.json()['sourceKey']
        else:
            print atrib, r.status_code, r.text
    return source_list


# In[7]:

##################################################################################################################
############################## CREATE NEW DATASTREAM ####################################
##################################################################################################################

unitList = {    'apparentTemperature' : 'Degree Celsius (C)', 
                'cloudCover' : 'Percentage (%)', 
                'dewPoint' : 'Degree Celsius (C)',
                'humidity' : 'Percentage (%)', 
                'icon' : 'Text', 
                'ozone' : 'Dobson', 
                'precipIntensity' : 'mm/hr', 
                'precipProbability' : 'Probability', 
                'precipType' : 'Text', 
                'pressure' : 'Hectopascals', 
                'summary' : 'Text', 
                'temperature' : 'Degree Celsius (C)', 
                'visibility' : 'Kilometers',                     
                'windBearing' : 'Degree', 
                'windSpeed' : 'meter/sec'}

dataTypeList = {'apparentTemperature' : 'FLOAT', 
                'cloudCover' : 'FLOAT', 
                'dewPoint' : 'FLOAT', 
                'humidity' : 'FLOAT', 
                'icon' : 'STRING', 
                'ozone' : 'FLOAT', 
                'precipIntensity' : 'FLOAT', 
                'precipProbability' : 'FLOAT', 
                'precipType' : 'STRING', 
                'pressure' : 'FLOAT', 
                'summary' : 'STRING', 
                'temperature' : 'FLOAT', 
                'visibility' : 'FLOAT',                 
                'windBearing' : 'FLOAT',
                'windSpeed' : 'FLOAT'}

def CREATE_NEW_DATASTREAMS(source_list):
    for dsName, dsKey in source_list.iteritems():
        print "\n", dsName, dsKey, dsName.split("-")[2]
        
        name = dsName.split("-")[2]

        # first add TIMESTAMP stream
        dsm_payload = {"name" : "TIMESTAMP", "streamDataType": "TIMESTAMP", "streamDataUnit": ""}
        r = DG_create_datastream(dsKey, dsm_payload)
        if r.status_code == 201:
            print "\t", "TIMESTAMP", r.status_code
        else:
            print "\t", "TIMESTAMP", r.status_code, r.text
            
        # there are 49 entries in the hourly clause in the forecast api call response
        # create 50datastreams.. temperature (current), temperature0 (forecast), temperature1, ...., temperature48
        for i in range(-1,49):
            if i == -1:
                nameNew = name
            else: 
                nameNew = name + str(i)
                
            dsm_payload = {"name" : nameNew,
                       "streamDataType": dataTypeList[name],
                       "streamDataUnit": unitList[name]}
            r = DG_create_datastream(dsKey, dsm_payload)
            if r.status_code == 201:
                print "\t", nameNew, r.status_code, 
            else:
                print "\t", nameNew, r.status_code, r.text,

        #time.sleep(2)


# In[59]:

server = "https://api.forecast.io/forecast/"
citygeo = "10.99,77.287" # palladam
#citygeo = "12.971599,77.594563" # bangalore
apikey = "a57f7f5faeebdfc290b311ebd31f8c12"

# url = "https://api.forecast.io/forecast/a57f7f5faeebdfc290b311ebd31f8c12/10.99,77.287"
url = server + apikey + "/" + citygeo
response = requests.get(url).json()
attributes = response['currently'].keys()
response['currently']


# In[52]:

#source_prefix = "ForecastIO-Musiri-"
source_prefix = ""


# In[53]:

SUMMARY_OF_DATASOURCES(source_prefix)


# In[54]:

DELETE_ALL_DATASOURCES(source_prefix)


# In[55]:

source_list = CREATE_NEW_DATASOURCES(attributes)


# In[56]:

CREATE_NEW_DATASTREAMS(source_list)


# In[57]:

SUMMARY_OF_DATASOURCES(source_prefix)

