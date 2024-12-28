from scan_service.lib.common import BaseScan
from scan_service.lib.modules.nginx.parse_nginx import NginxParse
import re
import hashlib

class NginxScan(BaseScan, NginxParse):

    def __init__(self, init_info):

        package_dict = {
            "name": "nginx",
            "pattern": r"^nginx-[0-9.]+"
        }

        feature_files_list = [
            {
                "name": "nginx",
                "pattern": r".*bin/nginx$",
                "dir_depth": 2,
                "attribute": "x"
            },
        ]

        process_pattern = r"nginx"

        scan_files_dict = {
            "version_file": [
                {
                    "name": "nginx",
                    "pattern": r".*bin/nginx$",
                    "dir_depth": 2,
                    "attribute": "x",
                    "package_manager": True
                }
            ],
            "conf_file": [
                {
                    "name": "nginx.conf",
                    "pattern": r".*((nginx)|(conf))/nginx\.conf$",
                    "dir_depth": 2,
                    "attribute": "f",
                    "package_manager": True
                }
            ],

            #通过分析配置文件获取日志文件的位置
            # "log_file": [
            #     {
            #         "name": "nginx",
            #         "pattern": r".*log/nginx",
            #         "dir_depth": 1,
            #         "attribute": "d"
            #     }
            # ]
        }

        NginxParse.__init__(self, ssh = init_info["ssh"], passwd = init_info["password"])
        BaseScan.__init__(self, init_info, package_dict, feature_files_list, process_pattern, scan_files_dict)

    def get_version(self, pid_dict):
        for pid in pid_dict:
            version = ""
            command = "%s -v" %pid_dict[pid]["file"]["version_file"][0]
            result = self.exec_shell(command, get_error = True)

            for line in result:
                match = re.search(r"nginx version: (.*)", line)
                if match:
                    version = match.group(1)
            pid_dict[pid]["base_info"]["software_version"] = version

        return pid_dict

    def get_cluster_info(self, pid_dict):
        for pid in pid_dict:
            result = self.parse_nginx(pid_dict[pid]["file"]["conf_file"][0], self.init_info, pid_dict[pid]["file"]["version_file"][0])
            pid_dict[pid]["config"] = result["cluster"]
            pid_dict[pid]["file"]["conf_file"].extend(result["conf_file"])
            pid_dict[pid]["file"]["log_file"] = result["log_file"]

            for cluster in pid_dict[pid]["config"]:
                item = {}
                item["role"] = "proxy"
                item["type"] = "nginx"
                item["listen"] = pid_dict[pid]["base_info"]["listen"]
                item["status"] = "UP"
                cluster["instance"].append(item)
                cluster["uuid"] = hashlib.md5((''.join(pid_dict[pid]["base_info"]["listen"]) + cluster["name"]).encode()).hexdigest()

            cluster = result["keepalived_cluster"]
            if cluster:
                item = {}
                item["listen"] = pid_dict[pid]["base_info"]["listen"]
                item["status"] = "UP"
                item["type"] = "nginx"
                if cluster["service_ip"] in self.get_local_ip():
                    item["role"] = "master"
                else:
                    item["role"] = "standby"
                cluster["instance"].append(item)

                listening_ports = [sock.split(":")[-1] for sock in pid_dict[pid]["base_info"]["listen"]]
                listening_ports = sorted(list(set(listening_ports)))
                cluster["uuid"] = hashlib.md5((cluster["service_ip"] + ''.join(listening_ports)).encode()).hexdigest()
                cluster["name"] = "nginx-%s" %cluster["uuid"]

                pid_dict[pid]["cluster"] = [ cluster ]

        return pid_dict
