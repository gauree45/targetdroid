
import sys, json, time, curses, signal, os
import zipfile, StringIO
from array import array
from threading import Thread
from xml.dom import minidom
#from utils import AXMLPrinter
import hashlib
from pylab import *
from yaml import load, dump
from markov2 import mongo_markov

try:
    from yaml import CLoader as Loader, CDumper as Dumper
except ImportError:
    from yaml import Loader, Dumper
import re
import redis
import unittest
#import markov
#from markov.markov import Markov

from device2cloneEvents.LogcatEvent import *


# -----------------------
# Constants
# -----------------------
debug = 1

# -----------------------
# Functions
# -----------------------

def get_keys(model):
    model_keys = model.get_keys()
    return [k.split(":")[1] for k in model_keys]

def decode(s, encodings=('ascii', 'utf8', 'latin1')):
    for encoding in encodings:
        try:
            return s.decode(encoding)
        except UnicodeDecodeError:
            pass
    return s.decode('ascii', 'ignore')

# Match an event with the event-model map
def match(map, input):
    for reg in map:
        if re.search(reg, input):
            #print input + ": " + map[reg]
            cmd = str(map[reg])
            if "*" in cmd:
                # getting the pattern specified in the map
                pattern = cmd.split("*")
                cmd = pattern[0].strip() # rewriting cmd
                # from init to end just, descarting the rest
                init = pattern[1][0]
                end = pattern[1][1]
                value = input[input.index(init)+1:input.index(end)]
                cmd += "_" + value
            yield cmd


markov=mongo_markov.MarkovChain()
# -----------------------
# Params
# -----------------------
print(sys.argv[0])
print(sys.argv[1])
print (sys.argv[2])


log_file=sys.argv[1]
words=log_file.split('_')
print words[0]
device_id=words[0]
event_type='Battery'
map_file = "context2model.map"

if len(sys.argv) >= 3 and len(sys.argv[2]) > 0:
    map_file = sys.argv[2]
    print("using the map file")
else:
    print "Using default map file: " + map_file

try:

    map = load(open(map_file), Loader=Loader)
except:
    print "Error: Map file is not a valid input parameter file: " + map_file
    sys.exit(1)

delete = False
if len(sys.argv) >= 3 and len(sys.argv[2]) > 0:
    delete = sys.argv[2]

# -----------------------
# Logo
# -----------------------


print '##########################################################################'
print '# Author: Guillermo Suarez de Tangil - guillermo.suarez.tangil@uc3m.es   #'
print '# (c) 2013, COmputer SEcurity (COSEC) - Universidad Carlos III de Madrid #'
print '##########################################################################'
print '#                                                                        #'
print '#                                                                        #'
print '#                                                                        #'
print '#   .d8888b .d88b.  .d8888b   .d88b.   .d8888b                           #'
print '#  d88P"   d88""88b 88K      d8P  Y8b d88P"                              #'
print '#  888     888  888 "Y8888b. 88888888 888                                #'
print '#  Y88b.   Y88..88P      X88 Y8b.     Y88b.                              #'
print '#   "Y8888P "Y88P"   88888P\'  "Y8888   "Y8888P                           #'
print '#                                                                        #'
print '#                                                                        #'
print '#                                                                        #'
print '#                    .d8888b.                                            #'
print '#                   d88P  Y88b                                           #'
print '#                        .d88P                                           #'
print '#  888  888  .d8888b    8888"  88888b.d88b.       .d88b.  .d8888b        #'
print '#  888  888 d88P"        "Y8b. 888 "888 "88b     d8P  Y8b 88K            #'
print '#  888  888 888     888    888 888  888  888     88888888 "Y8888b.       #'
print '#  Y88b 888 Y88b.   Y88b  d88P 888  888  888 d8b Y8b.          X88       #'
print '#   "Y88888  "Y8888P "Y8888P"  888  888  888 Y8P  "Y8888   88888P\'       #'
print '#                                                                        #'
print '#                                                                        #'
print '#                                                                        #'
print '##########################################################################'
print '########################### COSEC Usage2Model ############################'
print '##########################################################################'



# -----------------------
# Variables
# -----------------------

#model_name = "model"
#context_model =  Markov(prefix=model_name)
#if delete:
#    print "# Flushing " + model_name
#    context_model.flush(prefix=True)

#print "# Using " + model_name

buffer_max_len = 2
buffer = []

# -----------------------
# Main
# -----------------------
while 1:
    try:
        #print ("inside try")
        logcatInput = sys.stdin.readline()
        #print logcatInput
        if not logcatInput:
            break

        # Decode input events
        event_raw = decode(logcatInput)

        # Matching events of interest with context
        context = match(map, str(event_raw))
        #print context

        # Add the events to the model
        for c in context:

            #if "*" in c:


            buffer.append(c.replace(" ", "_"))

            if len(buffer) >= buffer_max_len:
                #buffer_line = ' '.join([str(x) for x in buffer])
                #context_model.add_pair_to_index(buffer)
                state=buffer[0]
                prediction=buffer[1]

                print buffer
                markov.insert(state,prediction,device_id,event_type)
                buffer = []

    except KeyboardInterrupt:
        break

# Add the reminder events to the model
if len(buffer) > 0:
    buffer_line = ' '.join([str(x) for x in buffer])
    #context_model.add_pair_to_index(buffer)
    print (buffer)
#prediction = context_model.generate(max_words=buffer_max_len)
#print prediction
#print context_model.score_for_pair(prediction)

#print "# Output stored in DB " + model_name + ":"
#print get_keys(context_model)
