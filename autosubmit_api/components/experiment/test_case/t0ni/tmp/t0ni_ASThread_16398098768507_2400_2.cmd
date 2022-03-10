#!/usr/bin/env python2
###############################################################################
#              t0ni_ASThread_16398098768507_2400_2
###############################################################################
#
#SBATCH -J t0ni_ASThread_16398098768507_2400_2
#SBATCH --qos=bsc_es
#SBATCH -A bsc32
#SBATCH --output=t0ni_ASThread_16398098768507_2400_2.out
#SBATCH --error=t0ni_ASThread_16398098768507_2400_2.err
#SBATCH -t 04:00:00
#SBATCH --cpus-per-task=1
#SBATCH -n 2400
#

#
###############################################################################

import os
import sys
from threading import Thread
from commands import getstatusoutput
from datetime import datetime
from math import ceil
from collections import OrderedDict
import copy
class Unbuffered(object):
   def __init__(self, stream):
       self.stream = stream
   def write(self, data):
       self.stream.write(data)
       self.stream.flush()
   def writelines(self, datas):
       self.stream.writelines(datas)
       self.stream.flush()
   def __getattr__(self, attr):
       return getattr(self.stream, attr)

sys.stdout = Unbuffered(sys.stdout)
wrapper_id = "61LRwk74h6_FAILED"
# Defining scripts to be run
scripts= ['t0ni_19931101_fc0_1_SIM.cmd', 't0ni_19931101_fc0_2_SIM.cmd']

class JobThread(Thread):
    def __init__ (self, template, id_run):
        Thread.__init__(self)
        self.template = template
        self.id_run = id_run

    def run(self):
        jobname = self.template.replace('.cmd', '')
        os.system("echo $(date +%s) > "+jobname+"_STAT")
        out = str(self.template) + ".out"
        err = str(self.template) + ".err"
        print(out+"\n")
        command = "bash " + str(self.template) + " " + str(self.id_run) + " " + os.getcwd()
        (self.status) = getstatusoutput(command + " > " + out + " 2> " + err)

failed_wrapper = os.path.join(os.getcwd(),wrapper_id)
for i in range(len(scripts)):
    current = JobThread(scripts[i], i)
    current.start()
    current.join()
    
    completed_filename = scripts[i].replace('.cmd', '_COMPLETED')
    completed_path = os.path.join(os.getcwd(), completed_filename)
    failed_filename = scripts[i].replace('.cmd', '_FAILED')
    failed_path = os.path.join(os.getcwd(), failed_filename)
    failed_wrapper = os.path.join(os.getcwd(), wrapper_id)
    if os.path.exists(completed_path):
        print datetime.now(), "The job ", current.template," has been COMPLETED"
    else:
        open(failed_wrapper,'w').close()
        open(failed_path, 'w').close()
        print datetime.now(), "The job ", current.template," has FAILED"
        #os._exit(1)
    
    if os.path.exists(failed_wrapper):
        os.remove(os.path.join(os.getcwd(),wrapper_id))
        wrapper_failed = os.path.join(os.getcwd(),"WRAPPER_FAILED")
        open(wrapper_failed, 'w').close()
        os._exit(1)
    
