from db import conn
import json
import c2_ssh
from beans import ComputeNodeMana
from public import NOVA_DB,NEUTRON_DB,NOVA,NEUTRON,RTN_200,RTN_500,getConnIp

import time

import conf

REGIONS=conf.REGIONS

"""
	LOG TYPE
        1.install minion
	2.update /etc/salt/minion  sed
		sed -i "s/^#cachedir: \/var\/cache\/salt\/minion/cachedir: \/opt\/minion/1" /etc/salt/minion
		sed -i "s/^#master: salt/master: 172\.30\.250\.22/1" /etc/salt/minion
		sed -i "s/^#open_mode: False/open_mode: True/1" /etc/salt/minion
	3.service salt-minion restart
	4.master allow minion key [salt-key -y -a HOSTNAME ]
	5.master sync modules to minion
"""

CMD_NO_KEY="salt-key -y -d '%s'"

CMD_REMOVE_MINION="yum remove -y salt-minion"

CMD_CLEAR_MINION_CONF="rm -rf /etc/salt"

CMD_CLEAR_MODULE_CONF="rm -rf /opt/minion"

CMD_INIT_MINION="yum install -y salt-minion"

CMD_CONFIG_MINION="""sed -i "s/^#cachedir: \/var\/cache\/salt\/minion/cachedir: \/opt\/minion/1" /etc/salt/minion;sed -i "s/^#master: salt/master: %s/1" /etc/salt/minion;mkdir /opt/minion;service salt-minion start"""

CMD_MASTER_PASS="salt-key -y -a '%s'"
CMD_SYNC_MASTER="salt '%s' saltutil.sync_modules"

def loop_compute_nodes():
    print "run loop_compute_nodes"
    print REGIONS
    rets=[]
    for region in REGIONS:
	minions=ComputeNodeMana().getSaltComputeNodes(region)
	nodes=ComputeNodeMana().getAllComputeNodes(NOVA_DB(region))
	print "region:%s,minions:%s,nodes:%s" % (region,len(minions),len(nodes))
	for node in nodes:
	    print "run check node:%s" % node
	    if minions.has_key("%s_%d"% (node.hypervisor_hostname,node.id)):
		#installed
		ret=updateOrNot(node,minions.get("%s_%d"% (node.hypervisor_hostname,node.id)),region)
		if ret:
		    rets.append(ret)
		    ComputeNodeMana().addSaltLog(ret,"UPDATE_NODE")
	    else:
		print "start to install new minion--- %s" % node
		ret=install_new_minion(node,region)
		rets.append(ret)
    print "end run loop_compute_nodes"
    return rets

#INSTALLED,ING,ERROR
def updateOrNot(node,minion,region):
    if not node.running_vms == minion["running_vms"] or not node.deleted == minion["node_deleted"]:
	ComputeNodeMana().updateMinion(node.running_vms,node.deleted,minion["id"],region)
	return "update_minion(%s,%s):vms:%s->%s,node_deleted:%s->%s" % (node.hypervisor_hostname,node.host_ip,minion["running_vms"],node.running_vms,minion["node_deleted"],node.deleted)
    return None

def install_new_minion(node,region):
    print "ADD MINION TO DB"
    ComputeNodeMana().addMinion(node,region)
    salt_master=conf.STATIC["Salt_master"]
    state="INSTALLED"
    rets=[]
    removeKey(node.hypervisor_hostname,node.id,region)

    print "------------start to remove minion ------------------"
    try:
	LOG=c2_ssh.conn2(getConnIp(node.host_ip),CMD_REMOVE_MINION)
	print "REMOVE_MINION log:%s" % LOG
    except Exception,ex:
	LOG="REMOVE_MINION exception:%s" % str(ex)
	ComputeNodeMana().addSaltLog("(%s)_REMOVE_MINION_ERROR:%s" % (node.hypervisor_hostname,LOG),"INSTALL_ERROR")
	print Exception,"REMOVE_MINION:",ex
    print "----------------finish remove minion --------------------------"

    print "------------start to clear minion config------------------"
    try:
	LOG=c2_ssh.conn2(getConnIp(node.host_ip),CMD_CLEAR_MINION_CONF)
	print "CLEAR_MINION_CONF log:%s" % LOG
    except Exception,ex:
	LOG="CLEAR_MINION_CONF exception:%s" % str(ex)
	print Exception,"CLEAR_MINION_CONF:",ex
    print "----------------finish clear minion config --------------------------"

