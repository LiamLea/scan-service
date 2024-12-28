import hashlib
import time
import re
from scan_service.lib.utils import MyList
from scan_service.lib.utils import size
from scan_service.lib.utils import string_to_bytes
import datetime
from scan_service.lib.utils import parse_pid_relation
from scan_service.lib.common import ScanViaSSH
from scan_service.lib.vars import global_var

class AixScan(ScanViaSSH):
    def __init__(self, init_info):
        super(AixScan, self).__init__(init_info)

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
        # self.mapping = {
        #     "base_info": {
        #         "memory_capacity": "",
        #         "storage_capacity": ""
        #     },
        #     "system": {
        #         "memory": ""
        #     },
        #     "volume":
        # }

    def get_base_info(self):
        def get_disk_info():
            ret = {"total": 0}
            result = self.exec_shell("lscfg -pl hdisk*|grep '^[[::space::]]*hdis*'")
            for line in result:
                ret[line.split()[0]] = int(re.split('\(|\)', line)[-2].strip('MB')) * 1024
                ret["total"] += int(re.split('\(|\)', line)[-2].strip('MB')) * 1024
                return ret

        ret = {}
        ret["serial_number"] = self.exec_shell("prtconf | grep 'Serial Number' | awk -F\":\" '{print $2}'")[0]
        ret["os_type"] = "AIX"
        ret["os_version"] = self.exec_shell("oslevel")[0]
        ret["storage_capacity"] = size(get_disk_info()["total"])
        ret["memory_capacity"] = size(int(self.exec_shell("svmon")[1].split()[1]) * 4)
        ret["status"] = "UP"
        # ret["vendor"] = self.exec_shell("dmidecode -s system-manufacturer")[0]
        ret["manufacturer"] = "IBM"
        ret["model"] = self.exec_shell("prtconf | grep 'System Model:'")[0].split(":")[1]
        ret["architecture"] = self.exec_shell("prtconf | grep 'Kernel Type:'")[0].split(":")[1]
        return ret

    def get_kernel_info(self):
        ret = {}
        ret["version"] = self.exec_shell('oslevel -s')[0]
        ret["kernel"] = self.exec_shell('lsattr -El sys0|awk \'{print $1,$2}\'')

        self.mapping["kernel"]["version"] = ret["version"]
        return ret
    def get_system_info(self):

        # 获取进程信息
        def get_process_info():
            ret = []

            estab_sock = {}
            for line in self.exec_shell("netstat -aAn|grep 'ESTABLISHED'"):
                Addr = line.split()[0]
                Proto_tcp = re.search(r"tcp\d*", line.split()[1])
                Proto_udp = re.search(r"udp\d*", line.split()[1])
                tcp = Proto_tcp.group()
                # udp = Proto_udp.group()
                pid = self.exec_shell("rmsock %s tcpcb" % Addr)[8]

                estab_sock[pid] = []
                estab_sock[pid].append((
                    "%s:%s" % (
                        global_var.ip_match.search(line.split()[4]).group(), line.split()[4].split(":")[-1]),
                    "%s:%s" % (
                        global_var.ip_match.search(line.split()[5]).group(), line.split()[5].split(":")[-1])
                ))

            command = "ps -e -o pid,ppid,stime,time,user,group,comm"
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

                # 下面的内容用于分析进程的信息
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


        # 获取cpu的信息
        def get_cpu_info():
            ret = {}
            result = self.exec_shell("prtconf |grep Processor|grep -v '^[[:space:]]'|grep -v '^+'")
            for line in result:
                ret[MyList(line.split(":"))[0]] = MyList(line.split(":"))[1].strip()
            return ret

        # 获取内存的信息
        def get_memory_info():
            ret = {}
            result = self.exec_shell("svmon -G")[1]
            # 行转列
            ret["size"] = size(int(result.split()[1]) * 4)
            ret["inuse"] = size(int(result.split()[2]))
            ret["free"] = size(int(result.split()[3]))
            ret["pin"] = size(int(result.split()[4]))
            ret["virtual"] = size(int(result.split()[5]))
            ret["mmode"] = result.split()[6]

            self.mapping["system"]["memory"]["MemTotal"] = self.mapping["hardware"]["memory"]["size"] = int(result.split()[1]) * 4
            self.mapping["system"]["memory"]["MemUsed"] = result.split()[2]
            self.mapping["system"]["memory"]["MemFree"] = result.split()[3]
            self.mapping["system"]["memory"]["pin"] = result.split()[4]
            self.mapping["system"]["memory"]["virtual"] = result.split()[5]

            return ret




        # 获取端口的信息
        def get_port_info():
            ret = {"tcp": [], "udp": []}
            result_tcp = self.exec_shell("ss -tlnp")[1:]
            result_udp = self.exec_shell("ss -tlnp")[1:]
            for line in result_tcp:
                ret["tcp"].append(line.split()[3].split(":")[-1])
            for line in result_udp:
                ret["udp"].append(line.split()[3].split(":")[-1])
            ret["tcp"] = list(set(ret["tcp"]))
            ret["udp"] = list(set(ret["udp"]))

            return ret

        def get_log_info():
            ret = {"main_log": "", "auth_log": ""}

            # 获取主要的log的位置
            result = self.exec_shell("grep '^*' /etc/syslog.conf  /etc/syslog.d/*")
            for line in result:
                match = re.search(r"(/\S+)", line.split()[1])
                if match:
                    ret["main_log"] = match.group(1)

            # 获取auth log的位置
            result = self.exec_shell("grep '^auth' /etc/syslog.conf  /etc/syslog.d/*")
            for line in result:
                match = re.search(r"(/\S+)", line.split()[1])
                if match:
                    ret["auth_log"] = match.group(1)

            return ret

        ret = {}

        daemon_services = self.exec_shell("lssrc -a  | grep \"active\" | awk '{print $1}'")
        result = self.exec_shell("uptime")[0]
        match = re.search(r".*?up\s+(\d+)\s+days.*?(\d+):(\d+):(\d+)", result)
        if match:
            d = int(match.group(1))
            h = int(match.group(2))
            m = int(match.group(3))
            s = int(match.group(4))
        else:
            d = h = m = s = 0


        ret["daemon"] = daemon_services
        ret["process"] = get_process_info()
        ret["env"] = self.exec_shell("env")
        ret["shell"] = self.exec_shell("echo $SHELL")[0]
        # ret["update"] = repo_info["update"]
        # ret["repo"] = repo_info["repo"]
        ret["uptime"] = (datetime.datetime.now() - datetime.timedelta(days = d, hours = h, minutes = m, seconds = s)).strftime('%Y-%m-%d %H:%M:%S')
        ret["locale"] = self.exec_shell("echo $LANG")[0]
        ret["timezone"] = self.exec_shell("date +'%Z %z'")[0]
        # ret["file-max"] = self.exec_shell("cat /proc/sys/fs/file-max")[0]

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
        # ret["software"] = repo_info["software"]
        ret["syslog"] = get_log_info()

        return ret

    def get_volume_info(self):
        # 获取文件系统信息
        def get_filesystem_info():
            ret = []
            result = self.exec_shell("df -P")
            for line in result[1:]:
                if MyList(line.split())[0] != "/proc":
                    item = {}
                    item["name"] = MyList(line.split())[0]
                    # item["type"] = MyList(line.split())[1]
                    item["size"] = size(int(MyList(line.split())[1]))
                    item["used"] = size(int(MyList(line.split())[2]))
                    item["avail"] = size(int(MyList(line.split())[3]))
                    item["usage"] = MyList(line.split())[4]
                    item["moun_point"] = MyList(line.split())[5]
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
            vgs = self.exec_shell("lsvg")
            for vg in vgs:
                lv = self.exec_shell("lsvg -l %s" % vg)[2:]
                for line in lv:
                    item = {}
                    item["name"] = line.split()[0]
                    item["vg_name"] = vg
                    # item["size"] = line.split()[3]
                    item["mount"] = line.split()[-1]
                    ret["lv"].append(item)

                    lv_temp.append(line.split()[-1])
                    # lv_temp.append(line.split()[-2])

            # 获取vg的信息
            vg = self.exec_shell("lsvg")
            for line in vg:
                result = self.exec_shell("lsvg %s" % line)
                item = {}
                item["name"] = result[0].split(":")[1].strip().split()[0]
                item["size"] = size(int(result[2].split(":")[2].split("(")[1].strip(")").split()[0]))
                item["pp_size"] = size(int(result[1].split(":")[2].strip().split()[0]))
                item["total_pe"] = size(int(result[2].split(":")[2].split("(")[0].split()[0]))
                # item["name"] = self.exec_shell("lsvg rootvg")[0].split(":")[1]
                # item["size"] = self.exec_shell("lsvg rootvg")[2].split(":")[3].split("(")[1]
                # item["pp_size"] = self.exec_shell("lsvg rootvg")[1].split(":")[3]
                # item["total_pe"] = self.exec_shell("lsvg rootvg")[2].split(":")[3].split("(")[0]

                ret["vg"].append(item)
                self.mapping["volume"]["vg"].append(
                    {
                        "size": string_to_bytes(item["size"]),
                        "pp_size": string_to_bytes(item["pp_size"])
                    }
                )
            # 获取pv的信息
            pv = self.exec_shell("lspv | awk /active/'{print $1}'")
            for line in pv:
                result = self.exec_shell("lspv %s" % line)
                item = {}
                item["name"] = result[0].split(":")[1].strip().split()[0]
                item["vg_name"] = result[0].split(":")[2].strip()
                item["size"] = size(int(result[5].split("(")[1].split(")")[0].split()[0]))
                ret["pv"].append(item)
                self.mapping["volume"]["pv"].append(
                    {
                        "size": string_to_bytes(item["size"])
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
            ret = {"status": "stoped", "enabled": "false", "zone": []}

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
                temp_list = [i for i in line.split("  ") if i != ""]
                item["user"] = temp_list[0]
                item["latest"] = temp_list[-1]
                item["tty"] = temp_list[1] if "/" in temp_list[1] else ""
                item["from"] = temp_list[2] if re.search("^[0-9.]+$", temp_list[2]) else ""

                ret["log"].append(item)

            return ret

        ret = {"sshd": "", "firewalld": get_firewall_info(), "selinux": "", "sudo": [],
               "login_records": get_login_info()}

        ret["sshd"] = "enabled"

        try:
            ret["selinux"] = self.exec_shell("sestatus")[0].split()[-1]
        except IndexError:
            ret["selinux"] = "disabled"
        try:
            sudo_content = self.exec_shell("cat /etc/sudoers | grep -v ^#")
            for line in sudo_content:
                result = re.search(r"^([a-zA-Z0-9][^\s]*)\s+.*?=\(.*?\)", line)
                if result:
                    ret["sudo"].append(result.group(1))
            ret["sudo"] = list(set(ret["sudo"]))
        except IndexError:
            ret["sudo"] = "disabled"

        return ret

    def get_net_info(self):
        def get_ntp_info():
            ret = []
            try:
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
            except IndexError:
                ret["ntp"] = "disabled"
            return ret

        def get_snmp_info():
            ret = {"listening_socket": "", "enabled": "false"}
            result = self.exec_shell(
                "ps aux | grep snmpd | grep -v grep | awk '{print $2}'")
            if result:
                ret["listening_socket"] = result[0]
                ret["version"] = [self.exec_shell("ls -l /usr/sbin/snmpd*")[0].split(">")[1]]
            return ret

        ret = {"hostname": "", "ip": [], "gateway": [], "dns": [], "interface": [], "route": [], "ntp": get_ntp_info(),
               "snmp": get_snmp_info()}

        # 获取主机名
        ret["hostname"] = self.exec_shell("hostname")[0]

        # 获取本地ip地址
        ret["ip"] = []

        # 获取网关信息
        ret["gateway"] = []
        result = self.exec_shell("netstat -ar | awk /^default/'{print $2,$6}'")
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
        #command = r'/bin/bash -c echo "";a="";for i in `ls /sys/class/net`;do path=`readlink "/sys/class/net/$i"`;if [ ! `echo $path | grep virtual` ];then a="$i 1\n$a" ;else a="$a\n$i 0"; fi;done;echo -e $a'
        interfaces = self.exec_shell("lsdev -Cc if| grep -i available")

        for line in interfaces:
            interface = line.split()[0]
            item = {
                "name": interface,
                "type": "",
                "state": "",
                "mac_address": "",
                "mtu": "",
                # "flags": "",
                "inet": [],
                "inet6": []
            }

            result = self.exec_shell("netstat -in | grep %s" % interface)
            # base_pattern = r"(<.*?>).*?mtu\s+(\d+)\s+.*?state\s+(\w+).*?link\S+\s+([0-9a-fA-F:.]+)\s+.*"
            # base_result = re.search(base_pattern, result)
                # item["flags"] = ent.group(1)
            item["mtu"] = result[0].split()[1]
            inter_type = self.exec_shell("netstat -in | grep %s | grep Virtual" % interface)
            if inter_type:
                item["type"] = "Virtual"
            item["type"] = "physical"
            item["state"] = "active"
            item["mac_address"] = result[0].split()[3]
            inet_result = self.exec_shell("ifconfig %s | grep inet" % interface)
            inet_item = {}
            inet_item["ip"] = inet_result[0].split()[1]
            inet_item["netmask"] = inet_result[0].split()[3]
            inet_item["type"] = "real"
            item["inet"].append(inet_item)

            inet6_result = self.exec_shell("ifconfig %s | grep inet6" % interface)
            if inet6_result:
                inet6_item = {}
                inet6_item["ip"] = inet6_result[0].split()[1]
                try:
                    inet6_item["netmask"] = inet6_result[0].split()[3]
                except:
                    pass
                inet6_item["type"] = "real"
                item["inet6"].append(inet6_item)

            if interface == sys_interface:
                self.sysip = item["inet"][0]["ip"]
                self.sysip_mask = item["inet"][0]["netmask"]
                self.sysip_mac = item["mac_address"]
                if item["inet6"]:
                    self.sys_ipv6 = item["inet6"][0]["ip"]

            ret["interface"].append(item)

        # 获取路由信息
        routes_list = self.exec_shell("netstat -nr")[4:]
        for route in routes_list:
            item = {}
            item["destination"] = route.split()[0]
            item["gateway"] = route.split()[1]
            # item["mask"] = route.split()[2]
            item["iface"] = route.split()[5]
            ret["route"].append(item)

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
                "size": "",  # 需要补充
                # "capacity": "",
                # "type": "",
                # "slot_number": "",
            }

            ret["number"] = self.exec_shell('lscfg -vp|grep DIMM |wc -l')[0].strip()

            return ret

        def get_disk_info():
            ret = {
                "type": "",
                "number": "",
            }

            # result = self.exec_shell('dmidecode  -t connector 2>/dev/null | grep "External Reference Designator" | grep -i sata')
            # if result:
            #     ret["type"] = "SATA"
            #     ret["slot_number"] = "%s" %len(result)
            result = self.exec_shell("lsdev -Cc disk|grep -i sas")
            if result:
                ret["type"] = "SAS"
                ret["number"] = "%s" %len(result)
            return ret

        ret = {
            "port": [],
            "port_number": "",
            "interface_number": self.exec_shell("lsdev -Cc adapter | grep ent | wc -l")[0].strip(),
            "usb_number": self.exec_shell("lsdev -Cc adapter| grep usb | wc -l")[0].strip(),
            "hba_number": self.exec_shell("lsdev -Cc adapter | grep fcs | wc -l")[0].strip(),
            "memory": get_memory_info(),
            "disk": get_disk_info()
        }

        return ret

    def format_output(self):

        base_info = self.get_base_info()
        kernel_info = self.get_kernel_info()
        system_info = self.get_system_info()
        volume_info = self.get_volume_info()
        security_info = self.get_security_info()
        net_info = self.get_net_info()
        user_group_info = self.get_usergroup_info()
        hardware_info = self.get_hardware_info()

        # 补充base_info的信息
        base_info["serial_number"] = base_info["serial_number"]
        base_info["cpu_core_number"] = system_info["cpu"]["Number Of Processors"]
        base_info["sysip"] = self.sysip
        base_info["sysip_mask"] = self.sysip_mask
        base_info["sys_ipv6"] = self.sys_ipv6
        base_info["sysip_mac"] = self.sysip_mac

        uuid = hashlib.md5(base_info["serial_number"].encode()).hexdigest()
        # 补充内存总量的信息
        hardware_info["memory"]["size"] = base_info["memory_capacity"]

        data = {
            "os_type": "AIX",
            "collect_time": time.strftime('%Y-%m-%d %H:%M:%S %a'),
            "uuid": uuid,
            "base_info": base_info,
            "kernel": kernel_info,
            "system": system_info,
            "volume": volume_info,
            "security": security_info,
            "network": net_info,
            "user": user_group_info["user"],
            "group": user_group_info["group"],
            "hardware": hardware_info,
            "mapping": self.mapping,
            "scan_ip": self.scan_ip,
        }
        return data
