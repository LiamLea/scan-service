import time
import re
import hashlib
from scan_service.lib.common import ScanViaSSH
from scan_service.lib.utils import size
from scan_service.lib.utils import MyList
from scan_service.lib.utils import kv_to_dict
from scan_service.lib.utils import string_to_bytes
from scan_service.lib.utils import get_speed_type
from scan_service.lib.utils import version_format
import datetime
import uuid
from scan_service.lib.vars import global_var
from uuid import UUID
from scan_service.lib.framework import BusinessException

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


# def kv_to_dict(kv_list):
#     ret = {}
#
#     for line in kv_list:
#         ret[line.split("=")[0].strip()] = line.split("=")[1].strip()
#
#     return ret

class EsxiScan(ScanViaSSH):
    def __init__(self, init_info):
        super(EsxiScan, self).__init__(init_info)
        self.sysip = ""
        self.sysip_mask = ""
        self.sysip_mac = ""
        self.sys_ipv6 = ""
        self.main_interface = ""

        self.disk_number = 0

        self.mapping = {
            "base_info": {
                "memory_available": "",
                "memory_capacity": "",
                "os_version": "",
                "storage_available": "",
                "storage_capacity": ""
            },
            "system": {
                "memory": {
                    "Free": "",
                    "Total": ""
                }
            },
            "volume": [],
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
            ret = {"total": 0, "available": 0}
            result = self.exec_shell("esxcli --formatter=keyvalue storage core device list")
            for line in result:
                if "DeviceType.string=Direct-Access" in line:
                    self.disk_number += 1
                elif "ScsiDevice.Size.integer" in line:
                    ret["total"] += int(line.split("=")[1].strip())

            result = self.exec_shell("df -k | awk '{print $4}'")[1:]
            for line in result:
                ret["available"] += int(line)
            return ret

        hard_info = kv_to_dict(self.exec_shell("esxcli  --formatter=keyvalue hardware platform get"))
        system_info = kv_to_dict(self.exec_shell("esxcli --formatter=keyvalue system version get"))
        disk_info = get_disk_info()

        ret = {}

        serial_number = hard_info.get("PlatformGet.SerialNumber.string", "")
        # if "empty" in serial_number.lower() or "unkown" in serial_number.lower():
        #     serial_number = self.host_uuid
        ret["serial_number"] = serial_number

        ret["manufacturer"] = hard_info.get("PlatformGet.VendorName.string", "")
        ret["model"] = hard_info.get("PlatformGet.ProductName.string", "")
        ret["architecture"] = self.exec_shell("uname -m")[0]
        ret["os_type"] = "ESXi"
        ret["os_version"] = system_info.get("VersionGet.Version.string", "")
        storage_capacity = disk_info["total"] * 1024 * 1024
        storage_available = disk_info["available"] * 1024
        ret["storage_capacity"] = size(storage_capacity)
        ret["storage_available"] = size(storage_available)
        memory_capacity = int(kv_to_dict(self.exec_shell("esxcli --formatter=keyvalue hardware memory get")).get(
            "Memory.PhysicalMemory.integer", "0"))
        memory_available = string_to_bytes(self.exec_shell("vsish -e get /memory/comprehensive | grep Free")[0].split(":")[1])
        ret["memory_capacity"] = size(memory_capacity)
        ret["memory_available"] = size(memory_available)
        ret["status"] = "UP"

        self.mapping["base_info"]["storage_capacity"] = storage_capacity
        self.mapping["base_info"]["storage_available"] = storage_available
        self.mapping["base_info"]["memory_capacity"] = memory_capacity
        self.mapping["base_info"]["memory_available"] = memory_available
        self.mapping["base_info"]["os_version"] = version_format(ret["os_version"])

        return ret

    def get_system_info(self):

        # 获取软件仓库的信息
        def get_package_info():

            ret = []
            for line in self.exec_shell("esxcli software profile get"):
                if "VIBs:" in line:
                    ret = [line.strip() for line in line.split(":", 1)[1].split(",") if line.strip() != ""]

            return ret

        # 获取cpu的信息
        def get_cpu_info():
            ret = {}
            result = self.exec_shell("esxcli hardware cpu global get")
            if len(result) > 1:
                for line in result:
                    ret[line.split(":")[0].strip()] = MyList(line.split(":"))[1].strip()
            else:
                result = self.exec_shell("esxcli --formatter=keyvalue hardware cpu list | grep PackageId | tail -1")
                match = re.search(r"structure\[(\d+)\].*?=(\d+)", result[0])
                ret["CPU Cores"] = "%s" %(int(match.group(1)) + 1)
                ret["CPU Packages"] = "%s" %(int(match.group(2)) + 1)

            result = kv_to_dict(self.exec_shell("esxcli --formatter=keyvalue hardware cpu list | head -20"))
            ret["Brand"] = result["structure[0].Cpu.Brand.string"]
            ret["Core Speed"] = "%d MHZ" % (int(result["structure[0].Cpu.CoreSpeed.integer"]) / 1000000)
            ret["Core(s) per socket"] = "%s" %int((int(ret["CPU Cores"]) / int(ret["CPU Packages"])))
            ret["Model name"] = "%s Family %s model %s" %(ret["Brand"], result.get("structure[0].Cpu.Family.integer", ""), result.get("structure[0].Cpu.Model.integer", ""))
            return ret

        # 获取内存的信息
        def get_memory_info():
            ret = {}
            memory_info = kv_to_dict(self.exec_shell("esxcli --formatter=keyvalue hardware memory get"))
            if len(memory_info) > 1:
                total_size = int(memory_info.get("Memory.PhysicalMemory.integer", 0))
                nodes = int(memory_info.get("Memory.NUMANodeCount.integer", 0))
                total_pages = 0
                free_pages = 0
                for i in range(nodes):
                    for line in self.exec_shell("vsish -e get memory/nodeList/%s" % i):
                        if "Total" in line:
                            total_pages += int(line.split(":")[1])
                        elif "Free" in line:
                            free_pages += int(line.split(":")[1])
                page_size = int(total_size / total_pages)
                ret["Total"] = size(total_size)
                ret["Free"] = size(free_pages * page_size)

                self.mapping["system"]["memory"]["Total"] = self.mapping["hardware"]["memory"]["size"] ="%s" %total_size
                self.mapping["system"]["memory"]["Free"] = "%s" %(free_pages * page_size)

                return ret
            else:
                ret = {
                    "Total": "0",
                    "Free": "0"
                }
                return ret

        # 获取端口的信息
        def get_port_info():
            ret = {"tcp": [], "udp": []}
            result = self.exec_shell("esxcli network ip connection list")[2:]
            for line in result:
                temp_list = line.split()
                if temp_list[0] == "tcp" and temp_list[5] == "LISTEN":
                    ret["tcp"].append(temp_list[3].split(":")[-1])
                else:
                    ret["udp"].append(temp_list[3].split(":")[-1])
            ret["tcp"] = list(set(ret["tcp"]))
            ret["udp"] = list(set(ret["udp"]))

            return ret

        ret = {}

        result = self.exec_shell("uptime")[0]
        match = re.search(r".*?up\s+(\d+)\s+days.*?(\d+):(\d+):(\d+)", result)
        if match:
            d = int(match.group(1))
            h = int(match.group(2))
            m = int(match.group(3))
            s = int(match.group(4))
        else:
            d = h = m = s = 0

        daemon_services = self.exec_shell("systemctl list-unit-files | grep enabled | awk '{print $1}'")
        if not daemon_services:
            daemon_services = self.exec_shell("for i in `ls /etc/init.d/`;do if [ -x /etc/init.d/$i ];then echo $i;fi;done")

        ret["daemon"] = daemon_services
        ret["env"] = self.exec_shell("env")
        ret["shell"] = self.exec_shell("echo $SHELL")[0]
        # ret["uptime"] = "%s days %s hours %s minutes" % (d, h, m)
        ret["uptime"] = (datetime.datetime.now() - datetime.timedelta(days = d, hours = h, minutes = m, seconds = s)).strftime('%Y-%m-%d %H:%M:%S')
        ret["locale"] = self.exec_shell("echo $LANG")[0]
        ret["timezone"] = self.exec_shell('date +"%Z %z"')[0]
        ret["cpu"] = get_cpu_info()
        ret["memory"] = get_memory_info()
        ret["port"] = get_port_info()
        ret["software"] = get_package_info()

        return ret

    def get_volume_info(self):

        ret = []
        result = self.exec_shell("df -h")
        for line in result[1:]:
            if MyList(line.split())[1] != "overlay":
                item = {}
                item["type"] = MyList(line.split())[0]
                item["size"] = MyList(line.split())[1]
                item["used"] = MyList(line.split())[2]
                item["avail"] = MyList(line.split())[3]
                item["usage"] = MyList(line.split())[4]
                item["moun_point"] = MyList(line.split())[5]
                ret.append(item)

                self.mapping["volume"].append(
                    {
                        "avail": string_to_bytes(item["avail"]),
                        "size": string_to_bytes(item["size"]),
                        "used": string_to_bytes(item["used"])
                    }
                )
        return ret

    def get_security_info(self):

        def get_firewall_info():
            ret = []
            for line in self.exec_shell("esxcli network firewall ruleset rule list")[2:]:
                item = {}
                item["Ruleset"] = line.split()[0]
                item["Direction"] = line.split()[1]
                item["Protocol"] = line.split()[2]
                item["Port Type"] = line.split()[3]
                item["Port Begin"] = line.split()[4]
                item["Port End"] = line.split()[5]
                ret.append(item)

            return ret

        ret = {"firewall_rules": get_firewall_info()}

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

        def get_nic_info():
            ret = []
            for line in self.exec_shell("esxcfg-nics -l")[1:]:
                item = {}
                item["name"] = line.split()[0]
                item["status"] = line.split()[3]
                item["speed"] = re.search("\d+", line.split()[4]).group()
                item["duplex"] = line.split()[5]
                item["mac"] = line.split()[6]
                item["mtu"] = line.split()[7]
                ret.append(item)

            return ret

        def get_interface_info():
            ret = {"ip": [], "interface": []}
            inet_dict = kv_to_dict(self.exec_shell("esxcli --formatter=keyvalue network ip interface list"))
            i = 0
            while True:
                item = {}
                item["name"] = inet_dict.get("structure[%s].NetworkInterface.Name.string" %i, "")
                if not item["name"]:
                    break
                item["state"] = inet_dict.get("structure[%s].NetworkInterface.Enabled.boolean" %i).replace("true", "UP").replace("false", "down")
                item["mac_address"] = inet_dict.get("structure[%s].NetworkInterface.MACAddress.string" %i, "").upper()
                item["mtu"] = inet_dict.get("structure[%s].NetworkInterface.MTU.integer" %i, "")
                item["flags"] = ""
                item["inet"] = []
                item["inet6"] = []

                result = self.exec_shell("esxcli network ip interface ipv4 address list")[2:]
                if not result:
                    result = self.exec_shell("esxcli network ip interface ipv4 get")[2:]
                for line in result:
                    if item["name"] == line.split()[0]:
                        inet_item = {}
                        inet_item["ip"] = line.split()[1]
                        inet_item["netmask"] = line.split()[2]
                        inet_item["type"] = "real"
                        if item["inet"]:
                            inet_item["type"] = "vip"
                        item["inet"].append(inet_item)
                        ret["ip"].append({"ip": inet_item["ip"], "mask": inet_item["netmask"]})

                for line in self.exec_shell("esxcli network ip interface ipv6 address list")[2:]:
                    if item["name"] == line.split()[0]:
                        inet_item = {}
                        inet_item["ip"] = line.split()[1]
                        inet_item["netmask"] = line.split()[2]
                        inet_item["type"] = "real"
                        if item["inet"]:
                            inet_item["type"] = "vip"
                        item["inet6"].append(inet_item)

                ret["interface"].append(item)

                i += 1

            return ret

        def get_route_info():
            ret = {"gateway": [], "route": []}
            for line in self.exec_shell("esxcli network ip route ipv4 list")[2:]:
                item = {}
                if line.split()[0] == "default":
                    #获取主网卡的信息，即默认路由使用的网卡
                    self.main_interface = line.split()[3]

                    ret["gateway"].append(line.split()[2])
                    item["destination"] = "0.0.0.0"
                else:
                    item["destination"] = line.split()[0]
                item["mask"] = line.split()[1]
                item["gateway"] = line.split()[2]
                item["iface"] = line.split()[3]
                ret["route"].append(item)

            return ret

        ret = {
            "hostname": "",
            "nic": get_nic_info(),
            "ip": [],
            "gateway": [],
            "dns": [],
            "interface": [],
            "route": [],
            "ntp": get_ntp_info()
        }

        # 获取主机名
        ret["hostname"] = kv_to_dict(self.exec_shell("esxcli --formatter=keyvalue system hostname get")).get(
            "FullyQualifiedHostName.FullyQualifiedDomainName.string", "")

        interface_info = get_interface_info()
        # 获取本地ip地址
        ret["ip"] = interface_info["ip"]
        ret["interface"] = interface_info["interface"]

        route_info = get_route_info()
        # 获取网关信息
        ret["gateway"] = route_info["gateway"]
        ret["route"] = route_info["route"]

        #获取主ip和掩码
        for interface in interface_info["interface"]:
            if interface["name"] == self.main_interface:
                self.sysip = interface["inet"][0]["ip"]
                self.sysip_mask = interface["inet"][0]["netmask"]
                self.sysip_mac = interface["mac_address"]
                if interface["inet6"]:
                    self.sys_ipv6 = interface["inet6"][0]["ip"]

        # 获取dns信息
        dns = self.exec_shell("cat /etc/resolv.conf")
        for line in dns:
            if "#" not in line:
                ret["dns"].append(MyList(line.split())[1])

        return ret

    def get_virtual_type(self):
        ret = {"virtual": "", "virtual_type": ""}
        product = kv_to_dict(self.exec_shell("esxcli --formatter=keyvalue system version get")).get(
            "VersionGet.Product.string", "")
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
            item["group"] = temp[item["gid"]]
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
            capacity = 0
            slot_number = 0
            for line in self.exec_shell("smbiosDump  | sed -rn '/Physical Memory Array/,/^\s{2}\S/p' | grep -iE 'slots|size'"):
                if "slot" in line.lower():
                    slot_number += int(line.split(":")[1].strip())
                elif "size" in line.lower():
                    capacity += string_to_bytes(line.split(":")[1].strip())
            ret["slot_number"]  = slot_number
            ret["capacity"] = size(capacity)
            ret["type"] = re.search("\((.*)\)", self.exec_shell('smbiosDump | grep "Form Factor" | head -1')[0]).group(1)
            ret["number"] = self.exec_shell("smbiosDump  | sed -rn '/Memory Device/,/^\s{2}\S/p' | grep -i Size: | grep -v 'No' | wc -l")[0]

            self.mapping["hardware"]["memory"]["size"] = "%s" %capacity

            return ret

        def get_disk_info():
            ret = {
                "number": self.disk_number,
                "disks": []
            }

            disk_info = kv_to_dict(self.exec_shell("esxcli --formatter=keyvalue storage core device list"))
            for i in range(0, self.disk_number):
                if disk_info.get("structure[%s].ScsiDevice.DeviceType.string" %i, "") == "Direct-Access":
                    disk_size = int(disk_info.get("structure[%s].ScsiDevice.Size.integer" %i, 0)) * 1024 * 1024
                    item = {
                        "name": disk_info.get("structure[%s].ScsiDevice.Device.string" %i, ""),
                        "size": size(disk_size)
                    }
                    ret["disks"].append(item)

                    self.mapping["hardware"]["disk"]["disks"].append(
                        {
                            "size": "%s" %disk_size
                        }
                    )

            return ret

        usb_number = com_number = vga_number = hba_number = fan_number = 0

        connectors = ' '.join(self.exec_shell("smbiosDump | sed -rn '/Port Connector/,/^\s{2}[a-zA-OQ-Z]+/p'"))
        for connector in connectors.split("Port Connector"):
            if "USB" in connector:
                usb_number += 1
            elif "COM" in connector:
                com_number += 1
            elif "VGA" in connector:
                vga_number += 1
            elif "HBA" in connector:
                hba_number += 1
            elif "FAN" in connector:
                fan_number += 1

        ret = {
            "port": [],
            "port_number": "",
            "interface_number": "", #需要补充
            "usb_number": "%s" %usb_number,
            "com_number": "%s" %com_number,
            "vga_number": "%s" %vga_number,
            "hba_number": "%s" %hba_number,
            "power": "",
            "memory": get_memory_info(),
            "disk": get_disk_info()
        }

        return ret

    def get_vm_info(self):
        ret = {
            "number": 0,
            "vms": []
        }

        vm_info = self.exec_shell("esxcli --formatter=keyvalue vm process list  | grep UUID")
        match = re.search(r"structure\[(\d+)\]", vm_info[-1])
        if match:
            ret["number"] = int(match.group(1)) + 1
            vm_info = kv_to_dict(vm_info)
            for i in range(ret["number"]):

                if vm_info.get("structure[%s].VirtualMachine.UUID.string" % i):

                    sn = vm_info.get("structure[%s].VirtualMachine.UUID.string" % i)
                    l = sn.split("-")[0].split(" ")
                    sn = l[3] + l[2] + l[1] + l[0] + l[5] + l[4] + l[7] + l[6] + sn.split("-")[1]

                    item = {
                        "sn": "%s" % uuid.UUID(sn.replace(" ", ""))
                        # "sn": "VMware-%s" %vm_info.get("structure[%s].VirtualMachine.UUID.string" %i, "")
                    }
                    ret["vms"].append(item)

        return ret

    def format_output(self):
        base_info = self.get_base_info()
        system_info = self.get_system_info()
        volume_info = self.get_volume_info()
        security_info = self.get_security_info()
        net_info = self.get_net_info()
        virtual_type = self.get_virtual_type()
        user_group_info = self.get_usergroup_info()
        hardware_info = self.get_hardware_info()
        vm_info = self.get_vm_info()

        base_info["cpu_core_number"] = system_info["cpu"]["CPU Cores"]
        base_info["sysip"] = self.sysip
        base_info["sysip_mask"] = self.sysip_mask
        base_info["sysip_mac"] = self.sysip_mac
        base_info["sys_ipv6"] = self.sys_ipv6

        if virtual_type["virtual"] == "YES" or "empty" in base_info["serial_number"].lower() or "unknown" in base_info["serial_number"].lower() or "o.e.m" in base_info["serial_number"].lower() or not base_info["serial_number"].strip():
            base_info["serial_number"] = uuid = self.exec_shell("esxcli system uuid get")[0]
            if not global_var.uuid_match.search(uuid):
                if self.sysip_mac:
                    base_info["serial_number"] = uuid = "%s" %UUID(hashlib.md5(self.sysip_mac.encode()).hexdigest())
                else:
                    raise BusinessException("无法获取uuid，请检查esxcli命令是否有效")
        else:
            uuid = hashlib.md5(base_info["serial_number"].encode()).hexdigest()

        #补充内存信息
        hardware_info["memory"]["size"] = system_info["memory"]["Total"]
        #补充网卡信息
        hardware_info["port_number"] = hardware_info["interface_number"] = len(net_info["nic"])
        for nic in net_info["nic"]:
            item = {
                "name": nic["name"],
                "mac": nic["mac"],
                "ip": "",
                "type": "unknown",
                "bandwidth_type": "unknown"
            }

            item["bandwidth_type"] = get_speed_type(int(nic["speed"]))
            hardware_info["port"].append(item)

        data = {
            "os_type": "ESXi",
            "collect_time": time.strftime('%Y-%m-%d %H:%M:%S %a'),
            "uuid": uuid,
            "base_info": base_info,
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
            "scan_ip": self.scan_ip
        }
        return data
