import os
import json
import platform
import codecs
import json
import datetime
from common import *
from kickshaws import *

def get_app_config():
  try:
    pth = 'enclave/transmitter-config.json'
    return slurp_json(pth)
  except IOError:
    pth = '../enclave/transmitter-config.json'
    return slurp_json(pth)

def get_log_filepath():
  return get_app_config().get('logfile') 

log = smart_logger() 

def setup__get_study_config():
  memo = {}
  def get_study_config_inner(study_tag):
    pth = 'enclave/' + study_tag + '-config.json'
    if study_tag not in memo:
      memo[study_tag] = slurp_json(pth)
    return dict(memo[study_tag]) 
  return get_study_config_inner
get_study_config=setup__get_study_config()

def ip_is_allowed(ip, ip_allowed_list):
  return ip in ip_allowed_list
  
def run_workflow_chain(request, chain):
  '''chain should be a collection of workflow functions
  -- actual function objects (not names as strings).
  Here we run a set of workflow functions, one after another.
  (Recall that a workflow receives a request-shaped map
  and returns another one).
  Convention: if a workflow returns a map with 'done' as 
  a key (and value 'yes'), then it 
  should also include a 'response' key.
  This short-circuits the chain and we're done.
  If all goes well, this function returns the final
  request-shaped map returned by the final workflow
  function; otherwise, returns the 'response' value
  when a short-circuit occurred.
  '''
  log.info('Entered.')
  x = request
  for f in chain:
    x = f(x)
    if x.get('done','') == 'yes':
      log.info('Finished early; exiting workflow chain.')  
      return x
  log.info('Workflow chain done. Exiting.')
  return x

def imux_handlers(handler1, handler2):
  '''imux (aka inverse multiplex), takes two handlers,
  and returns a single handler. (Recall that a handler
  takes a single request and returns a single response.)'''
  def imuxed_handle(req):
    log.info('in')
    rslt1 = handler1(req)
    print str(rslt1)
    rslt2 = handler2(req)
    print str(rslt2)
    # Return 200 if both returned 200; else first non-200
    # status is what gets returned.
    out_status = -1
    if rslt1.get('status') == 200 and rslt2.get('status') == 200:
      log.info('both handler1 and handler2 returned 200')
      out_status = 200
    elif rslt1.get('status') != 200:
      log.info('handler1 returned non-200')
      out_status = rslt1.get('status')
    else:
      log.info('handler2 returned non-200')
      out_status = rslt2.get('status')
    log.info('out')
    return {'status': out_status}
  return imuxed_handle

def finalize(request, status=200):
  '''Configure request-shaped map to indicate that
  the workflow should not continue. You can set
  a custom HTTP if desired.'''
  request['done'] = 'yes'
  request['response'] = {'status': status} 
  return request

