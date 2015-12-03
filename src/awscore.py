import sys;
import time;
import json;
import os;

import boto.ec2;
import boto.vpc;

from awsutils import awsUtils;

class awsCore (object):
    

    def __init__ (self, name, expected_participants):

            """
            Dictionary 'conf' holds IDs for VPC resources
            It would be serialized before the script exits
            It could be used to add private subnets to the VPC
            and free-up VPC resources
            """
            
            self.conf = {"name" : name}; 
            self.expected_participants = expected_participants; 
            self.ec2_conn = self.__create_ec2_conn(); 
            self.vpc_conn = self.__create_vpc_conn(); 
            
            self.vpc = self.__create_vpc(); 
            self.public_subnet = self.__create_public_subnet(); 
            self.ig = self.__create_attach_internet_gateway();
            self.main_rtable = self.__get_main_rtable();
            self.custom_rtable, self.custom_rtable_assoc = \
                                                self.__create_custom_rtable();
            # TODO: Delete All trafic rules from both security groups
            self.sg_nat = self.__create_sg_nat();
            self.sg_private = self.__create_sg_private();
            
            self.nat_instance = self.__run_nat_instance();
            self.eip = self.__allocate_eip_nat();
            self.__create_route_to_nat();
            
            self.__populate_conf(); 
            self.__persist_conf(); 
    
    def __create_ec2_conn (self):
        
        singapore = boto.ec2.regions()[4];
        return boto.ec2.connect_to_region (region_name=singapore.name);
    
    def __create_vpc_conn (self):
        
        singapore = boto.ec2.regions()[4];
        return boto.vpc.VPCConnection (region=singapore);
    
    def __create_vpc (self):
        
        vpc = self.vpc_conn.create_vpc (cidr_block = "172.16.0.0/16");
        vpc.add_tag("Name", self.conf["name"] + "_VPC");
        return vpc;
    
    def __create_public_subnet (self):
        
        public_subnet = self.vpc_conn.create_subnet (
                                    self.vpc.id, 
                                    cidr_block = "172.16.0.0/24");
        public_subnet.add_tag("Name", self.conf["name"] + "_public_subnet");
        return public_subnet;
    
    def __create_attach_internet_gateway (self):
    
        ig = self.vpc_conn.create_internet_gateway();
        ig.add_tag ("Name", self.conf["name"] + "_ig");
        self.vpc_conn.attach_internet_gateway(ig.id, self.vpc.id);
        return ig;
    
    def __get_main_rtable(self):
        
        main_rtable_filter = {'association.main':'true', 
                                'vpc-id':self.vpc.id};

        return self.vpc_conn.get_all_route_tables(
                            filters = main_rtable_filter)[0];
    
    """
    This method creates a custom routing table for public subnet
    And adds a route for egress traffic to internet gateway
    """
    
    def __create_custom_rtable(self):
    
        custom_rtable = self.vpc_conn.create_route_table(self.vpc.id);
        custom_rtable.add_tag ("Name", self.conf["name"] + "_custom_rtable");
        self.vpc_conn.create_route(custom_rtable.id, "0.0.0.0/0", self.ig.id);
        custom_rtable_assoc = self.vpc_conn.associate_route_table (
                                                    custom_rtable.id, 
						    self.public_subnet.id);
        return custom_rtable, custom_rtable_assoc;
    
    def __create_sg_nat(self):

        sg_nat = self.ec2_conn.create_security_group (
                            name = self.conf["name"] + "_SGNAT",
                            description = "Security Group for NAT instances",
                            vpc_id = self.vpc.id);
        sg_nat.add_tag("Name", self.conf["name"]+ "_SGNAT");
        self.__add_sgnat_rules(sg_nat);
        return sg_nat;
    
    def __create_sg_private(self):
        
        sg_private = self.ec2_conn.create_security_group (
                                name = self.conf["name"]+ "_Private", 
                                description= "SG for private instances",
                                vpc_id = self.vpc.id);
        sg_private.add_tag("Name", self.conf["name"] +"_Private");
        self.__add_sgprivate_rules(sg_private);
        return sg_private;
    
    def __run_nat_instance (self):
        
        reservation = self.ec2_conn.run_instances (
                        image_id = 'ami-1a9dac48', min_count = 1, 
			max_count = 1, key_name ='openstack-workshop',
                        instance_type = 't2.micro',
                        subnet_id = self.public_subnet.id,
                        private_ip_address='172.16.0.5',
                    	security_group_ids = [self.sg_nat.id]);
        nat_instance = reservation.instances[0];
        nat_instance.add_tag("Name", self.conf["name"] + "_NAT");
        # Each EC2 instance performs source/destination checks by default. 
        # This means that the instance must be the source or destination 
        # of any traffic it sends or receives. 
        # However, a NAT instance must be able to send and receive traffic
        # whem the source or destination is not itself. Therefore, we must 
        # disable source/destination checks on the NAT instance
        
        self.ec2_conn.modify_instance_attribute(
                                            instance_id = nat_instance.id,
                                            attribute = 'sourceDestCheck', 
                                            value=False);
        # Wait for the NAT instance to get into running state 
        # We cannot assing an EIP to it until it is in the running
        awsUtils.wait_for_instances([nat_instance.id], 'running', 
                                    self.ec2_conn);
        return nat_instance;

    def __allocate_eip_nat (self):
            
        # Allocating an elastic IP address for our NAT instance
        eip = self.ec2_conn.allocate_address(domain="vpc");
        # Associating EIP with NAT instance
        eip.association_id = self.ec2_conn.associate_address_object (
                            instance_id = self.nat_instance.id,
                            allocation_id = eip.allocation_id).association_id;
        
        return eip;
    
    def __create_route_to_nat (self):
    
        # Creating a route in main route table such that all outgoing traffic
        # from private subnets will be sent to our NAT instance
        self.vpc_conn.create_route(self.main_rtable.id, "0.0.0.0/0", 
                                   instance_id = self.nat_instance.id);
        
    def __add_sgnat_rules (self, sg_nat):
        # inbound traffic rules
        # Allowing all inbound traffic to NAT instances
        self.ec2_conn.authorize_security_group(
                            group_id = sg_nat.id, ip_protocol = "-1",
                            from_port = None, to_port = None, 
                            cidr_ip = "0.0.0.0/0");
    
    def __add_sgprivate_rules(self,sg_private):
           
        # inbound traffic rules
        # Allow SSH from public subnet
        self.ec2_conn.authorize_security_group(
                            group_id = sg_private.id, ip_protocol = "tcp",
                            from_port = 22, to_port = 22, 
                            cidr_ip = "172.16.0.0/24");
    
    def __populate_conf(self):
            
        self.conf["vpc"] = self.vpc.id;
        self.conf["public_subnet"] = self.public_subnet.id;
        self.conf["ig"] = self.ig.id;
        self.conf["main_rtable"] = self.main_rtable.id;
        self.conf["custom_rtable"] = self.custom_rtable.id;
        self.conf["custom_rtable_assoc"] = self.custom_rtable_assoc;
        self.conf["sg_nat"] = self.sg_nat.id;
        self.conf["sg_private"] = self.sg_private.id;
        self.conf["nat_instance"] = self.nat_instance.id;
        self.conf["eip_address"] = self.eip.public_ip;
        self.conf["eip_alloc"] = self.eip.allocation_id;
        self.conf["eip_assoc"] = self.eip.association_id;
    
    def __persist_conf(self):
        
        configs = os.path.join (os.getcwd(), 'configs');
        if not os.path.exists(configs):
            os.makedirs(configs);
        with open ('configs/conf_core.json','w') as fp:
            json.dump(self.conf,fp);    
        
        # Port offset
        p_offset = 30000; 
        for i in range (1,self.expected_participants):
            self.conf["cidr"] = "172.16." + str(i) + ".0/24";
            self.conf["port_1"] = str(i + p_offset);
            self.conf["port_2"] = str(self.expected_participants+i + p_offset);
            with open ('configs/conf_' + str(i), 'w') as fp:
                json.dump(self.conf,fp);

if __name__ == '__main__':
    
    if len (sys.argv) != 3:
        print 'usage: python awsCore.py <name_tag> <expected_participants>';
        sys.exit(-1);
    
    aws = awsCore (sys.argv[1], int(sys.argv[2]));
