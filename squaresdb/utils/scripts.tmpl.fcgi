#!{executable}
import sys, os, time, threading, django.utils.autoreload
os.chdir("{base}")
os.environ['DJANGO_SETTINGS_MODULE'] = "squaresdb.settings"

import django
django.setup()

def reloader_thread():
  while True:
    if django.utils.autoreload.code_changed():
      os._exit(3)
    time.sleep(1)
t = threading.Thread(target=reloader_thread)
t.daemon = True
t.start()

from flup.server.fcgi import WSGIServer
from django.core.handlers.wsgi import WSGIHandler
WSGIServer(WSGIHandler()).run()
