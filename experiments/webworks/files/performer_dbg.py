#! /usr/bin/python

import sys, getopt
import time, os 
import fileinput
import datetime
from dateutil.parser import parse
import json
from pyvirtualdisplay import Display
from selenium import webdriver

urlfile =''
iterations =0 
url=''
num_urls=0
domains = "devtools.netmonitor.har."
num_urls =0
url_list = []
count = 0
getter=''
newurl=''
getter_version=''
h1='http://'
h1s='https://'
h2='https://'
current_directory =''
har_directory =''
def	performer (url,count):
		display = Display(visible=0, size=(1600, 1200))
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

		#filename = url[:-1]+"_"+"%y-%m-%d_%H-%M-%S"			
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
		driver = webdriver.Firefox(profile)
		
		driver.get(newurl)
		time.sleep(5)

		#close the firefox driver after HAR is written
		driver.save_screenshot('screenie.png')
		driver.close()
		display.stop()
		har_stats={}
                objs=[]
                pageSize=0
                with open("har/"+filename+".har") as f:
                        msg=json.load(f)
                for entry in msg["log"]["entries"]:
                        obj={}
                        obj["ObjectSize"]=entry["response"]["bodySize"]+entry["response"]["headersSize"]
                        pageSize=pageSize+entry["response"]["bodySize"]+entry["response"]["headersSize"]
                        obj["time"]=entry["time"]
                        objs.append(obj)

                har_stats["Objects"]=objs
                har_stats["PageSize"]=pageSize
                start=0
                for entry in msg["log"]["entries"]:
                        if start==0:
                                start_time=entry["startedDateTime"]
                                start=1
                        end_time=entry["startedDateTime"]
                        ms=entry["time"]

                hours,minutes,seconds=str(((parse(end_time)+ datetime.timedelta(milliseconds=ms))- parse(start_time))).split(":")
                hours = int(hours)
                minutes = int(minutes)
                seconds = float(seconds)
                plt_ms = int(3600000 * hours + 60000 * minutes + 1000 * seconds)
                har_stats["Web load time"]=plt_ms
		har_stats["Protocol"]=getter_version
		har_stats["Url"]=url[:-1]

                print (json.dumps(har_stats,indent=2))
		#bashcommand= "java -cp  .:harlib-1.1.3.jar:harlib-jackson-1.1.3.jar ParseHarFile har/"+filename+".har > processed_har/"+filename
		#print bashcommand
		#os.system(bashcommand)
		#bashcommand="rm har/"+filename+".har"
		#print bashcommand
		#os.system(bashcommand)
	
if len(sys.argv) ==  1: 
	print 'Use: performer.py  <URL_File>  <Iterations> <HttpMethod:h1/h1s/h2>'
	sys.exit()
elif len(sys.argv) ==  2:
	print 'Use: performer.py  <URL_File>  <Iterations> <HttpMethod:h1/h1s/h2>'
	sys.exit()
elif len(sys.argv) ==  3:
	print 'Use: performer.py  <URL_File>  <Iterations> <HttpMethod:h1/h1s/h2>'
	sys.exit()
elif len(sys.argv) ==  4:
	urlfile = sys.argv[1]
	iterations = int(sys.argv[2])

	if sys.argv[3] == 'h1':
		getter = h1
		getter_version = 'HTTP1.1'
	elif sys.argv[3] == 'h1s':
		getter = h1s
		getter_version = 'HTTP1.1/TLS'
	elif sys.argv[3] == 'h2':
		getter = h2
		getter_version = 'HTTP2'
	else:
		print 'Unknown HTTP Scheme: <HttpMethod:h1/h1s/h2>'
		print 'Use: performer.py  <URL_File>  <Iterations> <HttpMethod:h1/h1s/h2>'	
		sys.exit()
	
   	os.system('clear')
	current_directory = os.path.dirname(os.path.abspath(__file__))
	har_directory  = os.path.join(current_directory, "har")
	
	print 'Checking if HTTP Archive directory exists . . . . . . . .'
	if os.path.exists(har_directory):
		print 'HTTP Archive Directory Exists!'
	else:
		os.mkdir(har_directory)
		print "HTTP Archive Directory created successfully in %s ..\n" % (har_directory)

	print "Current Directory is: %s" % (current_directory)
	print "HTTP Archive Directory is: %s" % (har_directory)
	print 'URL file is: ', urlfile
	print 'Number of Iterations: ', iterations
	print "HTTP Scheme is: %s" % (getter_version)
	print '----------------------------------\n'
	print 'List of URLs to fetch are: \n'
	
	loop = iterations
	
	with open(sys.argv[1], "r") as ins:
		for line in ins:
			#Make URL with passed in HTTP getter scheme
			#newurl = getter + line
			#Add each URL to the url_list
			url_list.append(line)
			#Print URLs
			print getter+url_list[num_urls-1]
	
for index in range(len(url_list)):
	for run in range(count, loop):
		url=url_list[index]
		performer(url_list[index], run+1)

print 'TEST SUCCESSFULLY COMPLETED\n'
