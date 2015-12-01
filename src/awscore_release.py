import sys;
import time;
import json;

import boto.ec2;
import boto.vpc;


class awsCoreRelease (object):
    

    def __init__ (self, conf_file):
        
        try:
            with open (conf_file, 'r') as fp:
                self.conf = json.load(fp);
            self.ec2_conn = self.__create_ec2_conn();
            self.vpc_conn = self.__create_vpc_conn();        
            self.__release();
        except IOError:
            print 'IOError: Conf file not found';
            sys.exit(-1);
        except KeyError as e:
            print conf_file + " does not contain key " + e.args[0];
            print "Make sure Conf file is valid and contains all resource ids";
            sys.exit(-1);

    def __create_ec2_conn (self):

        singapore = boto.ec2.regions()[4];
        return boto.ec2.connect_to_region (region_name=singapore.name);

    def __create_vpc_conn (self):

        singapore = boto.ec2.regions()[4];
        return boto.vpc.VPCConnection (region = singapore);

    def __release (self):

        self.ec2_conn.delete_security_group (
                                group_id = self.conf["sg_private"]);
        self.ec2_conn.disassociate_address (
                                association_id = self.conf["eip_assoc"]);
        self.ec2_conn.release_address (
                                allocation_id = self.conf["eip_alloc"]);
        self.__terminate_nat_instance();
        self.ec2_conn.delete_security_group (group_id = self.conf["sg_nat"]);
        self.vpc_conn.disassociate_route_table(
                                self.conf["custom_rtable_assoc"]);
        self.vpc_conn.delete_route (
                                self.conf["custom_rtable"], "0.0.0.0/0");
        self.vpc_conn.delete_route_table (self.conf["custom_rtable"]);
        self.vpc_conn.detach_internet_gateway (
                                self.conf["ig"], self.conf["vpc"]);
        self.vpc_conn.delete_internet_gateway (self.conf["ig"]);
        self.vpc_conn.delete_subnet (self.conf["public_subnet"]);
        self.vpc_conn.delete_vpc (self.conf["vpc"]);
    
    # Terminates NAT instance and returns when it get into 'terminated' state
    def __terminate_nat_instance (self):
    
        self.ec2_conn.terminate_instances (
                                instance_ids = [self.conf["nat_instance"]]);
    
        while True:
            reservation = self.ec2_conn.get_all_instances (
                                instance_ids = [self.conf["nat_instance"]]);
            if reservation[0].instances[0].state != 'terminated':
                print "instance {} shutting-down...".format(
                                            reservation[0].instances[0].id);
                time.sleep(10);
            else:
                return;

if __name__ == '__main__':

    if len (sys.argv) != 2:
        print 'usage: awsCoreRelease.py <conf_file>';    
        sys.exit(-1);
    
    acr = awsCoreRelease(sys.argv[1]);
