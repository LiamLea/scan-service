import re
from scan_service.lib.common import ParseViaSSH
from scan_service.lib.utils import MyList
from ..keepalived import KeepalivedScan
import hashlib

class NginxParse(ParseViaSSH):
    def __init__(self, ssh, passwd):
        super(NginxParse, self).__init__(ssh = ssh, passwd = passwd)

        #pattern
        self.include_pattern = re.compile(r"(?:^|\n)\s*include(.*?);")
        self.log_pattern = re.compile(r"(?:^|\n)\s*(error_log|access_log)\s+(\S+).*?;")
        self.upstream_pattern = re.compile(r"(?:^|\n)\s*upstream\s*(\S+)\s*{(({[\s\S]+?})|([^{}]+))*}")
        self.server_pattern = re.compile(r"(?:^|\n)\s*server\s*{(({[\s\S]+?})|([^{}]+))*}")
        self.listen_pattern = re.compile(r"(?:^|\n)\s*listen(.*?);")
        self.proxy_pass_pattern = re.compile(r"(?:^|\n)\s*proxy_pass\s+(?:(?:\S+)://)?(\S+);")

        #保存nginx的默认配置
        self.prefix = ""

        #文件列表
        self.include = []
        self.log = []

    def get_default_config(self, exec_file):
        result = self.exec_shell("%s -h" %exec_file, get_error = True)
        for line in result:
            if "-p prefix" in line:
                match = re.search(r"\(default: (.*?)\)", line)
                if match:
                    self.prefix = match.group(1).strip().rstrip("/")

    def get_all_content(self, file_content):
        """
        include所有文件内容，获取完整的文件内容
        """
        for line in self.include_pattern.finditer(file_content):
            path = line.group(1).strip()
            if path[0] != "/":
                path = self.prefix + "/conf/" + path
            item = self.exec_shell("ls %s 2>/dev/null | tr '' '\n'" %path)
            self.include.extend(item)

            #读取文件内容
            new_content = ""
            for file in item:
                new_content = new_content + "\n" + self.get_file_content(file)
            file_content = file_content.replace(line.group(), self.get_all_content(new_content))
        return file_content

    def parse_top_context(self, file_content, context):
        """
        分析stream context，获取cluster信息
        """
        ret = []

        cluster = {}

        #解析upstream context
        for match in self.upstream_pattern.finditer(file_content):
            item = {}
            item["name"] = match.group(1)
            item["type"] = "Loadbalance"
            item["proxy"] = {
                "listen": [],
                "server_name": [],
                "url": []
            }
            item["instance"] = []

            #server的格式 ip:port，ip可能是域名
            for server in match.group(2).split(";"):
                server = server.strip()
                if server != "" and server.split()[0].lower() == "server":
                    instance = {}
                    instance["role"] = "member"
                    instance["type"] = ""
                    instance["status"] = ""
                    instance["listen"] = []

                    listen = server.split()
                    if ":" in listen[1]:
                        hostname = listen[1].split(":")[0]
                        port = listen[1].split(":")[1]
                    else:
                        hostname = listen[1]
                        port = "80"

                    instance["listen"].append("%s:%s" % (self.get_ip_from_hostname(hostname)[0], port))
                    item["instance"].append(instance)

            cluster[item["name"]] = item

        #解析server context
        for match in self.server_pattern.finditer(file_content):

            #用于标识该server管理哪个集群
            cluster_name = ""

            #获取proxy_pass信息
            if context == "stream":
                proxy = self.proxy_pass_pattern.search(match.group())
                if proxy and cluster.get(proxy.group(1).strip()):
                    cluster_name = proxy.group(1).strip()

            elif context == "http":
                for location in re.finditer(r"(?:^|\n)\s*location\s*(\S+)\s*{(({[\s\S]+?})|([^{}]+))*}", match.group()):
                    proxy = self.proxy_pass_pattern.search(location.group())
                    if proxy and cluster.get(proxy.group(1).split("/")[0]):
                        cluster_name = proxy.group(1).split("/")[0]
                        cluster[cluster_name]["proxy"]["url"].append(location.group(1))

            if cluster_name:
                #获取listen信息
                for listen in self.listen_pattern.finditer(match.group()):
                    ip_port = MyList(listen.group(1).strip().split())[0]

                    #如果只有端口号
                    if re.search(r"^\d+$", ip_port):
                        cluster[cluster_name]["proxy"]["listen"].extend(["%s:%s" % (i, ip_port) for i in self.get_local_ip()])
                    #如果有hostname和port
                    elif ":" in ip_port:
                        cluster[cluster_name]["proxy"]["listen"].append("%s:%s" % (self.get_ip_from_hostname(ip_port.split(":")[0])[0], ip_port.split(":")[1]))
                    #只有hostname
                    else:
                        cluster[cluster_name]["proxy"]["listen"].append("%s:80" %self.get_ip_from_hostname(ip_port)[0])

                if not cluster[cluster_name]["proxy"]["listen"]:
                    cluster[cluster_name]["proxy"]["listen"].extend(["%s:80" %i for i in self.get_local_ip()])

                #获取server_name信息
                if context == "http":
                    server_name = re.search(r"(?:^|\n)\s*server_name(.*?);", match.group())
                    if server_name:
                        cluster[cluster_name]["proxy"]["server_name"].extend(server_name.group(1).strip().split())

                #去重
                cluster[cluster_name]["proxy"]["listen"] = list(set(cluster[cluster_name]["proxy"]["listen"]))
                cluster[cluster_name]["proxy"]["server_name"] = list(set(cluster[cluster_name]["proxy"]["server_name"]))

                ret.append(cluster[cluster_name])

        return ret

    def get_config(self, file_content):
        """"
        递归函数，读取所有的配置文件
        file_content是 过滤了 注释和空行 的配置文件 的内容
        """

        cluster = []

        content = self.get_all_content(file_content)

        #获取日志文件
        for line in self.log_pattern.findall(content):
            self.log.append(line[1].strip())
        if len(self.log) < 2:
            access_log = self.exec_shell("ls %s 2>/dev/null | tr '' '\n'" % (self.prefix + "/" + "logs/access.log"))
            self.log.extend(access_log)
            error_log = self.exec_shell("ls %s 2>/dev/null | tr '' '\n'" % (self.prefix + "/" + "logs/error.log"))
            self.log.extend(error_log)

        # 匹配stream context
        stream_pattern = re.compile(r"(?:^|\n)\s*stream\s*{(({[\s\S]+?})|([^{}]+))*}")
        # 匹配http context
        http_pattern = re.compile(r"(?:^|\n)\s*http\s*{(({[\s\S]+?})|([^{}]+))*}")

        #解析stream context内容
        match = stream_pattern.search(content)
        if match:
            cluster.extend(self.parse_top_context(match.group(), context = "stream"))

        #解析http context内容
        match = http_pattern.search(content)
        if match:
            cluster.extend(self.parse_top_context(match.group(), context = "http"))

        return cluster

    def check_keepalived(self, init_info):
        cluster = {}
        result = KeepalivedScan(init_info).format_output()
        if result and result[0]["config"]:
            cluster["service_ip"] = result[0]["config"][0]["vip"][0]
            # cluster["uuid"] = hashlib.md5((''.join(sorted(result[0]["config"][0]["vip"]))).encode()).hexdigest()
            # cluster["name"] = "nginx-%s" %cluster["uuid"]
            cluster["type"] = "HA"
            cluster["instance"] = []

        return cluster

    def parse_nginx(self, filename, init_info, exec_file):
        """
        nginx的配置文件的特点：
            以分号分隔配置项
            不能include一个目录
        :param filename:
        :return:
        """

        ret = {"conf_file": [], "log_file": [], "cluster": [], "keepalived_cluster": {}}

        self.get_default_config(exec_file)

        file_content = self.get_file_content(filename)
        ret["cluster"] = self.get_config(file_content)
        ret["conf_file"] = list(set(self.include))
        ret["log_file"] = list(set(self.log))
        ret["keepalived_cluster"] = self.check_keepalived(init_info)

        return ret