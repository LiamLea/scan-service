from xml.dom import minidom
from scan_service.lib.common import ScanViaShell
import time
import os
import re


class NmapScan(ScanViaShell):
    def __init__(self, init_info):
        super(NmapScan, self).__init__(init_info)

    def run_nmap(self, command, filename, progress_file):
        if not os.path.isdir(os.path.dirname(filename)):
            try:
                os.makedirs(os.path.dirname(filename))
            except Exception:
                pass
        # if not os.path.isdir(os.path.dirname(progress_file)):
        #     os.makedirs(os.path.dirname(progress_file))
        command = command + " -oX " + filename + " --stats-every 5s > " + progress_file
        self.exec_shell(command)

    def parse_nmap(self, filename):
        """
        该函数用于解析nmap输出的xml文件
        解析结果包括以下三个方面：
            1.机器的ip地址（同网段内能够采集到mac地址）
            2.
       :param filename:
        :return:
        """
        ret = []
        with open(filename, 'r', encoding='utf8') as fobj:
            dom = minidom.parse(fobj)
            ret = []

            # 变量<host>标签
            for host in dom.getElementsByTagName("host"):
                item = {"os": [], "address": [], "ports": []}
                host_status = host.getElementsByTagName("status")[0].getAttribute("state")

                # 只统计up主机的信息
                if host_status != "down":

                    # 获取主机的相关地址（包括ip和mac）
                    for addr in host.getElementsByTagName("address"):
                        address_item = {}
                        address_item["addr"] = addr.getAttribute("addr")
                        address_item["addrtype"] = addr.getAttribute("addrtype")
                        item["address"].append(address_item)

                    # 获取主机操作系统的信息
                    for os in host.getElementsByTagName("osmatch"):
                        os_item = {}
                        os_item["name"] = os.getAttribute("name")
                        os_item["accuracy"] = os.getAttribute("accuracy")
                        if os_item["accuracy"] == "100":
                            os_item["type"] = os.getElementsByTagName("osclass")[0].getAttribute("type")
                            os_item["vendor"] = os.getElementsByTagName("osclass")[0].getAttribute("vendor")
                            os_item["osfamily"] = os.getElementsByTagName("osclass")[0].getAttribute("osfamily")
                            os_item["osgen"] = os.getElementsByTagName("osclass")[0].getAttribute("osgen")
                            item["os"].append(os_item)
                    if not item["os"] and host.getElementsByTagName("osmatch"):
                        os_item["name"] = host.getElementsByTagName("osmatch")[0].getAttribute("name")
                        os_item["type"] = host.getElementsByTagName("osclass")[0].getAttribute("type")
                        os_item["vendor"] = host.getElementsByTagName("osclass")[0].getAttribute("vendor")
                        os_item["osfamily"] = host.getElementsByTagName("osclass")[0].getAttribute("osfamily")
                        os_item["osgen"] = host.getElementsByTagName("osclass")[0].getAttribute("osgen")
                        os_item["accuracy"] = host.getElementsByTagName("osmatch")[0].getAttribute("accuracy")
                        item["os"].append(os_item)

                    try:
                        ports = host.getElementsByTagName("ports")[0].getElementsByTagName("port")
                    except IndexError:
                        ports = []

                    # 获取主机的端口信息
                    for port in ports:
                        port_item = {}
                        port_item["portid"] = port.getAttribute("portid")
                        port_item["protocol"] = port.getAttribute("protocol")
                        try:
                            state = port.getElementsByTagName("state")[0]
                            port_item["state"] = state.getAttribute("state")
                        except IndexError:
                            port_item["state"] = "closed"
                        try:
                            service = port.getElementsByTagName("service")[0]
                            port_item["service"] = {}
                            port_item["service"]["name"] = service.getAttribute("name")
                            port_item["service"]["product"] = service.getAttribute("product")
                            port_item["service"]["version"] = service.getAttribute("version")
                        except IndexError:
                            port_item["service"] = {}
                        item["ports"].append(port_item)

                    ret.append(item)
        return ret

    def format_out(self):
        result = {}
        # command = "nmap -A -n " + self.args
        if self.level == "0":
            command = "nmap -sn -n --min-rate 1000 " + self.args
        elif self.level == "2":
            command = "nmap  -A -n -T5 --min-rate 100 --max-retries 2 --top-ports 1000 " + self.args
        elif self.level == "3":
            command = "nmap  -A -n -T4 --min-rate 100 --max-retries 2 -p %s %s" %(self.ports, self.args)
        else:
            command = "nmap  -A -n -T5 --min-rate 100 --max-retries 2 --top-ports 100 " + self.args

        filename = "/tmp/nmap_output/" + self.init_info["id"] + ".xml"
        progress_file = "/tmp/nmap_output/" + self.init_info["id"] + ".pro"
        collecttime = time.strftime('%Y-%m-%d %H:%M:%S %a')

        #执行nmap扫描
        self.run_nmap(command, filename, progress_file)

        #解析nmap扫描结果
        hosts = self.parse_nmap(filename)

        #解析后，删除扫描结果
        os.remove(filename)

        result["args"] = command
        result["collecttime"] = collecttime
        result["hosts"] = hosts

        return result

def get_progress(id):
    """
    总扫描数量 = 已完成扫描数量 + 正在扫描数量
    """
    #已经完成扫描数量
    completed_hosts_pattern = re.compile(r"([0-9]+)\s*hosts completed\s*\(([0-9]+)\s*up\)")

    progress_file = "/tmp/nmap_output/" + id + ".pro"

    if os.path.isfile(progress_file):
        with open(progress_file, "r", encoding = "utf8") as fobj:
            completed_hosts = 0

            for line in fobj.readlines():

                match = completed_hosts_pattern.search(line)
                if match:
                    # completed_hosts = int(match.group(1)) - int(match.group(2))
                    completed_hosts = int(match.group(1))

        return completed_hosts
    else:
        return 0