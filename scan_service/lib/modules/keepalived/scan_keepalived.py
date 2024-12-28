from scan_service.lib.common import BaseScan
from .parse_keepalived import KeepalivedParse

class KeepalivedScan(BaseScan, KeepalivedParse):

    def __init__(self, init_info):

        package_dict = {
            "name": "keepalived",
            "pattern": r"keepalived"
        }

        feature_files_list = [
            {
                "name": "keepalived",
                "pattern": r".*bin/keepalived$",
                "dir_depth": 2,
                "attribute": "x"
            },
        ]

        process_pattern = r"keepalived"

        scan_files_dict = {
            "version_file": [
                {
                    "name": "keepalived",
                    "pattern": r".*bin/keepalived$",
                    "dir_depth": 2,
                    "attribute": "x",
                    "package_manager": True
                }
            ],
            "conf_file": [
                {
                    "name": "keepalived.conf",
                    "pattern": r".*.*/keepalived\.conf$$",
                    "dir_depth": 2,
                    "attribute": "f",
                    "package_manager": True
                }
            ],
        }

        KeepalivedParse.__init__(self, ssh = init_info["ssh"], passwd = init_info["password"])
        BaseScan.__init__(self, init_info, package_dict, feature_files_list, process_pattern, scan_files_dict)

    def get_cluster_info(self, pid_dict):
        for pid in pid_dict:
            result = self.parse_keepalived(pid_dict[pid]["file"]["conf_file"][0])
            pid_dict[pid]["config"] = result["config"]

        return pid_dict
