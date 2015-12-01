import sys;
import time;
import json;

import boto.ec2;
import boto.vpc;
from awsconn import awsConn;

class awsParticipant (object):


    def __init__ (self, conf_file, cidr_block):

        self.conf = self.__load_conf (conf_file);
        self.cidr_block = cidr_block;
        self.ec2_conn = awsConn.create_ec2_conn_singapore ();
        self.vpc_conn = awsConn.create_vpc_conn_singapore ();
        self.private_subnet = self.__create_private_subnet ();
        self.cloud_instances = self.__run_cloud_instances ();
        
        
    def __create_private_subnet(self):   
        
        private_subnet = self.vpc_conn.create_subnet (vpc_id = self.conf["vpc"],
                                                      cidr_block = self.cidr_block);
        private_subnet.add_tag ("Name", "Participant Subnet");
        return private_subnet;
    
    def __run_cloud_instances(self):
        reservation = self.ec2_conn.run_instances (
                            image_id = 'ami-96f1c1c4', min_count = 2,
                            max_count = 2, key_name = 'openstack-workshop',
                            instance_type ='t2.micro', 
                            subnet_id = self.private_subnet.id, 
                            security_group_ids = [self.conf["sg_private"]]);
        cloud_instances = reservation.instances;
        ids = [];
        for instance in cloud_instances:
            ids.append(instance.id);
        while True:
            reservation = self.ec2_conn.get_all_instances (instance_ids=ids);
            if all (instance.state == 'running' 
                        for instance in reservation[0].instances):
                return cloud_instances;
            else:
                print 'Cloud instance starting up...';
                time.sleep(10);
                             
    def __load_conf (self, conf_file):
        
        try:
            with open(conf_file, 'r') as fp:
                conf = json.load(fp);
                return conf;
        except IOError:
            print 'IOError: Conf file not found';
            sys.exit(-1);
    


if __name__ == '__main__':
    
    if len (sys.argv) != 3:
        print 'usage: awsParticipant.py <conf_file> <cidr_block>'
        sys.exit(-1);
    conf_file = sys.argv[1];
    cidr_block = sys.argv[2];
    acr = awsParticipant (conf_file, cidr_block);
