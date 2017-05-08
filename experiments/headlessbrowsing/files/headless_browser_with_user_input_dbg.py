#!/usr/bin/python
# -*- coding: utf-8 -*-

# Author: Mohammad Rajiullah (Used general experiment logic from 
# Jonas Karlsson)
# Date: October 2016
# License: GNU General Public License v3
# Developed for use by the EU H2020 MONROE project

"""
headless firefox browsing using selenium web driver.
The browsing can make request using h1, h2 or h1 over tls.
The script will execute one experiment for each of the allowed_interfaces.
All default values are configurable from the scheduler.
The output will be formated into a json object suitable for storage in the
MONROE db.
"""

import sys, getopt
import time, os
import fileinput
from pyvirtualdisplay import Display
from selenium import webdriver
import datetime
from dateutil.parser import parse
from selenium.common.exceptions import WebDriverException
import json
import zmq
import netifaces
import time
import subprocess
import socket
import struct
import random
from subprocess import check_output, CalledProcessError
from multiprocessing import Process, Manager

urlfile =''
iterations =0 
url=''
num_urls=0
domains = "devtools.netmonitor.har."
num_urls =0
url_list = []
start_count = 0
getter=''
newurl=''
getter_version=''
h1='http://'
h1s='https://'
h2='https://'
current_directory =''
har_directory =''

# Configuration
DEBUG = True
CONFIGFILE = '/monroe/config'

# Default values (overwritable from the scheduler)
# Can only be updated from the main thread and ONLY before any
# other processes are started
EXPCONFIG = {
        "guid": "no.guid.in.config.file",  # Should be overridden by scheduler
        "url": "http://193.10.227.25/test/1000M.zip",
        "size": 3*1024,  # The maximum size in Kbytes to download
        "time": 3600,  # The maximum time in seconds for a download
        "zmqport": "tcp://172.17.0.1:5556",
        "modem_metadata_topic": "MONROE.META.DEVICE.MODEM",
        "dataversion": 1,
        "dataid": "MONROE.EXP.FIREFOX.HEADLESS.BROWSING",
        "nodeid": "fake.nodeid",
        "meta_grace": 120,  # Grace period to wait for interface metadata
        "exp_grace": 120,  # Grace period before killing experiment
        "ifup_interval_check": 5,  # Interval to check if interface is up
        "time_between_experiments": 30,
        "verbosity": 2,  # 0 = "Mute", 1=error, 2=Information, 3=verbose
        "resultdir": "/monroe/results/",
        "modeminterfacename": "InternalInterface",
        "urls": [['facebook.com/telia/'],
		['en.wikipedia.org/wiki/As_Slow_as_Possible'],
		['linkedin.com/company/google'],
		['instagram.com/nike/'],
		['google.com/search?q=iPhone+7'],
		['youtube.com/watch?v=xGJ5a7uIZ1g'],
		['ebay.com/sch/Cell-Phones-Smartphones-/9355/i.html'],
		['nytimes.com/section/science/earth?action=click&contentCollection=science&region=navbar&module=collectionsnav&pagetype=sectionfront&pgtype=sectionfront'],
		['theguardian.com/football/2017/apr/11/juventus-barcelona-champions-league-quarter-final-match-report','theguardian.com/football/2017/apr/11/barcelona-neymar-clasico-ban'],
		['soupsoup.tumblr.com']],
        "http_protocols":["h1s","h2"],
        "iterations": 1,
        "allowed_interfaces": ["op0","op1","op2","eth0"],  # Interfaces to run the experiment on
        "interfaces_without_metadata": ["eth0"]  # Manual metadata on these IF
        }

