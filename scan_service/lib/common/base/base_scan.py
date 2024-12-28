import re
import time
import hashlib
from scan_service.lib.utils import get_dir
from scan_service.lib.utils import MyList
from scan_service.lib.utils import SHELL
from scan_service.lib.utils import SNMP
from scan_service.lib.utils import parse_pid_relation
from scan_service.lib.utils import format_socket
import datetime
from scan_service.lib.framework import logger

class Scan:
    def __init__(self, init_info):
        """
        用于设置扫描到的初始化信息（比如：操作系统的版本，所有的进程列表）
        当进行 组合扫描时，就可以共享初始化信息
        :param init_info: 
        """
        #设置变量
        for k, v in init_info.items():
            setattr(self, k ,v)

        self.init_info = init_info
        
class ScanViaSSH(Scan, SHELL):
    def __init__(self, init_info):
        Scan.__init__(self, init_info)
        SHELL.__init__(self, ssh = init_info["ssh"], passwd = init_info["password"])

class ScanViaShell(Scan, SHELL):
    def __init__(self, init_info):
        Scan.__init__(self, init_info)
        SHELL.__init__(self, local = True)

class ScanViaSNMP(Scan, SNMP):
    def __init__(self, init_info):
        Scan.__init__(self, init_info)
        SNMP.__init__(self, init_info["credential"])

