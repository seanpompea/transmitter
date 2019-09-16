from __future__ import division
from __future__ import print_function
import traceback
import aoulib
import kickshaws as ks
import datastore as store
import common

'''
================================
AoU Confirm Affiliation Workflow
================================

This workflow should be placed near the beginning of your workflow chain
(just after redcap_intake_workflow). Here, we only confirm that the record
has a PMI ID and that the participant is paired/affiliated with WCM. If so, 
we return the request unmodified, allowing the workflow chain to continue;
if not (or if we can't confirm), we short-circuit the workflow chain, ending
it immediately (via the common.finalize function), b/c Transmitter should not
process non-WCM participants.
'''

log = ks.smart_logger()

AOU_WCM_PAIRED = 'aou-wcm-paired'
YES = 'yes'
NO = 'no'
UNKNOWN = 'unknown'

#------------------------------------------------------------------------------

def _rc_is_wcm_paired(rcd):
  '''Does the REDCap record indicate participant is WCM *not* paired?
  This one only confirms if not paired, but cannot confirm if paired.
  Returns NO / UNKNOWN.'''
  log.info('in')
  if str(rcd.get('other_enrollment', '*')) == '1':
    log.info('out')
    return NO
  else:
    log.info('out')
    return UNKNOWN

def _db_is_wcm_paired(redcap_server_tag, pid, record_id):
  '''Does database/cache indicate participant is WCM paired?
  (Or confirm participant is *not* paired?) 
  Returns YES / NO / UNKNOWN.'''
  log.info('in')
  rslt = None
  if store.key_exists(redcap_server_tag, pid, record_id, AOU_WCM_PAIRED):
    rslt = store.get_latest_value(redcap_server_tag, pid,
                                  record_id, AOU_WCM_PAIRED)
    # If exists, should always be 'yes' or 'no', but let's be safe.
    rslt = rslt if rslt in (YES, NO) else UNKNOWN
  else:
    rslt = UNKNOWN
  log.info('out')
  return rslt

def _aou_api_is_wcm_paired(pmi_id):
  '''Does AoU Data Ops API indicate participant is WCM paired?
  (Or confirm participant is *not* paired?) 
  Returns YES / NO / UNKNOWN.'''
  log.info('in')
  if type(pmi_id) not in (str, unicode):
    raise TypeError('pmi_id must be str or unicode')
  aou_api_spec = ks.slurp_json('enclave/aou-api-spec.json')
  sess = aoulib.make_authed_session(aou_api_spec['path-to-key-file'])
  rslt = UNKNOWN
  try: 
    param = {'participantId': pmi_id[1:]} # Chop 'P' from front of ID.
    api_data = aoulib.get_records(aou_api_spec, sess, param) # can throw
    if len(api_data) == 1:
      api_rcd = api_data[0]
      org = api_rcd.get('organization', '')
      if org == 'COLUMBIA_WEILL':
        rslt = YES
      elif org != 'UNSET' and org != '':
        rslt = NO
      # else stays as UNKNOWN
    else:
      raise Exception('Expected one row from API but didn\'t get that.')
  except Exception, ex:
    log.error('aoulib error. Could PMI ID be invalid? Details: {}'\
              ''.format(traceback.format_exc()))
  finally:
    log.info('out')
    return rslt

#------------------------------------------------------------------------------

def _cache_as_paired(redcap_server_tag, pid, record_id):
  return store.put(redcap_server_tag, pid, record_id, AOU_WCM_PAIRED, YES)

def _cache_as_not_paired(redcap_server_tag, pid, record_id):
  return store.put(redcap_server_tag, pid, record_id, AOU_WCM_PAIRED, NO)

#------------------------------------------------------------------------------

def go(request):
  '''See comments at top of module.'''
  log.info('in')
  redcap_server_tag = request['redcap-server-tag']
  pid = request['pid']
  # In newer REDCap versions, sometimes the record is a list;
  # in that case, we only want first element of the list.
  record = {}
  if type(request['full-record']) == list:
    record = request['full-record'][0]
  else:
    record = request['full-record']
  record_id = record['record_id']
  # Has PMI ID? Bail if not.
  pmi_id = record.get('pmi_id_test', '')
  if pmi_id == '':
    log.info('record_id=[{}]; No PMI ID. Bail.'.format(record_id))
    log.info('out')
    return common.finalize(request)
  # 1/3: Check RC record.
  rslt = _rc_is_wcm_paired(record)
  # RC only confirms if not, but cannot confirm if so.
  if rslt == NO:
    log.info('record_id=[{}]: \'other_enrollment\' is true. Bail.'\
             ''.format(record_id))
    log.info('out')
    return common.finalize(request)
  # 2/3: Check DB.
  rslt = _db_is_wcm_paired(redcap_server_tag, pid, record_id)
  if rslt == YES:
    log.info('record_id=[{}]: db indicates WCM pairing. Continue.'\
             ''.format(record_id))
    log.info('out')
    return request
  if rslt == NO:
    log.info('record_id=[{}]: db indicates non-WCM pairing. Bail.'\
             ''.format(record_id))
    log.info('out')
    return common.finalize(request)
  # 3/3: Check AoU API and potentially cache result in DB.
  rslt = _aou_api_is_wcm_paired(pmi_id)
  if rslt == YES:
    log.info('record_id=[{}]: AoU API indicates WCM pairing. Continue.'\
             ''.format(record_id))
    _cache_as_paired(redcap_server_tag, pid, record_id)
    log.info('out')
    return request
  if rslt == NO:
    log.info('record_id=[{}]: AoU API indicates non-WCM pairing. Bail.'\
             ''.format(record_id))
    _cache_as_not_paired(redcap_server_tag, pid, record_id)
    log.info('out')
    return common.finalize(request)
  if rslt == UNKNOWN:
    # We've tried everything at this point. They have a PMI ID
    # but we can't find a pairing. Do not proceed w/ wf chain.
    log.info('#reconciliation Could not determine affiliation for record ID: {}'\
             '. Bail.'.format(record_id))
    log.info('out')
    return common.finalize(request)
  raise Exception # Should never get here.

