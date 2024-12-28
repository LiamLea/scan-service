import xmltodict
import os
import json
import re
from scan_service.lib.common import ParseViaSSH
from scan_service.lib.vars import global_var
import traceback
from scan_service.lib.framework import logger
from scan_service.lib.utils import parse_jdbc
from scan_service.lib.utils import get_ip_from_hostname
from scan_service.lib.utils import MyList


class WeblogicParse(ParseViaSSH):
    def __init__(self, ssh, passwd):
        super(WeblogicParse, self).__init__(ssh = ssh, passwd = passwd)
        self.local_ip_list = self.get_local_ip()

    def format_config(self, filename):

        # 读取配置文件，并转换为字典类型
        my_dict = xmltodict.parse(self.get_file_content(filename), xml_attribs=False)
        my_dict = json.loads(json.dumps(my_dict))

        # 调整字典的格式
        config_dict = {
            "name": "",
            "admin_server": "",
            "server": [],
            "cluster": [],
            "app": [],
            "machine": [],
            "jdbc": []
        }

        config_dict["name"] = my_dict["domain"].get("name", "unknown")
        config_dict["admin_server"] = my_dict["domain"].get("admin-server-name", "AdminServer")

        try:
            if isinstance(my_dict["domain"]["server"], dict):
                config_dict["server"].append(my_dict["domain"]["server"])
            else:
                config_dict["server"] = my_dict["domain"]["server"]
        except Exception:
            pass

        if my_dict["domain"].get("cluster"):
            if isinstance(my_dict["domain"]["cluster"], dict):
                config_dict["cluster"].append(my_dict["domain"]["cluster"])
            else:
                config_dict["cluster"] = my_dict["domain"]["cluster"]

        if my_dict["domain"].get("app-deployment"):
            if isinstance(my_dict["domain"]["app-deployment"], dict):
                config_dict["app"].append(my_dict["domain"]["app-deployment"])
            else:
                config_dict["app"] = my_dict["domain"]["app-deployment"]

        if my_dict["domain"].get("machine"):
            if isinstance(my_dict["domain"]["machine"], dict):
                config_dict["machine"].append(my_dict["domain"]["machine"])
            else:
                config_dict["machine"] = my_dict["domain"]["machine"]

            temp_dict = {}
            for item in config_dict["machine"]:
                temp_dict[item["name"]] = item["node-manager"]
            config_dict["machine"] = temp_dict

        if my_dict["domain"].get("jdbc-system-resource"):
            if isinstance(my_dict["domain"]["jdbc-system-resource"], dict):
                config_dict["jdbc"].append(my_dict["domain"]["jdbc-system-resource"])
            else:
                config_dict["jdbc"] = my_dict["domain"]["jdbc-system-resource"]

        return config_dict

    def parse_domain(self, config_dict, filename):
        """
        该函数根据用于解析出domain的信息
        :param
            config_dict: 经过格式化的字典，存储的是配置信息
            pid_dict：实例的信息
        :return:
            ret = {
                "name": "",
                "cluster": [],
                "member": [
                    "name": "",
                    "role": "",
                    "listen": [],
                    "status": "",
                    "cluster": "临时的，为了方便后面分析集群数据",
                ]
            }
        """
        ret = {
            "name": "",
            "cluster": [],
            "member": [],
            "datasource": {}
        }

        ret["name"] = config_dict.get("name", "")

        for server in config_dict.get("server", []):

            item = {"name":"", "role": "", "listen": [], "status": ""}

            item["name"] = server.get("name", "")

            if server["name"] == config_dict["admin_server"]:

                item["role"] = "admin"
                item["listen"] = [server["listen-address"]] if server.get("listen-address") else []

            else:
                item["role"] = "managed"

                #默认"listen-address"必须是填写的，不填写默认监听的是所在机器的所有地址，解析就会出现偏差
                if server.get("listen-port") and server["listen-port"]:

                    if server.get("listen-address") and server["listen-address"]:
                        # 判断listen-address是否为空，如果为空，则监听本地所有地址
                        item["listen"].append("%s:%s" %(server["listen-address"], server["listen-port"]))

                    elif server.get("machine") and config_dict["machine"][server["machine"]].get("listen-address") and config_dict["machine"][server["machine"]]["listen-address"]:
                        item["listen"].append("%s:%s" %(config_dict["machine"][server["machine"]]["listen-address"], server["listen-port"]))

                    else:
                        for ip in self.local_ip_list:
                            item["listen"].append("%s:%s" % (ip, server["listen-port"]))

            if server.get("cluster"):
                item["cluster"] = server["cluster"]

            ret["member"].append(item)

        for machine in config_dict.get("machine", []):
            item = {"name":"", "role": "", "listen": [], "status": ""}
            item["name"] = machine
            item["role"] = "manager"

            #machine需要明确指定ip和port，不然无法连接
            if config_dict["machine"][machine].get("listen-port") and config_dict["machine"][machine]["listen-port"] and config_dict["machine"][machine].get("listen-address") and config_dict["machine"][machine]["listen-address"]:
            # item["listen"].append("%s:%s" %(config_dict["machine"][machine]["listen-address"], config_dict["machine"][machine]["listen-port"]))
                item["listen"].append("%s:%s" % (config_dict["machine"][machine]["listen-address"], config_dict["machine"][machine]["listen-port"]))

                ret["member"].append(item)

        for cluster in config_dict.get("cluster", []):
            ret["cluster"].append(cluster["name"])

        for jdbc in config_dict.get("jdbc", []):
            if jdbc.get("target"):

                item = {}
                target = jdbc["target"]
                item["name"] = jdbc.get("name", "")

                try:
                    path = os.path.dirname(filename) + '/' + jdbc["descriptor-file-name"]
                    result = xmltodict.parse(self.get_file_content(path), xml_attribs=False)
                    jdbc_dict = json.loads(json.dumps(result))

                    if jdbc_dict["jdbc-data-source"].get("jdbc-driver-params"):
                        # jdbc_dict["jdbc-data-source"]["jdbc-driver-params"]["driver-name"]
                        jdbc = jdbc_dict["jdbc-data-source"]["jdbc-driver-params"].get("url", "").lower()
                        jdbc_parse = parse_jdbc(jdbc)

                        if jdbc_parse:
                            item["driver"] = jdbc_parse["driver"]
                            item["url"] = []
                            for url in jdbc_parse["url"]:
                                item["url"].append(
                                    "%s:%s" % (get_ip_from_hostname(url.split(":")[0])[0], url.split(":")[1]))
                            item["database"] = jdbc_parse["database"]
                        else:
                            item["driver"] = MyList(jdbc.split(":"))[1]
                            item["url"] = []
                            for host, port in re.findall(r"host=(.*?).*?port=([0-9]+)", jdbc):
                                item["url"].append("%s:%s" % (get_ip_from_hostname(host)[0], port))

                            database = re.search(r"SERVICE_NAME=([0-9a-zA-Z])+", jdbc)
                            if database:
                                item["database"] = database.group(1)

                        ret["datasource"][target] = item
                except Exception:
                    logger.error("jdbc文件解析失败：%s" % traceback.format_exc())

        return ret

    def parse_cluster(self, config_dict, domain_info):
        ret = {}

        for cluster in config_dict.get("cluster", []):
            ret[cluster["name"]] = {
                "type": "Cluster",
                "instance": [],
                "app": [],
                "datasource": []
            }

        for server in domain_info.get("member", []):
            if server.get("cluster") and ret.get(server["cluster"]):
                item = {}
                item["name"] = server["name"]
                item["role"] = "member"
                item["listen"] = server["listen"]
                item["status"] = server["status"]
                item["type"] = "weblogic"
                ret[server["cluster"]]["instance"].append(item)
                server.pop("cluster")

        for app in config_dict.get("app", []):
            if app.get("target"):
                for target in app["target"].split(","):
                    if ret.get(target):
                        item = {}
                        item["name"] = app.get("name", "")
                        item["location"] = app.get("source-path", "")
                        item["module-type"] = app.get("module-type", "")
                        if ret.get(target):
                            ret[target]["app"].append(item)

        for targets, datasource in domain_info["datasource"].items():
            for target in targets.split(","):
                # 判断该jdbc是否应用在该cluster上
                if ret.get(target):
                    ret[target]["datasource"].append(item)
        # for jdbc in config_dict.get("jdbc", []):
        #     if jdbc.get("target"):
        #
        #
        #         for target in jdbc["target"].split(","):
        #             # 判断该jdbc是否应用在该cluster上
        #             if ret.get(target):
        #
        #                 item = {}
        #                 item["name"] = jdbc.get("name", "")
        #
        #                 try:
        #                     path = os.path.dirname(filename) + '/' + jdbc["descriptor-file-name"]
        #                     result = xmltodict.parse(self.get_file_content(path), xml_attribs=False)
        #                     jdbc_dict = json.loads(json.dumps(result))
        #
        #                     if jdbc_dict["jdbc-data-source"].get("jdbc-driver-params"):
        #                         # jdbc_dict["jdbc-data-source"]["jdbc-driver-params"]["driver-name"]
        #                         jdbc = jdbc_dict["jdbc-data-source"]["jdbc-driver-params"].get("url", "").lower()
        #                         jdbc_parse = parse_jdbc(jdbc)
        #
        #                         if jdbc_parse:
        #                             item["driver"] = jdbc_parse["driver"]
        #                             item["url"] = []
        #                             for url in jdbc_parse["url"]:
        #                                 item["url"].append("%s:%s" %(get_ip_from_hostname(url.split(":")[0])[0], url.split(":")[1]))
        #                             item["database"] = jdbc_parse["database"]
        #                         else:
        #                             item["driver"] = MyList(jdbc.split(":"))[1]
        #                             item["url"] = []
        #                             for host,port in re.findall(r"host=(.*?).*?port=([0-9]+)", jdbc):
        #                                 item["url"].append("%s:%s" %(get_ip_from_hostname(host)[0], port))
        #
        #                             database = re.search(r"SERVICE_NAME=([0-9a-zA-Z])+", jdbc)
        #                             if database:
        #                                 item["database"] = database.group(1)
        #
        #                         ret[target]["datasource"].append(item)
        #                 except Exception:
        #                     logger.error("jdbc文件解析失败：%s" %traceback.format_exc())

        temp_dict = ret
        ret = []
        for cluster in temp_dict:
            item = temp_dict[cluster]
            item["name"] = cluster
            ret.append(item)

        return ret

    def parse_weblogic(self, filename):

        ret = {"domain": {}, "cluster": []}

        config_dict = self.format_config(filename)

        ret["domain"] = self.parse_domain(config_dict, filename)
        ret["cluster"] = self.parse_cluster(config_dict, ret["domain"])
        for cluster in ret["cluster"]:
            cluster["uuid"] = ""

        return ret