import os, pytz

from rest_framework import status
from django.utils import timezone
import socket

import django
django.setup()
from django.utils.encoding import smart_str, force_str
django.utils.encoding.smart_text = smart_str

django.utils.encoding.force_unicode = force_str


# TODO Take sensitive information out of settings.py - such as database names/passwords.
# TODO https://code.djangoproject.com/wiki/SplitSettings
# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.7/howto/deployment/checklist/
# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = '0ad%xbt$pvy&)7psam8ltkjss^u3ir^9p&ur508bf27$7)w3(0'

CASSANDRA_UPDATE = True

# SECURITY WARNING: don't run with debug turned on in production!
hostname = socket.gethostname()
if hostname in ["dataglen.com", "dgn.dataglen.net", "preprod.dataglen.com", "dataglen-prod-01", "dataglen-clone-1",
                "dataglen-clone-3", "dataglen-clone-2"]:
    DEBUG = False
else:
    DEBUG = True

ALLOWED_HOSTS = ['45.33.127.43', '176.58.122.184', '104.237.130.172', '35.198.197.69',
                 '106.51.119.81', 'www.dataglen.com','45.33.125.58', '35.197.135.44', '35.186.145.141',
                 'dev.dataglen.com', 'dataglen.com', 'dataglen.net', 'www.dataglen.net',
                 'kafka.dataglen.org', 'preprod.dataglen.com', 'clone.dataglen.com', 'g.clone.dataglen.com',
                 'solarestimator.dataglen.com', '35.186.234.168', 'clone03.dataglen.com', 'dataglen-clone-1',
                 '35.247.142.158 ']

'''
    LIST OF INSTALLED APPLICATIONS
'''
# Application definition
INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',
    'django.contrib.humanize',
    'bootstrapform',
    'bootstrap3',
    'rest_framework',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'django_extensions',
    'django_crontab',
    'dashboards',
    'dataglen',
    'organizations',
    'website',
    'rest',
    'logger',
    'cronjobs',
    'monitoring',
    'captcha',
    'rest_framework.authtoken',
    'rest_framework_swagger',
    'rest_auth',
    'solarrms',
    'ioelab',
    'action',
    'config',
    'events',
    'reports',
    'hijack',
    'compat',
    'hijack_admin',
    'customwidgets',
    'errors',
    'corsheaders',
    'helpdesk',
    'dwebdyn',
    'dgusers',
    'features',
    'widgets',
    'oandmmanager',
    'otp',
    'screamshot',
    'microgrid',
    'django_comments',
    'dgcomments',
    'tagging',
    'solarrms2',
    'eventsframework',
    'dganalysis',
    'license'
)

HOST_IP = ['104.237.130.172']
if CASSANDRA_UPDATE:
    HOST_IP = ['10.148.0.14', '10.148.0.15']

INSTALLED_APPS = ('django_cassandra_engine',) + INSTALLED_APPS
SITE_ID = 1
COMMENTS_APP = 'dgcomments'

AUTHENTICATION_BACKENDS = (
    # Needed to login by username in Django admin
    'django.contrib.auth.backends.ModelBackend',
    # `allauth` specific authentication methods, such as login by e-mail
    'allauth.account.auth_backends.AuthenticationBackend',
)
INVITATION_BACKEND = 'dashboards.defaults.DataglenInvitationBackend'

ANONYMOUS_USER_ID = None
ACCOUNT_ADAPTER = ('dataglen.account_adapter.NoNewUsersAccountAdapter')
#ACCOUNT_ADAPTER = 'invitations.models.InvitationsAdapter'
ACCOUNT_AUTHENTICATION_METHOD = ("email")
ACCOUNT_CONFIRM_EMAIL_ON_GET = (True)

ACCOUNT_EMAIL_CONFIRMATION_ANONYMOUS_REDIRECT_URL = ("/accounts/signup/")
ACCOUNT_EMAIL_CONFIRMATION_AUTHENTICATED_REDIRECT_URL = ("/dataglen/")
ACCOUNT_EMAIL_CONFIRMATION_EXPIRE_DAYS = (7)
ACCOUNT_DEFAULT_HTTP_PROTOCOL = "https"
ACCOUNT_EMAIL_REQUIRED = (True)
ACCOUNT_EMAIL_VERIFICATION = ("mandatory")
ACCOUNT_LOGOUT_ON_GET = (True)
ACCOUNT_LOGOUT_REDIRECT_URL = ("/")
ACCOUNT_SIGNUP_PASSWORD_VERIFICATION = (True)
ACCOUNT_UNIQUE_EMAIL = (True)
ACCOUNT_USERNAME_REQUIRED = ("True")
ACCOUNT_USERNAME_MIN_LENGTH = (5)
ACCOUNT_PASSWORD_MIN_LENGTH = (6)
ACCOUNT_LOGIN_ON_EMAIL_CONFIRMATION = (True)
ACCOUNT_SESSION_COOKIE_AGE = (1209600)


ACCOUNT_SIGNUP_FORM_CLASS = 'dataglen.forms.SignupForm'

#INVITATIONS_INVITATION_ONLY = True

RECAPTCHA_PUBLIC_KEY = '6Ld39wUTAAAAAPejEbOFj0VLQfGPsDtEK9kc7moD'
RECAPTCHA_PRIVATE_KEY = '6Ld39wUTAAAAAFmX1FDfxIfhRdLOHWmTwJsojh6l'
RECAPTCHA_USE_SSL = True
NOCAPTCHA = True
DEBUG_TOOLBAR_PATCH_SETTINGS = False
INTERNAL_IPS = ('127.0.0.1',)

'''
    MIDDLEWARE DETAILS
'''
MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

CORS_ORIGIN_ALLOW_ALL = True

ROOT_URLCONF = 'kutbill.urls'
WSGI_APPLICATION = 'kutbill.wsgi.application'


