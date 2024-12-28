from .apache import ApacheScan
from .mysql import MysqlScan
from .nginx import NginxScan
from .oracle import OracleScan
from .postgresql import PGScan
from .tomcat import TomcatScan
from .weblogic import WeblogicScan
from .linux import LinuxScan
from .esxi import EsxiScan
from .AIX import AixScan
from .nmap import NmapScan
from .nmap import get_progress
from .url_probe import UrlProbe
from .windows import WindowsScan
from .network_device import device_route
from .run_scripts import RunScripts

from scan_service.lib.vars import global_var
from scan_service.lib.utils import SSH
from scan_service.lib.utils import SHELL
from scan_service.lib.utils import WMIC
import importlib
import hashlib
from scan_service.lib.framework import BusinessException
from scan_service.lib.framework import AuthException
from scan_service.lib.framework import logger
import traceback

from scan_service.lib.utils import SNMP
from .network_device import get_vender

class RunScan():

    def ssh_init(self, credential_info, scan_type = "os"):

        # 建立ssh连接
        ssh = SSH(credential_info["host"], credential_info["port"], credential_info["username"], credential_info["password"])

        #这个shell用于获取初始化信息
        shell = SHELL(ssh = ssh, passwd = credential_info["password"])
        kernel = shell.exec_shell("uname -s")[0].strip().lower()

        try:
            if kernel == "linux":
                return self.linux_init(credential_info, ssh, shell, scan_type = scan_type)

            elif kernel == "vmkernel":
                if scan_type != "os":
                    ssh.__del__()
                    raise BusinessException("ESXI系统不支持软件扫描")
                else:
                    return self.esxi_init(credential_info, ssh, shell)

            elif kernel == "aix":
                if scan_type != "os":
                    ssh.__del__()
                    raise BusinessException("AIX系统不支持软件扫描")
                else:
                    return self.aix_init(credential_info, ssh, shell)

            else:
                ssh.__del__()
                raise BusinessException("无法识别操作系统")

        except AuthException as e:
            ssh.__del__()
            raise AuthException("%s" %str(e))

        except Exception as e:
            ssh.__del__()
            raise BusinessException("%s" %str(e))

    def linux_init(self, credential_info, ssh, shell, scan_type):
        """
        初始化：
            1.获取所有安装的rpm包的名称
            2.更新文件数据库，从而实现能够很快的查找文件
            3.设置位置变量
            4.建立ssh连接

        {
            "ssh": "SSH实例",
            "tool": "shell工具类",
            "system_release": "操作系统版本",
            "packages": "软件包",
            "processes": "所有进程",
            "all_sockets": "所有套接字",
            "host_uuid": "主机uuid",
            "local_ip_list": "ip列表",
            "jvm_list": "jvm列表"
        }
        """

        init_info = {
            "type": "linux",
            #下面是linux扫描用到的信息
            "system_release": "",

            #下面是linux和software扫描都用到的信息
            "ssh": "SSH实例",
            "password": "ssh密码",
            "host_uuid": "主机uuid",
            "scan_ip": "扫描地址",

            #下面是软件扫描用到的信息
            "local_ip_list": "ip列表",
            "packages": "软件包",
            "processes": "所有进程",
            "all_sockets": "所有套接字"
        }

        host = credential_info["host"]
        password = credential_info["password"]

        # 建立ssh连接
        init_info["ssh"] = ssh
        #根据ssh，获取shell的工具类
        init_info["password"] = password
        #获取scan_ip
        init_info["scan_ip"] = host
        #这个shell用于获取初始化信息
        shell = shell

        # 获取系统类型
        #从而判断应该调用哪种扫描脚本
        os_info = shell.exec_shell("cat /etc/os-release /etc/system-release /etc/redhat-release")
        for line in os_info:
            if "pretty_name" in line.lower():
                init_info["system_release"] = line.split('"')[1]
        if not init_info["system_release"]:
            init_info["system_release"] = os_info[-1]

        if "big-ip" in ' '.join(os_info).lower():
            raise AuthException("big-ip不支持ssh部署")
        # if os_info:
        #     for line in os_info:
        #         if "pretty_name" in line.lower():
        #             init_info["system_release"] = line.split('"')[1]
        # else:
        #     init_info["system_release"] = shell.exec_shell("cat /etc/system-release")[0]

        # 获取主机的uuid
        product = shell.exec_shell("dmidecode -s system-product-name")[0]
        if "virtual" in product.lower() or "openstack" in product.lower():
            init_info["host_uuid"] = hashlib.md5(shell.exec_shell("dmidecode -s system-uuid")[0].encode()).hexdigest()
        else:
            serial_number = shell.exec_shell("dmidecode -s system-serial-number")[0]
            if "empty" in serial_number.lower() or "unknown" in serial_number.lower() or "o.e.m" in serial_number.lower() or not serial_number.strip():
                init_info["host_uuid"] = hashlib.md5(shell.exec_shell("dmidecode -s system-uuid")[0].encode()).hexdigest()
            else:
                init_info["host_uuid"] = hashlib.md5(serial_number.encode()).hexdigest()

        # 获取所有的sockets的信息
        init_info["all_sockets"] = shell.exec_shell('timeout 10 ss -tuanp')
        if not init_info["all_sockets"]:
            init_info["all_sockets"] = shell.exec_shell('ss -tuanp')
        if not init_info["all_sockets"]:
            result = shell.exec_shell('timeout 10 netstat -tuanp')
            if not result:
                result = shell.exec_shell('netstat -tuanp')
            for line in result:
                new_list = []
                old_list = line.split()
                if old_list[0] == "tcp":
                    new_list = [old_list[0], old_list[5].replace("ESTABLISHED", "ESTAB"), old_list[1], old_list[2],
                                old_list[3], old_list[4], "%s,%s" % (
                                ' '.join(' '.join(old_list[6:]).split("/")[1:]), ' '.join(old_list[6:]).split("/")[0])]
                elif old_list[0] == "udp":
                    new_list = [old_list[0], "UNCONN", old_list[1], old_list[2], old_list[3], old_list[4], "%s,%s" % (
                    ' '.join(' '.join(old_list[5:]).split("/")[1:]), ' '.join(old_list[5:]).split("/")[0])]
                else:
                    new_list = old_list
                init_info["all_sockets"].append(' '.join(new_list))

        if scan_type == "software":
            if not init_info["all_sockets"]:
                raise BusinessException("software部署失败，失败原因：未采集到sockets信息")
            # 获取本地ip
            init_info["local_ip_list"] = shell.get_local_ip()

            # 获取所有安装的软件包
            if "centos" in init_info["system_release"].lower() or "red hat" in init_info["system_release"].lower():
                init_info["packages"] = shell.exec_shell('rpm -qa')
            else:
                # init_info["packages"] = ["%s-%s" % (line.split()[1].strip(), line.split()[2].strip()) for line in
                #                        shell.exec_shell("dpkg -l | grep ^ii")]
                init_info["packages"] = ["%s" % line.split()[1].strip() for line in shell.exec_shell("dpkg -l | grep ^ii")]

            # 获取所有进程信息
            init_info["processes"] = shell.exec_shell(
                "ps -o pid,ppid,etime,time,user,group,command ax | grep -v grep | awk '$1!=2 && $2!=2{print}'")

        return init_info

    def esxi_init(self, credential_info, ssh, shell):
        host = credential_info["host"]
        password = credential_info["password"]

        esxi_init_info = {
            "ssh": ssh,
            "password": password,
            "scan_ip": host,
            "type": "esxi"
        }

        return esxi_init_info

    def aix_init(self, credential_info, ssh, shell):
        host = credential_info["host"]
        password = credential_info["password"]

        aix_init_info = {
            "ssh": ssh,
            "password": password,
            "scan_ip": host,
            "type": "aix"
        }

        return aix_init_info

    def snmp_init(self, credential_info):
        init_info = {
            "credential": "凭证信息",
            "snmp": "snmp实例",
            "scan_ip": "扫描ip",
            "type": ""
        }

        credential = {}
        credential["hostname"] = credential_info.get("host")
        credential["remote_port"] = int(credential_info.get("port", "161"))
        if credential_info.get("protocol", "") == "SNMPv3":
            credential["version"] = 3
            credential["security_username"] = credential_info.get("username", "")
            level_mapping = {
                "noAuthNoPriv": "no_auth_or_privacy",
                "authNoPriv": "auth_without_privacy",
                "authPriv": "auth_with_privacy"
            }
            credential["security_level"] = level_mapping.get(credential_info.get("snmpv3Securitylevel", ""), "no_auth_or_privacy")

            if credential_info.get("snmpv3Authprotocol"):
                credential["auth_protocol"] = credential_info.get("snmpv3Authprotocol", "").upper()
                credential["auth_password"] = credential_info.get("snmpv3Authpassphrase", "")

            if credential_info.get("snmpv3Privprotocol"):
                credential["privacy_protocol"] = credential_info.get("snmpv3Privprotocol", "").upper()
                credential["privacy_password"] = credential_info.get("snmpv3Authpassphrase", "")
        else:
            credential["version"] = 2
            credential["community"] = credential_info.get("snmpCommunity", "")

        init_info["credential"] = credential
        init_info["snmp"] = SNMP(credential)
        init_info["scan_ip"] = credential_info.get("host")

        vender = get_vender(SNMP(credential, use_sprint_value=False).snmp_walk("1.3.6.1.2.1.1.2")[0].split(".")[7])
        init_info["device_info"] = " ".join([vender] + init_info["snmp"].snmp_walk("1.3.6.1.2.1.1.2") + init_info["snmp"].snmp_walk("1.3.6.1.2.1.1.1"))

        return init_info

    def nmap_init(self, id, params):
        init_info = {
            "id": "",
            "tool": "shell工具类",
            "level": "",
            "args": "命令参数",
            "ports": ""
        }
        init_info["id"] = id
        init_info["level"] = params.get("level", "")
        init_info["args"] = params["hosts"]
        init_info["ports"] = params.get("ports", "")
        return init_info

    def url_probe_init(self, url):
        probe_dict = {
            "url": url,
            "level": "0"
        }
        return probe_dict

    def windows_init(self, credential_info):
        init_info = {
            "host": credential_info["host"],
            "username": credential_info["username"],
            "password": credential_info["password"],
            "wmic": WMIC(credential_info)
        }

        return init_info

