import re
from scan_service.lib.common import ParseViaSSH
import hashlib

class PGParse(ParseViaSSH):

    def __init__(self, ssh, passwd):
        super(PGParse, self).__init__(ssh = ssh, passwd = passwd)

    def parse_pg(self, cluster_file_list):
        ret = {}
        for cluster_file in cluster_file_list:
            if not cluster_file:
                continue

            content = self.get_file_content(cluster_file)
            master_pattern = "(?:^|\n)\s*primary_conninfo\s*=(.*)"
            match = re.search(master_pattern, content)
            if match:

                master_info = {}
                master_config = match.group(1)

                #获取master的ip
                match = re.search("host\s*=\s*(\S+)", master_config)
                if match:
                    master_info["host"] = self.get_ip_from_hostname(match.group(1))[0]
                else:
                    continue

                #获取master的port
                match = re.search("port\s*=\s*(\S+)", master_config)
                if match:
                    master_info["port"] = match.group(1)
                else:
                    continue

                master_instance = {
                    "type": "pg",
                    "status": "",
                    "role": "master",
                    "listen": ["%s:%s" %(master_info["host"], master_info["port"])]
                }
                ret = {
                    "uuid": hashlib.md5(master_instance["listen"][0].encode()).hexdigest(),
                    "service_ip": master_info["host"],
                    "type": "Replication",
                    "instance": [ master_instance ]
                }
                ret["name"] = "postgresql-%s" %ret["uuid"]
                break

        return ret


