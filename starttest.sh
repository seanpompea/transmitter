#!/bin/sh
# Modify the details below to suit your environment.
cd /home/ras3005/boost/transmitter-test
source /home/ras3005/boost/transmitter-test/venv/bin/activate && nohup python /home/ras3005/boost/transmitter-test/main.py >> out.log 2>&1 &