class BaseScan(ScanViaSSH):

    def __init__(self, init_info, package_dict, feature_files_list, process_pattern, scan_files_dict, type = ""):
        """
        init函数用于初始化BaseScan这个类
        :param package_dict: 字典，用于描述软件包名字
            形如：
            {
                name: <STRING>,         #该软件的名称，比如：nginx，tomcat等
                pattern: <REGEXP>       #正则表达式，用于匹配软件包的名称（当通过包管理器安装时，会用这个进行匹配查找）
            }

        :param feature_files_list: 特征文件，用于验证进程是否是所要扫描进程，定位安装目录
            形如：
            [
                {
                    name: <STRING>,
                    pattern: <REGEXP>,
                    dir_depth: <INT>,
                    attribute: "文件的属性"      #比如：x表示可执行属性，f表示文件属性，等
                },
            ]

        :param process_pattern：<REGEXP>     #用于发现进程

        :param scan_files_dict: 需要发现的文件
        {
            exec_file: [                      #<TYPE>为该文件的类型，比如：exec_file，conf_file等
                {
                    name: "文件名",
                    pattern: <REGEXP>,
                    dir_depth: <INT>,
                    attribute: "文件属性"
                    package_manager: True    #如果该软件是通过包管理器安装的，这个能够标识该文件一定能够在包管理器中找到，否则认为检查到的包不符合要求
                },
            ]
            conf_file: [
                {
                    name: "文件名",
                    pattern: <REGEXP>,
                    dir_depth: <INT>,
                    attribute: "文件属性"
                },
            ],
            version_file: []    #这个file用于获取软件的版本,fortmat_out时，需要踢出这个文件
        }

        """

    #扫描到的初始信息
    #之后，将一些module组合扫描时，可能共享初始信息，所以需要传递扫描到的初始信息
        super(BaseScan, self).__init__(init_info)
        # Scan.__init__(self, init_info)
        
    #变量信息
        self.__package_dict = package_dict
        self.__feature_filess_list = feature_files_list
        self.__process_pattern = process_pattern
        self.__scan_files_dict = scan_files_dict

        #如果是通过包管理器安装的，获取包的名字和包里的文件内容
        self.__package_name = ""
        self.__package_files = []
        # 标识该软件的类型，不同软件类型，有些地方处理会有些区别，比如数据库类型的socket分析就会跟其他软件不太一样
        self.__type = type

    #基本信息
        self.ctime = time.strftime('%Y-%m-%d %H:%M:%S %a')

    #软件包信息
        #扫描包管理器中软件包的信息（在包管理器中，一种软件只能装一个版本）
        self.package = self.check_package(package_dict["pattern"], scan_files_dict)

    #实例信息
        """
        获取该软件的实例
        [
            {
                uuid: "实例的uuid，利用<IP>:<PORT>计算md5值"
                "file":{
                    "config_files":["/opt/oracle/conf/listner.ora","","..."],
                    "log_files":["/opt/oracle/log/access.log","domian.log","adminServer.log","..."],
                    "db_files":["","",""],
                    "control_files":["","",""],
                },
                
                "base_info":{
                    "software_version": "",
                    "software_name": "",
                    "instance_name": "",
                    "user_group": "<USER>:<GROUP>",
                    "install_location": "",
                    "listen": ["<IP>:<PORT>"],
                    "uptime": "<HOUR>h<MINUTE>m<SECONDS>s",
                    "status": "RUNNING"
                },
                
                "params":{
                    <KEY>: <VALUE>,  
                },                
                
                #只有weblogic有这个信息
                "domain":{
                    "name": "管理域名称",
                    "status": "OK,无法取到时可空",
                    "member":[{
                        "role":"manager",
                        "listen":["3.1.5.141:8002"],
                        "status":"OK",
                    },
                    {
                        "role":"managed",
                        "listen":["3.1.5.142:8001"],
                        "status":"OK",
                    },
                    ]
                },
                
                "cluster": [
                    {
                        "name":"cluster-test",
                        "domain":"只有weblogic有",
                        "type":"cluster or RAC ...",
                        "status":"OK",
                        "instance": {
                            "member":[
                                {
                                    "role":"proxy",
                                    "type":"F5",
                                    "listen":["3.1.5.142:8001"]
                                },
                                {
                                    "role":"member",
                                    "type":"weblogic",
                                    "listen":["3.1.5.141:8002"]
                                },
                            ],
                            
                        }
                        
                        "datasource":[
                            {
                                "name":"JNDI/oracle-3.1.3.210",
                                "type":"GENERIC",
                                "driver":"oracle.jdbc.OracleDriver",
                                "url":"jdbc:oracle:thin:@//3.1.3.210:1521/orcl2",
                                "status":"正常"
                            },
                        ],
                        
                        "app":[
                            {
                                "name": "demo",
                                "location": "/root/demo.war",
                                "module-type": "war"
                            }
                        ],
                        
                        "datasource": [
                            {
                                "name": "JDBC Data Source-0",
                                "driver": "com.mysql.cj.jdbc.MysqlXADataSource",
                                "url": "jdbc:mysql://3.1.5.20:3306/test"
                            }
                        ],
                    },
                ]
                
            }
        ]
        """
        self.instances = self.get_instances(process_pattern, self.package, feature_files_list, scan_files_dict)

    #获取安装包
    def check_package(self, package_pattern, scan_files_dict):
        """
        该函数用于扫描包管理器，寻找是否安装了相应的软件包

        :param package_pattern: "正则表达式，用于匹配软件包"
        :param scan_files_dict:
            {
                <TYPE>: {                       #<TYPE>为该文件的类型，比如：exec_file，conf_file等
                    name: <STRING>,
                    pattern: <REGEXP>,
                    dir_depth: <INT>,
                }
            }

        :return:
            {
                <TYPE>: {                       #<TYPE>为该文件的类型，比如：exec_file，conf_file等
                    name: "文件名",
                    pattern: <REGEXP>,
                    dir_depth: <INT>,
                    path: "绝对路径"
                }
            }
        """
        ret = {}
        packages = []
        #扫描包管理器。获取符合要求的软件包的名称
        for package in self.packages:
            if re.search(package_pattern, package, re.IGNORECASE):
                packages.append(package)

        for package in packages:
            done = False

            #获取该软件包的所有文件路径
            if "centos" in self.system_release.lower() or "red hat" in self.system_release.lower():
                all_files = self.exec_shell("rpm -ql %s" %package)
            else:
                all_files = self.exec_shell("dpkg -L %s" %package)

            #找出 需要发现文件 的路径
            # 如果该文件标识为一定能够找到（package_manager = True），如果未找到，表明该软件包不是所寻找的软件包
            for file_type in scan_files_dict:
                if done:
                    break
                ret[file_type] = scan_files_dict[file_type]
                for item in ret[file_type]:
                    pattern = re.compile(item["pattern"])

                    #利用正则表达式匹配文件
                    for file in all_files:
                        if pattern.search(file) and self.check_file_attribute(file, item["attribute"]):
                            item["path"] = file

                    if item.get("package_manager") and not item.get("path"):
                        ret = {}
                        done = True
                        break

            if ret:
                self.__package_files = all_files
                self.__package_name = package
                return ret
        return ret

    def verify_process(self, pid_dict, feature_files_list):

        """
        利用特征文件验证进程是否符合要求，如果符合要求，根据特征文件返回安装目录
        :param pid_dict:
        :param feature_files_list:
        :return:
        """
        #验证进程是否符合要求（即有特征文件且特征文件的属性是正确的
        for pid in list(pid_dict):
            # exec_file = exec_shell("cat /proc/%s/maps | awk '{if($2~/x/ && $6~/%s/) {print $6}}'" %(pid, feature_files_dict["exec_file"]["pattern"].replace("/", "\/")))[0]

            loaded_files = list(set(self.exec_shell("cat /proc/%s/maps | awk '{print $6}';readlink /proc/%s/exe" %(pid, pid))))
            pid_dict[pid]["file_dict"] = []

            #如果该进程的可执行文件没有符合要求，则去除该进程信息
            for file_dict in feature_files_list:
                verify = False
                for file in loaded_files:
                    if re.search(file_dict["pattern"], file) and self.check_file_attribute(file, file_dict["attribute"]):
                        pid_dict[pid]["file_dict"] = file_dict.copy()
                        pid_dict[pid]["file_dict"]["path"] = file
                        verify = True
                        break
                if not verify:
                    pid_dict.pop(pid)
                    break
        """
        根据特征文件判断安装位置
        如果通过包管理器安装的，则安装位置说明为"package_manager"
        如果手动安装，则通过dir_depth，找到安装目录
        """

        for pid in pid_dict:
            if pid_dict[pid]["file_dict"]["path"] in self.__package_files or get_dir(pid_dict[pid]["file_dict"]["path"], 1) in self.__package_files:
                pid_dict[pid]["install_location"] = "package_manager:%s" %self.__package_name
            else:
                pid_dict[pid]["install_location"] = get_dir(pid_dict[pid]["file_dict"]["path"], pid_dict[pid]["file_dict"]["dir_depth"])

            pid_dict[pid].pop("file_dict")

        return pid_dict

    # 获取实例的基础信息
    def get_instance_base_info(self, pid_dict):
        """
        获取instance的基础信息
        :param pid_dict:
            {
                "<PID>":
                    {
                        "ppid": "",
                        "child_pids": [],
                        "install_location": "",
                        "uptime": "",
                        "user_group": ""
                    }
            }
        :return:
            {
                "<PID>":
                    {
                        "base_info":{
                            "software_name":"weblogic",
                            "ppid": "",
                            "child_pids": [],
                            "install_location":"",
                            "uptime":"12h22m32s",
                            "user_group":"weblogic:weblogic，启动服务的用户和用户组",

                            "status":"RUNNING",
                            "instance_name":"数据库实例名或中间件软件提供的service名称",
                            "listen":["ip:port"],
                            "software_version":"12.0.1",
                        }
                        "foreign_address": []
                    }
            }
        """

        ret = {}
        etime_pattern = re.compile(r"(?:(\d+)-)?(?:(\d+):)?(\d+):(\d)")
        for pid in pid_dict:
            ret[pid] = {"base_info": pid_dict[pid], "foreign_address": []}

            for line in self.processes:
                if pid == line.split()[0]:
                    match = etime_pattern.search(line.split()[2])
                    d = int(match.group(1)) if match.group(1) else 0
                    h = int(match.group(2)) if match.group(2) else 0
                    m = int(match.group(3)) if match.group(3) else 0
                    s = int(match.group(4)) if match.group(4) else 0
                    ret[pid]["base_info"]["uptime"] = (datetime.datetime.now() - datetime.timedelta(days=d, hours=h, minutes=m, seconds=s)).strftime('%Y-%m-%d %H:%M:%S')
                    ret[pid]["base_info"]["user_group"] = "%s:%s" %(line.split()[4],line.split()[5])
                    break

            ret[pid]["base_info"]["software_name"] = self.__package_dict["name"]
            ret[pid]["base_info"]["status"] = "RUNNING"
            ret[pid]["base_info"]["instance_name"] = ""
            ret[pid]["base_info"]["software_version"] = ""
            ret[pid]["base_info"]["listen"] = []
            ret[pid]["base_info"]["cwd"] = self.exec_shell("readlink /proc/%s/cwd" % pid)[0]
            ret[pid]["foreign_address"] = []
            ret[pid]["connections"] = {}
            ret[pid]["params"] = {}
            ret[pid]["domain"] = {}
            ret[pid]["cluster"] = []
            ret[pid]["datasource"] = []

            # for line in global_var.all_sockets:
            #     if line.split()[1] == "LISTEN":
            #         if pid in MyList(MyList(line.split())[6].split(','))[1]:
            #             ret[pid]["base_info"]["listen"].append(line.split()[4])
            #
            #         if pid_dict[pid].get("child_pids"):
            #             for c_pid in pid_dict[pid]["child_pids"]:
            #                 if c_pid in MyList(MyList(line.split())[6].split(','))[1]:
            #                     ret[pid]["base_info"]["listen"].append(line.split()[4])
            #
            #         #去重
            #         ret[pid]["base_info"]["listen"] = list(set(ret[pid]["base_info"]["listen"]))
            #
            #         #修改listen格式
            #         for item in ret[pid]["base_info"]["listen"]:
            #             if ":::" in item or "*" in item or '[::]:' in item:
            #                 port = item.split(':')[-1]
            #                 ret[pid]["base_info"]["listen"].remove(item)
            #                 for ip in self.ip_list:
            #                     ret[pid]["base_info"]["listen"].append("%s:%s" %(ip, port))
            #             else:
            #                 ip = re.search(r'([0-9]{1,3}\.){3}[0-9]{1,3}', item)
            #                 if ip:
            #                     port = item.split(':')[-1]
            #                     ret[pid]["base_info"]["listen"].remove(item)
            #                     ret[pid]["base_info"]["listen"].append("%s:%s" %(ip.group(), port))
            #
            #         # 去重
            #         ret[pid]["base_info"]["listen"] = sorted(list(set(ret[pid]["base_info"]["listen"])))
            #
            #
            #     elif line.split()[2] == "ESTAB":
            #         if pid in MyList(MyList(line.split())[6].split(','))[1]:
            #             ret[pid]["foreign_address"].append(line.split()[5])
            #
            #         if pid_dict[pid].get("child_pids"):
            #             for c_pid in pid_dict[pid]["child_pids"]:
            #                 if c_pid in MyList(MyList(line.split())[6].split(','))[1]:
            #                     ret[pid]["foreign"].append(line.split()[4])
            #
            #         ret[pid]["foreign_address"] = list(set(ret[pid]["foreign_address"]))

        return ret

    #解析socket套接字，包括监听的socket和已建立连接的外部socket
    def parse_socket_info(self, pid_dict):
        for pid in pid_dict:

            for line in self.all_sockets:
                if line.split()[1] == "LISTEN":
                    if pid in MyList(MyList(line.split())[6].split(','))[1]:
                        pid_dict[pid]["base_info"]["listen"].append(line.split()[4])

                    # if pid_dict[pid].get("child_pids"):
                    for c_pid in pid_dict[pid]["base_info"].get("child_pids", []):
                        if c_pid in MyList(MyList(line.split())[6].split(','))[1]:
                            pid_dict[pid]["base_info"]["listen"].append(line.split()[4])

                elif line.split()[1] == "ESTAB":
                    if pid in MyList(MyList(line.split())[6].split(','))[1]:
                        # pid_dict[pid]["foreign_address"].append(line.split()[5])
                        if not "127.0.0.1" in line.split()[4] and not "127.0.0.1" in line.split()[4]:
                            port = line.split()[4].split(":")[-1]
                            if not pid_dict[pid]["connections"].get(port):
                                pid_dict[pid]["connections"][port] = []
                            pid_dict[pid]["connections"][port].append(line.split()[5])

                    # if pid_dict[pid].get("child_pids"):
                    for c_pid in pid_dict[pid]["base_info"].get("child_pids", []):
                        if c_pid in MyList(MyList(line.split())[6].split(','))[1]:
                            # pid_dict[pid]["foreign_address"].append(line.split()[4])
                            if not "127.0.0.1" in line.split()[4] and not "127.0.0.1" in line.split()[4]:
                                port = line.split()[4].split(":")[-1]
                                if not pid_dict[pid]["connections"].get(port):
                                    pid_dict[pid]["connections"][port] = []
                                pid_dict[pid]["connections"][port].append(line.split()[5])

            if self.__type == "database":
                """
                去除没有被连接的监听端口
                这样可以去除更多次要的端口（比如oracle只需要1521这个端口，其他监听端口都是内部的监听端口）
                """
                listen_list = []
                for listen_socket in pid_dict[pid]["base_info"]["listen"]:
                    # 判断该监听端口是否有连接，如果有连接，则保留
                    if pid_dict[pid]["connections"].get(listen_socket.split(":")[-1]):
                        listen_list.append(listen_socket)

                # for line in self.all_sockets:
                #     if line.split()[1] == "ESTAB":
                #         if pid in MyList(MyList(line.split())[6].split(','))[1]:
                #             for listen_socket in pid_dict[pid]["base_info"]["listen"]:
                #                 #判断该监听端口是否有连接，如果有连接，则保留
                #                 if line.split()[4].split(":")[-1] == listen_socket.split(":")[-1]:
                #                     listen_list.append("%s:%s" %(listen_socket.rsplit(":", maxsplit=1)[0], listen_socket.rsplit(":", maxsplit=1)[1]))
                #
                #         # if pid_dict[pid].get("child_pids"):
                #         for c_pid in pid_dict[pid]["base_info"].get("child_pids", []):
                #             if c_pid in MyList(MyList(line.split())[6].split(','))[1]:
                #                 if line.split()[4].split(":")[-1] == listen_socket.split(":")[-1]:
                #                     listen_list.append("%s:%s" % (listen_socket.rsplit(":", maxsplit=1)[0], listen_socket.rsplit(":", maxsplit=1)[1]))

                pid_dict[pid]["base_info"]["listen"] = listen_list

            # 去重
            pid_dict[pid]["base_info"]["listen"] = list(set(pid_dict[pid]["base_info"]["listen"]))
            # pid_dict[pid]["foreign_address"] = list(set(pid_dict[pid]["foreign_address"]))

            """
            修改listen格式
            将能够匹配到ip，才加入到监听端口，所以监听在ipv6地址的都被去除了
            如果匹配所有地址，则会获取本机所有ipv4地址（并排除127.0.0.1）
            """
            temp_list = pid_dict[pid]["base_info"]["listen"].copy()
            pid_dict[pid]["base_info"]["listen"] = []
            for item in temp_list:
                pid_dict[pid]["base_info"]["listen"].extend(format_socket(item, self.local_ip_list))
                # if ":::" in item or "*" in item or '[::]:' in item:
                #     port = item.split(':')[-1]
                #     # pid_dict[pid]["base_info"]["listen"].remove(item)
                #     for ip in self.local_ip_list:
                #         pid_dict[pid]["base_info"]["listen"].append("%s:%s" % (ip, port))
                # else:
                #     ip = global_var.ip_match.search(item)
                #     if ip and ip.group() != "127.0.0.1":
                #         port = item.split(':')[-1]
                #         # pid_dict[pid]["base_info"]["listen"].remove(item)
                #         pid_dict[pid]["base_info"]["listen"].append("%s:%s" % (ip.group(), port))

            """
            清洗connections
            """
            temp_dict = pid_dict[pid]["connections"].copy()
            pid_dict[pid]["connections"] = {}
            for port in temp_dict:
                pid_dict[pid]["connections"][port] = []

                for sock in list(set(temp_dict[port])):
                    ip_port_list = format_socket(sock, self.local_ip_list)
                    pid_dict[pid]["connections"][port].extend(ip_port_list)
                    pid_dict[pid]["foreign_address"].extend(ip_port_list)

                pid_dict[pid]["connections"][port] = list(set(pid_dict[pid]["connections"][port]))

            #清洗foreign address
            # temp_list = pid_dict[pid]["foreign_address"].copy()
            # pid_dict[pid]["foreign_address"] = []
            # for item in temp_list:
            #     ip = global_var.ip_match.search(item)
            #     if ip:
            #         port = item.split(":")[-1]
            #         pid_dict[pid]["foreign_address"].append("%s:%s" % (ip.group(), port))

            # 去重
            pid_dict[pid]["base_info"]["listen"] = list(set(pid_dict[pid]["base_info"]["listen"]))
            pid_dict[pid]["foreign_address"] = list(set(pid_dict[pid]["foreign_address"]))

        # tmp_dict = pid_dict.copy()
        # for pid in tmp_dict:
        #     if not tmp_dict[pid]["base_info"]["listen"]:
        #         pid_dict.pop(pid)
        #         logger.error("未获取监听端口，pid：%s" %pid)

        return pid_dict

    #获取更多信息，并进行信息的整合
    def get_instance_more_info(self, pid_dict):
        return pid_dict

    #根据安装路径，获取其他文件的绝对路径
    def get_files_info(self, pid_dict, scan_files_dict):
        for pid in pid_dict:
            pid_dict[pid]["file"] = {}
            if "package_manager" in pid_dict[pid]["base_info"]["install_location"]:
                for type in scan_files_dict:
                    pid_dict[pid]["file"][type] = []
                    for item in scan_files_dict[type]:
                        if item.get("path"):
                            pid_dict[pid]["file"][type].append(item["path"])
            else:
                for type in scan_files_dict:
                    pid_dict[pid]["file"][type] = []
                    for item in scan_files_dict[type]:
                        path_list = self.find_file(pid_dict[pid]["base_info"]["install_location"], item["pattern"])
                        for path in path_list:
                            if get_dir(path, item["dir_depth"]) and self.check_file_attribute(path, item["attribute"]):
                                pid_dict[pid]["file"][type].append(path)

                    #如果在install_location中找不到，则在cwd中继续寻找
                    if not pid_dict[pid]["file"][type] and pid_dict[pid]["base_info"]["install_location"] not in pid_dict[pid]["base_info"]["cwd"]  and len(pid_dict[pid]["base_info"]["cwd"].split("/")) > 2:
                        for item in scan_files_dict[type]:
                            path_list = self.find_file(pid_dict[pid]["base_info"]["cwd"], item["pattern"])
                            for path in path_list:
                                if get_dir(path, item["dir_depth"]) and self.check_file_attribute(path, item["attribute"]):
                                    pid_dict[pid]["file"][type].append(path)


        return pid_dict

    def get_more_files_info(self, pid_dict):
        return pid_dict

    # 获取软件版本，每个软件需要重写该函数
    def get_version(self, pid_dict):
        return pid_dict

    #获取集群信息
    def get_cluster_info(self, pid_dict):
        return pid_dict

    #整合信息
    def integrate_info(self, pid_dict):
        return pid_dict

    # 获取实例信息
    def get_instances(self, process_pattern, package, feature_files_list, scan_files_dict):

        #根据process_pattern过滤出符合要求的进程
        processes = {}
        for line in self.processes:
            command = ' '.join(line.split()[6:])
            pattern = re.compile(process_pattern)
            if pattern.search(command):
                processes[line.split()[0]] = {}
                processes[line.split()[0]]["ppid"] = line.split()[1]

        #验证进程是否符合要求（验证后的主进程为一个实例）
        processes = self.verify_process(processes, feature_files_list)

        """
        解析过滤出的进程间的父子关系
        :param pid_list:
            {
                "<PID>": {
                    "ppid": ""
                    "child_pids": []
                    ...
                }
            }
        :return:
            {
                "<PID>":
                    {
                        "ppid": ""
                        "child_pids": []
                        ...
                    }
            }
        """
        processes = parse_pid_relation(processes)

        #获取实例的基本信息
        processes = self.get_instance_base_info(processes)

        #解析套接字的信息
        processes = self.parse_socket_info(processes)

        #获取更多信息，并进行信息的整合
        processes = self.get_instance_more_info(processes)

        #获取其他文件的绝对路径
        processes = self.get_files_info(processes, scan_files_dict)

        #获取更多的文件信息（这里实现不同的软件，文件查找的差异
        processes = self.get_more_files_info(processes)

        #获取实例的版本
        processes = self.get_version(processes)

        #获取集群信息
        processes = self.get_cluster_info(processes)

        #对信息进行整合
        processes = self.integrate_info(processes)

        #删掉未采集到端口的进程
        tmp_dict = processes.copy()
        for pid in tmp_dict:
            if not tmp_dict[pid]["base_info"]["listen"]:
                processes.pop(pid)
                logger.error("未获取监听端口，pid：%s" %pid)

        return processes

    def format_output(self):
        ret = []
        instances = self.instances.copy()
        for pid in instances:
            instances[pid]["base_info"]["pid"] = pid
            instances[pid]["collect_time"] = self.ctime
            instances[pid]["host_uuid"] = self.host_uuid
            instances[pid]["scan_ip"] = self.scan_ip

            #剔除用于获取软件版本的文件
            if instances[pid]["file"].get("version_file"):
                instances[pid]["file"].pop("version_file")

            listening_ports = [ sock.split(":")[-1] for sock in instances[pid]["base_info"]["listen"] ]
            listening_ports = sorted(list(set(listening_ports)))
            id = self.host_uuid + instances[pid]["base_info"]["instance_name"].join(listening_ports)
            instances[pid]["uuid"] = hashlib.md5(id.encode()).hexdigest()

            ret.append(instances[pid])

        return ret