def py_traceroute(dest_name):
    dest_addr = socket.gethostbyname(dest_name)
    port = 33434
    max_hops = 30
    icmp = socket.getprotobyname('icmp')
    udp = socket.getprotobyname('udp')
    ttl = 1

    tr_output=""
    while True:
        recv_socket = socket.socket(socket.AF_INET, socket.SOCK_RAW, icmp)
        send_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, udp)
        send_socket.setsockopt(socket.SOL_IP, socket.IP_TTL, ttl)
        
        # Build the GNU timeval struct (seconds, microseconds)
        timeout = struct.pack("ll", 5, 0)
        
        # Set the receive timeout so we behave more like regular traceroute
        recv_socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVTIMEO, timeout)
        
        recv_socket.bind(("", port))
        #sys.stdout.write(" %d  " % ttl)
        send_socket.sendto("", (dest_name, port))
        curr_addr = None
        curr_name = None
        finished = False
        tries = 3
        while not finished and tries > 0:
            try:
                _, curr_addr = recv_socket.recvfrom(512)
                finished = True
                curr_addr = curr_addr[0]
                try:
                    curr_name = socket.gethostbyaddr(curr_addr)[0]
                except socket.error:
                    curr_name = curr_addr
            except socket.error as (errno, errmsg):
                tries = tries - 1
                sys.stdout.write("* ")
        
        send_socket.close()
        recv_socket.close()
        
        if not finished:
            pass
        
        if curr_addr is not None:
            curr_host = "%s (%s)" % (curr_name, curr_addr)
        else:
            curr_host = ""
            curr_addr = " "
        tr_output+=curr_addr+" "

        ttl += 1
        if curr_addr == dest_addr or ttl > max_hops:
            break
    return tr_output