'''
    DATABASE DETAILS.
    MYSQL AND CASSANDRA
'''
DATABASES = {
    'default' : {
        'ENGINE': 'django.db.backends.mysql',
        'NAME' : 'dataglen_meta1',
        'USER' : 'root',
        'PASSWORD': 'password',
        'HOST': '127.0.0.1',
        'PORT' : '3306',
    },

    'cassandra': {
        'ENGINE': 'django_cassandra_engine',
        'NAME': 'dataglen_data',
        'TEST_NAME': 'test_dataglen',
        'HOST': '35.208.221.234',
        'USER': 'cassandra',
        'PASSWORD': 'cassandra',
        'PORT': '9046',
        'OPTIONS': {
            'replication': {
                'strategy_class': 'SimpleStrategy',
                'replication_factor': 1
            },
            'session': {
                'default_timeout': None,
                'default_fetch_size': None,
            }
        }
    }
}

if CASSANDRA_UPDATE:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': 'dataglen_meta',
            'USER': 'myuser_',
            'PASSWORD': 'mypass',
            'HOST': '35.208.221.234',
            'PORT': '9042',
        },

        'cassandra': {
            'ENGINE': 'django_cassandra_engine',
            'NAME': 'dataglen_data',
            'TEST_NAME': 'test_dataglen',
            'HOST': '10.148.0.14,10.148.0.15',
            'USER': 'cassandra',
            'PASSWORD': 'cassandra',
            'OPTIONS': {
                'replication': {
                    'strategy_class': 'SimpleStrategy',
                    'replication_factor': 2
                },
                'schema_metadata_enabled': False,
                'session': {
                    'default_timeout': None,
                    'default_fetch_size': None,
                }
            }
        }
    }

# Password validation
# https://docs.djangoproject.com/en/4.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Define a router for logging application since we're using a separate database
#DATABASE_ROUTERS = ['logger.routers.LogRouter',]

'''
    LOGGING. DIFFERENT HANDLERS FOR BOTH DATAGLEN AND DATASINK+DATAVIZ.
'''
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,

    'formatters': {
        'verbose': {
            'format': "[%(asctime)s] %(levelname)s [%(name)s:%(lineno)s] %(message)s",
            'datefmt': "%d/%b/%Y %H:%M:%S"
        },
        'simple': {
            'format': '%(levelname)s %(message)s'
        },
        'log_message': {
            'format': '%(message)s'
        },
    },

    'handlers': {
        'file': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': '/var/log/kutbill/datasink.log',
            'formatter': 'verbose'
        },
        'file_pdf': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': '/var/log/kutbill/file_pdf.log',
            'formatter': 'verbose'
        },
        'file_dataglen': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': '/var/log/kutbill/dataglen.log',
            'formatter': 'verbose'
        },

        'file_dataglen_rest': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': '/var/log/kutbill/rest_dataglen.log',
            'formatter': 'verbose'
        },

        'file_dataviz': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': '/var/log/kutbill/dataviz.log',
            'formatter': 'verbose'
        },

        'file_dataglen_cronjobs': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': '/var/log/kutbill/cronjobs.log',
            'formatter': 'verbose'
        },

        'file_dataglen_logging_errors': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': '/var/log/kutbill/log_errors.log',
            'formatter': 'verbose'
        },

        'file_dataglen_monitoring_errors': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': '/var/log/kutbill/monitoring_errors.log',
            'formatter': 'verbose'
        },
        'file_dataglen_celery_logs': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': '/var/log/kutbill/celery.log',
            'formatter': 'verbose'
        },

        'file_tickets_logs': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': '/var/log/kutbill/tickets.log',
            'formatter': 'verbose'
        },

        'widgets_log': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': '/var/log/kutbill/widgets.log',
            'formatter': 'verbose'
        },

        'eventsframework_log': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': '/var/log/kutbill/eventsframework.log',
            'formatter': 'verbose'
        },

    },

    'loggers': {
        'django': {
            'handlers': ['file'],
            'propagate': True,
            'level': 'DEBUG',
        },

        'django-screamshot': {
            'handlers': ['file_pdf'],
            'level': 'DEBUG',
            'propagate': True,
        },

        'datasink.views': {
            'handlers': ['file'],
            'level': 'DEBUG',
        },

        'datasink.apps': {
            'handlers': ['file'],
            'level': 'DEBUG',
        },

        'dataglen.views': {
            'handlers': ['file_dataglen'],
            'level': 'DEBUG',
        },

        'dataglen.rest_views': {
            'handlers': ['file_dataglen_rest'],
            'level': 'DEBUG',
        },

        'logger.tasks': {
            'handlers': ['file_dataglen_logging_errors'],
            'level': 'DEBUG',
        },

        'monitoring.views': {
            'handlers': ['file_dataglen_monitoring_errors'],
            'level': 'DEBUG',
        },

        'cronjobs.views': {
            'handlers': ['file_dataglen_cronjobs'],
            'level': 'DEBUG',
        },

        'django_crontab.crontab': {
            'handlers': ['file_dataglen_cronjobs'],
            'level': 'DEBUG',
        },

        'kutbill.worker': {
            'handlers': ['file_dataglen_celery_logs'],
            'level': 'DEBUG',
        },

        'helpdesk.models': {
            'handlers': ['file_tickets_logs'],
            'level': 'DEBUG',
        },

        'widgets.models': {
            'handlers': ['widgets_log'],
            'level': 'DEBUG',
        },

        'eventsframework.views': {
            'handlers': ['eventsframework_log'],
            'level': 'DEBUG',
        },

    }
}

# Internationalization
# https://docs.djangoproject.com/en/1.7/topics/i18n/
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

'''
    STATIC FILE DETAILS
'''
# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.7/howto/static-files/
STATIC_ROOT = os.path.join(BASE_DIR, 'static')
# URL prefix for static files.
STATIC_URL = '/static/'

# Additional locations of static files
STATICFILES_DIRS = (
     #os.path.join(BASE_DIR, 'static'),
)

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    #'django.contrib.staticfiles.finders.DefaultStorageFinder',
)

