try:
    import easysnmp
    from easysnmp import exceptions
except:
    pass

class MyList(list):
    """
    在list的基础上，实现新的list类，添加处理IndexError异常的功能
    """
    def __getitem__(self, y):
        try:
            return super(MyList, self).__getitem__(y)
        except IndexError:
            return ""


class SNMP:

    def __init__(self, credential_dict, **kwargs):
        self.credential_dict = credential_dict
        self.session = easysnmp.Session(**self.credential_dict, use_sprint_value = True, abort_on_nonexistent = True, **kwargs)
        self.test_credential()

    def snmp_walk(self, oid, return_dict=False):
        """
        :param oid: 指定Oid
        :param return_dict: 默认为False，当为True时，返回字典类型
        :param reserve_number: 当返回字典时，就取指定位数的oid作为key
        :param map_dict: 对结果进行映射
        :return:
        """
        if return_dict:
            ret = {}
        else:
            ret = MyList([])

        try:
            result = self.session.walk(oid)

            if not result:
                temp = self.session.get(oid).value
                result = [temp]

        # except exceptions.EasySNMPConnectionError:
        #     print("-------------------------------snmp连接失败--------------------------------------")
        #     print(oid)
        #     print(ret)
        #     raise AuthException("snmp连接失败，请检查凭证")

        except (exceptions.EasySNMPError, exceptions.EasySNMPConnectionError):
            result = []

        except Exception:
            raise Exception("snmp连接异常")

        for line in result:

            value = line.value.strip("\"")
            if return_dict:
                ret[line.oid_index] = value
            else:

                if value.strip() != "":
                    ret.append(value)
        return ret

    def test_credential(self):
        try:
            self.session.walk("1.3.6.1.2.1.1.2")
            return 1
        except exceptions.EasySNMPConnectionError:
            raise Exception("凭证错误")
        except Exception:
            raise Exception("snmp连接异常（测试凭证时）")

def get_portlist_from_hex(hex_string, reverse = False):
    ret = []
    if hex_string:
        i = 0
        for item in hex_string.strip().split():
            if item != "00":
                number = int(item, 16)
                if reverse:
                    port_index = i*8 + 8 - (len(bin(number))-2) + 1
                else:
                    port_index = i*8 + len(bin(number)) - 2
                ret.append("%s" %port_index)
            i += 1
    return ret

credential_v2 = {
    "hostname": "192.168.40.106",
    "remote_port": "161",
    "version": 2,
    "community": "111111"
}

credential_v3 = {
    "hostname": "192.168.40.106",
    "remote_port": "161",
    "version": 3,
    "security_username": "",
    "security_level": "",
    "auth_protocol": "",
    "auth_password": "",
    "privacy_protocol": "",
    "privacy_password": ""
}

from concurrent.futures import ThreadPoolExecutor

def task():
    result = SNMP(credential_v2, use_numeric=True).snmp_walk("1.3.6.1.2.1.1.2")
    print(result)

num = 2

thread_pool = ThreadPoolExecutor(num)
thread_pool.submit(task)