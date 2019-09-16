from common import *

study_tag = 'aou'

def get_env_tag_for_handler(handler_tag, study_tag='aou'):
  '''See the aou-config.json file and documentation for details'''
  cfg = get_study_config(study_tag)
  return cfg.get('envs').get(handler_tag)
  
def get_study_details(study_tag='aou'):
  '''See the aou-config.json file and documentation for details'''
  return get_study_config(study_tag).get('study-details')  


