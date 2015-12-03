import sys;
import time;
import json;
import os;

import boto.ec2;
import boto.vpc;

from awsconn import awsConn;
from awsutils import awsUtils;


class awsParticipant (object):


    def __init__ (self, conf_file, cidr_block):

        self.conf = self.__load_conf (conf_file);
        self.cidr_block = self.conf["cidr"];
        self.ec2_conn = awsConn.create_ec2_conn_singapore ();
        self.vpc_conn = awsConn.create_vpc_conn_singapore ();
        self.private_subnet = self.__create_private_subnet ();
        self.participant_id = self.conf["cidr"].split(".")[2];
        self.cloud_instances = self.__run_cloud_instances ();
        self.conf_participant = self.__populate_conf_participant();
        self.__persist_conf_participant();   
             
    def __populate_conf_participant (self):
        
        # Creating a tuple of cloud instance ids
        instance_ids = ();
        for instance in self.cloud_instances:
            instance_ids = instance_ids + (instance.id,);
        
        conf_participant["cidr"] = self.cidr_block;
        conf_participant["instance-ids"] = ','.join(instance_ids);
        conf_participant["private-subent"] = self.private_subnet.id;
        return conf_participant;
            
    def __create_private_subnet(self):   
        
        private_subnet = self.vpc_conn.create_subnet (
                                            vpc_id = self.conf["vpc"],
                                            cidr_block = self.cidr_block);
        private_subnet.add_tag ("Name", "Participant Subnet");
        return private_subnet;
    
    def __run_cloud_instances (self, private_ip = None):
        
        cloud_instances = [];
        controller = self.__run_cloud_instance(
                                self.__create_private_ip('91'),
                                image_id='ami-ea00c089');
        compute = self.__run_cloud_instance(
                                self.__create_private_ip('92'),
                                image_id='ami-7001c113');
        controller.add_tag("Name", "Controller_" + self.participant_id );
        compute.add_tag("Name", "Compute_" + self.participant_id);
        cloud_instances.append(controller);
        cloud_instances.append(compute);
        ids = [];
        for instance in cloud_instances:
            ids.append(instance.id);
        awsUtils.wait_for_instances(ids, 'running');
        return cloud_instances;
    
    def __create_private_ip (self, last_quad):
    
        ip = self.cidr_block;
        quads = ip.split(".");
        private_ip = '';
        for quad in quads[:3]:
            private_ip = private_ip + quad + '.';
        
        return private_ip + last_quad;
            
    def __run_cloud_instance (self, private_ip = None,
                              image_id = 'ami-96f1c1c4'):
    
        reservation = self.ec2_conn.run_instances (
                            image_id = image_id, min_count = 1,
                            max_count = 1, key_name = 'openstack-workshop',
                            instance_type ='m4.xlarge', 
                            subnet_id = self.private_subnet.id, 
                            private_ip_address=private_ip,
                            security_group_ids=[self.conf["sg_private"]]);

        cloud_instance= reservation.instances[0];
        return cloud_instance;
            
    def __load_conf (self, conf_file):
        
        try:
            with open(conf_file, 'r') as fp:
                conf = json.load(fp);
                return conf;
        except IOError:
            print 'IOError: Conf file not found';
            sys.exit(-1);
    
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

    def __persist_conf_participant (self):
        
        configs = os.path.join(os.getcwd(), 'configs');
        if not os.path.exists(configs):
            os.makedirs(configs);   
        
        with open('configs/conf_participant_' + self.participant_id +'.json', 
                  'w') as fp:
            json.dump (self.conf_participant, fp);

            
if __name__ == '__main__':
    
    if len (sys.argv) != 3:
        print 'usage: python awsParticipant.py <conf_file> <cidr_block>'
        sys.exit(-1);
    conf_file = sys.argv[1];
    cidr_block = sys.argv[2];
    acr = awsParticipant (conf_file, cidr_block);
