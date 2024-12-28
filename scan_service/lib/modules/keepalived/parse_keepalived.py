from scan_service.lib.common import ParseViaSSH
import re
from scan_service.lib.vars import global_var

class KeepalivedParse(ParseViaSSH):
    def __init__(self, ssh, passwd):
        super(KeepalivedParse, self).__init__(ssh = ssh, passwd = passwd)
        self.vrrp_instance_pattern = re.compile(r"(?:^|\n)\s*vrrp_instance\s*\S+\s*{(({[\s\S]+?})|([^{}]+))*}")
        self.unicast_peer_pattern = re.compile(r"(?:^|\n)\s*unicast_peer\s*{(({[\s\S]+?})|([^{}]+))*}")
        self.virtual_ipaddress_pattern = re.compile(r"(?:^|\n)\s*virtual_ipaddress\s*{(({[\s\S]+?})|([^{}]+))*}")

    def get_config(self, file_config):
        ret = []

        match = self.vrrp_instance_pattern.finditer(file_config)

        for instance in match:
            item = {
                "peer_ip": [],
                "vip": []
            }
            vrrp_content = instance.group()

            match = self.unicast_peer_pattern.search(vrrp_content)
            if match:
                for ip in global_var.ip_match.finditer(match.group()):
                    item["peer_ip"].append(ip.group())

            match = self.virtual_ipaddress_pattern.search(vrrp_content)
            if match:
                for ip in global_var.ip_match.finditer(match.group()):
                    item["vip"].append(ip.group())

            if item["vip"]:
                ret.append(item)

        return ret

    def parse_keepalived(self, conf_file):
        ret = {
            "config": []
        }
        content = self.get_file_content(conf_file, comments = "#!")
        ret["config"] = self.get_config(content)

        return ret