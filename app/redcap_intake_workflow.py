from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from collections import *
from functools import *
from itertools import *
from operator import *

import sys
import json

import kickshaws as ks
import redcaplib
import common

log = ks.smart_logger()

#------------------------------------------------------------------------------

def go(request):
  log.info('Entered; redcap-server-tag=[{}]; pid=[{}]'.format(
           request['redcap-server-tag'], request['pid']))
  try:

    # Do a bit of setup. (redcap_handler_template should have loaded several
    # bits of pertinent data into the request map.)
    study_tag = request['study-tag']
    study_config = common.get_study_config(study_tag)
    env_tag = study_config['handler-tag-to-env-tag'][request['handler-tag']]

    redcap_spec = study_config[env_tag]['redcap-spec']
    record_id = request['record-id']

    # Call REDCap API and retrieve full record.
    record = redcaplib.get_full_record(redcap_spec, record_id)
    log.info('Retrieved full record from REDCap API for record id of: ['
             + str(record_id) + ']')

    # Load new information into request for downstream use.
    request['env-tag'] = env_tag
    request['full-record'] = record

    # All done. Return.
    return request

  except Exception, e:
    log.error('Exception caught: ' + str(e))
    raise e

