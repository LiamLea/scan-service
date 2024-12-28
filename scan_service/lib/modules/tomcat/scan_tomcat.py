from scan_service.lib.common import JavaScan
from .parse_tomcat import TomcatParse
import re

class TomcatScan(JavaScan, TomcatParse):

    # package_dict = {
    #     "name": "tomcat",
    #     "pattern": r"^tomcat.(server.)?[0-9.]*"
    # }
    #
    # feature_files_dict = {
    #     "exec_file": {
    #         "name": "catalina.sh",
    #         "pattern": r".*bin/catalina\.sh$",
    #         "dir_depth": 2
    #     },
    #     "conf_file": {
    #         "name": "server.xml",
    #         "pattern": r".*conf/server\.xml$",
    #         "dir_depth": 2
    #     }
    # }

    def __init__(self, init_info):
        package_dict = {
            "name": "tomcat",
            "pattern": r"^tomcat.(server.)?[0-9.]*"
        }

        feature_files_list = [
            {
                "name": "catalina.jar",
                "pattern": r"(.*lib/catalina.jar$)",
                "dir_depth": 2,
                "attribute": "f"
            },
        ]

        process_pattern = r"tomcat"

        scan_files_dict = {
            "version_file": [
                {
                    "name": "catalina.sh",
                    "pattern": r"(.*bin/catalina.sh)",
                    "dir_depth": 2,
                    "attribute": "x"
                }
            ],
            "conf_file": [
                {
                    "name": "server.xml",
                    "pattern": r".*conf/server\.xml$",
                    "dir_depth": 2,
                    "attribute": "f"
                },
                {
                    "name": "context.xml",
                    "pattern": r".*conf/context\.xml$",
                    "dir_depth": 2,
                    "attribute": "f"
                }
            ]
        }

        TomcatParse.__init__(self, ssh=init_info["ssh"], passwd=init_info["password"])
        JavaScan.__init__(self, init_info, package_dict, feature_files_list, process_pattern, scan_files_dict)

    def get_version(self, pid_dict):
        for pid in pid_dict:
            version = ""
            if pid_dict[pid]["file"]["version_file"]:
                command = "%s version" %pid_dict[pid]["file"]["version_file"][0]
                result = self.exec_shell(command)

                for line in result:
                    match = re.search("server +version: *(.*)", line, re.IGNORECASE)
                    if match:
                        version = match.group(1)

            pid_dict[pid]["base_info"]["software_version"] = version

        return pid_dict

    def get_cluster_info(self, pid_dict):
        for pid in pid_dict:
            result = self.parse_tomcat(pid_dict[pid]["file"]["conf_file"])
            pid_dict[pid]["datasource"] = result["datasource"]

        return pid_dict