def run_exp(meta_info, expconfig, url,count):
    """Seperate process that runs the experiment and collect the ouput.

        Will abort if the interface goes down.
    """
    ifname = meta_info[expconfig["modeminterfacename"]]

    #url=url_list[index]

    try:
    	routes=py_traceroute(str(url).split("/")[0])
    except Exception:
    	print ("tracerouting unsuccessful")

    try:
    	response = subprocess.check_output(
        ['fping', '-I',ifname,'-c', '3', '-q', str(url).split("/")[0]],
        stderr=subprocess.STDOUT,  # get all output
        universal_newlines=True  # return string not bytes
    	)
    	ping_outputs= response.splitlines()[-1].split("=")[-1]
    	ping_output=ping_outputs.split("/")
        ping_min = ping_output[0]
    	ping_avg = ping_output[1]
    	ping_max = ping_output[2]
    except subprocess.CalledProcessError:
    	response = None
	print "Ping info is unknown"


    #count=run+1
    display = Display(visible=0, size=(800, 600))
    display.start()
    profile = webdriver.FirefoxProfile("/opt/monroe/")
    profile.accept_untrusted_certs = True
    profile.add_extension("har.xpi")
    
    #set firefox preferences
    profile.set_preference("app.update.enabled", False)
    profile.set_preference('browser.cache.memory.enable', False)
    profile.set_preference('browser.cache.offline.enable', False)
    profile.set_preference('browser.cache.disk.enable', False)
    profile.set_preference('browser.startup.page', 0)
    profile.set_preference("general.useragent.override", "Mozilla/5.0 (Android 4.4; Mobile; rv:46.0) Gecko/46.0 Firefox/46.0")
    
    #Check the HTTP(getter) scheme and disable the rest
    if getter_version == 'HTTP1.1':
        profile.set_preference('network.http.spdy.enabled.http2', False)
        profile.set_preference('network.http.spdy.enabled', False)
        profile.set_preference('network.http.spdy.enabled.v3-1', False)
        profile.set_preference('network.http.max-connections-per-server', 6)
        filename = "h1-"+url.split("/")[0]+"."+str(count)
    elif getter_version == 'HTTP1.1/TLS':
        profile.set_preference('network.http.spdy.enabled.http2', False)
        profile.set_preference('network.http.spdy.enabled', False)
        profile.set_preference('network.http.spdy.enabled.v3-1', False)
        profile.set_preference('network.http.max-connections-per-server', 6)
        filename = "h1s-"+url.split("/")[0]+"."+str(count)
    elif getter_version == 'HTTP2':
        profile.set_preference('network.http.spdy.enabled.http2', True)
        profile.set_preference('network.http.spdy.enabled', True)
        profile.set_preference('network.http.spdy.enabled.v3-1', True )
        filename = "h2-"+url.split("/")[0]+"."+str(count)
    
    
    profile.set_preference('network.prefetch-next', False)
    profile.set_preference('network.http.spdy.enabled.v3-1', False)
    
    newurl = getter+url
    
    #set the preference for the trigger
    profile.set_preference("extensions.netmonitor.har.contentAPIToken", "test")
    profile.set_preference("extensions.netmonitor.har.autoConnect", True)
    profile.set_preference(domains + "defaultFileName", filename)
    profile.set_preference(domains + "enableAutoExportToFile", True)
    profile.set_preference(domains + "defaultLogDir", har_directory)
    profile.set_preference(domains + "pageLoadedTimeout", 1000)
    time.sleep(1)

    #create firefox driver

    try:
        driver = webdriver.Firefox(profile)
        driver.get(newurl)
    except Exception as e:
        raise WebDriverException("Unable to start webdriver with FF.", e)
        return
    
    time.sleep(5)
    driver.save_screenshot(filename+'.png')

    #close the firefox driver after HAR is written
    driver.close()
    display.stop()
    har_stats={}
    objs=[]
    pageSize=0

    try:
    	with open("har/"+filename+".har") as f:
        	msg=json.load(f)
    except IOError:
    	print "har/"+filename+".har doesn't exist"
        return
    num_of_objects=0

    start=0
    for entry in msg["log"]["entries"]:
        try:
                obj={}
                obj["url"]=entry["request"]["url"]
                obj["objectSize"]=entry["response"]["bodySize"]+entry["response"]["headersSize"]
                pageSize=pageSize+entry["response"]["bodySize"]+entry["response"]["headersSize"]
		obj["mimeType"]=entry["response"]["content"]["mimeType"]
		obj["startedDateTime"]=entry["startedDateTime"]
                obj["time"]=entry["time"]
                obj["timings"]=entry["timings"]
                objs.append(obj)
                num_of_objects=num_of_objects+1
                if start==0:
                        start_time=entry["startedDateTime"]
                        start=1
                end_time=entry["startedDateTime"]
                ms=entry["time"]
    	except KeyError:
        	pass

    try:
       har_stats["tracedRoutes"]=routes.rstrip().split(" ")
    except Exception:
       print "traceroute info is not available"

    try:
    	har_stats["ping_max"]=ping_max
        har_stats["ping_avg"]=ping_avg
	har_stats["ping_min"]=ping_min
	har_stats["ping_exp"]=1
    except Exception:
	print("Ping info is not available")
        har_stats["ping_exp"]=0
    har_stats["Objects"]=objs
    har_stats["NumObjects"]=num_of_objects
    har_stats["PageSize"]=pageSize
    hours,minutes,seconds=str(((parse(end_time)+ datetime.timedelta(milliseconds=ms))- parse(start_time))).split(":")
    hours = int(hours)
    minutes = int(minutes)
    seconds = float(seconds)
    plt_ms = int(3600000 * hours + 60000 * minutes + 1000 * seconds)
    har_stats["url"]=url
    har_stats["Protocol"]=getter_version	
    har_stats["Web load time"]=plt_ms
    #har_stats["Guid"]= expconfig['guid']
    har_stats["DataId"]= expconfig['dataid']
    har_stats["DataVersion"]= expconfig['dataversion']
    har_stats["NodeId"]= expconfig['nodeid']
    har_stats["Timestamp"]= time.time()
    try:
    	har_stats["Iccid"]= meta_info["ICCID"]
    except Exception:
    	print("ICCID info is not available")
    try:
    	har_stats["Operator"]= meta_info["Operator"]
    except Exception:
    	print("Operator info is not available")
    #try:
    #	har_stats["IMSI"]=meta_info["IMSI"]
    #except Exception:
    #	print("IMSI info is not available")
    #try:
    #	har_stats["IMEI"]=meta_info["IMEI"]
    #except Exception:
    #	print("IMEI info is not available")
    try:
    	har_stats["InternalInterface"]=meta_info["InternalInterface"]
    except Exception:
    	print("InternalInterface info is not available")
    try:
    	har_stats["IPAddress"]=meta_info["IPAddress"]
    except Exception:
    	print("IPAddress info is not available")
    try:
    	har_stats["InternalIPAddress"]=meta_info["InternalIPAddress"]
    except Exception:
    	print("InternalIPAddress info is not available")
    try:
    	har_stats["InterfaceName"]=meta_info["InterfaceName"]
    except Exception:
    	print("InterfaceName info is not available")
    try:
    	har_stats["IMSIMCCMNC"]=meta_info["IMSIMCCMNC"]
    except Exception:
    	print("IMSIMCCMNC info is not available")
    try:
    	har_stats["NWMCCMNC"]=meta_info["NWMCCMNC"]
    except Exception:
    	print("NWMCCMNC info is not available")
