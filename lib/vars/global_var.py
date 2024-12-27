
#脚本接收的位置参数
global args_list

#用于匹配ip的正则
ip_pattern = r"(?:[0-9]{1,3}\.){3}(?!255)[0-9]{1,3}"
except_ip_pattern = r"^(127|169)"
mac_pattern = r"([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})"
# except_ip_pattern = r"^(?!127|169).(?:[0-9]{1,3}\.){2}(?!255|0)[0-9]{1,3}$"

global global_config

except_filesystems = ["overlay", "tmpfs", "devtmpfs", "squashfs"]

import re
ip_match = re.compile(ip_pattern)
except_ip_match = re.compile(except_ip_pattern)
mac_match = re.compile(mac_pattern)
size_match = re.compile(r"(\d+[.\d]+)\s*([a-zA-Z]+)")
uuid_match = re.compile(r"^[a-z0-9-]+$", re.IGNORECASE)
num_match = re.compile(r"^\d+$")

manufacturer_mapping = {
    "vmware": "VMware",
    "dell": "Dell",
    "inspur": "Inspur",
    "lenovo": "Lenovo",
    "o.e.m": "O.E.M",
    "h3c": "H3C",
    "huawei": "Huawei",
    "zte": "ZTE",
    "fiberhome": "Fiberhome"
}