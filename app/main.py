import sys
import json
# WCM libraries
import metaphor
from kickshaws import *
# app modules
from common import *
# app modules - handlers
import stdout_handler
import test_email_handler
import hello_world_handler
import aou_handler

cfg = get_app_config() 
log = smart_logger()

def main():
  '''In this function we set up a collection of route handlers, and
  then we start up the listener. A route handler is a function
  that takes a *single* argument, a request-shaped map (see README).
  '''
  routes = {

    # Hello world endpoint for testing:
    '/hello-world': hello_world_handler.handle

    # Test project on sandbox server
    ,'/sand1090': stdout_handler.handle 

    # AoU DEV project (pid 2897) on REDCap prod server
    ,'/prod2897': aou_handler.compose_handler('prod', 2897)

    # AoU TST project (pid 2911) on REDCap prod server
    ,'/prod2911' : aou_handler.compose_handler('prod', 2911)

    # AoU Production project (pid 2525) on REDCap prod server:
    ,'/prod2525': aou_handler.compose_handler('prod', 2525)

  }
  path_to_key = cfg['path-to-key']
  path_to_pem = cfg['path-to-pem']
  log.info('-----------------------------------------------------')
  log.info('---------------STARTING TRANSMITTER------------------')
  metaphor.listen(routes, cfg['port'], path_to_key, path_to_pem, None, logger=log)
  return 

if __name__ == "__main__": main()