'''
    TEMPLATES
'''
TEMPLATE_PATH = os.path.join(BASE_DIR, 'templates')

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [TEMPLATE_PATH],
        'OPTIONS': {
            'context_processors': [
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "django.template.context_processors.debug",
                "django.template.context_processors.i18n",
                "django.template.context_processors.media",
                "django.template.context_processors.static",
                "django.template.context_processors.tz",
                "django.template.context_processors.request",
                "django.contrib.messages.context_processors.messages",
            ],
            'loaders': [
                'django.template.loaders.filesystem.Loader',
                'django.template.loaders.app_directories.Loader',
                'django.template.loaders.eggs.Loader',
            ],
        },
    },
]



'''
    EMAIL CONFIGURATION
'''
# EMAIL_USE_TLS = True
# EMAIL_HOST = 'smtp.gmail.com'
# EMAIL_HOST_USER = 'admin@dataglen.com'
# EMAIL_HOST_PASSWORD = 'n>B=4E8j'
# EMAIL_PORT = 587

EMAIL_USE_TLS = True
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_HOST_USER = 'alerts@dataglen.com'
EMAIL_HOST_PASSWORD = '8HUrL*JQ'
EMAIL_PORT = 587

'''
    REGISTRATION RELATED PARAMETERS
'''
# Registration related parameters
REGISTRATION_OPEN = True
ACCOUNT_ACTIVATION_DAYS = 7
REGISTRATION_AUTO_LOGIN = False
LOGIN_URL = '/accounts/login/'
LOGIN_REDIRECT_URL = "/dashboards/redirect/"

'''
    REST API CONFIGURATION
'''
REST_FRAMEWORK = {
    # Use Django's standard `django.contrib.auth` permissions,
    # or allow read-only access for unauthenticated users.
#    'DEFAULT_PERMISSION_CLASSES': [
#        'rest_framework.permissions.DjangoModelPermissionsOrAnonReadOnly'
#    ]
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 5000
}

'''
    Website error notifications
'''


class USER_STATUS():
    OWNER = 'OWNER'
    EMPLOYEE = 'EMPLOYEE'
    MEMBER = 'MEMBER'
    UNASSIGNED = 'UNASSIGNED'


class Error():
    def __init__(self, code, description):
        self.code = code
        self.description = description

    def __unicode__(self):
        return self.description


class ERRORS():
    BAD_REQUEST = Error(status.HTTP_400_BAD_REQUEST, 'BAD_REQUEST')
    UNAUTHORIZED_ACCESS = Error(status.HTTP_401_UNAUTHORIZED, 'UNAUTHORIZED_ACCESS')
    METHOD_NOT_ALLOWED = Error(status.HTTP_405_METHOD_NOT_ALLOWED, 'METHOD_NOT_ALLOWED')
    INTERNAL_SERVER_ERROR = Error(status.HTTP_500_INTERNAL_SERVER_ERROR, 'INTERNAL_SERVER_ERROR')
    INVALID_SOURCE_KEY = Error(status.HTTP_400_BAD_REQUEST, 'INVALID_SOURCE_KEY')
    INVALID_DATA_STREAM = Error(status.HTTP_400_BAD_REQUEST, 'INVALID_DATA_STREAM')
    DUPLICATE_SOURCE = Error(status.HTTP_409_CONFLICT, 'DUPLICATE_SOURCE')
    DUPLICATE_STREAM = Error(status.HTTP_409_CONFLICT, 'DUPLICATE_STREAM')
    SOURCE_ACTIVE = Error(status.HTTP_400_BAD_REQUEST, 'SOURCE_ACTIVE')
    SOURCE_INACTIVE = Error(status.HTTP_400_BAD_REQUEST, 'SOURCE_INACTIVE')
    INVALID_DATA = Error(status.HTTP_400_BAD_REQUEST, 'INVALID_DATA')
    INVALID_REQUEST_PARAMETERS = Error(status.HTTP_400_BAD_REQUEST, 'INVALID_REQUEST_PARAMETERS')
    ESSENTIAL_PARAMETERS_MISSING = Error(status.HTTP_400_BAD_REQUEST, 'ESSENTIAL_PARAMETERS_MISSING')
    ERROR_RETRIEVING_PAYLOAD = Error(status.HTTP_400_BAD_REQUEST, 'ERROR_RETRIEVING_PAYLOAD')
    ERROR_SPLITTING_RECORDS = Error(status.HTTP_400_BAD_REQUEST, 'ERROR_SPLITTING_RECORDS')
    ERROR_SPLITTING_STREAMS = Error(status.HTTP_400_BAD_REQUEST, 'ERROR_SPLITTING_STREAMS')
    STREAM_PARSING_FAILED = Error(status.HTTP_400_BAD_REQUEST, 'STREAM_PARSING_FAILED')
    STREAMS_INCONSISTENCY = Error(status.HTTP_500_INTERNAL_SERVER_ERROR, 'STREAMS_INCONSISTENCY')
    DEACTIVATE_BEFORE_DELETE = Error(status.HTTP_400_BAD_REQUEST, 'DEACTIVATE_BEFORE_DELETE')
    ERROR_SAVING_BETA_REQUEST_FORM = Error(status.HTTP_500_INTERNAL_SERVER_ERROR, 'Error processing details. Please write to us at contact@dataglen.com')
    ERROR_NONMATCHING_STREAMS_UID_OWNER = Error(status.HTTP_409_CONFLICT, 'ERROR_NONMATCHING_STREAMS_UID_OWNER')
    STREAM_NAME_MISSING = Error(status.HTTP_400_BAD_REQUEST, 'PROVIDE_AT_LEAST_ONE_STREAM_NAME')
    INVALID_PLANT_SLUG = Error(status.HTTP_400_BAD_REQUEST, 'INVALID_PLANT_SLUG')
    INVALID_INVERTER_KEY = Error(status.HTTP_400_BAD_REQUEST, 'INVALID_INVERTER_KEY')
    INVALID_ACTION_DATA_STREAM = Error(status.HTTP_400_BAD_REQUEST, 'INVALID_ACTION_DATA_STREAM')
    DUPLICATE_ACTION_STREAM = Error(status.HTTP_409_CONFLICT, 'DUPLICATE_ACTION_STREAM')
    INVALID_CONFIG_DATA_STREAM = Error(status.HTTP_400_BAD_REQUEST, 'INVALID_CONFIG_DATA_STREAM')
    DUPLICATE_CONFIG_STREAM = Error(status.HTTP_409_CONFLICT, 'DUPLICATE_CONFIG_STREAM')
    FUTURE_TIMESTAMP = Error(status.HTTP_400_BAD_REQUEST, 'FUTURE_TIMESTAMP')
    SOURCE_CONFIGURATION_ISSUE = Error(status.HTTP_400_BAD_REQUEST, 'SOURCE_CONFIGURATION_ISSUE')
    JSON_PARSE_ERROR = Error(status.HTTP_400_BAD_REQUEST, "JSON parse error - Expecting property name enclosed in double quotes with no comma after the last property")
    INVALID_API_KEY = Error(status.HTTP_401_UNAUTHORIZED, 'INVALID_API_KEY')
    INVALID_EVENT_NAME = Error(status.HTTP_400_BAD_REQUEST, 'INVALID_EVENT_NAME')
    EVENT_NAME_REQUIRED = Error(status.HTTP_400_BAD_REQUEST, 'EVENT_NAME_REQUIRED')
    REQUEST_BODY_EMPTY = Error(status.HTTP_400_BAD_REQUEST, 'REQUEST_BODY_EMPTY')
    NO_PLANT_META_SOURCE = Error(status.HTTP_400_BAD_REQUEST, 'NO_PLANT_META_SOURCE')
    INVALID_AGGREGATOR = Error(status.HTTP_400_BAD_REQUEST, 'INVALID_AGGREGATOR')

