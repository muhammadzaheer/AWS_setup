import time;
import boto.ec2;
from awsconn import awsConn;

class awsUtils (object):


    """
    This method will wait for the instances to be in desired state
    """
    @staticmethod
    def wait_for_instances (instances, state='running', ec2_conn=None):
        """
        If there isn't any instance created, create the instance to singapore region
        """
        if ec2_conn == None:
            ec2_conn = awsConn.create_ec2_conn_singapore();
        while True:
            """
            Gets all EC2 instances based on their IDs provided.
            """
            reservation = ec2_conn.get_all_instances (
                                instance_ids=instances);
            """
            Checks the state of each instance one by one
            """                    
            if all(instance.state == state
                    for instance in reservation[0].instances):
                time.sleep(20);
                return;
            else:
                print 'Waiting for instances to be in ' + state + ' state';
                time.sleep(5);