class RunSoftwareScan(RunScan):
    """
    当使用多线程时，可以在__init__函数中设置共享变量
    """
    def __init__(self, credential):
        self.init_info = self.ssh_init(credential, scan_type = "software")

    def start(self):
        ret = []
        if self.init_info.get("type", "") == "linux":
            for scan_class in global_var.global_config["software"]["load_modules"]:
                try:
                    module = importlib.import_module("lib.modules")
                    instance = getattr(module, scan_class)(self.init_info)
                    result = instance.format_output()
                    if result:
                        ret.extend(result)
                except Exception:
                    logger.error("%s软件部署失败，ip：%s，%s" %(scan_class, self.init_info["scan_ip"], traceback.format_exc()))
        return ret

#后续接口接收的扫描类型应该为ssh，RunSshScan
class RunSshScan(RunScan):
    def __init__(self, credential):
        self.init_info = self.ssh_init(credential)

    def start(self):
        try:
            if self.init_info.get("type", "") == "linux":
                instance = LinuxScan(self.init_info)
            elif self.init_info.get("type", "") == "esxi":
                instance = EsxiScan(self.init_info)
            elif self.init_info.get("type", "") == "aix":
                instance = AixScan(self.init_info)

            result = instance.format_output()

            self.init_info["ssh"].__del__()
            return result

        except Exception as e:
            self.init_info["ssh"].__del__()
            raise BusinessException("%s" %str(e))