class INTERNAL_ERRORS():
    INTERNAL_UNKNOWN_ERROR = Error(0, 'INTERNAL_UNKNOWN_ERROR')
    DATAGLEN_GROUP_DOES_NOT_EXIST = Error(1, 'DATAGLEN_GROUP_DOES_NOT_EXIST')
    DATAGLEN_CLIENT_DOES_NOT_EXIST = Error(2, 'DATAGLEN_CLIENT_DOES_NOT_EXIST')
    DATAGLEN_USER_DOES_NOT_EXIST = Error(3, 'DATAGLEN_USER_DOES_NOT_EXIST')

class DATA_COUNT_PERIODS():
    AGGREGATED = 0
    SECOND = 1
    MINUTE = 60
    FIVE_MINTUES = 60*5
    FIFTEEN_MINUTUES = 60*15
    HOUR = 60*60
    DAILY = 60*60*24
    WEEK = 60*60*24*7
    MONTH = 60*60*24*7*4


class TIMESTAMP_TYPES():
    BASED_ON_REQUEST_ARRIVAL = 'BASED_ON_REQUEST_ARRIVAL'
    BASED_ON_TIMESTAMP_IN_DATA = 'BASED_ON_TIMESTAMP_IN_DATA'
    BASED_ON_END_TIME_SLOT = 'BASED_ON_END_TIME_SLOT'
    BASED_ON_START_TIME_SLOT = 'BASED_ON_START_TIME_SLOT'


IDENTIFIER_FOR_ALL_USERS_DATA_SUM = "ALL"
EPOCH_TIME = timezone.now().replace(day=1, month=1, year=1970,
                                    hour=0, minute=0, second=0,
                                    microsecond=0, tzinfo=None)

class RESPONSE_TYPES():
    DRF = 'DRF'
    DJANGO = 'DJANGO'

TIMEZONE_CHOICES = [(zone, zone) for zone in pytz.all_timezones]

LIVE_CHART_LEN = 60
# TODO CLEAN THIS DICTIONARY!
DATAGLEN  = {
        'DATA_FORMATS' : (('JSON', 'JSON'),
                        ('CSV', 'CSV')),


        'DATA_TYPES': (('INTEGER', 'Integer'),
                       ('BOOLEAN', 'Boolean'),
                       ('STRING', 'String'),
                       ('FLOAT', 'Float'),
                       ('LONG', 'Long'),
                       ('MAC', 'Mac'),
                       ('TIMESTAMP', 'Timestamp'),
                       ('DATE', 'Date'),
                       ('TIME', 'Time')),

        # in seconds
        'LOG_EXPIRY' : 604800*4,

        'DISCARDED_RECORDS_UI_WINDOW_MINUTES': 300,
        'DISCARDED_RECORDS_UI_WINDOW_NUMBERS': 500,
}


EVENTS_UPDATE_INTERVAL_MINUTES = 15
ATRIA_FTP_DATA_COPY_INTERVAL_MINUTES = 10
PERFORMANCE_RATIO_UPDATE_INTERVAL_HOURS = 1
MONITORING_UPDATE_INTERVAL_HOURS = 1
DEMO_ACCOUNT_DATA_COPY_MINUTES = 5
DEMO_ALPINE_DATA_COPY_MINUTES = 5

