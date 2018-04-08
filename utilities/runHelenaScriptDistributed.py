# usage: python runHelenaScriptDistributed.py <helenaScriptNumericId> <numDistributedMachines> <timeoutInHours> <howManyRunsToAllowPerWorker>
# ex: python runHelenaScriptDistributed.py 1022 8 24 1

import paramiko
import boto3
import sys
import pprint
import requests
import multiprocessing

scriptName = int(sys.argv[1])
numDistributedMachines = int(sys.argv[2])
timeoutInHours = float(sys.argv[3])
howManyRunsToAllowPerWorker = int(sys.argv[4])

tag = "helena-1"

ec2 = boto3.client('ec2', region_name='us-west-2')  
tags = [{  
    'Name': 'tag:' + tag,
    'Values': ['true']
    }]
reservations = ec2.describe_instances(Filters=tags)
pp = pprint.PrettyPrinter(indent=1)
pp.pprint(reservations)

# ok, first get an id for the new dataset run
# before we can do anything else, we need to get the dataset id that we'll use for all of the 'threads'
# 'http://kaofang.cs.berkeley.edu:8080/newprogramrun', {name: dataset.name, program_id: dataset.program_id}
r = requests.post('http://kaofang.cs.berkeley.edu:8080/newprogramrun', data = {"name": str(scriptName)+"_"+str(numDistributedMachines)+"_distributed_hashBased", "program_id": scriptName})
output = r.json()
runid = output["run_id"]
print "current parallel run's dataset id:", runid
print "-----"

# what machines do we have available to us?  let's get their ips
availableIps = []
reservationsDeets = reservations["Reservations"]
l = len(reservationsDeets)
for i in range(l):
	machine = reservationsDeets[i]["Instances"][0]
	if (not "PublicIpAddress" in machine):
		# this one doesn't have a public ip address, probably because it's not running right now
		continue
	ip = machine["PublicIpAddress"]
	availableIps.append(ip)

# the function that will actually talk to a given machine at a given index in the list of ips
def talkToOneDistributedMachine(i):
	ip = availableIps[i]
	print "ip", ip
	#k = paramiko.RSAKey.from_private_key_file("/Users/schasins/.ssh/MyKeyPair.pem")
	k = paramiko.RSAKey.from_private_key_file("/Users/sarahchasins/.ssh/MyKeyPair.pem")
	c = paramiko.SSHClient()
	c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
	print "connecting"
	c.connect( hostname = ip, username = "ec2-user", pkey = k )
	print "connected"
	# below, 1 is fixed because for now we only set one browser instance going on any given distributed machine
	# also all our amazon images have chromedriver in the same folder where we run, thus the hardcoded chromedriver loc
	com = "python runHelenaScriptInParallel.py " + str(scriptName) + " 1 " + str(timeoutInHours) + " " + str(howManyRunsToAllowPerWorker) + " ./chromedriver " + str(runid) + ")"
	commands = ['(cd helena/utilities;' + com]
	for command in commands:
	    print "Executing {}".format( command )
	    stdin , stdout, stderr = c.exec_command(command)
	    print stdout.read()
	    print( "Errors")
	    print stderr.read()
	c.close()

# all right, now we know all the ips available to us.  let's give some out
pool = multiprocessing.Pool(numDistributedMachines)
pool.map(talkToOneDistributedMachine, range(0, numDistributedMachines))