#    try:
#    	har_stats["LAC"]=meta_info["LAC"]
#    except Exception:
#    	print("LAC info is not available")
#    try:
#    	har_stats["CID"]=meta_info["CID"]
#    except Exception:
#    	print("CID info is not available")
#    try:
#    	har_stats["RSCP"]=meta_info["RSCP"]
#    except Exception:
#    	print("RSCP info is not available")
#    try:
#    	har_stats["RSSI"]=meta_info["RSSI"]
#    except Exception:
#    	print("RSSI info is not available")
#    try:
#    	har_stats["RSRQ"]=meta_info["RSRQ"]
#    except Exception:
#    	print("RSRQ info is not available")
#    try:
#    	har_stats["RSRP"]=meta_info["RSRP"]
#    except Exception:
#    	print("RSRP info is not available")
#    try:
#    	har_stats["ECIO"]=meta_info["ECIO"]
#    except Exception:
#    	print("ECIO info is not available")
#    try:
#    	har_stats["DeviceMode"]=meta_info["DeviceMode"]
#    except Exception:
#    	print("DeviceMode info is not available")
#    try:
#    	har_stats["DeviceSubmode"]=meta_info["DeviceSubmode"]
#    except Exception:
#    	print("DeviceSubmode info is not available")
#    try:
#    	har_stats["DeviceState"]=meta_info["DeviceState"]
#    except Exception:
#    	print("DeviceState info is not available")
#
    har_stats["SequenceNumber"]= count

    #msg=json.dumps(har_stats)
    with open('/tmp/'+str(har_stats["NodeId"])+'_'+str(har_stats["DataId"])+'_'+str(har_stats["Timestamp"])+'.json', 'w') as outfile:
        json.dump(har_stats, outfile)
    
    if expconfig['verbosity'] > 2:
            print har_stats
    if not DEBUG:
	    print har_stats
            monroe_exporter.save_output(har_stats, expconfig['resultdir'])
    try:
        os.remove("/opt/monroe/har/"+filename+".har")
    except OSError, e:  ## if failed, report it back to the user ##
        print ("Error: %s - %s." % (e.filename,e.strerror))
    
    

def metadata(meta_ifinfo, ifname, expconfig):
    """Seperate process that attach to the ZeroMQ socket as a subscriber.

        Will listen forever to messages with topic defined in topic and update
        the meta_ifinfo dictionary (a Manager dict).
    """
    context = zmq.Context()
    socket = context.socket(zmq.SUB)
    socket.connect(expconfig['zmqport'])
    socket.setsockopt(zmq.SUBSCRIBE, expconfig['modem_metadata_topic'])
    # End Attach
    while True:
        data = socket.recv()
        try:
            ifinfo = json.loads(data.split(" ", 1)[1])
            if (expconfig["modeminterfacename"] in ifinfo and
                    ifinfo[expconfig["modeminterfacename"]] == ifname):
                # In place manipulation of the reference variable
                for key, value in ifinfo.iteritems():
                    meta_ifinfo[key] = value
        except Exception as e:
            if expconfig['verbosity'] > 0:
                print ("Cannot get modem metadata in http container {}"
                       ", {}").format(e, expconfig['guid'])
            pass


