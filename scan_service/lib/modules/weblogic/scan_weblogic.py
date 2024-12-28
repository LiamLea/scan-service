from scan_service.lib.common import JavaScan
from scan_service.lib.vars import global_var
from scan_service.lib.utils import MyList
from scan_service.lib.utils import get_dir
from scan_service.lib.modules.weblogic.parse_weblogic import WeblogicParse
import re
import hashlib

class WeblogicScan(JavaScan, WeblogicParse):
    """
    weblogic特征文件：
        lib/weblogic.jar

    找域：
        find / -regex ".*/domains/[^/]+"

    获取版本号：
        java -cp server/lib/weblogic.jar weblogic.version

    对于weblogic，扫描的是一个域
    根据 特征文件 获取 创建的域
    根据 startWeblogic.sh 和 weblogic.jar 脚本获取启动的服务（可以得到有该域启动的服务）
    """

    def __init__(self, init_info):

        package_dict = {
            "name": "weblogic",
            "pattern": r"^weblogic.(server.)?[0-9.]*"
        }

        feature_files_list = [
            {
                "name": "weblogic.jar",
                "pattern": r".*lib/weblogic\.jar$",
                "dir_depth": 4,
                "attribute": "f"
            },
        ]

        process_pattern = r"weblogic"

        scan_files_dict = {
            "version_file": [
                {
                    "name": "weblogic.jar",
                    "pattern": r".*lib/weblogic\.jar$",
                    "dir_depth": 4,
                    "attribute": "f"
                }
            ],
            "conf_file": [
                {
                    "name": "config.xml",
                    "pattern": r".*config/config\.xml$",
                    "dir_depth": 2,
                    "attribute": "f"
                }
            ],
            "log_file": [
                {
                    "name": "access.log",
                    "pattern": r".*logs/access\.log$",
                    "dir_depth": 3,
                    "attribute": "f"
                },
                {
                    "name": "domain.log",
                    "pattern": r".*logs/<DOMAIN>\.log$",
                    "dir_depth": 3,
                    "attribute": "f"
                },
                {
                    "name": "admin.log",
                    "pattern": r".*/(.*)/logs/\1\.log$",
                    "dir_depth": 3,
                    "attribute": "f"
                }
            ]
        }

        JavaScan.__init__(self, init_info, package_dict, feature_files_list, process_pattern, scan_files_dict)
        WeblogicParse.__init__(self, ssh = init_info["ssh"], passwd = init_info["password"])
        # super(WeblogicScan, self).__init__(init_info, package_dict, feature_files_list, process_pattern, scan_files_dict)

    #获取更多实例的信息
    def get_instance_more_info(self, pid_dict):

        for pid in pid_dict:

            # 获取实例名
            line = [ ' '.join(line.split()[6:]) for line in self.processes if line.split()[0] == pid ][0]
            instance_name = re.search(r"-Dweblogic\.Name=(\S+)", line)
            if instance_name:
                pid_dict[pid]["base_info"]["instance_name"] = instance_name.group(1)

            #获取domain的信息
            path = self.exec_shell("readlink /proc/%s/cwd" %pid)[0]
            # result = re.search(r"/domains/([^/]+)", path)
            result = re.search(r"/user_projects/.*?/([^/]+)", path)
            if  result:
                pid_dict[pid]["domain"]["name"] = result.group(1)
            else:
                pid_dict[pid]["domain"]["name"] = path.split("/")[-1]

        return pid_dict

    def get_files_info(self, pid_dict, scan_files_dict):
        """
        根据安装路径，获取其他文件的绝对路径
        weblogic需要重写该方法，因为需要进一步判断，是否在相应域目录下
        如果有多个域的话，找出其他域中的文件是没有意义的
        """
        for pid in pid_dict:
            pid_dict[pid]["file"] = {}
            if "package_manager" in pid_dict[pid]["base_info"]["install_location"]:
                for type in scan_files_dict:
                    pid_dict[pid]["file"][type] = []
                    for item in scan_files_dict[type]:
                        pid_dict[pid]["file"][type].append(item["path"])
            else:
                for type in scan_files_dict:
                    pid_dict[pid]["file"][type] = []
                    for item in scan_files_dict[type]:
                        #替换file pattern中的变量
                        item["pattern"] = item["pattern"].replace("<DOMAIN>", pid_dict[pid]["domain"]["name"])

                        path_list = self.find_file(pid_dict[pid]["base_info"]["install_location"], item["pattern"])
                        for path in path_list:
                            if get_dir(path, item["dir_depth"]) and self.check_file_attribute(path, item["attribute"]):
                                if type != "version_file":
                                    if pid_dict[pid].get("domain") and pid_dict[pid]["domain"]["name"] in path:
                                        pid_dict[pid]["file"][type].append(path)
                                else:
                                    pid_dict[pid]["file"][type].append(path)

                    #如果在install_location中找不到，则在cwd中继续寻找
                    if not pid_dict[pid]["file"][type] and pid_dict[pid]["base_info"]["install_location"] not in pid_dict[pid]["base_info"]["cwd"]  and len(pid_dict[pid]["base_info"]["cwd"].split("/")) > 2:
                        for item in scan_files_dict[type]:
                            # 替换file pattern中的变量
                            item["pattern"] = item["pattern"].replace("<DOMAIN>", pid_dict[pid]["domain"]["name"])

                            path_list = self.find_file(pid_dict[pid]["base_info"]["cwd"], item["pattern"])
                            for path in path_list:
                                if get_dir(path, item["dir_depth"]) and self.check_file_attribute(path, item["attribute"]):
                                    if type != "version_file":
                                        if pid_dict[pid].get("domain") and pid_dict[pid]["domain"]["name"] in path:
                                            pid_dict[pid]["file"][type].append(path)
                                    else:
                                        pid_dict[pid]["file"][type].append(path)

        return pid_dict

    #获取版本信息
    def get_version(self, pid_dict):
        for pid in pid_dict:
            command = "java -cp %s weblogic.version | grep -i 'weblogic server' | awk '{print $3}'" %pid_dict[pid]["file"]["version_file"][0]
            version = self.exec_shell(command)[0]
            pid_dict[pid]["base_info"]["software_version"] = version

        return pid_dict

    #获取集群信息
    def get_cluster_info(self, pid_dict):

        conf_file_dict = {}
        #找出配置文件相同的所有实例
        for pid in pid_dict:
            if pid_dict[pid]["file"]["conf_file"]:
                if not conf_file_dict.get(pid_dict[pid]["file"]["conf_file"][0]):
                    conf_file_dict[pid_dict[pid]["file"]["conf_file"][0]] = {}
                conf_file_dict[pid_dict[pid]["file"]["conf_file"][0]][pid] = pid_dict[pid]

        # 如果实例是同一个配置文件只要解析一次
        for conf_file in conf_file_dict:
            #返回一个集群的列表，因为一个域中，可能有多个集群
            result = self.parse_weblogic(conf_file)
            for pid in conf_file_dict[conf_file]:

                pid_dict[pid]["domain"] = result["domain"]

                #获取实例的数据源信息
                for targets, datasource in result["domain"]["datasource"].items():
                    if pid_dict[pid]["base_info"]["instance_name"] in targets.split(","):
                        pid_dict[pid]["datasource"].append(datasource)

                # 获取admin server的ip+port
                line = [' '.join(line.split()[6:]) for line in self.processes if line.split()[0] == pid][0]
                admin_address = re.search(r"-Dweblogic.management.server=.*?(%s:[0-9]+)" %global_var.ip_pattern, line)

                if admin_address:
                    for member in pid_dict[pid]["domain"]["member"]:
                        if member["role"] == "admin":
                            member["listen"] = [admin_address.group(1)]

                    # 生成cluster的uuid，生成规则：
                    # cluster名+admin_server的ip+port
                    for cluster in result["cluster"]:

                        #判断该实例是否在该集群中
                        # 如果在，需要标识出，该实例的状态
                        in_cluster = False
                        for server in cluster["instance"]:
                            if server["listen"] and server["listen"][0] in pid_dict[pid]["base_info"]["listen"]:
                                in_cluster = True
                                server["status"] = "UP"

                        if in_cluster:
                            # 生成uuid
                            cluster["uuid"] = hashlib.md5((cluster["name"] + admin_address.group(1)).encode()).hexdigest()
                            pid_dict[pid]["cluster"] = [cluster]
                            break

                        else:
                            pid_dict[pid]["cluster"] = []

                #如果cluster没有uuid，则该集群不存在
                else:
                    pid_dict[pid]["cluster"] = []

        return pid_dict

    # 对所有信息进行整合
    def integrate_info(self, pid_dict):
        """
        根据ip和port信息，进行以下几个方面的信息整合：
            1.更新实例的名称
            2.根据集群信息中的ip和port，更新实例的ip+port
            3.更新集群信息中各个成员的状态
        """

        for pid in pid_dict:

            for server in pid_dict[pid]["domain"].get("member", []):
                if server["role"] == "admin" and server["name"] == pid_dict[pid]["base_info"]["instance_name"]:
                    server["listen"] = pid_dict[pid]["base_info"]["listen"]
                    server["status"] = "UP"
                elif server["listen"] and server["listen"][0] in pid_dict[pid]["base_info"]["listen"]:
                    pid_dict[pid]["base_info"]["instance_name"] = server["name"]
                    pid_dict[pid]["base_info"]["listen"] = server["listen"]
                    server["status"] = "UP"

        return pid_dict