STRING_EVENTS_UPDATE_INTERVAL_MINUTES = 60
STRING_EVENTS_INTERVAL = 1
ACTIVE_DEVIATION_NUMBER = 3
HISTORICAL_ENERGY_VALUE_INTERVAL_HOURS = 0o2
HISTORICAL_ENERGY_VALUE_WITH_PREDICTION_INTERVAL_HOURS = 0o2
ENERGY_LOSS_INTERVAL_HOURS = 1
NEW_ENERGY_LOSS_INTERVAL_HOURS = 1
SOLAR_METRIC_COMPUTE_INTERVAL = 1
GROWELS_DATA_COPY_MINUTES = 10
PLANT_DOWN_TIME_INTERVAL = 1
PLANT_DETAILS_UPDATE_INTERVAL_MINUTES = 20
ALPINE_KAFKA_COPY = 10
WAANEEP_KAFKA_COPY = 5
TICKET_ESCALATE_INTERVAL_MINUTES = 10
CLEANING_INTERVAL_HOURS = 14
STATISTICAL_PREDICTION_INTERVAL_HOUR = 1
PLANT_SUMMARY_INTERVAL_HOURS = 1
PREDICTION_GLM_INTERVAL_HOURS = 1
SOLAR_METRIC_COMPUTE_INTERVAL_MINS = 15
POWER_CURRENT_UPDATE_INTERVAL = 15
PLANT_SUMMARY_DEVICE_INTERVAL_HOURS = 1
PLANT_AGGREGATED_PARAMETERS_INTERVAL_HOURS = 1
AGGREGATED_POWER_COMPUTATION_INTERVAL_HOURS = 1
COMPARISON_INTERVAL = 1
SEND_DAILY_REPORTS = 15
SEND_DAILY_REPORTS_RENEW = 0
NEW_ENERGY_LOSS = 15
WEATHER_DATA_INTERVAL_HOURS = 13
DARK_SKY_WEATHER_DATA_INTERVAL_HOURS = 13
GLM_FIT_INTERVAL_HOURS = 16

DEMO_CHEMTROLS_DATA_COPY_MINUTES = 10
DEMO_HERO_DATA_COPY_MINUTES = 10
MAX_VALUES_COMPUTATION_HOURS = 1
LOAD_BALANCER_TEST_MINUTES = 5
POWER_PREDICTION_INTERVAL_HOURS = 15
POWER_BOOSTING_INVETERL_HOURS = 16