# Helper functions
def check_if(ifname):
    """Check if interface is up and have got an IP address."""
    return (ifname in netifaces.interfaces() and
            netifaces.AF_INET in netifaces.ifaddresses(ifname))


def check_meta(info, graceperiod, expconfig):
    """Check if we have recieved required information within graceperiod."""
    return (expconfig["modeminterfacename"] in info and
            "Operator" in info and
            "Timestamp" in info and
            time.time() - info["Timestamp"] < graceperiod)


def add_manual_metadata_information(info, ifname, expconfig):
    """Only used for local interfaces that do not have any metadata information.

       Normally eth0 and wlan0.
    """
    info[expconfig["modeminterfacename"]] = ifname
    info["Operator"] = "local"
    info["Timestamp"] = time.time()
    info["ipaddress"] ="172.17.0.3"	


def create_meta_process(ifname, expconfig):
    meta_info = Manager().dict()
    process = Process(target=metadata,
                      args=(meta_info, ifname, expconfig, ))
    process.daemon = True
    return (meta_info, process)


def create_exp_process(meta_info, expconfig,url,count):
    process = Process(target=run_exp, args=(meta_info, expconfig,url,count))
    process.daemon = True
    return process


if __name__ == '__main__':
    """The main thread control the processes (experiment/metadata))."""
    # Settings related to browsing 

    os.system('clear')
    current_directory = os.path.dirname(os.path.abspath(__file__))
    har_directory  = os.path.join(current_directory, "har")
        
    print 'Checking if HTTP Archive directory exists . . . . . . . .'
    if os.path.exists(har_directory):
        print 'HTTP Archive Directory Exists!'
    else:
        os.mkdir(har_directory)
        print "HTTP Archive Directory created successfully in %s ..\n" % (har_directory)



    if not DEBUG:
        import monroe_exporter
        # Try to get the experiment config as provided by the scheduler
        try:
            with open(CONFIGFILE) as configfd:
                EXPCONFIG.update(json.load(configfd))
        except Exception as e:
            print "Cannot retrive expconfig {}".format(e)
            raise e
    else:
        # We are in debug state always put out all information
        EXPCONFIG['verbosity'] = 3

    # Short hand variables and check so we have all variables we need
    try:
        allowed_interfaces = EXPCONFIG['allowed_interfaces']
	iterations=EXPCONFIG['iterations']
        urls=EXPCONFIG['urls']
	http_protocols=EXPCONFIG['http_protocols']
        if_without_metadata = EXPCONFIG['interfaces_without_metadata']
        meta_grace = EXPCONFIG['meta_grace']
        exp_grace = EXPCONFIG['exp_grace'] + EXPCONFIG['time']
        ifup_interval_check = EXPCONFIG['ifup_interval_check']
        time_between_experiments = EXPCONFIG['time_between_experiments']
        EXPCONFIG['guid']
        EXPCONFIG['modem_metadata_topic']
        EXPCONFIG['zmqport']
        EXPCONFIG['verbosity']
        EXPCONFIG['resultdir']
        EXPCONFIG['modeminterfacename']
    except Exception as e:
        print "Missing expconfig variable {}".format(e)
        raise e
    for ifname in allowed_interfaces:
	if ifname not in open('/proc/net/dev').read():
		allowed_interfaces.remove(ifname)

    for ifname in allowed_interfaces:
        # Interface is not up we just skip that one
        if not check_if(ifname):
            if EXPCONFIG['verbosity'] > 1:
                print "Interface is not up {}".format(ifname)
            continue
        # set the default route
            

        # Create a process for getting the metadata
        # (could have used a thread as well but this is true multiprocessing)
        meta_info, meta_process = create_meta_process(ifname, EXPCONFIG)
        meta_process.start()

        if EXPCONFIG['verbosity'] > 1:
            print "Starting Experiment Run on if : {}".format(ifname)

        # On these Interfaces we do net get modem information so we hack
        # in the required values by hand whcih will immeditaly terminate
        # metadata loop below
        if (check_if(ifname) and ifname in if_without_metadata):
            add_manual_metadata_information(meta_info, ifname,EXPCONFIG)
