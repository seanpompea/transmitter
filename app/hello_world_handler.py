from common import *
from kickshaws import *

__all__ = ['handle']

log =  smart_logger()

def handle(request):
  log.info('Handling request. Will return status 200.')
  return {'status':200
         ,'content-type': 'text/plain'
         ,'body': 'Hello world!'} 

