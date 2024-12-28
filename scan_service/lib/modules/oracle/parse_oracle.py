from scan_service.lib.vars import global_var
import  re
import hashlib
from scan_service.lib.common import ParseViaSSH

class OracleParse(ParseViaSSH):
    def __init__(self, ssh, passwd):
        super(OracleParse, self).__init__(ssh, passwd)

    # def get_ip(self, crsctl_file, ip_name):
    #     result = self.exec_shell("%s status ip -A %s" % (crsctl_file, ip_name))
    #     for line in result:
    #         ip = re.search(global_var.ip_pattern, line)
    #         if ip:
    #             return ip.group()
    #         else:
    #             return ""

    def parse_oracle(self, install_location):
        ret = {}
        cluster = {}
        cemu_file = self.find_file(install_location, ".*bin/cemutlo$")[0]
        crsctl_file = self.find_file(install_location, ".*bin/crsctl$")[0]
        srv_file =self.find_file(install_location, ".*bin/srvctl$")[0]

        if cemu_file and srv_file:
            cluster["name"] = self.exec_shell("%s -n" %cemu_file)[0]
            cluster["service_ip"] = ""
            cluster["type"] = ""
            cluster["instance"] = []
            cluster["database"] = []
            cluster["node"] = []
            cluster["uuid"] = ""

            #查询oracle集群的节点
            node_list = []
            for line in self.exec_shell("%s status server" %crsctl_file):
                result = re.search("NAME=(.*)", line)
                if result:
                    node_list.append(result.group(1))

            #查看oracle集群的数据库数
            db_list = self.exec_shell("%s config database" %srv_file)
            for db in db_list:
                item = {}
                db_info_dict = {}
                for line in self.exec_shell("%s config database -d %s" %(srv_file, db)):
                    if ":" in line:
                        db_info_dict[line.split(":")[0].lower().strip()] = line.split(":")[1].strip()
                item["name"] = db_info_dict.get("database unique name", "")
                item["home"] = db_info_dict.get("oracle home", "")
                item["user"] = db_info_dict.get("oracle user", "")
                item["type"] = db_info_dict.get("type", "")

                if db_info_dict.get("database instances"):
                    item["instance"] = db_info_dict["database instances"].split(',')
                else:
                    item["instance"] = []

                if db_info_dict.get("configured nodes"):
                    item["node"] = db_info_dict["configured nodes"].split(',')
                else:
                    item["node"] = []
                    for line in self.exec_shell("%s status database -d %s" %(srv_file, db)):
                        result = re.search(r"node (\S+)", line)
                        if result:
                            item["node"].append(result.group(1))

                cluster["database"].append(item)

            #获取实例信息
            for db in cluster["database"]:
                for node in node_list:
                    item = {}
                    result = self.exec_shell("%s status instance -d %s -n %s" %(srv_file, db["name"], node))[0]

                    match_name = re.search(r"Instance (\S+)", result)
                    if match_name:
                        item["name"] = match_name.group(1)
                    else:
                        item["name"] = ""

                    match_node = re.search(r"node (\S+)", result)
                    if match_node:
                        item["node"] = match_node.group(1)
                    else:
                        item["node"] = ""

                    item["role"] = "member"
                    item["type"] = "oracle"
                    item["listen"] = []
                    item["status"] = ""

                    #如果实例name为空，表示该实例不存在
                    if item["name"]:
                        if "is not running" in result:
                            item["status"] = "DOWN"
                        elif "is running" in result:
                            item["status"] =  "UP"

                        cluster["instance"].append(item)

            #获取节点的信息
            for node in node_list:
                item = {}
                item["name"] = node
                # item["ip"] = self.get_ip(crsctl_file, node)
                item["ip"] = self.get_ip_from_hostname(node)[0]
                # item["vip"] = self.get_ip(crsctl_file, self.exec_shell("%s status vip -n %s" %(srv_file, node))[0].split()[1])
                item["vip"] = self.get_ip_from_hostname(self.exec_shell("%s status vip -n %s" %(srv_file, node))[0].split()[1])[0]
                cluster["node"].append(item)

            #获取scan_ip
            match = re.search(r"(%s)\n" %global_var.ip_pattern, '\n'.join(self.exec_shell("%s config scan" % srv_file)) + '\n')
            cluster["service_ip"] = match.group(1)

            cluster["type"] = cluster["database"][0]["type"]

            if cluster["service_ip"]:
                # cluster["uuid"] = hashlib.md5(''.join(cluster["service_ip"]).encode()).hexdigest()
                ret = cluster

        return ret