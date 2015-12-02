import sys;
import time;
import json;

import boto.ec2;
import boto.vpc;

from awsconn import awsConn;
from awsutils import awsUtils;


class awsParticipantRelease (object):


    def __init__ (self, conf_file):
        
        try:
            with open (conf_file, 'r') as fp:
                self.conf = json.load(fp);
            self.ec2_conn = awsConn.create_ec2_conn_singapore();
            self.vpc_conn = awsConn.create_vpc_conn_singapore();
            self.instance_ids = self.conf['instance_ids'].split(',');
            self.private_subnet = self.conf['private_subnet'];
            self.__release();
        except IOError:
            print 'IOError: Participant conf file not found';
            sys.exit(-1);
        except KeyError as e:
            print conf_file + "does not contain key " + e.args[0];
            print "Make sure Conf file is valid and contains all resource ids";
            sys.exit(-1);
    
    def __release (self):
        
        self.__terminate_cloud_instances();
        self.vpc_conn.delete_subnet(self.private_subnet);
 
    def __terminate_cloud_instances (self):
        
        self.ec2_conn.terminate_instances (instance_ids=self.instance_ids);
        awsUtils.wait_for_instances(self.instance_ids, 'terminated', 
                                    self.ec2_conn);

if __name__ == '__main__':
    
    if len(sys.argv) != 2:
        print 'usage: awsParticipantRelease.py <conf_file>';
        sys.exit(-1);

    apr = awsParticipantRelease (sys.argv[1]);
