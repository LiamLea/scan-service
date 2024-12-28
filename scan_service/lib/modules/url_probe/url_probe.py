import re
from scan_service.lib.utils import get_ip_from_hostname
from scan_service.lib.framework import BusinessException
from scan_service.lib.database import Session
from scan_service.lib.database import AtomSystem,AtomConfig,ClusterInfo,ClusterNode,MonitorHost,HostConfig

"""
需要用到的表：
    原子系统表：cmdb_atomic_system
    原子系统采集信息表：cmdb_ci_instance_software_config
    集群信息表：cmdb_software_cluster
    集群节点表：cmdb_software_cluster_node
    
    设备扫描表：monitor_host
    设备配置信息表：cmdb_ci_instance_host_config
"""
class UrlProbe:

    """
    传入的参数和输出的参数结构，
    level表示该url在哪一层探测出来的，level为0表示该url是初始化url，还未进行探测

    probe_dict = {
        "url": "http://192.168.33.59:8000",
        "level": "0",
    }
    """

    def __init__(self):
        self.session = Session()
        self.url_match = re.compile(r"(?:(\S+)[:@]//)?([^:/]+):?(\d+)?(/.*)?")
        self.protocol_dict = {
            "http": "80",
            "https": "443"
        }

        #存储各个层级的ip:port，用于检测死循环
        self.all_ip_port = {}

    def get_probe_info(self, url):
        """
        解析url，获取需要的信息
        """
        probe_info = {
            "protocol": "",
            "hostname": "",
            "ip": "",
            "port": "",
            "path": ""
        }
        match = self.url_match.search(url)
        if match:
            probe_info["protocol"] = match.group(1).lower() if match.group(1) else "http"
            probe_info["hostname"] = match.group(2)
            probe_info["ip"] = get_ip_from_hostname(match.group(2))[0]
            probe_info["port"] = match.group(3) if match.group(3) else self.protocol_dict.get(probe_info["protocol"])
            probe_info["path"] = match.group(4) if match.group(4) else "/"

        if not probe_info["ip"] and not probe_info["port"]:
            raise BusinessException("url解析失败：%s" %url)

        return probe_info

    def probe_atom_system(self, probe_dict):
        """
        component表示本层的组件
        其中item的结构：
            {
                "uuid": "原子系统uuid",
                "type": "原子系统类型",
                "level": "所在层级",
                "id": "原子系统在表中的id",
                "name": "原子系统的名称"
            }

        backend表示下一层的组件
        其中item的结构：
            {
                "url": datasource["url"],
                "level": "%s" %(int(probe_dict["level"]) + 1),
                "type": "datasource",   #当后端是数据源是，需要设置这个type
            }
        """
        ret = {
            "component": [],
            "backend": []
        }

        probe_info = self.get_probe_info(probe_dict["url"])

        if probe_dict["level"] == "0":
            self.all_ip_port[0] = ["%s:%s" %(probe_info["ip"], probe_info["port"])]

        for obj in self.session.query(AtomSystem.ip, AtomSystem.uuid, AtomSystem.type, AtomSystem.id, AtomSystem.name).all():

            for ip_port in obj.ip.split(","):
                if ip_port.strip() == "%s:%s" %(probe_info["ip"], probe_info["port"]):

                    if not self.all_ip_port.get(int(probe_dict["level"]) + 1):
                        self.all_ip_port[int(probe_dict["level"]) + 1] = []
                    self.all_ip_port[int(probe_dict["level"]) + 1].extend(obj.ip.split(","))

                    item = {
                        "uuid": obj.uuid,
                        "type": obj.type,
                        "level": "%s" %(int(probe_dict["level"]) + 1),
                        "id": obj.id,
                        "name": obj.name
                    }
                    ret["component"].append(item)

                    config_dict = self.session.query(AtomConfig.config).filter(AtomConfig.uuid == obj.uuid).first().config
                    """
                    解析负载均衡配置
                    """
                    default_config = {}
                    get_default = False
                    match_config = {}
                    for config in config_dict.get("config", []):
                        if "%s:%s" %(probe_info["ip"], probe_info["port"]) in config["proxy"]["listen"]:
                            if not get_default:
                                default_config = config
                            if not config["proxy"]["server_name"] or probe_info["hostname"] in config["proxy"]["server_name"]:
                                if not config["proxy"]["url"]:
                                    match_config = config
                                    break
                                for url in config["proxy"]["url"]:
                                    # if probe_info["path"] in url:
                                    if re.search(r"%s" %url.rstrip("/"), probe_info["path"]):
                                        match_config = config
                                        break
                    if not match_config:
                        match_config = default_config

                    for instance in match_config.get("instance", []):
                        if instance.get("role") != "proxy":
                            item = {
                                "url": instance["listen"][0],
                                "level": "%s" % (int(probe_dict["level"]) + 1)
                            }

                            ret["backend"].append(item)

                    #存储数据源，包括原子系统数据源和符合要求的集群数据源
                    datasources = []

                    #获取原子系统的数据源
                    for datasource in config_dict.get("datasource", []):
                        datasources.append(datasource)

                    """
                    解析集群配置
                    如果访问ip == service_ip，表示集群中的节点都在后端，并且获取集群的数据源
                    """
                    for cluter in config_dict["cluster"]:

                        if probe_info["ip"] == cluter.get("service_ip", ""):
                            #获取集群的uuid，去表里匹配集群的其他成员
                            subquery1 = self.session.query(ClusterInfo.cluster_id).filter(ClusterInfo.cluster_code == cluter["uuid"]).subquery()
                            subquery2 = self.session.query(ClusterNode.ci_instance_id).filter(ClusterNode.cluster_id == subquery1.c.cluster_id).subquery()
                            for line in self.session.query(AtomSystem.ip, AtomSystem.uuid, AtomSystem.type, AtomSystem.id, AtomSystem.name).filter(AtomSystem.id == subquery2.c.ci_instance_id, AtomSystem.id != obj.id).all():
                                item = {
                                    "uuid": line.uuid,
                                    "type": line.type,
                                    "level": "%s" % (int(probe_dict["level"]) + 1),
                                    "id": line.id,
                                    "name": line.name
                                }
                                ret["component"].append(item)

                            for datasource in cluter.get("datasource", []):
                                datasources.append(datasource)

                            break

                        #如果原子没有数据源且地址没有与service_ip，使用集群的数据源
                        elif not datasources:
                            for datasource in cluter.get("datasource", []):
                                datasources.append(datasource)

                    """
                    解析数据源
                    """
                    for datasource in datasources:
                        for url in datasource.get("url", []):
                            item = {
                                "url": url,
                                "level": "%s" % (int(probe_dict["level"]) + 1),
                                "type": "datasource"
                            }

                            ret["backend"].append(item)

                    """
                    解析foregin address
                    如果未发现后端的任何url且type不为datasource，
                    通过foreign address进行解析
                    """
                    if not ret["backend"] and probe_dict.get("type", "") != "datasource":
                        connections = config_dict.get("connections", {})
                        for listen_sock in config_dict["base_info"]["listen"]:
                            connections.pop(listen_sock.split(":")[-1], "")
                        for port in connections:
                            for ip_port in connections[port]:
                                if "127.0.0.1" not in ip_port:
                                    item = {
                                        "url": ip_port,
                                        "level": "%s" % (int(probe_dict["level"]) + 1)
                                    }
                                    ret["backend"].append(item)

                    """
                    防止死循环
                    当检测到后端的某个ip，在前面的层级中出现了，就会发生死循环
                    """
                    for backend in ret["backend"]:
                        for i in range(int(backend["level"]) + 1):
                            if backend["url"] in self.all_ip_port[i]:
                                raise BusinessException("url探测发生死循环，发生死循环的url：%s" %backend["url"])

                    return ret
        return ret

    def probe_loadbalance(self, probe_dict):
        """
        return: {
            "url": "",
            "uuid": "",
            "type": "",
            "level": ""
        }
        """

        ret = {
            "component": [],
            "backend": [],
        }

        probe_info = self.get_probe_info(probe_dict["url"])

        #遍历所有的F5
        subquery = self.session.query(MonitorHost.uuid).filter(MonitorHost.host_type == "Load_Balance").subquery()
        for obj in self.session.query(HostConfig.config, HostConfig.uuid).filter(subquery.c.uuid == HostConfig.uuid).all():
            #获取F5的配置
            config_dict = obj.config

            #遍历F5中的VirtualServer
            for virtual_server in config_dict["VirtualServer"]:

                #匹配url中的ip:port
                if virtual_server["VirtualServAddr"] == probe_info["ip"] and virtual_server["VirtualServPort"] == probe_info["port"]:
                    # if re.search(r"%s" %(virtual_server["VirtualServName"].strip("/")), probe_info["path"]):

                    if not self.all_ip_port.get(int(probe_dict["level"]) + 1):
                        self.all_ip_port[int(probe_dict["level"]) + 1] = []
                    self.all_ip_port[int(probe_dict["level"]) + 1].extend("%s:%s" %(probe_info["ip"], probe_info["port"]))

                    item = {
                        "uuid": obj.uuid,
                        "type": "Load_Balance",
                        "level": "%s" %(int(probe_dict["level"]) + 1),
                        "id": "",
                        "name": ""
                    }
                # atom_system = self.session.query(AtomSystem.id, AtomSystem.name).filter(AtomSystem.uuid == obj.uuid).first()
                # item = {
                #     "uuid": obj.uuid,
                #     "type": "Load_Balance",
                #     "level": "%s" %(int(probe_dict["level"]) + 1),
                #     "id": atom_system.id,
                #     "name": atom_system.name
                # }
                    ret["component"].append(item)

                    this_pool = virtual_server["VirtualServDefaultPool"]

                    #遍历F5中的pool，找出后端的server
                    for pool in config_dict["Pool"]:
                        if pool["PoolName"] == this_pool:
                            #遍历后端的server
                            for member in pool["PoolMember"]:
                                if member["PoolMemberEnableState"] == "enabled":
                                    item = {
                                        "url": "%s://%s:%s%s" %(probe_info["protocol"], member["PoolMemberAddr"], member["PoolMemberPort"], probe_info["path"]),
                                        "level": "%s" % (int(probe_dict["level"]) + 1),
                                    }
                                    ret["backend"].append(item)

                            return ret
        return ret

    def recursion_probe(self, probe_dict):
        ret = []

        #迭代查询
        try:
            if probe_dict["url"]:
                result = self.probe_atom_system(probe_dict)
                if result["component"]:
                    ret.extend(result["component"])

                    for backend_dict in result["backend"]:
                        ret.extend(self.recursion_probe(backend_dict))

                else:
                    result = self.probe_loadbalance(probe_dict)
                    if result["component"]:
                        ret.extend(result["component"])

                    for backend_dict in result["backend"]:
                        ret.extend(self.recursion_probe(backend_dict))

            self.session.close()

            return [dict(t) for t in {tuple(d.items()) for d in ret}]

        except Exception as e:
            self.session.close()
            raise BusinessException(e)
