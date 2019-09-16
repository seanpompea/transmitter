import pymysqlwrapper as db
from common import *
from kickshaws import *

'''
===============================================================================

-----------------------
      datastore
-----------------------

Interface for simple key-value-like storage in MySQL. Also timestamps
each entry so that longitudinal versioning can be maintained for
any particular key.

===============================================================================
'''

db_table = 'datastore'
db_spec = get_app_config().get('db-spec')

# Should throw exception if there's a database connectivity issue.
# Program should not proceed if so.
db.check_conn(db_spec)

#------------------------------------------------------------------------------

def key_exists(redcap_env, projectid, recordid, attrname):
  qy1 = '''select count(*) as ttl
          from datastore
          where env = %s and projectid = %s
            and recordid = %s
            and attrname = %s	'''
  vals = redcap_env, projectid, recordid, attrname
  ttl =	db.go(db_spec, qy1, vals, db.ReturnKind.SINGLEVAL)
  if ttl > 0: return True
  else: return False

def get_latest_value(redcap_env, projectid, recordid, attrname):
  '''Will return empty string if it can't find anything.'''
  qy2 = '''select ifnull(attrval, 'nil') as attrval
          from datastore
          where env = %s and projectid = %s
            and recordid = %s
            and attrname = %s
          order by ts DESC -- put latest value in first row '''
  vals = redcap_env, projectid, recordid, attrname
  # Grab the first value in the first row
  rslt = db.go(db_spec, qy2, vals, db.ReturnKind.SINGLEVAL)
  return rslt

def put(redcap_env, projectid, recordid, attrname, attrval):
  '''Put a new name-value pair into the store. It will create
  a new version if an older one already exists. Note: returns empty tuple.'''
  stmt = '''insert into datastore (env, projectid, recordid, attrname, attrval)
            values (%s, %s, %s, %s, %s) '''
  vals = redcap_env, projectid, recordid, attrname, attrval
  rslt = db.go(db_spec, stmt, vals, commit=True)
  return rslt

#------------------------------------------------------------------------------
# flag functions
# A flag is a key with a value of either 'yes' or 'no' indicating set/unset.
# (Absence is equivalent to 'no' or unset.)

def flag_is_set(redcap_env, project_id, record_id, key):
  '''Convenience predicate function that checks whether
  the value corresponding to the passed-in args is 'yes'.
  '''
  return (get_latest_value(redcap_env, project_id, record_id, key)
          == 'yes')

def set_flag_if_unset(redcap_env, project_id, record_id, key):
  if not flag_is_set(redcap_env, project_id, record_id, key):
    return put(redcap_env, project_id, record_id, key, 'yes')

def unset_flag_if_set(redcap_env, project_id, record_id, key):
  if flag_is_set(redcap_env, project_id, record_id, key):
    return put(redcap_env, project_id, record_id, key, 'no')

