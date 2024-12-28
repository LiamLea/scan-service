from scan_service.lib.utils import MyList
from scan_service.lib.framework import BusinessException
from scan_service.lib.framework import AuthException
import re

try:
    import easysnmp
    from easysnmp import exceptions
except:
    pass

class SNMP:

    def __init__(self, credential_dict, use_sprint_value = True):
        self.credential_dict = credential_dict
        self.session = easysnmp.Session(**self.credential_dict, use_sprint_value = use_sprint_value, abort_on_nonexistent = True)
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
            raise BusinessException("snmp连接异常")

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
            raise AuthException("凭证错误")
        except Exception:
            raise BusinessException("snmp连接异常（测试凭证时）")

def get_portlist_from_hex(hex_string, reverse = False, type = "common"):
    ret = []
    if not hex_string:
        return ret

    if type == "binary":
        hex_string = re.sub("\s+", "", hex_string)
        b = bin(int(hex_string, 16))[2:].zfill(len(hex_string) * 4)
        num = 1
        for i in b:
            if i != "0":
                ret.append(str(num))
            num += 1

    else:
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

