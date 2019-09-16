import requests
import traceback
from functools import partial
import kickshaws as ks
from common import *
import redcaplib as rc

'''
RACIE Legacy Handler: route to legacy service.
'''

__all__ = ['compose_handler']

racie_legacy_url = 'http://localhost:80/index/'

log = ks.smart_logger()

def _handle(ip_whitelist, req):
  '''Route to RACIE Legacy service. Assumes we're always POSTing.'''
  log.info('in')
  # Confirm requesting IP is in whitelist, or bail.
  if not ip_is_whitelisted(req['client_ip'], ip_whitelist):
    log.info('client_ip of {} is not whitelisted.'.format(req.get('client_ip')))
    return {'status': 403}
  status = -1
  try:
    raw_data = (req.get('data', ''))
    log.info('DET payload from REDCap: {}'.format(raw_data))
    log.info('About to call RACIE Legacy...')
    outgoing_data = rc.parse_det_payload(raw_data)
    rslt = requests.post(racie_legacy_url, data=outgoing_data)
    status = rslt.status_code
    msg = rslt.text
    log.info('Result of RACIE Legacy call: status is {}; message is {}.'\
             ''.format(status, msg))
    log.info('out')
    return {'status': status}
  except Exception, ex:
    log.error(traceback.format_exc())
    ks.send_email(study_cfg[env_tag]['from-email']
                 ,study_cfg[env_tag]['to-email']
                 ,'Boost Transmitter Exception'
                 ,'Please check the log.')
    return {'status': 500}

def compose_handler(ip_whitelist):
  '''This returns a function that only takes a request-shaped
  map -- e.g., a handler function like Metaphor framework expects.
  Any use of legacy_handler needs to be tied to whitelist, but
  possibly that whitelist needs to be dynamic.'''
  return partial(_handle, ip_whitelist)