#
        # Try to get metadadata
        # if the metadata process dies we retry until the IF_META_GRACE is up
        start_time = time.time()
        while (time.time() - start_time < meta_grace and
               not check_meta(meta_info, meta_grace, EXPCONFIG)):
            if not meta_process.is_alive():
                # This is serious as we will not receive updates
                # The meta_info dict may have been corrupt so recreate that one
                meta_info, meta_process = create_meta_process(ifname,
                                                              EXPCONFIG)
                meta_process.start()
            if EXPCONFIG['verbosity'] > 1:
                print "Trying to get metadata"
            time.sleep(ifup_interval_check)

        # Ok we did not get any information within the grace period
        # we give up on that interface
        if not check_meta(meta_info, meta_grace, EXPCONFIG):
            if EXPCONFIG['verbosity'] > 1:
                print "No Metadata continuing"
            continue

        # Ok we have some information lets start the experiment script

        if EXPCONFIG['verbosity'] > 1:
            print "Starting experiment"
        
        
        for url_list in urls:
	    random.shuffle(url_list)
	    for url in url_list:	
	    	for protocol in http_protocols:
			if protocol == 'h1':
            			getter = h1
            			getter_version = 'HTTP1.1'
        		elif protocol == 'h1s':
            			getter = h1s
            			getter_version = 'HTTP1.1/TLS'
        		elif protocol == 'h2':
            			getter = h2
            			getter_version = 'HTTP2'
        		else:
            			print 'Unknown HTTP Scheme: <HttpMethod:h1/h1s/h2>' 
            			sys.exit()	
            		for run in range(start_count, iterations):
                		# Create a experiment process and start it
                		start_time_exp = time.time()
                		exp_process = exp_process = create_exp_process(meta_info, EXPCONFIG, url,run+1)
                		exp_process.start()
        
                		while (time.time() - start_time_exp < exp_grace and
                       			exp_process.is_alive()):
                    			# Here we could add code to handle interfaces going up or down
                    			# Similar to what exist in the ping experiment
                    			# However, for now we just abort if we loose the interface
        
                    			# No modem information hack to add required information
                    			if (check_if(ifname) and ifname in if_without_metadata):
                    		    		add_manual_metadata_information(meta_info, ifname, EXPCONFIG)
        
                    			if not (check_if(ifname) and check_meta(meta_info,
                                                            meta_grace,
                                                            EXPCONFIG)):
                        			if EXPCONFIG['verbosity'] > 0:
                            				print "Interface went down during a experiment"
                        			break
                    			elapsed_exp = time.time() - start_time_exp
                    			if EXPCONFIG['verbosity'] > 1:
                        			print "Running Experiment for {} s".format(elapsed_exp)
                    			time.sleep(ifup_interval_check)
        
                		if exp_process.is_alive():
                    			exp_process.terminate()
                		if meta_process.is_alive():
                    			meta_process.terminate()
        
                		elapsed = time.time() - start_time
                		if EXPCONFIG['verbosity'] > 1:
                    			print "Finished {} after {}".format(ifname, elapsed)
                		time.sleep(time_between_experiments)

    if EXPCONFIG['verbosity'] > 1:
        print ("Interfaces {} "
               "done, exiting").format(allowed_interfaces)
