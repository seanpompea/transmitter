from __future__ import division
from __future__ import print_function
from collections import *
from functools import *
from itertools import *
from operator import *

import kickshaws as ks

# local
import redcap_handler_template
import redcap_intake_workflow
import wf_aou_confirm_affiliation
import workflow_aou_events
import wf_tpl_oncore_enroll

'''
Handler for REDCap AoU Enrollment Projects.
'''

__all__ = ['compose_handler']

log = ks.smart_logger()

study_tag = 'aou'

def compose_handler(redcap_server_tag, project_id):
  workflow_chain = [redcap_intake_workflow.go,
                    wf_aou_confirm_affiliation.go,
                    workflow_aou_events.go
                    ]
  return redcap_handler_template.compose_handler(
    redcap_server_tag,
    project_id,
    study_tag,
    workflow_chain)

