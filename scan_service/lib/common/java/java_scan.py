from scan_service.lib.common import BaseScan
import os
import re
from scan_service.lib.utils import MyList

class JavaScan(BaseScan):
    def __init__(self, init_info, package_dict, feature_files_list, process_pattern, scan_files_dict):
        BaseScan.__init__(self, init_info, package_dict, feature_files_list, process_pattern, scan_files_dict)
        self.instances = self.add_jvm_info(self.instances.copy())

    def get_jvm_base_info(self, vmid, java_path, jinfo_file):
        ret = {}
        jvm_info_dict = {}
        for line in self.exec_shell("%s -sysprops %s" %(jinfo_file, vmid)):
            if "=" in line:
                jvm_info_dict[line.split("=", 1)[0].strip()] = line.split("=", 1)[1].strip()

        ret["java.version"] = jvm_info_dict.get("java.version", "")
        ret["java.home"] = jvm_info_dict.get("java.home", "")
        ret["java.vm.version"] = jvm_info_dict.get("java.vm.version", "")
        ret["java.vm.name"] = jvm_info_dict.get("java.vm.name", "")
        ret["user.dir"] = jvm_info_dict.get("user.dir", "")
        ret["user.timezone"] = jvm_info_dict.get("user.timezone", "")
        ret["sun.java.command"] = jvm_info_dict.get("sun.java.command", "")
        # ret["java.class.path"] = jvm_info_dict.get("java.class.path", "")

        if not jvm_info_dict:
            result = re.search(r".*(jre|jdk)", java_path)
            if result:
                ret["java.home"] = result.group()
            java_info = self.exec_shell("%s -version 2>&1" %java_path)
            ret["java.version"] = java_info[0].split("\"")[1]
            result = re.search(r"(.*)\s*\(build\s*(.*),.*", java_info[2])
            if result:
                ret["java.vm.name"] = result.group(1)
                ret["java.vm.version"] = result.group(2)

        return ret

    def get_jvm_flags(self, vmid, jinfo_file):
        ret = []
        jvm_flags = ""
        for line in self.exec_shell("%s -flags %s" %(jinfo_file, vmid)):
            if "VM flags" in line:
                jvm_flags = line.split(":", 1)[1].strip()
            elif "-XX" in line:
                jvm_flags = line.strip()

            ret = jvm_flags.split()

        return ret

    def get_jvm_parameters(self, vmid, jmap_file):
        ret = {}
        for line in self.exec_shell("%s -heap %s | sed -n '/Heap Configuration/,/^$/p'" %(jmap_file, vmid))[1:]:
            match = re.search(r"\((.*)\)", line.split("=", 1)[1])
            if match:
                ret[line.split("=", 1)[0].strip()] = match.group(1)
            else:
                ret[line.split("=", 1)[0].strip()] = line.split("=", 1)[1].strip()
        return ret

    def get_jvm_runtime(self, vmid, jstat_file):
        ret = {}
        result = self.exec_shell("%s -gcutil %s" %(jstat_file, vmid))[1]
        result_list = MyList(result.split())
        ret["S0 utilization"] = "%s %%" % result_list[0]
        ret["S1 utilization"] = "%s %%" % result_list[1]
        ret["Eden sapce utilization"] = "%s %%" % result_list[2]
        ret["Old space utilization"] = "%s %%" % result_list[3]
        ret["Metaspace utilization"] = "%s %%" % result_list[4]
        ret["Compressed class space utilization"] = "%s %%" % result_list[5]
        ret["Number of young generation GC events"] = result_list[6]
        ret["Young generation garbage collection time"] = "%s s" % result_list[7]
        ret["Number of full GC events"] = result_list[8]
        ret["Full garbage collection time"] = "%s s" % result_list[9]
        ret["Total garbage collection time"] = "%s s" % result_list[10]

        return ret

    def get_jvm_info(self, vmid, java_path):

        java_bin_path = java_path.rstrip("/java")
        jinfo_file = os.path.join(java_bin_path, "jinfo").replace("\\", "/")
        jinfo_file = jinfo_file if self.check_file_attribute(jinfo_file, "x") else "jinfo"

        jmap_file = os.path.join(java_bin_path, "jmap").replace("\\", "/")
        jmap_file = jmap_file if self.check_file_attribute(jmap_file, "x") else "jmap"

        jstat_file = os.path.join(java_bin_path, "jstat").replace("\\", "/")
        jstat_file = jstat_file if self.check_file_attribute(jmap_file, "x") else "jstat"

        ret = {
            "base_info": self.get_jvm_base_info(vmid, java_path, jinfo_file),
            "flags": self.get_jvm_flags(vmid, jinfo_file),
            "params": self.get_jvm_parameters(vmid, jmap_file),
            "runtime": self.get_jvm_runtime(vmid, jstat_file)
        }

        return ret


    #获取jvm的信息
    def add_jvm_info(self, pid_dict):
        for pid in pid_dict:
            java_path = self.exec_shell("readlink /proc/%s/exe" %pid)[0]
            if java_path.split("/")[-1] == "java":
                pid_dict[pid]["jvm"] = self.get_jvm_info(pid, java_path)
        return pid_dict

