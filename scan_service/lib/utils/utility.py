import os
import socket
import re
from scan_service.lib.vars import global_var

"""
简单工具类
"""

class MyList(list):
    """
    在list的基础上，实现新的list类，添加处理IndexError异常的功能
    """
    def __getitem__(self, y):
        try:
            return super(MyList, self).__getitem__(y)
        except IndexError:
            return ""


class MyInt(int):

    def __new__(cls, n, *args, **kwargs):
        return super(MyInt, cls).__new__(cls, n)

    def __init__(self, n, max):
        int.__init__(n)
        self.max = max

    def __add__(self, *args, **kwargs):
        if self >= self.max - 1:
            return MyInt(0, self.max)
        else:
            return MyInt(super(MyInt, self).__add__(*args, **kwargs), self.max)

def get_dir(path,n):
    """
    获取文件上层目录
    :param path: absolute path
    :param n: recursion number
    :return: directory path
    """
    for i in range(1,n+1):
        path = os.path.dirname(path)
    return path

def size(bytes):
    """
    将字节格式化成合适的单位
    :param bytes: 字节数（int类型）
    :return: 返回一个string
    """
    traditional = [
        (1024 ** 5, 'P'),
        (1024 ** 4, 'T'),
        (1024 ** 3, 'G'),
        (1024 ** 2, 'M'),
        (1024 ** 1, 'K'),
        (1024 ** 0, 'B'),
    ]

    for factor, suffix in traditional:
        if bytes >= factor:
            break
    amount = round(bytes / factor, 2)
    if isinstance(suffix, tuple):
        singular, multiple = suffix
        if amount == 1:
            suffix = singular
        else:
            suffix = multiple
    return str(amount) + suffix

def seconds_format(seconds):
    """
    将秒数格式化成合适的单位
    :param seconds: 秒数（int类型）
    :return: 返回一个string
    """
    seconds = int(seconds)
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    d, h = divmod(h, 24)
    if d != 0:
        return "%s days %s hours %s minutes" %(d, h, m)
    elif h !=0:
        return "%s hours %s minutes" %(h, m)
    else:
        return "%s minutes %s seconds" %(m, s)

def string_to_bytes(size_tring):
    """
    当带大小单位的string转换成bytes
    支持的格式：
        "10 GB" "10 G" "10GB "10G"
        "10 gb" "10 gB"等
    """
    traditional = [
        (1024 ** 5, 'P'),
        (1024 ** 4, 'T'),
        (1024 ** 3, 'G'),
        (1024 ** 2, 'M'),
        (1024 ** 1, 'K'),
        (1, 'B')
    ]

    try:
        match = global_var.size_match.search(size_tring)
        if match:
            num = float(match.group(1))
            unit = match.group(2)[0].upper()
        else:
            return 0
    except Exception:
        return 0

    for factor, suffix in traditional:
        if unit == suffix:
            return num * factor

def get_local_ip():
    """
    获取本地对外通信使用的ip
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.connect(('8.8.8.8', 80))
    return sock.getsockname()[0]

def get_ip_from_hostname(hostname):
    """
    根据主机名获取ip列表
    """
    ret = []
    if hostname:
        try:
            result = socket.gethostbyname_ex(hostname)
            ret = result[2]
        except Exception:
            ret = [ hostname ]
    return ret

def kv_to_dict(kv_list, separator = "="):
    ret = {}

    for line in kv_list:
        try:
            ret[line.split(separator)[0].strip()] = line.split(separator)[1].strip()
        except Exception:
            pass

    return ret

def get_speed_type(speed):

    if 100 <= int(speed) < 1000:
        return "100M"
    elif 1000 <= int(speed) < 10000:
        return "1000M"
    elif 10000 <= int(speed):
        return "10G"
    else:
        return "unknown"

def parse_jdbc(jdbc):
    ret = {}
    jdbc = jdbc.lower()
    pattern = r"([0-9a-zA-Z.]+:[0-9]+)[/:]([0-9a-zA-Z]+)"
    match = re.search(pattern, jdbc)
    if match:
        ret["driver"] = jdbc.split(":")[1].lower()
        ret["url"] = [match.group(1)]
        ret["database"] = match.group(2)
    return ret

def format_socket(sock, local_ip_list):
    ret = []
    if ":::" in sock or "*" in sock or '[::]:' in sock:
        port = sock.split(':')[-1]
        # pid_dict[pid]["base_info"]["listen"].remove(item)
        for ip in local_ip_list:
            ret.append("%s:%s" % (ip, port))
    else:
        ip = global_var.ip_match.search(sock)
        if ip and ip.group() != "127.0.0.1":
            port = sock.split(':')[-1]
            # pid_dict[pid]["base_info"]["listen"].remove(item)
            ret.append("%s:%s" % (ip.group(), port))

    return ret

def version_format(version):
    ret = []
    flag = True
    for i in version.split("."):
        if flag:
            match = global_var.num_match.search(i)
            if match:
               ret.append("%010d" %int(match.group()))
            else:
                ret.append(i)
                flag = False
        else:
            ret.append(i)

    return '.'.join(ret)


