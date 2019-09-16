from __future__ import division
from __future__ import print_function
from collections import *
from functools import *
from itertools import *
from operator import *

import json
import kickshaws as ks
import jiralib as jira
import common 
import aou_common
import datastore as store

__all__ = ['go']

'''
===============================================================================

-----------------------
AoU Enrollment Workflow
-----------------------

If participant has enrolled, create a JIRA enrollment ticket (if we
haven't done so before; we use the database to keep track of
this.) 

The OBC team will then transcribe the participant data into
the CTMS (CREST) as a new enrollment.

WHEN TO USE

Call this workflow after workflow_aou_events.

===============================================================================
'''

log = ks.smart_logger()

#------------------------------------------------------------------------------
# jira strings when creating tickets

study_details = aou_common.get_study_details('aou')
jira_summary = study_details.get('pi')
protocol_num = study_details.get('protocol-number')
jira_test_msg = ' [THIS IS A TEST TICKET; DO NOT PROCESS]'
jira_kind = 'Enrollment'
message = 'This is an automatically generated ticket.  Although PDFs of '\
          'participant consent forms are not available for this study, '\
          'please transcribe participant information from this ticket to '\
          'CREST.  If you have questions or comments, please contact '\
          'its-aou@med.cornell.edu.'
description_template = 'Name: $FIRST$ $LAST$ (MRN: $MRN$)\n'\
    'DOB: $DOB$\nREDCap Record ID: $RECORDID$\nDate Enrolled:'\
    ' $DATE_ENROLLED$\nProtocol: {}\n\n{}'.format(protocol_num, message)

#------------------------------------------------------------------------------

flag = 'jira-enrollment-ticket-created'

def have_created_jira_ticket(redcap_server_tag, projectid, recordid):
  '''Returns true or False'''
  log.info('Entered; REDCap env: [{}], projectid: [{}], recordid: [{}].'\
           ''.format(redcap_server_tag, projectid, recordid))
  if store.exists(redcap_server_tag, projectid, recordid, flag):
    rslt = store.get_latest_value(redcap_server_tag, projectid, recordid, flag)
    if rslt == 'yes':
      log.info('Already created JIRA enrollment ticket.')
      return True
  log.info('Have not created JIRA enrollment ticket.')
  return False

def set_jira_ticket_created_flag(redcap_server_tag, projectid, recordid):
  rslt = store.put(redcap_server_tag, projectid, recordid, flag, 'yes')
  return rslt

def store_ticket_id(redcap_server_tag, projectid, recordid, ticket_id):
  '''Store the Jira ticket ID in the db; useful for enrollment
  reconciliation later, etc.'''
  key = 'obc-enrollment-ticket-id'
  rslt = store.put(redcap_server_tag, projectid, recordid, key, ticket_id)
  log.info('Stored ticket id [{}] in db for record id [{}]'.format(ticket_id, recordid))
  return rslt

def create_jira_ticket(redcap_server_tag, projectid, rcd, request):
  '''Creates Jira ticket. Returns the result of calling jiralib.
  Note: assumption is that should_create_jira_ticket returned true (if not,
  you're going to potentially have a bad time).'''
  name_first = rcd['name_first']
  name_last = rcd['name_last']
  mrn = rcd['mrn']
  date_enrolled = rcd['enroll_date']
  description = (
      description_template
        .replace('$FIRST$', name_first)
        .replace('$LAST$', name_last)
        .replace('$DOB$', rcd.get('dob'))
        .replace('$MRN$', mrn)
        .replace('$RECORDID$', rcd.get('record_id'))
        .replace('$DATE_ENROLLED$', date_enrolled))
  env_tag = request['env-tag']
  study_tag = request['study-tag']
  study_config = common.get_study_config(study_tag)
  jira_spec = study_config[env_tag]['jira-spec']
  jira_project = study_config[env_tag]['jira-project']
  my_summary = jira_summary
  if env_tag != 'prod' and jira_project == 'OBC':
    my_summary += jira_test_msg
  additional_fields = {}
  if jira_project == 'OBC':
    additional_fields['customfield_10070'] = protocol_num
  result = jira.create_issue(jira_spec
                            ,jira_project
                            ,jira_kind
                            ,my_summary
                            ,description
                            ,None              # exclude assignee 
                            ,additional_fields)
  if study_config.get('send-jira-ping-emails') == 'yes':
    try:
      ks.send_email(study_config[env_tag]['jira-ping-from-email']
                    ,study_config[env_tag]['jira-ping-to-email']
                    ,'jira enrollment result'
                    ,str(str(result) + "\n" + "record: "+rcd['record_id'] + "\n" 
                         + str(redcap_server_tag + str(projectid))))
    except Exception, ex:
      log.error('Attempting to send Jira ping email but failed: ' + str(ex))
  if result['status'] != 201:
    raise Exception(str(result))
  log.info('Created Jira enrollment ticket; details: {}'.format(result))
  return result

def should_create_jira_ticket(request, redcap_server_tag, pid, record_id):
  return (
    request['has-enrolled'] == 'yes'
    and not have_created_jira_ticket(redcap_server_tag, pid, record_id))

#------------------------------------------------------------------------------
# driver

def go(req):
  '''
  The incoming request-shaped map should have these keys:
      o client_ip         (from metaphor)
      o method            (from metaphor)
      o path              (from metaphor)
      o redcap-server-tag        
      o pid               
      o full-record            
      o has-enrolled      (from workflow_aou_events)
  Returns the request unmodified.
  ''' 
  log.info('in')
  redcap_server_tag = req['redcap-server-tag']
  pid = req['pid']
  # In newer REDCap versions, sometimes record is a list;
  # we only want first part in that case.
  record = {}
  if type(req['full-record']) == list:
    record = req['full-record'][0]
  else:
    record = req['full-record']
  record_id = record['record_id']
  try:
    if should_create_jira_ticket(req, redcap_server_tag, pid, record_id):
      log.info('Enrolled; new JIRA ticket needs to be created.')
      rslt = create_jira_ticket(redcap_server_tag, pid, record, req)
      log.info('Created ticket; will insert new data into database (flag and ticket id).')
      ticket_id = json.loads(rslt.get('payload')).get('key') 
      store_ticket_id(redcap_server_tag, pid, record_id, ticket_id)
      set_jira_ticket_created_flag(redcap_server_tag, pid, record_id)
      log.info('{} flag set for {}'.format(flag, record_id))
    else:
      log.info('No action taken.')
  except Exception, ex:
    log.exception(ex)
    raise ex
  log.info('out')
  return req

