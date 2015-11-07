#!/usr/bin/env python

################################################################################
# (c) 2013, COmputer SEcurity (COSEC) - Universidad Carlos III de Madrid
# Author: Guillermo Suarez de Tangil - guillermo.suarez.tangil@uc3m.es
################################################################################

import sys, os, shutil, tempfile, ntpath, telnetlib, socket

from subprocess import Popen, call, PIPE
from shlex import split

# ------------------

class Comando(object):

    def __init__(self, comando):
        self.comandoraw = comando
        self.comando = None

    def __parse__(self):
        self.comando = str(self.comandoraw)

    def execTelnet(self):

        self.__parse__()

        ip = "localhost"
        port = 5554

        try:
            telnet = telnetlib.Telnet(ip, port)

        except EOFError:
            print "Error: cannot connect to the cloud..."
            raise

        try:

            telnet.read_until("OK")
            telnet.write(self.comando + "\r\n")

        except socket.error:
            print "Error: cannot connect to the cloud..."

        telnet.read_until("OK")
        telnet.close()
        return 0

    def execBroadcast(self):

        #print "COMANDO RAW:"+self.comandoraw
        call(['adb', "-e", "shell", "am", "broadcast", "-a", "sergio.samples.replicator2.REPLICATE", self.comandoraw], stderr=PIPE)
        #call(["adb", "-s", "emulator-5554", "shell", "am", "broadcast", "-a", "sergio.samples.replicator2.REPLICATE", self.comandoraw], stderr=PIPE)

class Event(object):
    def __init__(self, event):
        self.event_type = None
        self.event_raw = event
        self.elements = None

# PARSER ORIGINAL

