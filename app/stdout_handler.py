import sys
import redcaplib as rc

__all__ = ['handle']

def handle(req):
  try:
    pyld = rc.parse_det_payload(req.get('data','')) 
    print 'Request:'
    print str(req)
    print 'DET payload:'
    print str(pyld)
    resp = {'status': 200
           ,'content-type': 'text/plain'
           ,'body': 'ok'}
    return resp
  except Exception, e:
    return {'status': 500 
           ,'content-type': 'text/plain'
           ,'body': 'error'} 

