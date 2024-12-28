from scan_service.lib.common import BaseScan
import re
from .parse_postgresql import PGParse
import os
from scan_service.lib.utils import MyList

class PGScan(BaseScan, PGParse):
    """
    特征文件：
        可执行文件：postgresql
        配置文件：data目录
    """



    def __init__(self, init_info):
        package_dict = {
            "name": "pg",
            "pattern": r"^postgresql[0-9]+-server-[0-9.]+"
        }

        feature_files_list = [
            {
                "name": "postgres",
                "pattern": r".*bin/postgres",
                "dir_depth": 2,
                "attribute": "x"
            },
        ]

        process_pattern = r"postmaster|postgres"

        scan_files_dict = {
            "version_file": [
                {
                    "name": "postmaster",
                    "pattern": r".*bin/postmaster$",
                    "dir_depth": 2,
                    "attribute": "x",
                    "package_manager": True
                }
            ],
            "conf_file": [],
            "log_file": []
        }

        PGParse.__init__(self, ssh = init_info["ssh"], passwd = init_info["password"])
        BaseScan.__init__(self, init_info, package_dict, feature_files_list, process_pattern, scan_files_dict)

    def get_param_value(self, param, command, user = "postgres", type = "", data_dir = ""):
        new_command = 'su - %s -c "%s -C %s"' % (user, command, param)
        value = self.exec_shell(new_command)[0]
        if type == "file" and value and value[0] != "/":
            value = os.path.join(data_dir, value).replace("\\", "/")
        return value

    def get_more_files_info(self, pid_dict):

        for pid in pid_dict:
            #获取工作目录（即数据目录）
            data_dir = self.exec_shell("readlink /proc/%s/cwd" %pid)[0]
            if not pid_dict[pid]["file"].get("data_file"):
                pid_dict[pid]["file"]["data_file"] = []
            pid_dict[pid]["file"]["data_file"].append(data_dir)

            #获取启动命令
            command = self.exec_shell(r"cat /proc/%s/cmdline  | tr '\0' ' '" %pid)[0]
            # 获取配置文件
            for param in ["config_file", "hba_file", "ident_file"]:
                path = self.get_param_value(param, command, pid_dict[pid]["base_info"]["user_group"].split(":")[0], type = "file", data_dir = data_dir)
                if path:
                    pid_dict[pid]["file"]["conf_file"].append(path)
            #获取日志目录
            path = self.get_param_value("log_directory", command, pid_dict[pid]["base_info"]["user_group"].split(":")[0], type="file", data_dir=data_dir)
            if path:
                pid_dict[pid]["file"]["log_file"].append(path)
        return pid_dict

    def get_version(self, pid_dict):
        for pid in pid_dict:
            version = ""
            command = "%s -V" %pid_dict[pid]["file"]["version_file"][0]
            result = self.exec_shell(command)

            for line in result:
                match = re.search(r"postgres.*?([0-9.]+)", line)
                if match:
                    version = match.group(1)
            pid_dict[pid]["base_info"]["software_version"] = version

        return pid_dict

    def get_cluster_info(self, pid_dict):
        for pid in pid_dict:

            if not pid_dict[pid]["file"]["data_file"]:
                pid_dict[pid]["cluster"] = []

            else:
                cluster_file_list = []
                cluster_file_list.append(self.exec_shell("ls %s/recovery.conf" %pid_dict[pid]["file"]["data_file"][0])[0])
                cluster_file_list.append(MyList(pid_dict[pid]["file"]["conf_file"])[0])
                cluster = self.parse_pg(cluster_file_list)
                if cluster:
                    instance = {
                        "role": "standby",
                        "listen": pid_dict[pid]["base_info"]["listen"],
                        "status": "UP",
                        "type": "pg"
                    }
                    cluster["instance"].append(instance)
                    pid_dict[pid]["cluster"] = [cluster]

        return pid_dict
