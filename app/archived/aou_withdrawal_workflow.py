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

------------------------------
REDCap AoU Withdrawal Workflow
------------------------------

WHAT IT DOES

This workflow creates an OBC JIRA withdrawal ticket if participant has withdrawn
(per rules established as study policy) and a JIRA ticket has not 
yet been created. (The OBC team will then transcribe the participant 
data into the CTMS (CREST) as a widthdrawal.)

WHEN TO USE

workflow_aou_events must have been called prior to this one. 
Additionally, to ensure correct rule processing, you will almost always also
want to call aou_enrollment_workflow beforehand (since the definition of withdrawal
depends on whether enrollment happened), but it is not strictly
required from a technical standpoint. 

===============================================================================
'''
#------------------------------------------------------------------------------
# load specs and config

log = ks.smart_logger()
study_details = aou_common.get_study_details('aou')

#------------------------------------------------------------------------------
# jira strings when creating tickets

jira_test_msg = ' [THIS IS A TEST TICKET; DO NOT PROCESS]'
jira_kind = 'Disenrollment'

#------------------------------------------------------------------------------
# db flag

flag = 'jira-withdrawal-ticket-created'

def have_created_jira_withdrawal_ticket(redcap_server_tag, projectid, recordid):
  '''Returns True or False'''
  log.info('Entered; REDCap env: [{}], projectid: [{}], recordid: [{}]'\
           ''.format(redcap_server_tag, projectid, recordid))
  if store.exists(redcap_server_tag, projectid, recordid, flag):
    rslt = store.get_latest_value(redcap_server_tag, projectid, recordid, flag)
    if rslt == 'yes':
      log.info('Already created JIRA withdrawal ticket.')
      return True
  log.info('Have not created JIRA withdrawal ticket.')
  return False

def set_jira_ticket_created_flag(redcap_server_tag, projectid, recordid):
  attrval = 'yes'
  rslt = store.put(redcap_server_tag, projectid, recordid, flag, attrval)
  return rslt

def calc_date_withdrawn(rcd):
  '''Currently, the presence of 'withdrawal_date' means withdrawal occurred.'''
  return rcd.get('withdrawal_date')

def store_ticket_id(redcap_server_tag, projectid, recordid, ticket_id):
  attrname = 'obc-withdrawal-ticket-id'
  rslt = store.put(redcap_server_tag, projectid, recordid, attrname, ticket_id)
  log.info('Stored ticket id [{}] in db for record id [{}]'.format(ticket_id, recordid))
  return rslt

def create_jira_ticket(redcap_server_tag, projectid, rcd, request):
  '''Kind of ticket (here, 'Disenrollment') is determined by jira_kind variable.'''
  name_first = rcd['name_first']
  name_last = rcd['name_last']
  mrn = rcd['mrn']
  name_mrn = name_first + ' ' + name_last + ' (' + mrn + ')'
  date_withdrawn = calc_date_withdrawn(rcd)
  env_tag = request['env-tag']
  study_tag = request['study-tag']
  study_config = common.get_study_config(study_tag)
  jira_spec = study_config[env_tag]['jira-spec']
  jira_project = study_config[env_tag]['jira-project']
  jira_summary = study_details.get('pi')
  protocol_num = study_details.get('protocol-number')
  if env_tag != 'prod' and jira_project == 'OBC':
    jira_summary += jira_test_msg
  additional_fields = {}
  if jira_project == 'OBC':
    additional_fields['customfield_10190'] = name_mrn
    additional_fields['customfield_10070'] = protocol_num
    additional_fields['customfield_10191'] = date_withdrawn
    # customfield_10193 below is Withdrawal Reason; 10424 means "Pt. Withdrew"
    additional_fields['customfield_10193'] = {'id': '10424'}
  result = jira.create_issue(jira_spec
                            ,jira_project
                            ,jira_kind
                            ,jira_summary
                            ,None              # exclude description
                            ,None              # exclude assignee
                            ,additional_fields)
  if study_config.get('send-jira-ping-emails') == 'yes':
    try:
      ks.send_email(study_config[env_tag]['jira-ping-from-email'],
                    study_config[env_tag]['jira-ping-to-email'],
                    'jira withdrawal result',
                    str(str(result) + '\n' + "record: "+rcd['record_id'] + "\n" 
                        + str(redcap_server_tag + str(projectid))))
    except Exception, ex:
      log.error('Attempting to send Jira ping email but failed: ' + str(ex))
  if result.get('status') != 201:
    raise Exception(str(result))
  log.info('Created Jira withdrawal ticket; details: {}'.format(result))
  return result

def should_create_jira_ticket(request, redcap_server_tag, pid, record_id):
  return (
    request['has-withdrawn'] == 'yes'
    and not have_created_jira_withdrawal_ticket(redcap_server_tag, pid, record_id))

#------------------------------------------------------------------------------
# driver

def go(req):
  '''The incoming request-shaped map should have these keys:
      o client_ip         (metaphor)
      o method            (metaphor)
      o path              (metaphor)
      o redcap-server-tag        
      o pid               
      o full-record            
      o new-enrollment    from aou_enrollment_workflow
  This function returns the request unmodified.
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
      log.info('About to create withdrawal ticket.')
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

