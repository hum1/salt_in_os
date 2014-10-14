from django.conf import settings
from db import conn
from public import NOVA_DB,NEUTRON_DB,NOVA,NEUTRON

class ComputeNode:
	def __init__(self,vcpus,memory_mb,vcpus_used,memory_mb_used,hypervisor_hostname,running_vms,deleted=0,host_ip=None,id=None):
		self.vcpus=vcpus
                self.memory_mb=memory_mb
		self.vcpus_used=vcpus_used
		self.memory_mb_used=memory_mb_used
		self.hypervisor_hostname=hypervisor_hostname
		self.running_vms=running_vms
		self.rest_vcpus=vcpus*4-vcpus_used
		self.rest_memory_mb=memory_mb-memory_mb_used
		self.deleted=deleted
		self.host_ip=host_ip
		self.id=id
	def __str__(self):
		return "--host:%s,rest_vcpus:%s,rest_mem:%s-- " % (self.hypervisor_hostname,self.rest_vcpus,self.rest_memory_mb)

        def __repr__(self):
                return "--host:%s,rest_vcpus:%s,rest_mem:%s-- " % (self.hypervisor_hostname,self.rest_vcpus,self.rest_memory_mb)

	def availability(self,cpu,mem):
		return self.rest_vcpus>cpu and self.rest_memory_mb>mem

ALL_PHYSICAL="SELECT vcpus,memory_mb,vcpus_used,memory_mb_used,hypervisor_hostname,running_vms,deleted,host_ip,id FROM compute_nodes"

GET_SALT_PHYSICAL="SELECT compute_node_ip,compute_node_host,region,running_vms,node_deleted,id FROM salt_nodes WHERE region=%s"

ADD_Minion="""
INSERT INTO salt_nodes(id,compute_node_ip,compute_node_host,region,running_vms,salt_state,node_deleted,update_time) VALUES (%s,%s,%s,%s,%s,"INIT",%s,now())
"""

UPDATE_MINION_VMS="""
UPDATE salt_nodes SET running_vms=%s,node_deleted=%s WHERE id=%s AND region=%s
"""

UPDATE_MINION_STATE="""
UPDATE salt_nodes SET salt_state=%s WHERE id=%s AND region=%s
"""

SALT_LOG="""
INSERT INTO salt_thread_log(log,create_time,type) VALUES (%s,now(),%s)
"""

class ComputeNodeMana:

    def updateMinion(self,vms,deleted,_id,region):
	cursor=conn().cursor()
	cursor.execute(UPDATE_MINION_VMS,(vms,deleted,_id,region))
	cursor.close()

    def updateMinionState(self,state,_id,region):
	cursor=conn().cursor()
	cursor.execute(UPDATE_MINION_STATE,(state,_id,region))
	cursor.close()

    def addMinion(self,n,region):
	cursor=conn().cursor()
	try:
	    cursor.execute(ADD_Minion,(n.id,n.host_ip,n.hypervisor_hostname,region,n.running_vms,n.deleted))
	except Exception,ex:
	    print Exception,":",ex
	    return False
	finally:
	    cursor.close()
	return True

    def addSaltLog(self,log,Type):
	cursor=conn().cursor()
	try:
	    cursor.execute(SALT_LOG,(log,Type,))
	except Exception,ex:
	    print Exception,":",ex
	    return False
	finally:
	    cursor.close()
	return True

    def getAllComputeNodes(self,db):
	cursor=db.cursor()
	cursor.execute(ALL_PHYSICAL)
	results=cursor.fetchall()
	nodes=[]
	for line in results:
		vcpus=line[0]
		memory_mb=line[1]
		vcpus_used=line[2]
		memory_mb_used=line[3]
		hypervisor_hostname=line[4]
		running_vms=line[5]
		deleted=line[6]
		host_ip=line[7]
		_id=line[8]
		nodes.append(ComputeNode(vcpus,memory_mb,vcpus_used,memory_mb_used,hypervisor_hostname,running_vms,deleted,host_ip,_id))
	cursor.close()
	return nodes

    def getSaltComputeNodes(self,region):
	cursor=conn().cursor()
	cursor.execute(GET_SALT_PHYSICAL,(region,))
	results=cursor.fetchall()
	cursor.close()
	nodes={}
	for line in results:
		minion={}
		minion["compute_node_ip"]=line[0]
		minion["compute_node_host"]=line[1]
		minion["region"]=line[2]
		minion["running_vms"]=line[3]
		minion["node_deleted"]=line[4]
		minion["id"]=line[5]
		nodes["%s_%d" % (line[1],minion["id"])]=minion
	return nodes
