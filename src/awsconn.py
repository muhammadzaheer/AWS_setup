import boto.ec2;
import boto.vpc;

class awsConn (object):
    

    """ Wraps static method to create AWS connections in various regions.
    (Currently, only singapore region is supported)
    """
    
    @staticmethod
    def create_ec2_conn_singapore():
        """ Creates an ec2 connection in Singapore Region """ 
        singapore = boto.ec2.regions()[4];
        return boto.ec2.connect_to_region (region_name=singapore.name);

    @staticmethod
    def create_vpc_conn_singapore():
        """ Create a VPC connection in Singapore Region """
        singapore = boto.ec2.regions()[4];
        return boto.vpc.VPCConnection (region=singapore);
