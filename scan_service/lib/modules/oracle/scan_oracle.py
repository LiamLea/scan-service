from scan_service.lib.common import BaseScan
import re
from scan_service.lib.modules.oracle.parse_oracle import OracleParse
from scan_service.lib.utils import get_dir
import hashlib

class OracleScan(BaseScan, OracleParse):

    def __init__(self, init_info):

        package_dict = {
            "name": "oracle",
            "pattern": r"^oracle-server-[0-9.]+"
        }

        feature_files_list = [
            {
                "name": "oracle",
                "pattern": r"^((?!grid).)*bin/oracle$",
                "dir_depth": 5,
                "attribute": "x"
            },
        ]

        process_pattern = r"pmon"

        scan_files_dict = {
            "version_file": [
                {
                    "name": "tnsping",
                    "pattern": r".*bin/tnsping$",
                    "dir_depth": 2,
                    "attribute": "x"
                }
            ],
            "log_file": [
                {
                    "name": "log",
                    "pattern": r".*alert_\S+\.log$",
                    "dir_depth": 4,
                    "attribute": "f"
                }
            ],
            "conf_file": [
                {
                    "name": "listener.ora",
                    "pattern": r".*admin/listener.ora$",
                    "dir_depth": 5,
                    "attribute": "f"
                }
            ]
        }

        """
        用于存储集群的安装目录
        该目录是根据tnslsnr进程探测出来的
        """
        self.grid_install_location = ""

        BaseScan.__init__(self, init_info, package_dict, feature_files_list, process_pattern, scan_files_dict)
        OracleParse.__init__(self, init_info["ssh"], init_info["password"])

    def get_tnslsnr_instance(self):
        package_dict = {
            "name": "oracle",
            "pattern": r"^oracle-server-[0-9.]+"
        }

        feature_files_list = [
            {
                "name": "tnslsnr",
                "pattern": r".*bin/tnslsnr$",
                "dir_depth": 2,
                "attribute": "x"
            },
        ]

        process_pattern = r".*tnslsnr.*LISTENER.*"

        scan_files_dict = {
            "conf_file": [
                {
                    "name": "listener.ora",
                    "pattern": r".*admin/listener\.ora$",
                    "dir_depth": 2,
                    "attribute": "f"
                }
            ],
        }

        tnslsnr_scan = BaseScan(self.init_info, package_dict, feature_files_list, process_pattern, scan_files_dict)
        return tnslsnr_scan.instances

    #根据安装路径，获取其他文件的绝对路径

    def get_files_info(self, pid_dict, scan_files_dict):
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

                        #根据文件的类型，在不同的目录下搜索
                        if type != "conf_file":
                            path_list = self.find_file(pid_dict[pid]["base_info"]["install_location"], item["pattern"])
                        else:
                            path_list = self.find_file(self.grid_install_location, item["pattern"])

                        for path in path_list:
                            if get_dir(path, item["dir_depth"]) and self.check_file_attribute(path, item["attribute"]):
                                pid_dict[pid]["file"][type].append(path)

        return pid_dict

    def get_instance_more_info(self, pid_dict):
        for pid in pid_dict:
            command = [ ''.join(line.split()[6:]) for line in self.processes if pid == line.split()[0] ][0]
            match = re.search("ora_pmon_(\S+)", command)
            if match:
                pid_dict[pid]["base_info"]["instance_name"] = match.group(1)

        """
        扫描tnslsnr实例
        得到oracle监听的端口和集群的安装目录（如果不是集群，得到的到oracle的安装目录）
        """
        listening = []
        foregin_address = []
        connections = {}
        tnslsnr = self.get_tnslsnr_instance()
        listening_ports = []

        for pid in tnslsnr:
            listening.extend(tnslsnr[pid]["base_info"]["listen"])
            foregin_address.extend(tnslsnr[pid]["foreign_address"])
            connections.update(tnslsnr[pid]["connections"])
            self.grid_install_location = tnslsnr[pid]["base_info"]["install_location"]
            listening_ports.extend([sock.split(":")[-1] for sock in tnslsnr[pid]["base_info"]["listen"]])
        for pid in pid_dict:
            pid_dict[pid]["base_info"]["listen"] = list(set(listening))
            pid_dict[pid]["foreign_address"] = list(set(foregin_address))
            pid_dict[pid]["connections"] = connections

        self.listening_ports = sorted(list(set(listening_ports)))

        return pid_dict

    def get_version(self, pid_dict):
        for pid in pid_dict:
            result = self.exec_shell(pid_dict[pid]["file"]["version_file"][0])[0]
            match = re.search(r"Version *([0-9.]+) *", result)
            if match:
                pid_dict[pid]["base_info"]["software_version"] = match.group(1)

        return pid_dict

    def get_cluster_info(self, pid_dict):

        if pid_dict:
            cluster_info = self.parse_oracle(self.grid_install_location)

            if cluster_info:
                for pid in pid_dict:

                    #补充实例的监听端口
                    for instance in cluster_info.get("instance", []):
                        if instance["name"] == pid_dict[pid]["base_info"]["instance_name"]:
                            instance["listen"] = pid_dict[pid]["base_info"]["listen"]
                    cluster_info["uuid"] = hashlib.md5((cluster_info["service_ip"] + ''.join(self.listening_ports)).encode()).hexdigest()
                    pid_dict[pid]["cluster"] = [cluster_info]

        return pid_dict

    def integrate_info(self, pid_dict):

        return pid_dict