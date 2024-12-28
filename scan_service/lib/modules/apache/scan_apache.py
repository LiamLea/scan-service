from scan_service.lib.common import BaseScan
from scan_service.lib.modules.apache.parse_apache import ApacheParse
import re
import hashlib

class ApacheScan(BaseScan, ApacheParse):

    def __init__(self, init_info):

        package_dict = {
            "name": "apache",
            "pattern": r"(^httpd-[0-9.]+)|(^apache2$)"
        }

        feature_files_list = [
            {
                "name": "httpd",
                "pattern": r"(.*bin/httpd$)|(.*bin/apache2$)",
                "dir_depth": 2,
                "attribute": "x"
            },
        ]

        process_pattern = r"httpd|apache2"

        scan_files_dict = {
            "version_file": [
                {
                    "name": "httpd",
                    "pattern": r"(.*bin/httpd$)|(.*bin/apache2ctl$)",
                    "dir_depth": 2,
                    "attribute": "x",
                    "package_manager": True
                }
            ],
            "conf_file": [
                {
                    "name": "httpd.conf",
                    "pattern": r"(.*conf/httpd\.conf$)|(.*/apache2\.conf$)",
                    "dir_depth": 2,
                    "attribute": "f",
                    "package_manager": True
                }
            ]
        }

        ApacheParse.__init__(self, ssh = init_info["ssh"], passwd = init_info["password"])
        BaseScan.__init__(self, init_info, package_dict, feature_files_list, process_pattern, scan_files_dict)

    def get_version(self, pid_dict):
        for pid in pid_dict:
            version = ""
            command = "%s -v" % pid_dict[pid]["file"]["version_file"][0]
            result = self.exec_shell(command)
            for line in result:
                match = re.search(r"Server *version: *(.*) ", line)
                if match:
                    version = match.group(1)
            pid_dict[pid]["base_info"]["software_version"] = version

        return pid_dict

    def get_cluster_info(self, pid_dict):
        for pid in pid_dict:
            result = self.parse_apache(pid_dict[pid]["file"]["conf_file"][0], pid_dict[pid]["file"]["version_file"][0])
            pid_dict[pid]["cluster"] = result["cluster"]
            pid_dict[pid]["file"]["conf_file"].extend(result["conf_file"])
            pid_dict[pid]["file"]["log_file"] = result["log_file"]

            for cluster in pid_dict[pid]["cluster"]:
                item = {}
                item["role"] = "proxy"
                item["type"] = "apache"
                item["listen"] = pid_dict[pid]["base_info"]["listen"]
                item["status"] = "UP"
                cluster["instance"].append(item)
                cluster["uuid"] = hashlib.md5(''.join(pid_dict[pid]["base_info"]["listen"]).encode()).hexdigest()

        return pid_dict