from scan_service.lib.common import BaseScan
from .parse_mysql import MysqlParse
import re
import os
from scan_service.lib.utils import MyList

class MysqlScan(BaseScan, MysqlParse):

    def __init__(self, init_info):

        package_dict = {
            "name": "mysql",
            "pattern": r"^mysql-(community-)?server-[0-9]+"
        }

        feature_files_list = [
            {
                "name": "mysqld",
                "pattern": r".*bin/mysqld$",
                "dir_depth": 2,
                "attribute": "x"
            },
        ]

        process_pattern = "mysqld"

        scan_files_dict = {
            "version_file": [
                {
                    "name": "mysqld",
                    "pattern": r".*bin/mysqld$",
                    "dir_depth": 2,
                    "attribute": "x",
                    "package_manager": True
                },
            ],

            "conf_file": [
                {
                    "name": "my.cnf",
                    "pattern": r".*/my\.cnf$",
                    "dir_depth": 2,
                    "attribute": "f",
                    "package_manager": True
                }
            ],

            "log_file": []
        }

        BaseScan.__init__(self, init_info, package_dict, feature_files_list, process_pattern, scan_files_dict)
        MysqlParse.__init__(self, ssh = init_info["ssh"], passwd = init_info["password"])

    def get_version(self, pid_dict):
        for pid in pid_dict:
            version = ""
            command = "%s -V" %pid_dict[pid]["file"]["version_file"][0]
            result = self.exec_shell(command)

            for line in result:
                match = re.search(r"mysqld\s*Ver\s*([0-9.]+)", line)
                if match:
                    version = match.group(1)
            pid_dict[pid]["base_info"]["software_version"] = version

        return pid_dict

    def get_more_files_info(self, pid_dict):
        for pid in pid_dict:

            #获取工作目录（即数据目录）
            data_dir = self.exec_shell("readlink /proc/%s/cwd" %pid)[0]
            if not pid_dict[pid]["file"].get("data_file"):
                pid_dict[pid]["file"]["data_file"] = []
            pid_dict[pid]["file"]["data_file"].append(data_dir)

            #获取启动命令
            command = self.exec_shell(r"cat /proc/%s/cmdline  | tr '\0' ' '" %pid)[0]

            #获取params
            pid_dict[pid]["params"] = {}
            command = command + " --verbose --help 2>/dev/null | sed -n '/----/,/^$/p'"
            for line in self.exec_shell(command)[1:]:
                pid_dict[pid]["params"][line.split()[0]] = ''.join(MyList(line.split()[1:])).replace("(No default value)", "")

            #解析出basedir，并判断是否有配置文件
            base_dir = pid_dict[pid]["params"].get("base_dir", "/usr/")
            conf_file = self.exec_shell("ls %s/my.cnf" % base_dir)
            pid_dict[pid]["file"]["conf_file"].extend(conf_file)

            #获取genral log
            if pid_dict[pid]["params"].get("general-log", "") == "TRUE":
                log_file = pid_dict[pid]["params"].get("general-log-file", "")
                if log_file:
                    if log_file[0] != "/":
                        log_file = os.path.join(data_dir, log_file).replace("\\", "/")
                    pid_dict[pid]["file"]["log_file"].append(log_file)
            #获取error log
            log_file = pid_dict[pid]["params"].get("log-error", "")
            if log_file:
                if log_file == "stderr":
                    match = re.search("--log-error=(\S+)", ''.join(self.exec_shell("%s --print-defaults" %pid_dict[pid]["file"]["version_file"][0])))
                    if match:
                        log_file = match.group(1)
                if log_file[0] != "/":
                    log_file = os.path.join(data_dir, log_file).replace("\\", "/")
                pid_dict[pid]["file"]["log_file"].append(log_file)
            #获取slow log
            if pid_dict[pid]["params"].get("slow-query-log", "") == "TRUE":
                log_file = pid_dict[pid]["params"].get("slow-query-log-file", "")
                if log_file:
                    if log_file[0] != "/":
                        log_file = os.path.join(data_dir, log_file).replace("\\", "/")
                    pid_dict[pid]["file"]["log_file"].append(log_file)



        return pid_dict

    def get_cluster_info(self, pid_dict):

        for pid in pid_dict:

            if not pid_dict[pid]["file"]["data_file"]:
                pid_dict[pid]["cluster"] = []

            else:
                cluster_file = pid_dict[pid]["params"].get("master-info-file", "master.info")
                if cluster_file and cluster_file[0] != "/":
                    cluster_file = os.path.join(pid_dict[pid]["file"]["data_file"][0], cluster_file).replace("\\", "/")

                cluster = self.parse_mysql(cluster_file)
                if cluster:
                    instance = {
                        "role": "standby",
                        "listen": pid_dict[pid]["base_info"]["listen"],
                        "status": "UP",
                        "type": "mysql"
                    }
                    cluster["instance"].append(instance)
                    pid_dict[pid]["cluster"] = [cluster]

        return pid_dict