import time
import re
import ipaddress
from scan_service.lib.utils import MyList
from scan_service.lib.utils import size
from scan_service.lib.utils import string_to_bytes
from scan_service.lib.utils import kv_to_dict
from scan_service.lib.utils import get_speed_type
from scan_service.lib.utils import parse_pid_relation
from scan_service.lib.utils import version_format
from scan_service.lib.common import ScanViaSSH
from scan_service.lib.vars import global_var
import datetime

"""
该脚本利用ssh方式采集linux主机配置信息，并将结果存入指定kafka的指定topic
接收6个位置参数：
    <IP>                 主机的ip地址
    <PORT>               ssh的端口号
    <USERNAME>           用于ssh的用户名
    <PASSWD>             用于sshd的密码
    <KAFKA_SERVER>       kafka的地址(ip:port)
    <KAFKA_TOPIC>        kafka的topic
"""


class LinuxScan(ScanViaSSH):

    def __init__(self, init_info):
        super(LinuxScan, self).__init__(init_info)

        self.sysip = ""
        self.sysip_mask = ""
        self.sys_ipv6 = ""
        self.sysip_mac = ""

        self.mapping = {
            "base_info": {
                "memory_available": "",
                "memory_capacity": "",
                "storage_available": "",
                "storage_capacity": ""
            },
            "system": {
                "cpu": {
                    "L1d cache": "",
                    "L1i cache": "",
                    "L2 cache": "",
                    "L3 cache": ""
                },
                "memory": {
                    "MemAvail": "",
                    "MemFree": "",
                    "MemTotal": "",
                    "MemUsed": "",
                    "buff/cache": ""
                }
            },
            "kernel": {
                "version": ""
            },
            "volume": {
                "filesystem": [],
                "lv": [],
                "vg": [],
                "pv": []
            },
            "hardware": {
                "disk": {
                    "disks": []
                },
                "memory": {
                    "capacity": "",
                    "size": ""
                }
            }
        }

    def get_base_info(self):
        def get_disk_info():
            ret = {"total": 0}

            result = self.exec_shell("lsblk -arb")[1:]
            for line in result:
                if MyList(line.split())[5] == "disk":
                    ret[line.split()[0]] = int(line.split()[3])
                    ret["total"] += int(line.split()[3])

            return ret

        ret = {}
        disk_info = get_disk_info()
        mem_info = self.exec_shell("free -b")[1]
        serial_number = self.exec_shell("dmidecode -s system-serial-number")[0]
        if "empty" in serial_number.lower() or "unknown" in serial_number.lower() or "o.e.m" in serial_number.lower() or not serial_number.strip():
            serial_number = self.host_uuid
        ret["serial_number"] = serial_number
        ret["os_type"] = "Linux"
        ret["os_version"] = self.system_release
        ret["storage_capacity"] = size(disk_info["total"])
        ret["memory_capacity"] = size(int(mem_info.split()[1]))
        ret["memory_available"] = size(int(mem_info.split()[3]))
        ret["status"] = "UP"
        ret["manufacturer"] = self.exec_shell("dmidecode -s system-manufacturer")[0]
        ret["model"] = self.exec_shell("dmidecode -s system-product-name")[0]
        ret["architecture"] = self.exec_shell("uname -m")[0]

        self.mapping["base_info"]["storage_capacity"] = "%s" %disk_info["total"]
        self.mapping["base_info"]["memory_capacity"] = mem_info.split()[1]
        self.mapping["base_info"]["memory_available"] = mem_info.split()[3]
        return ret

    def get_kernel_info(self):
        ret = {}
        ret["version"] = self.exec_shell("uname -r")[0]
        ret["kernel"] = self.exec_shell('sysctl -a | grep -v -E "^net.ipv6|^kernel.sched_domain|^dev.cdrom"')
        ret["kernel"] = [item for item in ret["kernel"] if "sysctl:" not in item]
        # for line in result:
        #     ret[MyList(line.split("="))[0].strip()] = MyList(line.split("="))[1].strip()

        ret["loaded_module"] = self.exec_shell("lsmod | awk '{print $1}'")[1:]

        self.mapping["kernel"]["version"] = version_format(ret["version"])

        return ret

    def get_system_info(self):

        # 获取进程信息
        def get_process_info():
            ret = []
            # command = 'ps -o pid,stime,comm,%cpu,%mem ax | awk \'NR!=1{"readlink /proc/"$1"/cwd"|getline cwd;"readlink /proc/"$1"/root"|getline root;"ls /proc/"$1"/fd|wc -l"|getline aa;print $0,root,cwd,aa}\''
            # result = exec_shell(command)
            # for line in result:
            #     item = {}
            #     item["pid"] = MyList(line.split())[0]
            #     item["stime"] = MyList(line.split())[1]
            #     item["command"] = MyList(line.split())[2]
            #     item["cpu_utilizaion"] = MyList(line.split())[3]
            #     item["mem_utilization"] = MyList(line.split())[4]
            #     item["cwd"] = MyList(line.split())[5]
            #     item["root"] = MyList(line.split())[6]
            #     item["fd"] = MyList(line.split())[7]
            #     ret.append(item)

            estab_sock = {}
            for line in self.all_sockets:
                tmp_list = MyList(line.split())
                if tmp_list[1] == "ESTAB":
            # for line in self.exec_shell("ss -tuanp | grep ESTAB"):
                    try:
                        match = re.search(r"\d+", MyList(tmp_list[6].split(','))[1])
                        if match:
                            pid = match.group()
                            if not estab_sock.get(pid):
                                estab_sock[pid] = []
                            estab_sock[pid].append((
                                "%s:%s" % (global_var.ip_match.search(tmp_list[4]).group(), tmp_list[4].split(":")[-1]),
                                "%s:%s" % (global_var.ip_match.search(tmp_list[5]).group(), tmp_list[5].split(":")[-1])
                            ))
                    except (IndexError, AttributeError):
                        pass

            command = "ps -o pid,ppid,stime,time,user,group,comm ax | awk '$1!=2 && $2!=2{print}'"
            result = self.exec_shell(command)[1:]

            """
            用于存放进程间的关系
            {
                "<PID>": {
                    "ppid": "",
                    "child_pids": []
                }
            }
            """
            pid_dict = {}

            for line in result:

                #下面的内容用于分析进程的信息
                item = {}
                t_list = line.split()
                item["pid"] = t_list[0]
                item["ppid"] = t_list[1]
                item["stime"] = t_list[2]
                item["time"] = t_list[3]
                item["user"] = "%s:%s" % (t_list[4], t_list[5])
                item["program"] = t_list[6]

                item["local_address"] = []
                item["foreign_address"] = []
                if estab_sock.get(item["pid"]):
                    for sock in estab_sock[item["pid"]]:
                        item["local_address"].append(sock[0])
                        item["foreign_address"].append(sock[1])

                item["local_address"] = list(set(item["local_address"]))
                item["foreign_address"] = list(set(item["foreign_address"]))

                # ret.append(item)
                item["child_pids"] = []
                if item["pid"] == "1":
                    ret.append(item)
                else:
                    pid_dict[item["pid"]] = item

            new_dict = parse_pid_relation(pid_dict)
            for pid in new_dict:
                for c_pid in new_dict[pid]["child_pids"]:
                    pid_dict[pid]["local_address"].extend(pid_dict[c_pid]["local_address"])
                    pid_dict[pid]["foreign_address"].extend(pid_dict[c_pid]["foreign_address"])
                ret.append(new_dict[pid])

            return ret

        # 获取软件仓库的信息
        def get_repo_info():

            ret = {"update": [], "repo": [], "software": []}

            if "centos" in self.system_release.lower() or "red hat" in self.system_release.lower():

                # #获取可更新的软件的列表
                # ret["update"] = self.exec_shell("yum check-update -C -q 2>/dev/null | awk '{print $1}'")

                # 获取仓库的url列表
                url_list = self.exec_shell("yum repolist -C -v 2>/dev/null | grep Repo-baseurl")
                for url in url_list:
                    ret["repo"].append(url.split()[-1])

                ret["software"] = self.exec_shell("rpm -qa")
            else:
                # ret["update"] = self.exec_shell("apt-get --just-print upgrade 2>/dev/null | grep ^Inst | awk '{print $2}'")
                result = self.exec_shell('egrep -v "^#|^ *$" /etc/apt/sources.list /etc/apt/sources.list.d/*')
                for line in result:
                    url = re.search(r"http[^\s]+", line)
                    ret["repo"].append(url.group())
                ret["repo"] = list(set(ret["repo"]))

                ret["software"] = self.exec_shell("dpkg -l | grep ^ii | awk '{print $2}'")

            return ret

        # 获取cpu的信息
        def get_cpu_info():
            ret = {}
            result = self.exec_shell("lscpu")
            cpu_info = self.exec_shell("cat /proc/cpuinfo")
            for line in result:
                ret[MyList(line.split(":"))[0]] = MyList(line.split(":"))[1].strip()
            ret["CPU Threads"] = ret.get("CPU(s)", "")
            ret["CPU(s)"] = 0
            ret["Socket(s)"] = 0
            ret["Model name"] = "UNKNOWN"
            ret["CPU MHz"] = "UNKNOWN"
            for line in cpu_info:
                if "cpu cores" in line:
                    ret["CPU(s)"] += int(line.split(":")[-1].strip())
                if "processor" in line:
                    ret["Socket(s)"] += 1
                if "model name" in line:
                    ret["Model name"] = line.split(":")[-1].strip()
                if "cpu MHz" in line:
                    ret["CPU MHz"] = "%s MHz" %line.split(":")[-1].strip()

            result = self.exec_shell('top -bn 1 -i -c | grep "Cpu(s):"')[0]
            usage_pattern = r"([\d.]+)\D*?us.*?([\d.]+)\D*?sy.*?([\d.]+)\D*?id"
            match = re.search(usage_pattern, result)
            if match:
                ret["user_usage"] = "%s %%" %match.group(1)
                ret["system_usage"] = "%s %%" %match.group(2)
                ret["idle"] = "%s %%" %match.group(3)
            else:
                ret["user_usage"] = ret["system_usage"] = ret["idle"] = "UNKNOWN"

            self.mapping["system"]["cpu"]["L1d cache"] = string_to_bytes(ret["L1d cache"]) if ret.get("L1d cache") else ""
            self.mapping["system"]["cpu"]["L1i cache"] = string_to_bytes(ret["L1i cache"]) if ret.get("L1i cache") else ""
            self.mapping["system"]["cpu"]["L2 cache"] = string_to_bytes(ret["L2 cache"]) if ret.get("L2 cache") else ""
            self.mapping["system"]["cpu"]["L3 cache"] = string_to_bytes(ret["L3 cache"]) if ret.get("L3 cache") else ""

            return ret

        # 获取内存的信息
        def get_memory_info():
            ret = {}
            # result = self.exec_shell("cat /proc/meminfo")
            # for line in result:
            #     ret[MyList(line.split(":"))[0]] = MyList(line.split(":"))[1].strip()
            result = self.exec_shell("free -b")[1].split()
            ret["MemTotal"] = size(int(result[1]))
            ret["MemUsed"] = size(int(result[2]))
            ret["MemFree"] = size(int(result[3]))
            ret["buff/cache"] = size(int(result[-2]))
            ret["MemAvail"] = size(int(result[-1]))

            self.mapping["system"]["memory"]["MemTotal"] = self.mapping["hardware"]["memory"]["size"] = result[1]
            self.mapping["system"]["memory"]["MemUsed"] = result[2]
            self.mapping["system"]["memory"]["MemFree"] = result[3]
            self.mapping["system"]["memory"]["buff/cache"] = result[-2]
            self.mapping["system"]["memory"]["MemAvail"] = result[-1]

            return ret

        # 获取端口的信息
        def get_port_info():
            ret = {"tcp": [], "udp": []}
            for line in self.all_sockets:
                tmp_list = line.split()
                if tmp_list[1] == "LISTEN" and tmp_list[0] == "tcp":
                    ret["tcp"].append(tmp_list[4].split(":")[-1])
                elif tmp_list[0] == "udp":
                    ret["udp"].append(tmp_list[4].split(":")[-1])

            ret["tcp"] = list(set(ret["tcp"]))
            ret["udp"] = list(set(ret["udp"]))

            return ret

        def get_log_info():
            ret = {"main_log": "", "auth_log": ""}

            # 获取主要的log的位置
            result = self.exec_shell("grep '^*' /etc/rsyslog.conf  /etc/rsyslog.d/*")
            for line in result:
                match = re.search(r"(/\S+)", line.split()[1])
                if match:
                    ret["main_log"] = match.group(1)

            # 获取auth log的位置
            result = self.exec_shell("grep '^auth' /etc/rsyslog.conf  /etc/rsyslog.d/*")
            for line in result:
                match = re.search(r"(/\S+)", line.split()[1])
                if match:
                    ret["auth_log"] = match.group(1)

            return ret

        def get_jdk_info():
            ret = {
                "version": ""
            }
            result = self.exec_shell("java -version 2>&1 | grep -i version")[0]
            ret["version"] = MyList(result.split("\""))[1]
            return ret

        ret = {}

        repo_info = get_repo_info()

        daemon_services = self.exec_shell("systemctl list-unit-files 2>/dev/null | grep enabled | awk '{print $1}'")
        if not daemon_services:
            daemon_services = self.exec_shell(
                "echo '';for i in `ls /etc/init.d/`;do if [ -x /etc/init.d/$i ];then echo $i;fi;done")

        ret["daemon"] = daemon_services
        ret["process"] = get_process_info()
        ret["env"] = self.exec_shell("env")
        ret["shell"] = self.exec_shell("echo $SHELL")[0]
        ret["update"] = repo_info["update"]
        ret["repo"] = repo_info["repo"]
        # ret["uptime"] = seconds_format(float(self.exec_shell("cat /proc/uptime")[0].split()[0]))

        result = MyList(self.exec_shell("cat /proc/uptime")[0].split())[0]
        ret["uptime"] = (datetime.datetime.now() - datetime.timedelta(seconds = int(float(result)))).strftime('%Y-%m-%d %H:%M:%S') if result else ""
        ret["locale"] = self.exec_shell("echo $LANG")[0]
        ret["timezone"] = self.exec_shell("date +'%Z %z'")[0]
        ret["file-max"] = self.exec_shell("cat /proc/sys/fs/file-max")[0]

        open_files_limit = MyList(self.exec_shell("echo `ulimit -Sn` `ulimit -Hn`")[0].split())
        processes_limit = MyList(self.exec_shell("echo `ulimit -Su` `ulimit -Hu`")[0].split())
        ret["ulimit"] = {
            "open_file": {
                "soft": open_files_limit[0],
                "hard": open_files_limit[1]
            },
            "processes": {
                "soft": processes_limit[0],
                "hard": processes_limit[1]
            }
        }

        ret["cpu"] = get_cpu_info()
        ret["memory"] = get_memory_info()
        ret["port"] = get_port_info()
        ret["software"] = repo_info["software"]
        ret["syslog"] = get_log_info()
        ret["jdk"] = get_jdk_info()

        return ret

    def get_volume_info(self):
        # 获取文件系统信息
        def get_filesystem_info():
            ret = []
            result = self.exec_shell("df -hTP")
            self.storage_available = 0
            for line in result[1:]:
                if MyList(line.split())[1] not in global_var.except_filesystems :
                    item = {}
                    item["name"] = MyList(line.split())[0]
                    item["type"] = MyList(line.split())[1]
                    item["size"] = MyList(line.split())[2]
                    item["used"] = MyList(line.split())[3]
                    item["avail"] = MyList(line.split())[4]
                    self.storage_available += string_to_bytes(item["avail"])
                    item["usage"] = MyList(line.split())[5]
                    item["moun_point"] = MyList(line.split())[6]
                    item["lv"] = ""
                    ret.append(item)

                    self.mapping["volume"]["filesystem"].append(
                        {
                            "size": string_to_bytes(item["size"]),
                            "used": string_to_bytes(item["used"]),
                            "avail": string_to_bytes(item["avail"])
                        }
                    )
            return ret

        # 获取逻辑卷的信息
        def get_logic_volume_info():
            ret = {"lv": [], "vg": [], "pv": []}

            # 获取lv的信息
            result = self.exec_shell("lvs -o+lv_path,lv_dm_path")[1:]
            if not result:
                tmp_result = self.exec_shell("lvs -o+lv_path")[1:]
                tmp_dict = {}
                for line in self.exec_shell("for i in `ls /dev/mapper/ | awk '{print \"/dev/mapper/\"$0}'`;do echo $i `readlink -f $i`;done"):
                    tmp_dict[line.split()[1]] = line.split()[0]
                for line in tmp_result:
                    dm_path = tmp_dict.get(self.exec_shell("readlink -f %s" %line.split()[-1])[0], "-")
                    result.append(line + " " + dm_path)

                #     for line self.exec_shell("ls /dev/mapper/ | awk '{print}'")
            for line in result:
                item = {}
                item["name"] = line.split()[0]
                item["path"] = line.split()[-2]
                item["dm_path"] = line.split()[-1]
                item["vg_name"] = line.split()[1]
                item["size"] = line.split()[3]
                ret["lv"].append(item)

                lv_temp.append(line.split()[-1])
                lv_temp.append(line.split()[-2])

                self.mapping["volume"]["lv"].append(
                    {
                        "size": string_to_bytes(item["size"].lstrip("<"))
                    }
                )

            # 获取vg的信息
            result = self.exec_shell("vgs -o+vg_extent_size,vg_extent_count")[1:]
            for line in result:
                item = {}
                item["name"] = line.split()[0]
                item["size"] = line.split()[5]
                item["pe_size"] = line.split()[7]
                item["total_pe"] = line.split()[8]
                ret["vg"].append(item)

                self.mapping["volume"]["vg"].append(
                    {
                        "size": string_to_bytes(item["size"].lstrip("<")),
                        "pe_size": string_to_bytes(item["pe_size"])
                    }
                )

            # 获取pv的信息
            result = self.exec_shell("pvs")[1:]
            for line in result:
                item = {}
                item["name"] = line.split()[0]
                item["vg_name"] = line.split()[1]
                item["size"] = line.split()[4]
                ret["pv"].append(item)

                self.mapping["volume"]["pv"].append(
                    {
                        "size": string_to_bytes(item["size"].lstrip("<"))
                    }
                )

            return ret

        lv_temp = []
        ret = get_logic_volume_info()

        filesystem_info = get_filesystem_info()
        for filesystem in filesystem_info:
            if filesystem["name"] in lv_temp:
                filesystem["lv"] = filesystem["name"]

        ret["filesystem"] = filesystem_info

        return ret

    def get_security_info(self):

        def get_firewall_info():
            # 判断firewalld是否开启自启
            ret = {"status": "stoped", "enabled": "disabled", "zone": []}

            # 获取firewalld的规则
            result = self.exec_shell(
                "echo '';for i in `firewall-cmd --list-all-zones | awk '/^\S/{print $1}'`;do firewall-cmd --list-all --zone=$i | tr '\n' '=';echo '';done")
            if result:
                ret["status"] = "started"
                for line in result:
                    item = {}
                    temp_list = [i for i in line.split("=") if i.strip() != '']
                    item["zone"] = temp_list[0]

                    for rule in temp_list[1:]:
                        item[rule.split(":")[0].strip()] = MyList(rule.split(":"))[1].strip()
                    ret["zone"].append(item)

            return ret

        def get_login_info():
            ret = {"current": [], "log": []}

            result = self.exec_shell("who")
            for line in result:
                item = {}
                temp_list = line.split()
                item["user"] = temp_list[0]
                item["tty"] = temp_list[1]
                item["time"] = temp_list[2] + " " + temp_list[3]
                item["from"] = ""
                if "(" in temp_list[-1]:
                    item["from"] = re.search("\((.*)\)", temp_list[-1]).group(1)
                ret["current"].append(item)

            result = self.exec_shell("lastlog  | grep -v 'Never logged in'")

            for line in result[1:]:
                item = {}
                temp_list = line.split()
                item["user"] = temp_list[0]
                item["latest"] = ' '.join(temp_list[-6:])
                if len(temp_list) == 7:
                    item["tty"] = item["from"] = ""
                elif len(temp_list) == 8:
                    if "/" in temp_list[1] or "tty" in temp_list[1].lower():
                        item["tty"] = temp_list[1]
                    else:
                        item["from"] = temp_list[1]
                else:
                    item["tty"] = temp_list[1]
                    item["from"] = temp_list[2]

                ret["log"].append(item)

            return ret

        ret = {"sshd": "", "firewalld": get_firewall_info(), "selinux": "", "sudo": [],
               "login_records": get_login_info()}

        ret["sshd"] = "enabled"

        try:
            ret["selinux"] = self.exec_shell("sestatus")[0].split()[-1]
        except IndexError:
            ret["selinux"] = "disabled"

        sudo_content = self.exec_shell("cat /etc/sudoers | grep -v ^#")
        for line in sudo_content:
            result = re.search(r"^([a-zA-Z0-9][^\s]*)\s+.*?=\(.*?\)", line)
            if result:
                ret["sudo"].append(result.group(1))
        ret["sudo"] = list(set(ret["sudo"]))

        return ret

    def get_net_info(self):
        def get_ntp_info():
            ret = []
            result = self.exec_shell("ntpq -p")
            for line in result:
                item = {}
                if line[0] == r'*':
                    item["server"] = line.split()[0][1:]
                    item["status"] = "使用中"
                    item["offset"] = "%s ms" % line.split()[-2]
                    ret.append(item)
                elif line[0] == r'+':
                    item["server"] = line.split()[0][1:]
                    item["status"] = "就绪"
                    item["offset"] = "%s ms" % line.split()[-2]
                    ret.append(item)
            return ret

        def get_snmp_info():
            ret = {"listening_socket": "", "enabled": "false"}

            result = self.exec_shell("ps aux | grep snmpd | grep -v grep | awk '{print $2}'")

            if result and result[0]:
                for line in self.all_sockets:
                    tmp_list = MyList(line.split())
                    if tmp_list[0] == "udp" and result[0] in tmp_list[6]:
                        ret["listening_socket"] = tmp_list[4]
                        break
                ret["version"] = [line.split()[2] for line in self.exec_shell("grep ^group /etc/snmp/snmpd.conf")]
            return ret

        ret = {"hostname": "", "ip": [], "gateway": [], "dns": [], "interface": [], "route": [], "ntp": get_ntp_info(),
               "snmp": get_snmp_info()}

        # 获取主机名
        ret["hostname"] = self.exec_shell("hostname")[0]

        # 获取本地ip地址
        ret["ip"] = []

        # 获取网关信息
        ret["gateway"] = []
        result = self.exec_shell("ip r | grep default | awk '{print $3,$5}'")
        # 主网卡，默认路由的外出地址为主网卡
        sys_interface = result[0].split()[1]
        for line in result:
            ret["gateway"].append(line.split()[0])

        # 获取dns信息
        dns = self.exec_shell("cat /etc/resolv.conf")
        for line in dns:
            if "#" not in line:
                ret["dns"].append(MyList(line.split())[1])

        # 获取网卡信息，并对网卡进行排序，将真实的网卡放在列表的头部
        # command = '/bin/bash -c echo "";a="";for i in `ls /sys/class/net`;do path=`readlink "/sys/class/net/$i"`;if [ ! `echo $path | grep virtual` ];then a="$i $a" ;else a="$a $i"; fi;done;echo $a | tr " " "\n"'
        command = r'echo "";a="";for i in `ls /sys/class/net | grep -v lo`;do path=`readlink "/sys/class/net/$i"`;if [ ! `echo $path | grep virtual` ];then a="$i 1\n$a" ;else a="$a\n$i 0"; fi;done;echo -e $a'
        interfaces = self.exec_shell(command)

        flag_pattern = re.compile(r"<.*?>")
        mtu_pattern = re.compile(r"mtu\s+(\d+)")
        state_pattern = re.compile(r"state\s+(\w+)")
        ether_pattern = re.compile(r"link/ether\s+(%s)" % global_var.mac_pattern)
        inet_pattern = re.compile(r"inet\s+(%s(?:/[0-9]+)?)" % global_var.ip_pattern)

        for line in interfaces:
            interface = line.split()[0].strip()
            item = {
                "name": interface,
                "type": "physical" if line.split()[1].strip() == "1" else "virtual",
                "state": "",
                "mac_address": "",
                "mtu": "",
                "flags": "",
                "speed": "UNKNOWN",
                "inet": [],
                "inet6": []
            }

            result = ' '.join(self.exec_shell("ip addr show %s" % interface))

            flag_match = flag_pattern.search(result)
            mtu_match = mtu_pattern.search(result)
            state_match = state_pattern.search(result)
            ether_match = ether_pattern.search(result)
            item["flags"] = flag_match.group() if flag_match else ""
            item["mtu"] = mtu_match.group(1) if mtu_match else "1500"
            item["state"] = state_match.group(1) if state_match else "UNKNOWN"
            item["mac_address"] = ether_match.group(1) if ether_match else ""

            speed = self.exec_shell("ethtool %s | grep 'Speed:'" %interface)
            if speed:
                item["speed"] = speed[0].split(":")[1]

            inet_result = inet_pattern.findall(result)
            for inet in inet_result:
                inet_temp = {}
                if_temp = ipaddress.IPv4Interface(inet)
                inet_temp["ip"] = str(if_temp.ip)
                inet_temp["netmask"] = str(if_temp.netmask)
                if item["state"].lower() != "down":
                    ret["ip"].append({"ip": inet_temp["ip"], "mask": inet_temp["netmask"]})
                inet_temp["type"] = "vip"
                item["inet"].append(inet_temp)
            try:
                item["inet"][0]["type"] = "real"
            except IndexError:
                pass

            inet6_pattern = r"inet6\s+([0-9a-fA-F:]+/[0-9]+)"
            inet6_result = re.findall(inet6_pattern, result)
            for inet6 in inet6_result:
                inet6_temp = {}
                if_temp = ipaddress.IPv6Interface(inet6)
                inet6_temp["ip"] = str(if_temp.ip)
                inet6_temp["netmask"] = str(if_temp.netmask)
                inet6_temp["type"] = "vip"
                item["inet6"].append(inet6_temp)
            try:
                item["inet6"][0]["type"] = "real"
            except IndexError:
                pass

            if interface == sys_interface:
                self.sysip = item["inet"][0]["ip"]
                self.sysip_mask = item["inet"][0]["netmask"]
                self.sysip_mac = item["mac_address"]
                if item["inet6"]:
                    self.sys_ipv6 = item["inet6"][0]["ip"]

            ret["interface"].append(item)

        # 获取路由信息
        route_match = re.compile(r"(?:via\s*(\S+)\s*)?dev\s*(\S+)")
        routes_list = self.exec_shell("ip route")
        for route in routes_list:
            item = {}
            destination = route.split()[0]
            if destination == "default":
                item["destination"] = "0.0.0.0"
                item["mask"] = "0.0.0.0"
            elif global_var.ip_match.search(destination):
                inet = ipaddress.IPv4Interface(destination)
                item["destination"] = str(inet.ip)
                item["mask"] = str(inet.netmask)
            match = route_match.search(route)
            if match:
                item["gateway"] = match.group(1) if match.group(1) else "0.0.0.0"
                item["iface"] = match.group(2)
            ret["route"].append(item)

        # routes_list = self.exec_shell("route -n")[2:]
        # for route in routes_list:
        #     item = {}
        #     item["destination"] = route.split()[0]
        #     item["gateway"] = route.split()[1]
        #     item["mask"] = route.split()[2]
        #     item["iface"] = route.split()[-1]
        #     ret["route"].append(item)

        return ret

    def get_virtual_type(self):
        ret = {"virtual": "", "virtual_type": ""}
        product = self.exec_shell("dmidecode -s system-product-name")[0]
        if "virtual" in product.lower() or "openstack" in product.lower():
            ret["virtual"] = "YES"
            ret["virtual_type"] = product.split()[0]
        elif not product:
            ret["virtual"] = ""
            ret["virtual_type"] = ""
        else:
            ret["virtual"] = "NO"
            ret["virtual_type"] = ""
        return ret

    def get_usergroup_info(self):
        ret = {"user": [], "group": []}
        temp = {}
        result = self.exec_shell("cat /etc/group")
        for line in result:
            item = {}
            item["name"] = MyList(line.split(":"))[0]
            item["gid"] = MyList(line.split(":"))[2]
            temp[item["gid"]] = item["name"]
            ret["group"].append(item)

        result = self.exec_shell("cat /etc/passwd")
        for line in result:
            item = {}
            item["name"] = MyList(line.split(":"))[0]
            item["uid"] = MyList(line.split(":"))[2]
            item["gid"] = MyList(line.split(":"))[3]
            item["home_directory"] = MyList(line.split(":"))[5]
            item["login_shell"] = MyList(line.split(":"))[6]
            item["group"] = temp.get(item["gid"], "")
            item["passwd"] = ""
            ret["user"].append(item)

        return ret

    def get_hardware_info(self):
        def get_memory_info():
            ret = {
                "number": "",
                "size": "",         #需要补充
                "capacity": "",
                "type": "",
                "slot_number": "",
            }
            memory_dict = kv_to_dict(self.exec_shell("dmidecode -q -t 16 2>/dev/null")[1:], separator = ":")
            ret["capacity"] = memory_dict.get("Maximum Capacity", "")
            ret["slot_number"] = memory_dict.get("Number Of Devices", "")
            ret["type"] = MyList(self.exec_shell('dmidecode -t 17 2>/dev/null | grep "Form Factor:" | grep -v -i "unknown"')[0].split(":"))[1]
            ret["number"] = self.exec_shell('dmidecode -q -t 17 2>/dev/null| grep -i Size: | grep -v "No" | wc -l')[0]

            self.mapping["hardware"]["memory"]["capacity"] = string_to_bytes(ret["capacity"])

            return ret

        def get_disk_info():
            ret = {
                "number": 0,
                "disks": []
            }

            result = self.exec_shell("lsblk -ar")[1:]
            for line in result:
                if MyList(line.split())[5] == "disk":
                    item = {
                        "name": MyList(line.split())[0],
                        "size": MyList(line.split())[3],
                        "partitions": []
                    }
                    ret["disks"].append(item)

                    self.mapping["hardware"]["disk"]["disks"].append(
                        {
                            "size": string_to_bytes(item["size"])
                        }
                    )

                if MyList(line.split())[5] == "part":
                    ret["disks"][-1]["partitions"].append(MyList(line.split())[0])

            ret["number"] = len(ret["disks"])

            return ret

        def get_power_info():
            power_info = self.exec_shell('dmidecode -t 39 2>/dev/null | grep --color=never "Max Power Capacity:"')
            ret = {
                "number": "",
                "power": ""
            }

            ret["number"] = "%s" %len(power_info)
            ret["power"] = MyList(power_info[0].split(":"))[1].strip()
            return ret

        ret = {
            "port": [],
            "port_number": "",
            "interface_number": self.exec_shell('dmidecode -t connector 2>/dev/null| grep "External Reference Designator" | grep -Ei "lan|network" | wc -l')[0],
            "usb_number": self.exec_shell('dmidecode -t connector 2>/dev/null| grep "Internal Reference Designator" | grep -i usb | wc -l')[0],
            "com_number": self.exec_shell('dmidecode -t connector 2>/dev/null | grep "External Reference Designator" | grep -i com | wc -l')[0],
            "vga_number": self.exec_shell('dmidecode -t connector 2>/dev/null | grep "External Reference Designator" | grep -i vga | wc -l')[0],
            "hba_number": self.exec_shell('lspci -nn | grep -i hba | wc -l')[0],
            "power": get_power_info(),
            "memory": get_memory_info(),
            "disk": get_disk_info()
        }

        return ret

    def get_vm_info(self):
        ret = {
            "number": 0,
            "vms": []
        }
        uuid_match = re.compile("-uuid\s*([0-9a-fA-F-]+)")
        vm_info = self.exec_shell("ps aux | grep hypervisor")
        for line in vm_info:
            match = uuid_match.search(line)
            if match:
                item = {
                    "sn": "%s" %match.group(1)
                }
                ret["vms"].append(item)

            ret["number"] = len(ret["vms"])

        return ret

    def format_output(self):
        base_info = self.get_base_info()
        kernel_info = self.get_kernel_info()
        system_info = self.get_system_info()
        volume_info = self.get_volume_info()
        security_info = self.get_security_info()
        net_info = self.get_net_info()
        virtual_type = self.get_virtual_type()
        user_group_info = self.get_usergroup_info()
        hardware_info = self.get_hardware_info()
        vm_info = self.get_vm_info()

        if virtual_type["virtual"] == "YES":
            base_info["serial_number"] = self.exec_shell("dmidecode -s system-uuid")[0].lower()

        #补充base_info的信息
        base_info["cpu_core_number"] = system_info["cpu"]["CPU(s)"]
        base_info["sysip"] = self.sysip
        base_info["sysip_mask"] = self.sysip_mask
        base_info["sys_ipv6"] = self.sys_ipv6
        base_info["sysip_mac"] = self.sysip_mac
        base_info["storage_available"] = size(self.storage_available)
        self.mapping["base_info"]["storage_available"] = "%s" %self.storage_available

        #补充内存总量的信息
        hardware_info["memory"]["size"] = base_info["memory_capacity"]
        #补充网口的信息
        for interface in net_info["interface"]:
            if interface["type"] == "physical":
                item = {
                    "name": interface["name"],
                    "mac": interface["mac_address"],
                    "ip": "",
                    "type": "unknown",
                    "bandwidth_type": "unknown"
                }
                if interface["inet"]:
                    item["ip"] = interface["inet"][0].get("ip", "")

                speed = self.exec_shell("cat /sys/class/net/%s/speed" %item["name"])
                if speed:
                    item["bandwidth_type"] = get_speed_type(speed[0])
                    hardware_info["port"].append(item)
        hardware_info["port_number"] = "%s" %len(hardware_info["port"])

        for daemon in system_info["daemon"]:
            if "firewalld" in daemon:
                security_info["firewalld"]["enabled"] = "enabled"
            elif "snmpd" in daemon:
                net_info["snmp"]["enabled"] = "true"

        data = {
            "os_type": "Linux",
            "collect_time": time.strftime('%Y-%m-%d %H:%M:%S %a'),
            "uuid": self.host_uuid,
            "base_info": base_info,
            "kernel": kernel_info,
            "system": system_info,
            "volume": volume_info,
            "security": security_info,
            "network": net_info,
            "virtualization": virtual_type,
            "user": user_group_info["user"],
            "group": user_group_info["group"],
            "hardware": hardware_info,
            "virtual_machine": vm_info,
            "mapping": self.mapping,
            "scan_ip": self.scan_ip,
        }
        return data