class RunSnmpScan(RunScan):
    def __init__(self, credential):
        self.init_info = self.snmp_init(credential)

    def start(self):
        Instance = device_route(self.init_info["device_info"])
        if not Instance:
            raise BusinessException("暂不支持使用snmp采集此设备: %s" % self.init_info["device_info"])

        result = Instance(self.init_info).format_out()
        # import json
        # from pathlib import Path
        # with open(str(Path(__file__).parent / "a.txt"), "w", encoding="utf8") as fobj:
        #     fobj.write(json.dumps(result, indent=2))
        return result

class RunNmapScan(RunScan):
    def __init__(self, id, params):
        self.init_info = self.nmap_init(id, params)

    def start(self):
        instance = NmapScan(self.init_info)
        result = instance.format_out()
        return result

class RunUrlProbeScan(RunScan):
    def __init__(self, url):
        self.probe_dict = self.url_probe_init(url)

    def start(self):
        probe = UrlProbe()
        return probe.recursion_probe(self.probe_dict)

class RunSnmpTest(RunScan):
    def __init__(self, credential):
        self.init_info = self.snmp_init(credential)

    def start(self):
        return self.init_info["snmp"].test_credential()

class RunSshTest(RunScan):
    def __init__(self, credential):
        self.host = credential["host"]
        self.port = credential["port"]
        self.username = credential["username"]
        self.password = credential["password"]

    def start(self):
        ssh = SSH(self.host, self.port, self.username, self.password)
        ssh.__del__()
        return 1

#以下扫描脚本由路遥维护

#运行windows的部署
class RunWmiScan(RunScan):

    def __init__(self, credential):
        self.init_info = self.windows_init(credential)

    def start(self):
        result = WindowsScan(self.init_info).format_out()
        return result

class RunWmiTest(RunScan):
    def __init__(self, credential):
        self.credential = credential

    def start(self):
        wmic = WMIC(self.credential)
        wmic.query("SELECT * FROM Win32_Processor")
        return 1
