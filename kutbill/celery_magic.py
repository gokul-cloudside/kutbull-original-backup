from __future__ import absolute_import

import os

import sys

## assuming your django settings file is at '/home/username/mysite/settings.py'
mypath = '/var/www/kutbill'
if mypath not in sys.path:
    sys.path.append(mypath)

from celery import Celery

# set the default Django settings module for the 'celery' program.
os.environ['DJANGO_SETTINGS_MODULE'] = 'kutbill.settings'
#os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'kutbill.settings')

from django.conf import settings

app = Celery('kutbill')

# Using a string here means the worker will not have to
# pickle the object when using Windows.
app.config_from_object('django.conf:settings')
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS + settings.DG_CELERY_TASK_PATH)