# Problema: elements no puede ser split de (': '). Si para obtener el event,
# pero no para pasarlo como parametro a cada modulo. A veces hay ':' y a veces no.

    def __parse__(self):
    # El parser debe porporcionar Elementos [0] y [1]. 0 es "D/AlarmProvider(234)" y 1 el resto. Sin el : separador.
        if self.event_type != None:
            return

        # --- Se crea de nuevo elements
        #buscar : y contar el caracter, para devolver elementos[0] = [0:contado-1] y elementos[1] = [contado:]
        temporal = self.event_raw.split(':')
        contar = len(temporal[0])
        total = len(self.event_raw)
        self.elements = [self.event_raw[0:contar], self.event_raw[contar+1:total]]
        # ---
        #print "raw:" + str(self.event_raw)
        event = str(self.event_raw).split('(')[0][2:]
        self.event_type = str(event)
        #print "event:" + str(event)
        #print "elements:" + str(elements)+"\n\n"
        return self.elements

    def get_event_handler(self, deviceId):
        elements = self.__parse__()
        try:
            klass = getattr(sys.modules[__name__], self.event_type)
            return klass(deviceId, elements)
        except AttributeError:
            raise EventNotSupportedByCloud('Event not supported by clone: ' + self.event_type)
    def get_elementos(self):
        return self.event_raw.split(': ')
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
    I/ActivityManager( 1108): START u0 {act=android.intent.action.MAIN cat=[android.intent.category.LAUNCHER] flg=0x10200000 cmp=com.android.browser/.BrowserActivity bnds=[192,385][240,433]} from pid 1430
    I/ActivityManager( 1004): START {act=android.intent.action.MAIN cat=[android.intent.category.LAUNCHER] flg=0x10200000 cmp=com.android.settings/.Settings u=0} from pid 1166
    I/ActivityManager(  854): Starting: Intent { act=android.intent.action.MAIN cat=[android.intent.category.LAUNCHER] flg=0x10200000 cmp=com.android.music/.MusicBrowserActivity } from pid 962
    """

    cloud_tmp_dir = "./tmp_data/"

    def clone_run(self):
        #print self.elements
        #print "clone runs"
        #print "evento Tipo: " + str(self.elements[0])
        print "elementos:" + str(self.elements[1])

        #if "Starting: Intent {" in self.elements[1].split(': ')[0]:
        #    self.startAction(self.elements[1].split(': ')[1])

        if "Starting: Intent {" in str(self.elements[1]) or "START u0 {" in str(self.elements[1]) or "START {" in str(self.elements[1]):
            intent=str(str(self.elements[1].split("}")[0]).split("{")[1])
            print "intentStarting:" + intent
            self.startAction(intent)

    def startAction(self, elementIntent):
        #print " -----> " + elementIntent
        if "com.android.packageinstaller/.InstallAppProgress" in elementIntent and "file:///" in elementIntent:
            self.startActionInstaller(elementIntent)
        else:
            self.startActionIntent(elementIntent)
        
        # script to run
        #print self.torun
        self.clone_call()
        try:
            shutil.rmtree(os.path.abspath(self.cloud_tmp_dir + "/*"))
            #os.remove(os.path.abspath(self.cloud_tmp_dir + "/*"))
        except OSError:
            pass

    def startActionInstaller(self, elementIntent): 
        # Start Installer
        #intent=str(str(elementIntent.split("}")[0]).split("{")[1])

        print "Action Installer:"+elementIntent
        for arg in elementIntent.split():
            print "arg:"+arg
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

        device_file = data.split("file://")[1]
        name = ntpath.basename(device_file)
        cloud_file = os.path.abspath(self.cloud_tmp_dir + name)

        print "instalar"
        print "cloud_file:"+cloud_file
        print "device_file:"+device_file
        print "self.cloud_tmp_dir:"+self.cloud_tmp_dir

        call(['adb', "-d", "pull", device_file, self.cloud_tmp_dir], stderr=PIPE)
        #call(['adb', "-e", "push", self.cloud_tmp_dir + name, device_file], stderr=PIPE)

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
        #intent=str(str(elementIntent.split("}")[0]).split("{")[1])

        replicateEvent = 1
        activityMain= 0
        catHome= 0

        for arg in elementIntent.split():
            pair=arg.split("=")
            if len(pair) != 2:
                continue
            key=pair[0]
            val=pair[1]

            # do not replicate call activities
            if("CALL" in val):
                #do not replicate call
                replicateEvent = 0
            # if home activity detected, proceed with replicator apk
            if("MAIN" in val):
                activityMain = 1
            if("HOME" in val):
                catHome = 1
                replicateEvent = 0
            # do not replicate wallpaper activities
            if("SET_WALLPAPER" in val):
                replicateEvent = 0
            if("CHOOSER" in val):
                replicateEvent = 0
            if("UninstallAppProgress" in val):
                replicateEvent = 0

            if "act" in key:
                action=val
                self.add_call("runAction = '" + action + "'")
                if len(arguments) > 0:
                    arguments += ', '
                arguments += 'action=runAction'
                ##print "runAction = '" + action + "'" + "\n\n"

            if "cat" in key:
                categories=(val.split("]")[0]).split("[")[1]
                runCategories = ''
                for category in categories.split():
                    if len(runCategories) > 0:
                        runCategories += ", "
                    runCategories += "'" +  category + "'"
                self.add_call("runCategories = [" + runCategories + "]")
                #self.add_call("runCategories = " + runCategories)
                ##print "runCategories = [" + runCategories + "]" + "\n\n"
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
                ##print "runComponent = '" + package + "/" + activity + "'" + "\n\n"

            if "flg" in key: 
                flags=val
                self.add_call("runFlags = " + flags + "")
                if len(arguments) > 0:
                    arguments += ', '
                arguments += 'flags=runFlags'
                ##print "runFlags = " + flags + "" + "\n\n"

            if "dat" in key:
                data=val
                self.add_call("runData = '" + data + "'")
                if len(arguments) > 0:
                    arguments += ', '
                arguments += 'data=runData'
                ##print "runData = '" + data + "'" + "\n\n"

            if "uri" in key:
                uri=val
                self.add_call("runURI = '" + uri + "'")
                if len(arguments) > 0:
                    arguments += ', '
                arguments += 'uri=runURI'
                ##print "runURI = '" + uri + "'" + "\n\n"

            if "typ" in key:
                mimetype=val
                self.add_call("runMimeType = '" + mimetype + "'")
                if len(arguments) > 0:
                    arguments += ', '
                arguments += 'mimetype=runMimeType'
                ##print "runMimeType = '" + mimetype + "'" + "\n\n"

        ##print "ARGUMENTOS FINALES: " + arguments + "\n"
        if(replicateEvent == 1):
            print "AM working:"+str(action)
            self.add_call("clone.startActivity(" + arguments + ")")
        elif (replicateEvent == 0 and activityMain == 1 and catHome == 1):
            # input 1: Starting: Intent { act=android.intent.action.MAIN cat=[android.intent.category.HOME] flg=0x10200000 cmp=com.android.launcher/com.android.launcher2.Launcher } from pid 71
            # broadcast: adb -e shell am broadcast -a sergio.samples.replicator2.REPLICATE --ei code 12
            print "AM HOME"
            call(["adb", "-s", self.deviceId, "shell", "am", "broadcast", "-a", "sergio.samples.replicator2.REPLICATE", "--ei", "code", "12"], stderr=PIPE)
        else:
            print "AM does not working:"+str(action)

class PackageManager(RunnerEvent):

    """
    Inputs:
    Running: ''
    """

    # Inputs: D/PackageManager(  527): Removing package com.estrongs.android.pop
    # Inputs: I/PackageManager( 1130): Removing non-system package:android.pruebas.bateria2

    def clone_run(self):

        if "Removing package" in self.elements[1] :
            paquete = self.elements[1].strip().split(" ")[2]
            call(['adb', "-s", self.deviceId, "uninstall", paquete], stderr=PIPE)

        elif "Removing" in self.elements[1] and "package" in self.elements[1] and ":" in self.elements[1]:
            paquete = self.elements[1].strip().split(":")[1]
            call(['adb', "-s", self.deviceId, "uninstall", paquete], stderr=PIPE)
    # inputs ()
        #if "Removing package" in self.elements[1] :
        #    paquete = self.elements[1].strip().split(" ")[2]
        #    self.add_call("clone.removePackage(\"" + paquete + "\")")
    # script to run
        #self.clone_call()

class AirplaneModeEnabler(RunnerEvent):

    """
    Inputs: D/AirplaneModeEnabler(  314): onAirplaneModeChanged : airplaneModeEnabled true
    Running: adb -e shell am broadcast -a sergio.samples.replicator2.REPLICATE --ei code 1 --ez enabled false
    """

    def clone_run(self):
    # inputs ()

        #comando = ""
        if("true" in self.elements[1]):
            call(['adb', "-s", self.deviceId, "shell", "am", "broadcast", "-a", "sergio.samples.replicator2.REPLICATE", "--ei", "code", "1", "--ez", "enabled", "true"], stderr=PIPE)
            #comando = comando + "--ei code 1 --ez enabled true"
        elif("false" in self.elements[1]):
            call(['adb', "-s", self.deviceId, "shell", "am", "broadcast", "-a", "sergio.samples.replicator2.REPLICATE", "--ei", "code", "1", "--ez", "enabled", "false"], stderr=PIPE)
            #comando = comando + "--ei code 1 --ez enabled false"
        #objeto = Comando(str(comando))
        #res = objeto.execBroadcast()

class CAPTUREVENTS(RunnerEvent):


    """
    Inputs: TAGSENSORS {accelerometer, gravity, gyroscope}, TAGLOCATION {lat, long}, TAGCALL {incoming, offhook, idle, outgoing}, TAGSCREEN {on, off}, TAGBATTERY {level, plugged, status}, TAGSMS {incoming, outgoing}, TAGRINGER {volume, mode}, TAGTIME {newtime, timezone}, TAGPICTURE {newpicture}, TAGSHUTDOWN
    Running: ''
    """
    global NUMhistorico
    global NUMaccept
    global NUMhungup
    NUMhistorico = -1
    NUMaccept = -1
    NUMhungup = -1

    def clone_run(self):
    # inputs ()

        # anadir comando. adb -e shell am broadcast -a sergio.samples.replicator2.REPLICATE --ei code 1 --ez enabled 0

        #print "evento Tipo: " + self.__class__.__name__
        #print "elements[0]: " + str(self.elements[0])
        #print "elements[1]: " + str(self.elements[1])
        
        #numElementos = len(self.elements)

        resto = self.elements[1].split('|')
        subtag = resto[0]

        # sensors
        #if("TAGSENSORS" in subtag):
            # con telnet

            #elemento[1]:  TAGSENSORS | 11 | Rotation Vector Sensor | [-0.027441667, -0.004943471, -0.63772464]
            #print "impl"

        # location
        if("TAGLOCATION" in subtag):
            # input: CAPTUREVENTS( 1812): TAGLOCATION | Lat:numberLat | Long:numberLong
            # con telnet
            #'geo fix <longitude> <latitude> [<altitude> [<satellites>]]'
            #allows you to send a simple GPS fix to the emulated system.
            #The parameters are:
            #<longitude>   longitude, in decimal degrees
            #<latitude>    latitude, in decimal degrees
            #<altitude>    optional altitude in meters
            #<satellites>  number of satellites being tracked (1-12)
            lat = resto[1].split(":")[1].strip()
            #print "lat:"+lat
            lon = resto[2].split(":")[1].strip()
            #print "lon:"+lon
            objeto = Comando("geo fix "+lon+" "+lat)
            res = objeto.execTelnet()

        # call
        elif("TAGCALL" in subtag):
            global NUMaccept
            global NUMhistorico
            global NUMhungup
            if ("RINGING" in resto[1]):
                numero = resto[1].split(":")[1].strip()
                NUMaccept = numero
                NUMhungup = numero
                objeto = Comando("gsm call "+numero)
                res = objeto.execTelnet()

            if ("OFFHOOK" in resto[1] and NUMaccept != -1):
                NUMhistorico = NUMaccept
                objeto = Comando("gsm accept "+NUMaccept)
                NUMaccept = -1
                res = objeto.execTelnet()

            if ("IDLE" in resto[1] and (NUMhistorico != -1 or NUMhungup != -1)):
                if(NUMhungup != -1):
                    objeto = Comando("gsm cancel "+NUMhungup)
                    NUMhungup = -1
                elif(NUMhistorico != -1):
                    objeto = Comando("gsm cancel "+NUMhistorico)
                    NUMhistorico = -1
                res = objeto.execTelnet()

            if ("OUTGOING" in resto[1]):
                numero = resto[1].split(":")[1].strip()
                NUMhungup = numero
                
                # modo 1 - hard
                #call(["adb", "-e", "shell", "am", "start", "-a", "android.intent.action.CALL_PRIVILEGED", "-d", str("tel:"+numero)], stderr=PIPE)
                #call(["adb", "-s", "emulator-5554", "shell", "am", "start", "-a", "android.intent.action.CALL_PRIVILEGED", "-d", str("tel:"+numero)], stderr=PIPE)

                # modo 2 - monkeyRunner
                arguments = ''

                self.add_call("runAction = 'android.intent.action.CALL_PRIVILEGED'")
                arguments += 'action=runAction'
                ##print "runAction = '" + action + "'" + "\n\n"
                self.add_call("runData = 'tel:" + str(numero) + "'")
                arguments += ', data=runData'

                self.add_call("clone.startActivity(" + arguments + ")")
                self.clone_call()


        # turn on/off the screen
        elif("TAGSCREEN" in subtag):
            #TAGSCREEN {on, off}
            call(["adb", "-s", self.deviceId, "shell", "input", "keyevent", "26"], stderr=PIPE)

        # set battery changes
        elif("TAGBATTERY" in subtag):
            #TAGBATTERY {level, plugged, status}
            # plugged:1 = AC | plugged:2 = USB | plugged:0 = unplugged (on battery)
            # status:3 = descargando | status:2 = cargando | status:5 = FULL
            #input CAPTUREVENTS( 1812): TAGBATTERY | LEVEL:100 | PLUGGED:2 | STATUS:5
            
            level = resto[1].split(":")[1].strip()
            plugged = resto[2].split(":")[1].strip()
            status = resto[3].split(":")[1].strip()

            # level
            objeto = Comando("power capacity "+level)
            res = objeto.execTelnet()

            # plugged
            if (int(plugged) == 1):
                objeto = Comando("power ac on")
                res = objeto.execTelnet()
            elif (int(plugged) == 0 or int(plugged) == 2):
                objeto = Comando("power ac off")
                res = objeto.execTelnet()

            # status
            if (int(status) == 3):
                objeto = Comando("power status discharging")
                res = objeto.execTelnet()
            elif (int(status) == 2):
                objeto = Comando("power status charging")
                res = objeto.execTelnet()
            elif int(status) == 5:
                objeto = Comando("power status full")
                res = objeto.execTelnet()

        # send/receive SMS
        elif("TAGSMS" in subtag):
            #TAGSMS {incoming, outgoing}
            #print "SMS resto1: "+resto[1]
            if ("INCOMING" in resto[1]):
                number = resto[2].split(":")[1].strip()
                # if body contains : then wrong thing
                body = resto[3][6:]
                objeto = Comando("sms send "+number+ " " + body)
                res = objeto.execTelnet()

            elif ("OUTGOING" in resto[1]):
                #print "resto1: "+resto[1]
                number = resto[2].split(":")[1].strip()
                body = resto[3][6:].replace("\n"," ").strip()
                #print "number:\""+number+"\""
                #print "cuerpo:"+body
                
                # --- no hay manera de que funcione, el string hay que pasarlo obligatoriamente entre "" o '' para que no sea interpretado como otro extra.
                # la funcion call de execBroadcast no pasa bien el parametro y da errores como: {Error: Unknown option: --ei code 10 --ei number 111 --es body 'Cccc bbbbb'}
                #objeto = Comando(str("--ei code 10 --ei number "+number+" --es body "+str(body)))
                #res = objeto.execBroadcast()
                call(['adb', "-s", self.deviceId, "shell", "am", "broadcast", "-a", "sergio.samples.replicator2.REPLICATE", "--ei", "code", "10", "--ei", "number", str(number), "--es", "body", str(body)], stderr=PIPE)
                #call(["adb", "-s", "emulator-5554", "shell", "am", "broadcast", "-a", "sergio.samples.replicator2.REPLICATE", "--ei", "code", "10", "--ei", "number", str(number), "--es", "body", str(body)], stderr=PIPE)

        # change volume or ringer mode
        elif("TAGRINGER" in subtag):
            #TAGRINGER {volume, mode}
            if ("VOLUME" in resto[1]):
                #adb -e shell am broadcast -a sergio.samples.replicator2.REPLICATE --ei code 5 --ei volume 0
                volume = resto[1].split(":")[1].strip()
                if(volume != -1):
                    call(["adb", "-s", self.deviceId, "shell", "am", "broadcast", "-a", "sergio.samples.replicator2.REPLICATE", "--ei", "code", "5", "--ei", "volume", str(volume)], stderr=PIPE)
            elif("MODE" in resto[1]):
                #adb -e shell am broadcast -a sergio.samples.replicator2.REPLICATE --ei code 8 --ei ringer 0
                mode = resto[1].split(":")[1].strip()
                if(mode != -1):
                    call(["adb", "-s", self.deviceId, "shell", "am", "broadcast", "-a", "sergio.samples.replicator2.REPLICATE", "--ei", "code", "8", "--ei", "ringer", str(mode)], stderr=PIPE)

        # change time or timezone
        elif("TAGTIME" in subtag):
            # timezone
            # input D/CAPTUREVENTS(571): TAGTIME | TIMEZONE:America/Los_Angeles
            # output adb -e shell am broadcast -a sergio.samples.replicator2.REPLICATE --ei code 11 --es timezone America/Los_Angeles
            if ("TIMEZONE" in resto[1]):
                zone = resto[1].split(":")[1].strip()
                #print "time:"+zone
                call(["adb", "-s", self.deviceId, "shell", "am", "broadcast", "-a", "sergio.samples.replicator2.REPLICATE", "--ei", "code", "11", "--es", "timezone", str(zone)], stderr=PIPE)
            # newtime
            # input D/CAPTUREVENTS(571): TAGTIME | NEWTIME:20140423.015410
            # output "adb -e shell date -s 20140423.135408"
            if ("NEWTIME" in resto[1]):
                time = resto[1].split(":")[1].strip()
                #print "time:"+time
                call(["adb", "-s", self.deviceId, "shell", "date", "-s", str(time)], stderr=PIPE)
        # take picture
        #elif("TAGPICTURE" in subtag):
            #print "impl"
            #sendBroadcast(code = X)
            
        # shutdown the emulator
        elif ("TAGSHUTDOWN" in subtag):
            #call(['adb', "-e", "shell", "reboot", "-p"], stderr=PIPE)
            call(['adb', "-s", self.deviceId, "emu", "kill"], stderr=PIPE)
            exit(1)

        elif ("TAGWALLPAPER" in subtag):
            # output: adb -e shell am broadcast -a sergio.samples.replicator2.REPLICATE --ei code 4
            call(['adb', "-s", self.deviceId, "shell", "am", "broadcast", "-a", "sergio.samples.replicator2.REPLICATE", "--ei", "code", "4"], stderr=PIPE)

class MmsSmsProvider(RunnerEvent):

    # delete sms conversation id

    """
    Inputs: V/MmsSmsProvider(  626): deleteConversation threadId: 4
    Running: 'adb shell am start -a sergio.replicator.REPL --ei code XX --ei id 4
    """

    def clone_run(self):
    # inputs ()
        print "empty"

class GpsLocationProvider(RunnerEvent):

    """
    Inputs: D/GpsLocationProvider(  128): handleEnable
    Running: ''
    """

    def clone_run(self):
    # inputs ()
        #comando = ""
        if("handleEnable" in self.elements[1]):
            #call(['adb', "-e", "shell", "am", "broadcast", "-a", "sergio.samples.replicator2.REPLICATE", "--ei", "code", "9", "--ez", "enabled", "true"], stderr=PIPE)
            print "encender gsp en:"+self.deviceId
            call(['adb', "-s", self.deviceId, "shell", "am", "broadcast", "-a", "sergio.samples.replicator2.REPLICATE", "--ei", "code", "9", "--ez", "enabled", "true"], stderr=PIPE)
            #comando = comando + "--ei code 9 --ez enabled true"
        elif("handleDisable" in self.elements[1]):

            call(['adb', "-s", self.deviceId, "shell", "am", "broadcast", "-a", "sergio.samples.replicator2.REPLICATE", "--ei", "code", "9", "--ez", "enabled", "false"], stderr=PIPE)
            #comando = comando + "--ei code 9 --ez enabled false"
        #objeto = Comando(comando)
        #res = objeto.execBroadcast()      

class ConnectivityService(RunnerEvent):

    """
    Inputs: D/ConnectivityService(  128): setMobileDataEnabled(false)
    Running: 'adb -e shell am broadcast -a sergio.samples.replicator2.REPLICATE --ei code 3 --ei enabled 0'
    """

    def clone_run(self):
    # inputs ()
        if("setMobileDataEnabled(true)" in self.elements[1]):
            call(['adb', "-s", self.deviceId, "shell", "am", "broadcast", "-a", "sergio.samples.replicator2.REPLICATE", "--ei", "code", "3", "--ei", "enabled", "1"], stderr=PIPE)
            #comando = comando + "--ei code 9 --ez enabled true"
        elif("setMobileDataEnabled(false)" in self.elements[1]):
            call(['adb', "-s", self.deviceId, "shell", "am", "broadcast", "-a", "sergio.samples.replicator2.REPLICATE", "--ei", "code", "3", "--ei", "enabled", "0"], stderr=PIPE)
            #comando = comando + "--ei code 9 --ez enabled false"
        #objeto = Comando(comando)
        #res = objeto.execBroadcast()

class PowerManagerService(RunnerEvent):

    """
    Inputs: D/PowerManagerService(  528): setScreenBrightnessMode : mAutoBrightessEnabled : true
    Running: 'adb -e shell am broadcast -a sergio.samples.replicator2.RECEIVER --ei code 7 --ei auto 1'
    """

    def clone_run(self):
    # inputs ()
        #comando = ""

        if("setScreenBrightnessMode : mAutoBrightessEnabled : true" in self.elements[1]):
            call(['adb', "-s", self.deviceId, "shell", "am", "broadcast", "-a", "sergio.samples.replicator2.REPLICATE", "--ei", "code", "7", "--ei", "auto", "1"], stderr=PIPE)
        elif("setScreenBrightnessMode : mAutoBrightessEnabled : false" in self.elements[1]):
            call(['adb', "-s", self.deviceId, "shell", "am", "broadcast", "-a", "sergio.samples.replicator2.REPLICATE", "--ei", "code", "7", "--ei", "auto", "0"], stderr=PIPE)

    # script to run
        #self.add_call("")
        #self.clone_call()


class Template(RunnerEvent):


    """
    Inputs:
    Running: ''
    """


    def clone_run(self):
    # inputs ()

    # script to run
        self.add_call("")
        self.clone_call()