import os
import sys

sys.path.append('/usr/local/lib/python2.7/dist-packages')

## assuming your django settings file is at '/var/www/project/project/settings.py'
mypath = '/var/www/kutbill'
if mypath not in sys.path:
    sys.path.append(mypath)

os.environ['DJANGO_SETTINGS_MODULE'] = 'kutbill.settings'

import django.core.wsgi
application = django.core.wsgi.get_wsgi_application()

