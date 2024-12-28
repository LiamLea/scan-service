from scan_service.lib.utils import SSH
from scan_service.lib.utils import SHELL
import re

# from lib.modules.nginx.parse_nginx import NginxParse

host = "3.1.5.19"
port = "22"
user = "root"
passwd = "Cangoal_123"
ssh = SSH(host, port, user, passwd)
shell = SHELL(ssh = ssh, passwd = passwd)

content = shell.get_file_content("/etc/keepalived/keepalived.conf", comments="!#")
print(content)

stream_pattern = re.compile(r"(?:^|\n)\s*stream\s*{(({[\s\S]+?})|([^{}]+))*}")
http_pattern = re.compile(r"(?:^|\n)\s*http\s*{(({[\s\S]+?})|([^{}]+))*}")
include_pattern = re.compile(r"(?:^|\n)\s*include(.*?);")
upstream_pattern = re.compile(r"(?:^|\n)\s*upstream\s*(\S+)\s*{(({[\s\S]+?})|([^{}]+))*}")
listen_pattern = re.compile(r"(?:^|\n)\s*listen(.*?);")
location = r"(?:^|\n)\s*location\s*(\S+)\s*{(({[\s\S]+?})|([^{}]+))*}"\


comment_pattern = r"(?:^|\n)(\s*[#!].*|\s*)(?=\n)"