if hostname == "dataglen.com" or CASSANDRA_UPDATE:
    CRONJOBS = [

        # ('*/' + str(DEMO_ACCOUNT_DATA_COPY_MINUTES) + ' * * * *', 'solarrms.demo_account_data.copy_data'),
        # ('*/' + str(DEMO_ALPINE_DATA_COPY_MINUTES) + ' * * * *', 'solarrms.copy_alpine_demoplant.copy_alpine_data', '>> /var/log/kutbill/alpine_data_copy.log 2>&1'),
        # ('*/' + str(GROWELS_DATA_COPY_MINUTES) + ' * * * *', 'solarrms.copy_growels_demoplant.copy_growels_data', '>> /var/log/kutbill/growels_demo_data_copy.log 2>&1'),
        # ('*/' + str(GROWELS_DATA_COPY_MINUTES) + ' * * * *', 'solarrms.cron_copy_growels_data.copy_growels_data',
        #  '>> /var/log/kutbill/growels_data_copy.log 2>&1'),
        # ('*/' + str(DEMO_CHEMTROLS_DATA_COPY_MINUTES) + ' * * * *',
        #  'solarrms.copy_demo_chemtrols_data.copy_chemtrols_demo_data',
        #  '>> /var/log/kutbill/chemtrols_data_copy.log 2>&1'),
        ('*/' + str(DEMO_HERO_DATA_COPY_MINUTES) + ' * * * *', 'solarrms.cron_copy_hero_data.copy_data',
         '>> /var/log/kutbill/hero_data_copy.log 2>&1'),

        # tickets
        ('*/' + str(EVENTS_UPDATE_INTERVAL_MINUTES) + ' * * * *', 'solarrms.cron_new_tickets.new_solar_events_check',
         '>> /var/log/kutbill/new_tickets.log 2>&1'),

        # cron to calculate historical values and prediction
        ('1 '+str(HISTORICAL_ENERGY_VALUE_INTERVAL_HOURS)+' * * *', 'solarrms.cron_historic_energy.compute_historical_energy_values', '>> /var/log/kutbill/compute_historical_energy.log 2>&1'),
        ('1 ' + str(HISTORICAL_ENERGY_VALUE_WITH_PREDICTION_INTERVAL_HOURS) + ' * * *',
         'solarrms.cron_historic_energy_with_prediction.compute_historical_energy_values_with_prediction',
         '>> /var/log/kutbill/compute_historical_energy_with_prediction.log 2>&1'),

        # edp related crons
        ('5 21 * * *', 'solarrms.cron_EDP_update_metric.compute_EDP_metrics', '>> /var/log/kutbill/compute_EDP_metric.log 2>&1'),
        ('5 21 * * *', 'solarrms.cron_inverters_comparison.compare_inverters_generation_edp', '>> /var/log/kutbill/edp_inverters_comparison.log 2>&1'),

        # step 1. solar metrics - 10,25,40,55 - calculates basic params - runs every 15 minute
        ('10,25,40,55 * * * *', 'solarrms.cron_compute_solar_metrics.compute_solar_metrics',
         '>> /var/log/kutbill/compute_solar_metrics.log 2>&1'),

        # step 2. runs at the 25th minute of each hour - populates PlantSummaryDetails using the raw tables for KPIs
        # PlantSummaryDetails - used by reports summary, excel and UI (sy, grid availability, equipment avail.)
        ('25 */' + str(PLANT_SUMMARY_INTERVAL_HOURS) + ' * * *',
         'solarrms.cron_plant_summary.compute_plant_summary_details', '>> /var/log/kutbill/plant_summary.log 2>&1'),

        # step 3. calculates everything - at every 20th minute - updates PlantCompleteValues
        # PlantCompleteValues - used by the UI widgets mostly
        ('*/' + str(PLANT_DETAILS_UPDATE_INTERVAL_MINUTES) + ' * * * *', 'solarrms.cron_plant_all_details.get_all_plant_details_hero', '>> /var/log/kutbill/plant_details.log 2>&1'),
        ('*/' + str(PLANT_DETAILS_UPDATE_INTERVAL_MINUTES) + ' * * * *', 'solarrms.cron_plant_all_details.get_all_plant_details_cleanmax', '>> /var/log/kutbill/plant_details.log 2>&1'),
        ('*/' + str(PLANT_DETAILS_UPDATE_INTERVAL_MINUTES) + ' * * * *', 'solarrms.cron_plant_all_details.get_all_plant_details_others', '>> /var/log/kutbill/plant_details.log 2>&1'),

        # calculate compute_device_summary - runs at the 25th minute of each hour
        # PlantDeviceSummaryDetails - generation related data for inverters and meters.
        ('25 */' + str(PLANT_SUMMARY_DEVICE_INTERVAL_HOURS) + ' * * *',
         'solarrms.cron_plant_devices_summary.compute_device_summary_others', '>> /var/log/kutbill/device_summary.log 2>&1'),
        ('25 */' + str(PLANT_SUMMARY_DEVICE_INTERVAL_HOURS) + ' * * *',
         'solarrms.cron_plant_devices_summary.compute_device_summary_hero', '>> /var/log/kutbill/device_summary.log 2>&1'),
        ('25 */' + str(PLANT_SUMMARY_DEVICE_INTERVAL_HOURS) + ' * * *',
         'solarrms.cron_plant_devices_summary.compute_device_summary_cleanmax', '>> /var/log/kutbill/device_summary.log 2>&1'),

        # solar metrics - 15
        ('15 */' + str(PLANT_DOWN_TIME_INTERVAL) + ' * * *', 'solarrms.cron_downtime.calculate_down_time',
         '>> /var/log/kutbill/downtime.log 2>&1'),

        ('10,25,40,55 * * * *', 'solarrms.cron_compute_inverters_metrics.compute_daily_performance_ratio_for_inverters',
         '>> /var/log/kutbill/compute_inverters_metrics.log 2>&1'),
        ('55 */' + str(MAX_VALUES_COMPUTATION_HOURS) + ' * * *', 'solarrms.cron_max_values.cron_max_values',
         '>> /var/log/kutbill/cron_max_values.log 2>&1'),
        ('*/' + str(PLANT_DETAILS_UPDATE_INTERVAL_MINUTES) + ' * * * *',
         'solarrms.cron_solar_plant_all_details.get_all_solar_groups_details',
         '>> /var/log/kutbill/group_details.log 2>&1'),

        # reports
        ('30 '+str(SEND_DAILY_REPORTS)+' * * *', 'solarrms.cron_send_reports.send_daily_performance_reports', '>> /var/log/kutbill/daily_report.log 2>&1'),
        ('30 ' + str(SEND_DAILY_REPORTS) + ' * * *', 'solarrms.cron_send_reports.cron_send_daily_sms_and_email_report_consolidated_for_all_plants_without_attachments','>> /var/log/kutbill/daily_report.log 2>&1'),
        ('1 0 * * *', 'oandmmanager.cron_create_cycle_and_task_items.create_update_task_and_cycle',
         '>> /var/log/kutbill/create_update_task_and_cycle.log 2>&1'),
        ('30 ' + str(SEND_DAILY_REPORTS) + ' * * *', 'solarrms.cron_send_reports.send_html_email_daily_portfolio',
         '>> /var/log/kutbill/daily_portfolio_html_email.log 2>&1'),
        ('30 0 * * *', 'solarrms.cron_send_reports.cron_send_daily_pdf_reports_cleanmax',
         '>> /var/log/kutbill/daily_portfolio_html_email.log 2>&1'),



        # later
        ('15 */'+str(PLANT_AGGREGATED_PARAMETERS_INTERVAL_HOURS)+' * * *', 'solarrms.cron_compute_aggregated_parameters.compute_aggregated_parameters', '>> /var/log/kutbill/aggregated_parameters.log 2>&1'),
        ('15 */'+str(AGGREGATED_POWER_COMPUTATION_INTERVAL_HOURS)+' * * *', 'solarrms.cron_power_aggregation.upload_aggregated_power_values', '>> /var/log/kutbill/aggregated_power.log 2>&1'),

        # analytics
        ('1 '+str(CLEANING_INTERVAL_HOURS)+' * * *', 'solarrms.cron_cleaning_schedule_new.cleaning_schedule', '>> /var/log/kutbill/cleaning_cron.log 2>&1'),
        ('44 */' + str(STATISTICAL_PREDICTION_INTERVAL_HOUR) + ' * * *', 'solarrms.cron_stat_generation_prediction_new.run_statistical_generation_prediction', '>> /var/log/kutbill/statistical_prediction.log 2>&1'),
        ('42 */' + str(STATISTICAL_PREDICTION_INTERVAL_HOUR) + ' * * *', 'solarrms.cron_stat_generation_prediction_new.run_periodic_prediction_adjustments', '>> /var/log/kutbill/prediction_adjustment.log 2>&1'),
        ('42 */' + str(STATISTICAL_PREDICTION_INTERVAL_HOUR) + ' * * *', 'solarrms.cron_stat_prediction_power.run_periodic_power_adjustments', '>> /var/log/kutbill/power_prediction_adjustment.log 2>&1'),
        ('1 ' + str(WEATHER_DATA_INTERVAL_HOURS) + ' * * *',
         'solarrms.cron_collect_weather_data.cron_collect_weather_data_main',
         '>> /var/log/kutbill/weather_data.log 2>&1'),
        ('30 ' + str(DARK_SKY_WEATHER_DATA_INTERVAL_HOURS) + ' * * *',
         'solarrms.cron_collect_darksky_weather_data.cron_collect_darksky_weather_data_main',
         '>> /var/log/kutbill/darksky_weather_data.log 2>&1'),
        ('45 ' + str(DARK_SKY_WEATHER_DATA_INTERVAL_HOURS) + ' * * *',
         'solarrms.cron_collect_solcast_weather_data.cron_collect_solcast_weather_data_main',
         '>> /var/log/kutbill/solcast_weather_data.log 2>&1'),
        ('5 * * * *', 'solarrms.cron_stat_prediction_power.run_statistical_power_prediction',
         '>> /var/log/kutbill/statistical_power_prediction.log 2>&1'),
        ('30 ' + str(POWER_BOOSTING_INVETERL_HOURS) + ' * * *',
         'solarrms.cron_powerprediction_boosting.GBM_Power_Prediction',
         '>> /var/log/kutbill/GBM_Power_Prediction.log 2>&1'),
        ('30 ' + str(POWER_BOOSTING_INVETERL_HOURS) + ' * * *',
         'solarrms.cron_energyprediction_boosting.GBM_Energy_Prediction',
         '>> /var/log/kutbill/GBM_Energy_Prediction.log 2>&1'),
        ('50 */' + str(STATISTICAL_PREDICTION_INTERVAL_HOUR) + ' * * *',
         'solarrms.cron_stat_gen_adjustment_adani.run_periodic_prediction_adjustments_adani',
         '>> /var/log/kutbill/run_periodic_prediction_adjustments_adani.log 2>&1'),
        ('1,16,31,46 * * * *', 'solarrms.bonsai_revision_energy.bonsai_realtime_m',
         '>> /var/log/kutbill/bonsai_realtime_m.log 2>&1'),

        # ('30 ' + str(SEND_DAILY_REPORTS_RENEW) + ' * * *',
        #  'solarrms.cron_send_reports.send_daily_performance_reports_for_renew',
        #  '>> /var/log/kutbill/daily_report.log 2>&1'),

        # ('10 */' + str(COMPARISON_INTERVAL) + ' * * *', 'solarrms.cron_inverters_comparison.compare_inverters_generation', '>> /var/log/kutbill/inverters_comparison.log 2>&1'),
        # ('10 */' + str(COMPARISON_INTERVAL) + ' * * *', 'solarrms.cron_mppt_comparison.compare_mppts', '>> /var/log/kutbill/mppt_comparison.log 2>&1'),
        # ('10 */' + str(COMPARISON_INTERVAL) + ' * * *', 'solarrms.cron_string_comparison.compare_strings', '>> /var/log/kutbill/ajb_comparison.log 2>&1'),

        # ('2 */' + str(MONITORING_UPDATE_INTERVAL_HOURS) + ' * * *', 'solarrms.cron_solar_events.solar_activate_monitoring', '>> /var/log/kutbill/events_cron.log 2>&1'),
        #('52 */'+str(PERFORMANCE_RATIO_UPDATE_INTERVAL_HOURS)+' * * *', 'solarrms.cron_compute_metrics_new.compute_performance_ratio', '>> /var/log/kutbill/compute_metric_job.log 2>&1'),
        #('15 */'+str(PERFORMANCE_RATIO_UPDATE_INTERVAL_HOURS)+' * * *', 'solarrms.cron_compute_pr_daily.compute_daily_performance_ratio', '>> /var/log/kutbill/compute_PR_job.log 2>&1'),
        #('*/' + str(EVENTS_UPDATE_INTERVAL_MINUTES) + ' * * * *', 'solarrms.cron_solar_events.solar_events_check', '>> /var/log/kutbill/events_cron.log 2>&1'),
        #('10 */' + str(STRING_EVENTS_INTERVAL) + ' * * *', 'solarrms.cron_string_events.check_string_events', '>> /var/log/kutbill/string_events_cron.log 2>&1'),
        #('15 */'+str(SOLAR_METRIC_COMPUTE_INTERVAL)+' * * *', 'solarrms.cron_compute_solar_metrics.compute_solar_metrics', '>> /var/log/kutbill/compute_solar_metrics.log 2>&1'),
        # ('20 */'+str(ENERGY_LOSS_INTERVAL_HOURS)+' * * *', 'solarrms.cron_energy_losses.compute_energy_losses', '>> /var/log/kutbill/energy_loss.log 2>&1'),
        # ('10 */'+str(NEW_ENERGY_LOSS_INTERVAL_HOURS)+' * * *', 'solarrms.cron_energy_loss_new.compute_energy_losses', '>> /var/log/kutbill/new_energy_loss.log 2>&1'),
        # START FTP DATA CRONS
        #('10 '+str(POWER_CURRENT_UPDATE_INTERVAL)+' * * *', 'solarrms.cron_update_ajb_current_power.update_current_power_values', '>> /var/log/kutbill/update_current_power.log 2>&1'),
        # END FTP DATA CRONS
        #('*/' + str(WAANEEP_KAFKA_COPY) + ' * * * *', 'solarrms.copy_live_data_waaneep.copy_waaneep_data', '>> /var/log/kutbill/live_waaneep_data_copy.log 2>&1'),
        #('*/' + str(TICKET_ESCALATE_INTERVAL_MINUTES) + ' * * * *', 'helpdesk.dg_cron_escalations.escalate_ticket', '>> /var/log/kutbill/escalate_ticket.log 2>&1'),
        #('42 */' + str(STATISTICAL_PREDICTION_INTERVAL_HOUR) + ' * * *',
        # 'solarrms.cron_stat_generation_prediction_new.run_periodic_prediction_adjustments_v2',
        # '>> /var/log/kutbill/prediction_adjustment_v2.log 2>&1'),
        #('5,20,35,50 * * * *', 'solarrms.cron_stat_generation_prediction_new.run_periodic_prediction_adjustments_15',
        # '>> /var/log/kutbill/prediction_adjustment_15.log 2>&1'),
        #('40 */' + str(STATISTICAL_PREDICTION_INTERVAL_HOUR) + ' * * *', 'solarrms.cron_test.run_test', '>> /var/log/kutbill/test.log 2>&1'),
        # ('10 '+str(NEW_ENERGY_LOSS)+' * * *', 'solarrms.cron_energy_loss_new.compute_energy_losses', '>> /var/log/kutbill/new_energy_loss.log 2>&1'),
        #('*/' + str(LOAD_BALANCER_TEST_MINUTES) + ' * * * *', 'solarrms.test_balancer.test_balancer', '>> /var/log/kutbill/load_banacer_test.log 2>&1'),
        #('30 */'+str(PREDICTION_GLM_INTERVAL_HOURS)+' * * *', 'solarrms.cron_energy_prediction_GLM.energy_prediction_glm', '>> /var/log/kutbill/prediction_glm.log 2>&1'),
        #('1 '+str(GLM_FIT_INTERVAL_HOURS)+' * * *', 'solarrms.cron_energy_prediction_GLM.generate_currentday_glm_fits', '>> /var/log/kutbill/glm_fit.log 2>&1'),

        # ftp data copy
        ('5,20,35,50 * * * *',
         'solarrms.cron_jakson_ftp.ftp_cron_for_current_time_main',
         '>> /var/log/kutbill/jakson_ftp_data.log 2>&1')
    ]
