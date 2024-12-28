import re
from scan_service.lib.common import ParseViaSSH

class ApacheParse(ParseViaSSH):
    def __init__(self, ssh, passwd):
        super(ApacheParse, self).__init__(ssh = ssh, passwd = passwd)
        self.include_pattern = re.compile(r"(?:^|\n)\s*Include.*?\s+(.*)")
        self.include = []
        self.log = []

    def get_all_content(self, file_content, server_root):
        """
        include所有文件内容，获取完整的文件内容
        """
        server_root = server_root
        for line in self.include_pattern.findall(file_content):
            if re.search("^/", line.strip()):
                item = self.exec_shell("ls %s 2>/dev/null | tr '' '\n'" %line.strip())
                self.include.extend(item)
            else:
                item = self.exec_shell("ls %s 2>/dev/null | tr '' '\n'" %(server_root + "/" + line.strip()))
                self.include.extend(item)

            #读取文件内容
            new_content = ""
            for file in item:
                new_content = new_content + "\n" + self.get_file_content(file)
            file_content = file_content.replace(line, self.get_all_content(new_content, server_root))

        return file_content

    def get_config(self, file_content, exec_file, server_root = None):

        #获取server_root
        server_root_pattern = r"(?:^|\n)\s*ServerRoot[\s\"']+([^\"'\s]+)"
        server_root_match = re.search(server_root_pattern, file_content)
        if server_root_match:
            server_root = server_root_match.group(1)
        else:
            for line in self.exec_shell("%s -V" % exec_file):
                if "HTTPD_ROOT" in line:
                    server_root = line.split("\"")[1]

        #获取配置文件所有内容（包括include的内容）
        content = self.get_all_content(file_content, server_root)

        #获取日志信息
        log_pattern = r"(?:^|\n)\s*(CustomLog|ErrorLog)[\s\"']+([^\"'\s]+)"
        for line in re.findall(log_pattern, content) :
            if re.search("^/", line[1].strip()):
                self.log.append(line[1].strip())
            else:
                self.log.append(server_root + "/" + line[1].strip())

        return []

    # def get_config(self, file_content, exec_file, server_root = None):
    #     """
    #     递归函数，读取所有的配置文件
    #     :param file_content:
    #     :param exec_file:
    #     :param server_root: 刚开始server_root为None，当找到sever_root后，就置为相应的目录
    #     :return:
    #     """
    #     ret = {"include": [], "log": [], "cluster": [] }
    #
    #     include_pattern = r"(?:^|\n)(?:(?!#).)*Include.*?\s+(.*)"
    #     server_root_pattern = r"(?:^|\n)(?:(?!#).)*ServerRoot[\s\"']+([^\"'\s]+)"
    #     log_pattern = r"(?:^|\n)(?:(?!#).)*(CustomLog|ErrorLog)[\s\"']+([^\"'\s]+)"
    #     cluster_pattern = r"(?:^|\n)(?:(?!#).)*<Proxy balancer://([^/\"'\s]+).*?>([\S\s]*)</Proxy>"
    #
    #     #获取ServerRoot路径
    #     if not server_root:
    #         result = re.search(server_root_pattern, file_content)
    #         if result:
    #             server_root = result.group(1)
    #         else:
    #             for line in self.exec_shell("%s -V" %exec_file):
    #                 if "HTTPD_ROOT" in line:
    #                     server_root = line.split("\"")[1]
    #
    #     #获取include的文件列表
    #     for line in re.findall(include_pattern, file_content):
    #         if re.search("^/", line.strip()):
    #             item = self.exec_shell("ls %s 2>/dev/null | tr '' '\n'" %line.strip())
    #             ret["include"].extend(item)
    #         else:
    #             item = self.exec_shell("ls %s 2>/dev/null | tr '' '\n'" %(server_root + "/" + line.strip()))
    #             ret["include"].extend(item)
    #
    #     #获取配置的日志文件
    #     for line in re.findall(log_pattern, file_content) :
    #         if re.search("^/", line[1].strip()):
    #             ret["log"].append(line[1].strip())
    #         else:
    #             ret["log"].append(server_root + "/" + line[1].strip())
    #
    #     # #获取集群信息
    #     for cluster in re.findall(cluster_pattern, file_content):
    #
    #         item = {}
    #         item["name"] = cluster[0].strip()
    #         item["instance"] = []
    #         for line in cluster[1].split('\n'):
    #
    #             #匹配server字段，并匹配是否设置了端口号
    #             match = re.search(r"^(?:(?!#).)*BalancerMember.*/((?:[^\s/\"':]+:\d+)|(?:[^\s/\"':]+))", line.strip())
    #
    #             if match:
    #                 instance = {}
    #                 instance["role"] = "member"
    #                 instance["type"] = ""
    #                 instance["status"] = ""
    #                 instance["listen"] = [ match.group(1) ]
    #
    #                 #将域名都转换成ip
    #                 if not re.search(global_var.ip_pattern, match.group(1)):
    #                     temp_list = match.group(1).split(":")
    #                     temp_list[0] = self.get_ip_from_hostname(temp_list[0])[0]
    #                     instance["listen"] = [ ':'.join(temp_list) ]
    #
    #                 if not ":" in match.group(1):
    #
    #                     if "http://" in match.group():
    #                         instance["listen"][0] = instance["listen"][0] + ":80"
    #
    #                     elif "https://" in match.group():
    #                         instance["listen"][0] = instance["listen"][0] + ":443"
    #
    #                 item["instance"].append(instance)
    #
    #         ret["cluster"].append(item)
    #
    #     for file in ret["include"]:
    #         result = self.get_config(file, exec_file, server_root = server_root)
    #         ret["log"].extend(result["log"])
    #         ret["cluster"].extend(result["cluster"])
    #
    #     return ret

    def parse_apache(self, filename, exec_file):
        """
        nginx的配置文件的特点：
            以分号分隔配置项
            不能include一个目录
        :param filename:
        :return:
        """

        ret = {"conf_file": [], "log_file": [], "cluster": []}

        file_content = self.get_file_content(filename)
        ret["conf_file"] = list(set(self.include))
        ret["log_file"] = list(set(self.log))
        ret["cluster"] = self.get_config(file_content, exec_file)

        return ret
