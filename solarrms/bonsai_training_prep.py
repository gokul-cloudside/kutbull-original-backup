################################################################################
# Imports
import pandas as pd
import numpy as np
import django
import sys
import os
sys.path.append("/var/www/kutbill")
os.environ["DJANGO_SETTINGS_MODULE"] = "kutbill.settings"
django.setup()
from solarrms.bonsai_revision_energy import bonsai_revision_prep
from django.utils import timezone
import pytz
from datetime import datetime


# Function1
# Wrapper functions for generating the training dataset for Bonsai
def bonsai_revision_prep_wrapper(training_endtime=''):
    if  training_endtime == '':
        # testing..
        currenttime = timezone.now().replace(hour=15,minute=30)
        # prepare the trainning datasets
        bonsai_revision_prep(currenttime)
    else:
        # Localize to India time..
        local_tz = pytz.timezone('Asia/Kolkata')
        # Parse the end date
        currenttime = datetime.strptime(training_endtime, '%Y-%m-%d')
        # localize to Asia kolkata
        currenttime = local_tz.localize(currenttime)
        currenttime = currenttime.replace(hour=22, minute=30)
        bonsai_revision_prep(currenttime)


if __name__ == '__main__':
    bonsai_revision_prep_wrapper()