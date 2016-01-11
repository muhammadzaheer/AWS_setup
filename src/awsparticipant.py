import sys;
import time;
import json;
import os;

import boto.ec2;
import boto.vpc;
from netaddr import *;
from awsconn import awsConn;
from awsutils import awsUtils;


class awsParticipant (object):


    def __init__ (self, conf_file, cidr_block):

	#Loads the conf file provided as cmd line argument 
        self.conf = self.__load_conf (conf_file);
        
        #Extracts CIDR from dictionary
        self.cidr_block = self.conf["cidr"];
        
        #Create connections
        self.ec2_conn = awsConn.create_ec2_conn_singapore ();
        self.vpc_conn = awsConn.create_vpc_conn_singapore ();
        
        #Create a private subnet for participant
        self.private_subnet = self.__create_private_subnet ();
        
        #Extracting Participant ID, CIDR='172.16.[participant_id].0/24'
        self.participant_id = self.conf["cidr"].split(".")[2];
        
        #Creating instances in private subnet of participant
        self.controller_ip, self.compute_ip, self.cloud_instances =self.__run_cloud_instances ();
                                                
        #Creates a dictionary for storing the IDs of instances created                                        
        self.conf_participant = self.__populate_conf_participant();
        
        #Store the conf in a file
        self.__persist_conf_participant();   
        
        print '============================================================='
        print '===      AWS machines successfully setup                  ==='
        print '============================================================='
        print '===      Jump Host IP: ', self.conf["eip_address"];
        print '===      Controller IP: ', self.controller_ip;
        print '===      Compute IP: ', self.compute_ip;
        print '============================================================='
  


    """
    This method will create a private subnet in VPC with the CIDR block provided to participant
    """
            
    def __create_private_subnet(self):   
        
        private_subnet = self.vpc_conn.create_subnet (
                                            vpc_id = self.conf["vpc"],
                                            cidr_block = self.cidr_block);
        private_subnet.add_tag ("Name", "Participant Subnet");
        return private_subnet;
    
    """
    This method will run the cloud instances with the different IPs 
    """
   
    def __run_cloud_instances (self, private_ip = None):
        
        cloud_instances = [];
        #create IP for the controller instance, [.91]
        controller_ip = self.__create_private_ip('91');
        #create IP for the compute instance, [.92]
        compute_ip = self.__create_private_ip('92');
        #It'll run the instance, ID here is the id of the instance with pre installed devstack in them
        controller = self.__run_cloud_instance(
                                controller_ip,
                                image_id='ami-0f7aba6c');
        compute = self.__run_cloud_instance(
                                compute_ip,
                                image_id='ami-9c7abaff');
        controller.add_tag("Name", "Controller_" + self.participant_id );
        compute.add_tag("Name", "Compute_" + self.participant_id);
        cloud_instances.append(controller);
        cloud_instances.append(compute);
        #Wait for instances to be in running state
        ids = [];
        for instance in cloud_instances:
            ids.append(instance.id);
        awsUtils.wait_for_instances(ids, 'running');
        return controller_ip, compute_ip, cloud_instances;
    
    """
    This method creates an IP address in IP range of participant with last quad provided
    """
    
    def __create_private_ip (self, last_quad):
    
        ip = self.cidr_block;
        quads = ip.split(".");
        private_ip = '';
        for quad in quads[:3]:
            private_ip = private_ip + quad + '.';
        
        return private_ip + last_quad;
            
            
    """
    This method starts the instance, in the private subnet and with the security group created before for private instances
    """
           
    def __run_cloud_instance (self, private_ip = None,
                              image_id = 'ami-96f1c1c4'):
                
        #image_id:  ID of the image we are creating, here these are images with pre installed devstack
        #instance_type:  This is the flavour we're using 
       	#		m3.xlarge provides 4 vCPUs,15GiB and 2*40 GB SSD Storage  		
        
  
        reservation = self.ec2_conn.run_instances (
                            image_id = image_id, min_count = 1,
                            max_count = 1, key_name = 'openstack-workshop',
                            instance_type ='m3.xlarge', 
                            subnet_id = self.private_subnet.id, 
                            private_ip_address=private_ip,
                            security_group_ids=[self.conf["sg_private"]]);

        cloud_instance= reservation.instances[0];
        return cloud_instance;
    
    """
    This method will load the conf file provided by participant.
    """ 
            
    def __load_conf (self, conf_file):
        
        try:
            with open(conf_file, 'r') as fp:
                conf = json.load(fp);
                return conf;
        except IOError:
            print 'IOError: Conf file not found';
            sys.exit(-1);
    
    """
    This will add the IDs of instances and subnet in the conf dictionary for release purposes.
    """ 
      
    def __populate_conf_participant (self):

        # Creating a tuple of cloud instance ids
        instance_ids = ();
        for instance in self.cloud_instances:
            instance_ids = instance_ids + (instance.id,);
        
        conf_participant = {};
        conf_participant["cidr"] = self.cidr_block;
        conf_participant["instance_ids"] = ','.join(instance_ids);
        conf_participant["private_subnet"] = self.private_subnet.id;
        return conf_participant;
        
        
    """
    This method  persist all the configuration in JSON files.
    """   
     
    def __persist_conf_participant (self):

        with open('conf_participant_' + self.participant_id +'.json', 
                  'w') as fp:
            json.dump (self.conf_participant, fp);

            
if __name__ == '__main__':
    
    if len (sys.argv) != 3:
        print 'usage: python awsParticipant.py <conf_file> <cidr_block>'
        sys.exit(-1); 
    if(os.path.exists(sys.argv[1])):   
    	conf_file = sys.argv[1];
    else:	
    	print "conf file doesn't exists, check file with file name conf_[Participant ID]"
    	sys.exit(-1);
try:
   cidr_block = sys.argv[2];
   ip=IPNetwork("%s" % (cidr_block));
   acr = awsParticipant (conf_file, cidr_block);
except AddrFormatError:
   print 'Error: CIDR block not valid';
   sys.exit(-1);