else :
    CRONJOBS = []


# default RabbitMQ broker
BROKER_URL='librabbitmq://'

# using redis
#CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'
#CELERY_RESULT_BACKEND = 'amqp://'

CELERY_DISABLE_RATE_LIMITS = True
#CELERYD_LOG_FILE = "/var/tmp/celery.log"#"/var/log/kutbill/celery.log"
CELERY_ACKS_LATE = True
CELERYD_PREFETCH_MULTIPLIER = 1

BROKER_POOL_LIMIT = 500

CASSANDRA_READ_RECORDS_LIMIT=1000

# Twilio account details. This is a trial account at present.
TWILIO_ACCOUNT_SID = 'AC517285b3bd2fc7fd18a48ad2e6cd2fff'
TWILIO_AUTH_TOKEN = 'c87f188a9390c65148d9387ef909a75d'
TWILIO_PHONE_NUMBER ='+18303411050'

#django-hijack redirections
HIJACK_LOGIN_REDIRECT_URL = '/dashboards/redirect/'  # Where admins are redirected to after hijacking a user
HIJACK_LOGOUT_REDIRECT_URL = '/dashboards/redirect/'  # Where admins are redirected to after releasing a user
HIJACK_USE_BOOTSTRAP = True
HIJACK_ALLOW_GET_REQUESTS = True