#CMD_CLEAR_MODULE_CONF

    print "------------start to clear MODULE config------------------"
    try:
	LOG=c2_ssh.conn2(getConnIp(node.host_ip),CMD_CLEAR_MODULE_CONF)
	print "CLEAR_MODULE_CONF log:%s" % LOG
    except Exception,ex:
	LOG="CLEAR_MODULE_CONF exception:%s" % str(ex)
	print Exception,"CLEAR_MODULE_CONF:",ex
    print "----------------finish clear MODULE config --------------------------"

    print "------------start to install minion ------------------"
    try:
	LOG=c2_ssh.conn2(getConnIp(node.host_ip),CMD_INIT_MINION)
	rets.append("CMD_INIT_MINION:%s" % LOG)
	print "install log:%s" % LOG
	ComputeNodeMana().addSaltLog("INSTALL_MINION:%s" % LOG,"INSTALL_MINION")
    except Exception,ex:
	LOG="install_new_minion exception:%s" % str(ex)
	ComputeNodeMana().addSaltLog("(%s)_INSTALL_ERROR:%s" % (node.hypervisor_hostname,LOG),"INSTALL_ERROR")
	print LOG
	print Exception,"install_new_minion:",ex
	state="ERROR"
    print "----------------finish install minion --------------------------"

    print "----------------start to update minion config-------------------"
    try:
	LOG=c2_ssh.conn2(getConnIp(node.host_ip),CMD_CONFIG_MINION % salt_master)
	rets.append("CMD_CONFIG_MINION:%s" % LOG)
	print "update config log:%s" % LOG
	ComputeNodeMana().addSaltLog("CONFIG_ERROR:%s" % LOG,"CONFIG_MINION")
    except Exception,ex:
	LOG="CONFIG_MINION exception:%s" % str(ex)
	ComputeNodeMana().addSaltLog("(%s)_CONFIG_MINION_ERROR:%s" % (node.hypervisor_hostname,LOG),"CONFIG_ERROR")
	print LOG
	print Exception,"CMD_CONFIG_MINION:",ex
	state="ERROR"
    print "----------------finish update minion config------------------------"
    if "_error_" in LOG:
	print LOG
        ComputeNodeMana().updateMinionState("INIT_ERROR",node.id,region)

    time.sleep(30)
    if not "_error_" in LOG:
	rets.append(masterAcceptKey(node.hypervisor_hostname,node.id,region))
	time.sleep(35)
	LOG=syncModules2Minion(node.hypervisor_hostname,node.id,region)
	if "modules" in LOG:
	    state="INSTALLED"
	    ComputeNodeMana().updateMinionState(state,node.id,region)
	rets.append(LOG)

    return "install_new_minion:(%s,%s),state:%s,LOG:%s" % (node.hypervisor_hostname,node.host_ip,state,rets)

def masterSync(hostname):
    salt_server=conf.STATIC["Salt"]
    print salt_server
    try:
	LOG=c2_ssh.conn2(salt_server,CMD_MASTER_SYNC.format(hostname,hostname))
	if "_error_" in LOG:
	    state="ERROR"
    except Exception,ex:
	print Exception,"masterSync:",ex
	LOG="masterSync exception:%s" % str(ex)
	state="SYNC_ERROR"
    salt_log="Master accpect key and sync modules(host:%s):%s" % (hostname,LOG)
    ComputeNodeMana().addSaltLog(salt_log,"AcceptedKey_SYNC_MOD")
    return salt_log

def removeKey(hostname,node_id,region):
    print "Start to remove key in master."
    salt_server=conf.STATIC["Salt"]
    try:
	LOG=c2_ssh.conn2(salt_server,CMD_NO_KEY % hostname)
    except Exception,ex:
	print Exception,"removeKey:",ex
	LOG="remove key exception:%s" % str(ex)
	ComputeNodeMana().updateMinionState("RMKEY_ERR",node_id,region)
    salt_log="Master remove key(host:%s):%s" % (hostname,LOG)
    print "finish remove key:%s;log:%s" % (hostname,salt_log)
    return salt_log

def masterAcceptKey(hostname,node_id,region):
    salt_server=conf.STATIC["Salt"]
    try:
	LOG=c2_ssh.conn2(salt_server,CMD_MASTER_PASS % hostname)
	if "_error_" in LOG:
	    state="ERROR"
    except Exception,ex:
	print Exception,"masterAcceptKey:",ex
	LOG="masterAcceptKey exception:%s" % str(ex)
	ComputeNodeMana().updateMinionState("KEY_ERROR",node_id,region)
    salt_log="Master accpect key(host:%s):%s" % (hostname,LOG)
    ComputeNodeMana().addSaltLog(salt_log,"Accepted_Key")
    return salt_log

def syncModules2Minion(minionName,node_id,region):
    salt_server=conf.STATIC["Salt"]
    try:
	LOG=c2_ssh.conn2(salt_server,CMD_SYNC_MASTER % minionName)
	if "_error_" in LOG:
	    state="ERROR"
    except Exception,ex:
	print Exception,"syncModules2Minion:",ex
	LOG="syncModules2Minion exception:%s" % str(ex)
	ComputeNodeMana().updateMinionState("SYNC_ERROR",node_id,region)
    salt_log="Master sync all(host:%s):%s" % (minionName,LOG)
    ComputeNodeMana().addSaltLog(salt_log,"SYNC_ALL")
    return salt_log

if __name__=="__main__":
		while True:
				try:
						loop_compute_nodes()
				except Exception,ex:
						print Exception,"install_error:",ex
				time.sleep(600)
