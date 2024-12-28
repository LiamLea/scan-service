from scan_service.lib.common import ParseViaSSH
import hashlib

class MysqlParse(ParseViaSSH):
    def __init__(self, ssh, passwd):
        super(MysqlParse, self).__init__(ssh = ssh, passwd = passwd)

    def parse_mysql(self, cluster_file):

        if not cluster_file:
            return {}

        master_info = self.exec_shell("cat %s | awk 'NR==4 || NR==7{print}'" %cluster_file)
        if not master_info:
            return {}

        master_instance = {
            "type": "mysql",
            "status": "",
            "role": "master",
            "listen": ["%s:%s" %(master_info[0], master_info[1])]
        }

        cluster = {
            "uuid": hashlib.md5(master_instance["listen"][0].encode()).hexdigest(),
            "service_ip": master_info[0],
            "type": "Replication",
            "instance": [ master_instance ]
        }
        cluster["name"] = "mysql-%s" %cluster["uuid"]

        return cluster

