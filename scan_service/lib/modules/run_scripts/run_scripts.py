from scan_service.lib.utils import SSH
from scan_service.lib.utils import SHELL
from pathlib import Path
from scan_service.lib.framework import BusinessException
import os

class RunScripts(SHELL):
    def __init__(self, credential_info, tasks, id, sudo = "0"):
        self.id = id
        self.tasks = tasks
        self.sudo = int(sudo)
        ssh = SSH(credential_info["host"], credential_info["port"], credential_info["username"], credential_info["password"], request_sudo = self.sudo)
        SHELL.__init__(self, ssh = ssh, passwd = credential_info["password"])


    def start(self):
        ret  = []
        dir_name = ".tmp_%s" % self.id
        parent_path = Path(Path(__file__).parent.parent.parent.parent / dir_name)
        # self.ssh.put_file(str(parent_path / dir_name), "/tmp/%s" % dir_name)
        self.exec_shell("mkdir /tmp/%s" %dir_name)
        for task in self.tasks:
            src_file = str(parent_path/task["id"])
            dst_file = "/tmp/%s/%s" %(dir_name, task["id"])
            self.ssh.put_file(src_file, dst_file)
            self.exec_shell("chmod +x %s" %dst_file)
            result = self.exec_shell("%s %s" %(dst_file, task["script_args"]), get_dict = True)
            if not result:
                raise BusinessException("执行脚本时ssh连接异常")

            # 执行回滚脚本
            rollback_result = {}
            if int(result["return_code"]) != 0 and os.path.isfile(str(parent_path / str("rollback_" + task["id"]))):
                src_file = str(parent_path / str("rollback_" + task["id"]))
                dst_file = "/tmp/%s/rollback_%s" %(dir_name, task["id"])
                self.ssh.put_file(src_file, dst_file)
                self.exec_shell("chmod +x %s" % dst_file)
                rollback_result = self.exec_shell("%s %s" %(dst_file, task["rollback_args"]), get_dict=True)

            ret.append(
                {
                    "id": task["id"],
                    "return_code": result["return_code"],
                    "stdout": result["stdout"],
                    "stderr": result["stderr"],
                    "rollback": {
                        "return_code": rollback_result.get("return_code", ""),
                        "stdout": rollback_result.get("stdout", ""),
                        "stderr": rollback_result.get("stderr", ""),
                    }
                }
            )
        self.exec_shell("rm -rf /tmp/%s" %dir_name)
        return ret
