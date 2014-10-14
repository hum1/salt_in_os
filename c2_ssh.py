#!/usr/bin/python
import paramiko
import json
import os

def conn(host,command,user="root",pwd=None,port=22):	
	ssh=paramiko.SSHClient()
	ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
	print "host:%s,command:%s,user:%s,pwd:%s,port:%s" % (host,command,user,pwd,port)
	PRIVATE_KEY='/root/.ssh/id_rsa'
	ssh.connect(host,port,user,pwd,key_filename=PRIVATE_KEY)
	stdin,stdout,stderr=ssh.exec_command(command)
	error=stderr.readlines()
	output=stdout.readlines()
	ssh.close()
	if not error:
	    return output
	else:
	    errot_list=json.dumps(error)
	    print "An error happened by:%s" % errot_list
	    return error


def conn2(host,command,user="root",pwd=None,port=22):	
	ssh=paramiko.SSHClient()
	ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
	PRIVATE_KEY='/root/.ssh/id_rsa'
	ssh.connect(host,port,user,pwd,key_filename=PRIVATE_KEY)
#,timeout=300
	stdin,stdout,stderr=ssh.exec_command(command)
	error=stderr.readlines()
	output=stdout.readlines()
	ssh.close()
	if not error:
	    return output
	else:
	    return "An _error_ happened by:%s" % error



