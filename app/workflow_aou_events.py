from __future__ import division
from __future__ import print_function
from collections import *
from functools import *
from itertools import *
from operator import *

import kickshaws as ks

import datastore as store

'''
==============================================================================
AoU Events Workflow
==============================================================================

Use this workflow to assess enrollment and withdrawal events.

Rules -- which represent study policy -- are used to determine if 
a REDCap record indicates an event based on the evaluation of 
specific fields in the REDCap record. 

To maintain a record of events observed, an event is recorded in 
the datastore the first time it's observed for that REDCap record.

The go function adds two new key-value pairs to the request before
returning:
  o 'has-enrolled' with value of 'yes' or 'no'
  o 'has-withdrawn' with value of 'yes' or 'no'

==============================================================================
'''

__all__ = ['go']

#-----------------------------------------------------------------------------

log = ks.smart_logger()

#-----------------------------------------------------------------------------
# predefined keys/values for datastore

HAS_ENROLLED = 'has-enrolled'
HAS_WITHDRAWN = 'has-withdrawn'
YES = 'yes'
NO = 'no'

#-----------------------------------------------------------------------------
# datastore

def is_event_noted(redcap_server_tag, pid, record_id, key):
  '''Predicate'''
  log.info('Entered; REDCap env: [{}], pid: [{}], record_id: [{}], key: [{}]'\
           ''.format(redcap_server_tag, pid, record_id, key))
  if store.key_exists(redcap_server_tag, pid, record_id, key):
    rslt = store.get_latest_value(redcap_server_tag, pid, record_id, key)
    if rslt == YES:
      log.info('{} event already stored.'.format(key))
      return True
  log.info('{} event *not* stored.'.format(key))
  return False

def note_event(redcap_server_tag, pid, record_id, key):
  '''Store event in datastore. Use a key defined at the top of
  this module.'''
  rslt = store.put(redcap_server_tag, pid, record_id, key, YES)
  log.info(key + ' event stored just now for record_id: ' + record_id)
  return rslt

#-----------------------------------------------------------------------------
# enrollment

def redcap_indicates_enrollment(redcap_server_tag, pid, record):
  '''Rules:
    If the field "mrn" has a value AND
    If the field "pmi_id_test" has a value AND
    If the field "dob" has a value AND
    If the field "pmi_dob" has a value AND
    If the values of "dob" and "pmi_dob" are equal AND
    If enroll_date is not empty 
    THEN: has enrolled.'''
  if (record['mrn'] 
      and record['pmi_id_test'] 
      and record['dob'] 
      and record['pmi_dob'] 
      and record['enroll_date']):
    if record['dob'] == record['pmi_dob']:
        log.info('Record indicates enrollment.')
        return True
    else:
      log.info('Warning: dob and pmi_dob did not match.')
      return False
  else:
    log.info('One or more needed fields blank.')
    return False

def assess_enrollment(redcap_server_tag, pid, record):
  '''Return a map w/ containing key-value pair with key of 'has-enrolled' 
  and value of 'yes' or 'no'.'''
  log.info('in')
  record_id = record['record_id']
  rslt = {}
  # Note: it's possible event happened, we recorded it, but later record
  # was amended such that record no longer indicates enrollment.
  if (redcap_indicates_enrollment(redcap_server_tag, pid, record)
      or is_event_noted(redcap_server_tag, pid, record_id, HAS_ENROLLED)):
    rslt = {HAS_ENROLLED: YES}
    if not is_event_noted(redcap_server_tag, pid, record_id, HAS_ENROLLED):
      # If here, record indicates enrollment; since not noted before, note now.
      note_event(redcap_server_tag, pid, record_id, HAS_ENROLLED)
  else:
    rslt = {HAS_ENROLLED: NO}
  log.info('record_id: {}; assessment: {}'.format(record_id, str(rslt)))
  log.info('out')
  return rslt

#-----------------------------------------------------------------------------
# withdrawal

def redcap_indicates_withdrawal(redcap_server_tag, pid, record):
  '''IF withdrawal_date is not empty
     THEN record indicates a withdrawal.'''
  return record.get('withdrawal_date', '') != ''

def assess_withdrawal(redcap_server_tag, pid, record):
  '''
  Return a map w/ containing key-value pair with key of 'has-withdrawn'
  and value of 'yes' or 'no'.
  Note: normally, you want to call this after assessing enrollment;
  withdrawal depends in part on prior enrollment and it's 
  theoretically possible that we'll process both events in a single
  request.
  '''
  log.info('in')
  record_id = record['record_id']
  rslt = {}
  # Note: enrollment must have been noted in the datastore as a
  # prereq for a withdrawal.
  # Note: It's possible event happened, we recorded it, but later record
  # was amended such that record no longer indicates withdrawal.
  if (is_event_noted(redcap_server_tag, pid, record_id, HAS_ENROLLED)
      and (redcap_indicates_withdrawal(redcap_server_tag, pid, record)
           or is_event_noted(redcap_server_tag, pid, record_id, HAS_WITHDRAWN))):
    rslt = {HAS_WITHDRAWN: YES}
    if not is_event_noted(redcap_server_tag, pid, record_id, HAS_WITHDRAWN):
      # If here, record indicates withdrawal; since not noted before, note now.
      note_event(redcap_server_tag, pid, record_id, HAS_WITHDRAWN)
  else:
    rslt = {HAS_WITHDRAWN: NO}
  log.info('record_id: {}; assessment: {}'.format(record_id, str(rslt)))
  log.info('out')
  return rslt

#-----------------------------------------------------------------------------
# driver

def go(request):
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
  request.update(assess_enrollment(redcap_server_tag, pid, record))
  request.update(assess_withdrawal(redcap_server_tag, pid, record))
  log.info('out')
  return request

