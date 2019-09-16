from __future__ import division
from __future__ import print_function

import kickshaws as ks
import oncorelib as oncore

import common
import datastore as store

__all__ = ['compose']

#------------------------------------------------------------------------------

log = ks.smart_logger()

FLEXMATCH_MIN_CONFIDENCE = 2

#------------------------------------------------------------------------------

def extract_mrn(request):
  # In newer REDCap versions, sometimes the record is a list;
  # in that case, we only want first element of the list.
  record = {}
  if type(request['full-record']) == list:
    record = request['full-record'][0]
  else:
    record = request['full-record']
  return record['mrn']

def simple_compare(d1, d2):
  '''Predicate; determines if all values in both maps 
  match (note that it ignores case).'''
  for k,v in d1.items():
    if d2.get(k, '*').lower() != v.lower():
      return False
  return True

def flexmatch_algo(d1, d2):
  '''Flexmatch algorithm for demographics comparison.
  d1 and d2 should be maps with (at least) the following keys:
    o first-name
    o last-name
    o birthdate as a string formatted yyyy-mm-dd
      (REDCap data will be formmatted like this; the oncorelib
      applies this formatting before returning subject data.)
  Returns a confidence level as int from 0 to 3 (inclusive).
    o 3: first, last, and dob match.
    o 2: first and last mostly match, dob match.
    o 1: first and/or last significant  mismatch, dob match.
    o 0: dob mismatch (other values not checked).
  '''
  if d1['dob'] != d2['dob']:
    return 0
  # Otherwise, dobs match.
  if (d1['first-name'].lower() == d2['first-name'].lower()
      and d1['last-name'].lower() == d2['last-name'].lower()):
    # All three demographic elements match.
    return 3
  if ( (d1['first-name'].lower() in d2['first-name'].lower()
        or d2['first-name'].lower() in d1['first-name'].lower())
       and
       (d1['last-name'].lower() in d2['last-name'].lower()
        or d2['last-name'].lower() in d1['last-name'].lower()) ):
    return 2
  return 1

def sufficient_confidence(request, retrieved_demographics):
  '''Predicate'''
  # Extract relevent demographics from request so
  # both structures have key parity, then pass 
  # to the actual algo.
  record = {}
  if type(request['full-record']) == list:
    record = request['full-record'][0]
  else:
    record = request['full-record']
  # Set up d1 so that key-wise it matches what (ought to be)
  # in the 2nd passed-in arg.
  d1 = dict(
         zip(['first-name', 'last-name', 'birthdate'],
             [record['name_first'], record['name_last'], record['dob']]))
  return (flexmatch_algo(d1, retrieved_demographics)
          == FLEXMATCH_MIN_CONFIDENCE)

#------------------------------------------------------------------------------
# datastore

ENROLLED_KEY = 'has-enrolled'
JIRA_ENROLLMENT_TICKET_KEY = 'jira-enrollment-ticket-created'
ONCORE_REGISTERED_KEY = 'enrollment-registered-in-oncore'
YES = 'yes'

# reconciliation flags
ONCORE_DEMOGRAPHICS_NOT_FOUND = 'oncore-demographics-not-found'
DEMOGRAPHICS_MISMATCH = 'demographics-mismatch'

def clear_all_recon_flags(redcap_server_tag, project_id, record_id):
  '''Clear all reconciliation flags in one fell swoop.'''
  store.unset_flag_if_set(redcap_server_tag, project_id, record_id,
                          ONCORE_DEMOGRAPHICS_NOT_FOUND)
  store.unset_flag_if_set(redcap_server_tag, project_id, record_id,
                          DEMOGRAPHICS_MISMATCH) 

#------------------------------------------------------------------------------

def _go(redcap_server_tag, project_id, study_tag, request):
  '''You generally won't call this directly; instead, use
  the 'compose' function further below.''' 
  log.info('in')
  record_id = request['record-id']
  # Note that below we also need to check for a JIRA ticket, which 
  # was the old pathway to CTMS registration.
  if (request[ENROLLED_KEY] == YES
      and not store.flag_is_set(redcap_server_tag, project_id, record_id,
                                JIRA_ENROLLMENT_TICKET_KEY)
      and not store.flag_is_set(redcap_server_tag, project_id, record_id,
                                ONCORE_REGISTERED_KEY)):
    mrn = extract_mrn(request)
    study_config = common.get_study_config(study_tag)
    handler_tag = redcap_server_tag + str(project_id)
    oncore_spec = study_config[
                    study_config['handler-tag-to-env-tag'][handler_tag]
                      ]['oncore-spec']
    subject_num = None
    demographics = oncore.get_subject_data(oncore_spec, mrn)
    # Grab demographics from OnCore; then compare with REDCap before
    # deciding to register in OnCore or not.
    if not oncore.subject_record_exists(demographics):
      # Flag, log, an bail.
      msg = ('No demographics found in OnCore for '
             'record ID of {}'.format(record_id))
      store.set_flag_if_unset(redcap_server_tag, project_id, record_id,
                              ONCORE_DEMOGRAPHICS_NOT_FOUND)
      log.info(msg)
      return request
    else:
      # OnCore gave us demographics; prep and keep going.
      subject_num = oncore.extract_subject_num(demographics)
      demographics = oncore.prep_subject_data(demographics)
    # Here, we should have demographics, or already bailed.
    # Also note that, by this point, demographics should have
    # keys/structure in format expected by oncorelib's register function.
    if sufficient_confidence(request, demographics):
      # If we get here, we're ready to register.
      # Unset previously set recon flags since they're no longer
      # necessary -- nor correct anymore, for that matter.
      clear_all_recon_flags(redcap_server_tag, project_id, record_id)
      protocol = study_config['study-details']['protocol-number']
      log.info('About to register; record ID: {}'.format(record_id))
      oncore.register_subject_to_protocol(oncore_spec,
                                          protocol,
                                          demographics,
                                          subject_num)
      log.info('Registered; record ID: {}'.format(record_id))
    else:
      # Flag, log, and bail.
      msg = ('Demographics comparison confidence below threshold for '
             'record ID of {}'.format(record_id))
      store.set_flag_if_unset(redcap_server_tag, project_id, record_id,
                              DEMOGRAPHICS_MISMATCH)
      log.info(msg)
  else:
    log.info('No action.')
  log.info('out')
  return request

#------------------------------------------------------------------------------

def compose(redcap_server_tag, project_id, study_tag):
  '''Returns a 'go'-style function (takes a request-shaped map
  and returns it as well), suitable for use in a workflow chain.
  '''
  return partial(_go, redcap_server_tag, project_id, study_tag)