#Solutions Infini details
SMS_KEY = 'A7c038153c8d4455a8cfad37d44a025dd'
if CASSANDRA_UPDATE:
    #TODO change KEY as previous once google server is live
    SMS_KEY = 'A7c038153c8d4455a8cfad37d44a025dd'
SMS_SENDER = 'DGTECH'
SMS_URL = 'http://api-alerts.solutionsinfini.com/v3/'


#Template Name
INVERTER_TEMPLATE = 'INVERTER_TEMPLATE'
PLANT_META_TEMPLATE = 'PLANT_META_TEMPLATE'
WMS_TEMPLATE = 'WMS_TEMPLATE'
GATEWAY_TEMPLATE = 'GATEWAY_TEMPLATE'
AJB_TEMPLATE = 'AJB_TEMPLATE'
ENERGY_METER_TEMPLATE = 'ENERGY_METER_TEMPLATE'
TRANSFORMER_TEMPLATE = 'TRANSFORMER_TEMPLATE'
WEATHER_STATION_TEMPLATE = 'WEATHER_STATION_TEMPLATE'
SOLAR_METRICS_TEMPLATE = 'SOLAR_METRICS_TEMPLATE'
WEBDYN_TEMPLATE = 'WEBDYN_TEMPLATE'

#Contact Us
contact_email = ['sunilkrghai@dataglen.com', 'tanuja@dataglen.com', 'dpseetharam@dataglen.com', 'rajat@dataglen.com','obu@dataglen.com', 'catherine@dataglen.com']
#contact_email = ['nishant@dataglen.com', 'siddharthpandey@dataglen.com']
from_email = 'alerts@dataglen.com'
PR_Email = ['sunilkrghai@dataglen.com', 'tanuja@dataglen.com', 'nishant@dataglen.com']

# KAFKA details
#KAFKA_HOSTS = ['139.162.25.193:9092', '172.104.49.5:9092', '13.127.17.99:9092']#, '139.162.43.87:9092'] # 'kafka.dataglen.org:9092' and 'analytics.dataglen.org' # this is a host with 6 hours of log retention policy
KAFKA_HOSTS = ['172.104.168.119:9092','13.127.17.99:9092']
KAFKA_WRITE_TO_HOSTS = [True, True]

if CASSANDRA_UPDATE:
    KAFKA_HOSTS = ['10.148.0.8:9093,10.148.0.11:9093']
    KAFKA_WRITE_TO_HOSTS = [True]

KAFKA_WRITE = True
#KAFKA_WRITE_TO_HOSTS = [True, False, True]#, True]

# ZOOKEEPER details not using below IP's
ZOOKEEPER_HOST = '172.104.168.119'
if CASSANDRA_UPDATE:
    ZOOKEEPER_HOST = '10.148.0.8, 10.148.0.11, 10.148.0.6'
ZOOKEEPER_PORT = 2181

#R server for cleaning
R_SERVER_HOST = 'http://kafkastaging.dataglen.org'
if CASSANDRA_UPDATE:
    R_SERVER_HOST = 'http://10.148.0.11'

# cleaning threshold percentage
CLEANING_THRESHOLD_PERCENT = 2

X_FRAME_OPTIONS = 'ALLOWALL'

if CASSANDRA_UPDATE:
    SCREAMSHOT_CONFIG = {
        'CASPERJS_CMD': '/usr/local/bin/casperjs',
        'CAPTURE_METHOD': 'casperjs',
        'TEST_CAPTURE_SCRIPT': False
    }

DG_CELERY_TASK_PATH = ('solarrms.cron_new_tickets.new_solar_events_check_for_a_plant', )

# tagging config
FORCE_LOWERCASE_TAGS = True
MAX_TAG_LENGTH = 20
# Default primary key field type
# https://docs.djangoproject.com/en/4.1/ref/settings/#default-auto-field
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'