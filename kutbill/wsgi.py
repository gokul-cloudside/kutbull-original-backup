"""
WSGI config for scripts project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/1.7/howto/deployment/wsgi/
"""

import os
#import mod_wsgi
import time
import sys
import signal
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "kutbill.settings")

from django.core.wsgi import get_wsgi_application
#print 'IMPORTING WSGI: ', __name__, 'from', __file__, 'in', os.getpid(), ":", mod_wsgi.process_group, ":", mod_wsgi.application_group
try:
    application = get_wsgi_application()
    print 'WSGI without exception'
except Exception as E:
    print 'handling WSGI exception: ', str(E)
    # Error loading applications.
    if 'mod_wsgi' in sys.modules:
        os.kill(os.getpid(), signal.SIGINT)
        time.sleep(2.5)
    raise