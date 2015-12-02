import time;

import boto.ec2;

from awsconn import awsConn;

class awsUtils (object):
    
    @staticmethod
    def wait_for_instances (instances, state='running', ec2_conn=None):
        
        if ec2_conn == None:
            ec2_conn = awsConn.create_ec2_conn_singapore();
        while True:
            reservation = ec2_conn.get_all_instances (
                                instance_ids=instances);
            if all(instance.state == state
                    for instance in reservation[0].instances):
                return;
            else:
                # TODO: Print more informative output
                print 'Waiting for instances to be in ' + state + ' state';
                time.sleep(20);
