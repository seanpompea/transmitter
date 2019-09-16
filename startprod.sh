#!/bin/sh
# Modify the details below to suit your environment.
cd /home/ras3005/boost/transmitter-prod
source /home/ras3005/boost/transmitter-prod/venv/bin/activate && nohup python /home/ras3005/boost/transmitter-prod/main.py >> out.log 2>&1 &

