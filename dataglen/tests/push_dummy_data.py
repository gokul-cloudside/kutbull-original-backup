import unirest, sys, json

# Define ACCESS parameters
BASE_URL = "http://dataglen.com"
USER = 'root'
PASSWD = 'django99'

# Define sensor key and return message
KEY = "kaqwX5zUKnfNhh3"
RETURN_MESSAGE = 'File accepted. [(REMOTECONFIGQUERY)]'

response = unirest.patch(BASE_URL + "/dataglen/sensors/",
                         auth=(USER, PASSWD),
                         params = {
                             'sourceKey': KEY,
                             'textMessageWithHTTP200': RETURN_MESSAGE},
                         )
print response.code
sys.exit()

# no spaces between fields - each data line should be sent like this (clean up extra spaces present in mSend files)
DATA = "0.28,0.26,0.93,226.90,0.43,50.00,30.67,0.03,0.92,227.82,0.13,0.18,0.18,0.99,230.70,0.77,0.09,0.05,0.59,222.17,0.39,8209.32,7550.63,0.00,0.00,0.00,0,39371335,958,22:02:56,12/10/14,mSendC48B,RadioStudio,1"
DATA = "49.96,220.970,0.092,0.037,0.000,0.024,5.371,5.372,0.017,89.021,17:16:30:15/04/15,18FE349F5C6E,BPlug_Radiostudio,608\r\n"
#DATA = "49.96,220.970,0.092,0.037,0.000,0.024,5.371,5.372,0.017,89.021,17:16:10:15/04/15,18FE349F5C6E,BPlug_Radiostudio,608\r\n" \
#       "49.98,220.818,0.117,0.037,0.000,0.025,5.439,5.440,0.021,88.772,17:16:12:15/04/15,18FE349F5C6E,BPlug_Radiostudio,609\r\n" \
#       "49.96,221.005,0.008,0.037,0.000,0.024,5.299,5.299,0.001,89.916,17:16:14:15/04/15,18FE349F5C6E,BPlug_Radiostudio,610\r\n"


# data write
