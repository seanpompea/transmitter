import sys
sys.path.insert(0, '../app/')

import wf_tpl_oncore_enroll as m

#------------------------------------------------------------------------------
'''
Usage: from the test folder, run:
python -m pytest
'''

#------------------------------------------------------------------------------
# test flexmatch_algo func

# 100% match
a1 = {'first-name': 'james',
      'last-name': 'joyce',
      'birthdate': '1882-02-02'}
a2 = {'first-name': 'james',
      'last-name': 'joyce',
      'birthdate': '1882-02-02'}

# dob mismatch
b1 = {'first-name': 'james',
      'last-name': 'joyce',
      'birthdate': '1882-02-02'}
b2 = { 'first-name': 'james',
      'last-name': 'joyce',
      'birthdate': '1882-02-03'}

# both names close
c1 = {'first-name': 'james a.',
      'last-name': 'joyce',
      'birthdate': '1882-02-02'}
c2 = { 'first-name': 'james',
      'last-name': 'joyce',
      'birthdate': '1882-02-02'}

# first names close but not last
d1 = {'first-name': 'james a.',
      'last-name': 'joyce',
      'birthdate': '1882-02-02'}
d2 = { 'first-name': 'james',
      'last-name': 'joycee',
      'birthdate': '1882-02-02'}

def test_flex_a():
  assert(m.flexmatch_algo(a1, a2) == 3) 

def test_flex_b():
  assert(m.flexmatch_algo(b1, b2) == 0) 

def test_flex_c():
  assert(m.flexmatch_algo(c1, c2) == 2) 

def test_flex_d():
  assert(m.flexmatch_algo(d1, d2) == 1) 


