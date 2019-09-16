from __future__ import division
from __future__ import print_function
from collections import *
from functools import *
from itertools import *
from operator import *

import traceback
from threading import Lock

import kickshaws as ks
import redcaplib

# local 
import common 
import aou_common

#------------------------------------------------------------------------------

__all__ = ['compose_handler']

log = ks.smart_logger()

#------------------------------------------------------------------------------

# See Note One below.
def build_key(req):
  return (str(req['redcap-server-tag'])
         + str(req['pid'])
         + '.'
         + str(req['record-id'] ))

# See Note One below.
map_lock = Lock() # Used solely by make_record_lock_if_absent.
record_locks = {} # Used in make_record_lock_if_absent and _handle.

# See Note One below.
def make_record_lock_if_absent(k):
  '''Instantiate a new Lock object and put it into the
  map for key k, but only if there's nothing for that key already.'''
  with map_lock:
    if not str(k) in record_locks:
      log.info('Creating new record lock for: {}'.format(k))
      record_locks[k] = Lock()

#------------------------------------------------------------------------------

def _handle(redcap_server_tag, pid, study_tag, workflow_chain, request):
  '''
  You won't normally invoke this function directly; it's 
  used by compose_handler below.
  '''
  log.info('=== Entered. ===')

  # Retrieve study config.
  study_config = common.get_study_config(study_tag)

  # Check: client IP is allowed or bail.
  if not common.ip_is_allowed(request['client_ip']
                              ,study_config['allowed-ips']):
    log.info('Client IP of ' + request['client_ip'] + ' is not allowed.')
    return {'status': 403}

  # Check: request was POSTed or bail.
  # Can happen if browser or other utility is just checking 
  # the URL for aliveness.
  if request['method'] != 'POST':
    log.info('Method is {}; nothing to do.'.format(request['method']))
    return {'status': 405}  

  # Check: request contains data or bail. E.g., request won't contain
  # data if user 'tests' endpoint via the Data Entry Trigger 
  # URL Test button in the Project Setup screen.
  if len(redcaplib.parse_det_payload(request['data'])) == 0:
    log.info('DET payload empty; nothing to do.')
    return {'status': 200}

  # We need the DET message now.
  det_payload = redcaplib.parse_det_payload(request['data'])
  log.info('DET payload: ' + str(det_payload))

  # Check: PID in DET message is PID we expect, or bail.
  # A mismatch indicates a misconfiguration needing attention (in the
  # REDCap project's Project Setup) so an Error is raised in this case.
  if str(det_payload['project_id']) != str(pid):
    raise RuntimeError('project_id in DET payload (' + det_msg['project_id']
                      +') does not match what handler expects (' + str(pid) + ')') 

  # At this point, initial checks were OK.
  log.info('Initial checks OK.')
  
  # Grab record ID. This is important for lock/serializing logic below.
  record_id = str(det_payload['record'])

  # Load up request with pertinent data elements for downstream use.
  request['redcap-server-tag'] = redcap_server_tag
  request['pid'] = str(pid) 
  request['study-tag'] = study_tag
  request['handler-tag'] = redcap_server_tag + str(pid)
  request['record-id'] = record_id
  request['det-payload'] = det_payload

  # Ok, ready to run workflows now.

  # Do some lock-related setup.
  # See Note One below.
  record_lock_key = build_key(request)
  make_record_lock_if_absent(record_lock_key)

  # Start of logic with lock.
  # See Note One below.
  log.info('About to start work with lock [{}].'.format(record_lock_key))
  with record_locks[record_lock_key]:
    log.info('Starting workflow chain for pid {}, record id {}'.format(pid, record_id))
    try:
      result = common.run_workflow_chain(request, workflow_chain)
      if result.get('response'):
        log.info('Done. Chain result includes response of {}; will use that.'\
                 ''.format(str(result.get('response'))))
        return result.get('response')
      else:
        log.info('Done. Will return 200 response.')
        return {'status': 200} 
    except Exception, e:
      log.error(traceback.format_exc())
      handler_tag = redcap_server_tag + str(pid)
      env_tag = aou_common.get_env_tag_for_handler(handler_tag)
      ks.send_email(study_config[env_tag]['from-email']
                   ,study_config[env_tag]['to-email']
                   ,'Boost Transmitter Exception'
                   ,'Please check the log.')
      log.error('Returning 500; details: ' + str(e))
      return {'status': 500}
    finally:
      log.info('Finished work with lock [{}].'.format(record_lock_key))
      log.info('== Finished ==')
  # End of logic with lock.

#------------------------------------------------------------------------------

def compose_handler(redcap_server_tag, pid, study_tag, workflow_chain):
  '''
  Args:
    - redcap_server_tag: this will usually be 'prod' or 'sand'
    - pid -- the REDCap project ID
    - study_tag -- a tag used for retrieving study-specific configuration
    - workflow_chain -- a list of functions that will be passed to
      common.run_workflow_chain. See README for more about workflows.
  Returns: a function that takes one argument: a request-shaped
  map -- e.g., a handler function that the Metaphor framework expects.
  '''
  return partial(_handle, redcap_server_tag, pid, study_tag, workflow_chain)

#------------------------------------------------------------------------------
'''  
-------------------------------------------------------------------------
Note One:
Technique to manage concurrent requests originating 
from the same REDCap record.
-------------------------------------------------------------------------

Goal: handle requests bearing different record IDs in parallel
      but handle simultaneous requests w/ the same record ID 
      (from the same REDCap project) in a serial fashion.

To achieve the above, behavior of this handler is as follows:

* We assume we're running in a multithreaded environment (i.e., each
  invocation happens on a separate thread, which is typical 
  Web server behavior.)
* Maintain a map of Lock objects called record_locks.
* Fill up record_locks on an ad hoc basis -- which means we modify the
  map as we go. Because of this, we also use a lock around record_locks,
  called map_lock.
* We construct a key like so for querying the record_locks map:

      redcap-server-tag (usually 'prod' or 'sand') + pid + '.' + record-id

  ... which, incidentally, is usually the same as:
     
      handler-tag + '.' + record-id
'''
#------------------------------------------------------------------------------


