#!/usr/bin/env python

################################################################################
# (c) 2013, COmputer SEcurity (COSEC) - Universidad Carlos III de Madrid
# Author: Guillermo Suarez de Tangil - guillermo.suarez.tangil@uc3m.es
################################################################################

import sys, os, shutil, tempfile, ntpath

from subprocess import Popen, call, PIPE
from shlex import split

# ------------------

class Event(object):
    def __init__(self, event):
	self.event_type = None
	self.event_raw = event

    def __parse__(self):
        if self.event_type != None:
            return
        elements = self.event_raw.split(': ')
        event = str(self.event_raw).split('(')[0][2:]
        self.event_type = str(event)
        return elements

    def get_event_handler(self, deviceId):
        elements = self.__parse__()
        try:
            klass = getattr(sys.modules[__name__], self.event_type)
            return klass(deviceId, elements)
        except AttributeError:
            raise EventNotSupportedByCloud('Event not supported by clone: ' + self.event_type)

# ------------------

class EventNotSupportedByCloud(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

# ------------------

class RunnerEvent():
    def __init__(self, deviceId, elements):
        self.deviceId = deviceId
        self.elements = elements
        self.endline = "\n"
        self.torun = "clone = MonkeyRunner.waitForConnection(deviceId='" + self.deviceId + "')" + self.endline

    def event_type(self):
        return self.__class__.__name__

    def add_call(self, call):
        self.torun += call + self.endline

    def clone_call(self):
        #pipe = Popen(split(self.torun), stdout=PIPE, shell=True)
        clonerunner_src = os.path.join(os.getcwd(), 'clonerunner.py')
        clonerunner_dst = os.path.join(os.getcwd(), 'gen_clonerunner')
        try:
            os.makedirs(clonerunner_dst)
        except OSError:
            pass
        clonerunner_file = tempfile.mktemp(prefix=self.event_type() + '_', suffix='.py', dir=clonerunner_dst)
        shutil.copyfile(clonerunner_src, clonerunner_file)
        clonerunner = open(clonerunner_file, 'a')
        clonerunner.write(self.torun)
        clonerunner.close()
        call(['monkeyrunner', clonerunner_file], stderr=PIPE)
        os.remove(clonerunner_file)

# ------------------
# %%%%%%%%%%%%%%%%%%

class ActivityManager(RunnerEvent):
    """
    Inputs: Package and Activity
    Running: 'Starting: Intent { act=android.intent.action.MAIN cat=[android.intent.category.LAUNCHER] flg=0x10200000 cmp=com.android.launcher/.CustomShirtcutActivity }'
    Running: 'Starting: Intent { dat=file:///mnt/sdcard/SinMachismoSi.apk cmp=com.android.packageinstaller/.InstallAppProgress (has extras) } from pid 785'
    Running: 'Starting: Intent { act=android.intent.action.MAIN cat=[android.intent.category.LAUNCHER] flg=0x10000000 pkg=es.booooo.sms cmp=es.booooo.sms/.SinMachismoSi } from pid 785'
    """

    cloud_tmp_dir = "./tmp_data/"

    def clone_run(self):
        print self.elements

        if "Starting" == self.elements[1]:
            self.startAction(self.elements[2])


    def startAction(self, elementIntent):
        #print " -----> " + elementIntent
        if "com.android.packageinstaller/.InstallAppProgress" in elementIntent and "file:///" in elementIntent:
            self.startActionInstaller(elementIntent)
        else:
            self.startActionIntent(elementIntent)
        
        # script to run
        print self.torun
        self.clone_call()
        try:
            shutil.rmtree(os.path.abspath(self.cloud_tmp_dir + "/*"))
            #os.remove(os.path.abspath(self.cloud_tmp_dir + "/*"))
        except OSError:
            pass

    def startActionInstaller(self, elementIntent): 
        # Start Installer
        intent=str(str(elementIntent.split("}")[0]).split("{")[1])
        for arg in intent.split():
            pair=arg.split("=")
            if len(pair) != 2:
                continue
            key=pair[0]
            val=pair[1]
            if "dat" in key:
                data=val
            if "cmp" in key:
                pair=val.split("/")
                package=pair[0]
                activity=pair[1]
        ## (i) Starting Installer Activity: No permissions to do this?
        #    self.torun += "runComponent = '" + package + "/" + activity + "'" + self.endline
        #    self.torun += "runData = '" + data + "'" + self.endline
        #    self.torun += "clone.startActivity(action=runAction, data=runData)" + self.endline
        # ^--------- I could't install the package throughout Intent: No permissions to do this?
        ## (ii) Installing package through emulator

        # ... 
	
        device_file = data.split("file://")[1]
        name = ntpath.basename(device_file)
        cloud_file = os.path.abspath(self.cloud_tmp_dir + name)

        print device_file
        print name


        call(['adb', "-d", "pull", device_file, self.cloud_tmp_dir], stderr=PIPE)
        #call(['adb', "-e", "push", cloud_tmp_dir + name, device_file], stderr=PIPE)  	

        self.add_call("clone.installPackage('" + cloud_file + "')")
        #os.remove(cloud_file)

    def startActionIntent(self, elementIntent): 

        action = ''
        categories = ''
        package = ''
        activity = ''
        data = ''

        uri = ''
        mimetype = ''
        extras = ''
        flags = ''

        # Other Intents
        arguments = ''
        intent=str(str(elementIntent.split("}")[0]).split("{")[1])
        for arg in intent.split():
            pair=arg.split("=")
            if len(pair) != 2:
                continue
            key=pair[0]
            val=pair[1]
            if "act" in key:
                action=val
                self.add_call("runAction = '" + action + "'")
                if len(arguments) > 0:
                    arguments += ', '
                arguments += 'action=runAction'
            if "cat" in key:
                categories=(val.split("]")[0]).split("[")[1]
		runCategories = ''
		for category in categories.split():
		    if len(runCategories) > 0:
			runCategories += ", "
		    runCategories += "'" +  category + "'"
                self.add_call("runCategories = [" + runCategories + "]")
                if len(arguments) > 0:
                    arguments += ', '
                arguments += 'categories=runCategories'
            if "cmp" in key:
                pair=val.split("/")
                package=pair[0]
                activity=pair[1]
                self.add_call("runComponent = '" + package + "/" + activity + "'")
                if len(arguments) > 0:
                    arguments += ', '
                arguments += 'component=runComponent'
       	    if "flg" in key: 
	        flags=val
		self.add_call("runFlags = " + flags + "")
		if len(arguments) > 0:
                    arguments += ', '
                arguments += 'flags=runFlags'
            if "dat" in key:
                data=val
                self.add_call("runData = '" + data + "'")
                if len(arguments) > 0:
                    arguments += ', '
	        arguments += 'component=runData'
            if "uri" in key:
                uri=val
                self.add_call("runURI = '" + data + "'")
                if len(arguments) > 0:
                    arguments += ', '
                arguments += 'component=runURI'
        self.add_call("clone.startActivity(" + arguments + ")")	    
		    


# %%%%%%%%%%%%%%%%%%

# %%%%%%%%%%%%%%%%%%

# %%%%%%%%%%%%%%%%%%

class Template(RunnerEvent):
    """
    Inputs:
    Running: ''
    """
    def clone_run():
	# inputs ()
	
	# script to run
	self.add_call("")
	self.clone_call()
    

