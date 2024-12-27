from .Cisco import CiscoSwitchScan,CiscoRouterScan
from .H3C import H3cSwitchScan,H3cRouterScan
from .Huawei import HuaweiSwitchScan,HuaweiRouterScan
from .DPtech import DptechSwitchScan,DptechRouterScan
from .ZTE import ZTESwitchScan,ZTERouterScan
from .Fiberhome import FiberhomeSwitchScan,FiberhomeRouterScan
from ..load_balance import F5LoadBalancerScan
import re
import sys
from pathlib import Path


def device_route(device_info):
    route_table = {

        #参考：https://github.com/librenms/librenms/blob/master/mibs/HH3C-PRODUCT-ID-MIB
        "H3c": {
            "pattern": "h3c",
            "device": {
                "Switch": r"switch|hh3c-?(ce|s)\d+",
                "Router": r"router|hh3c-?(sr|ar)\d+",
            }
        },

        #参考：https://github.com/librenms/librenms/blob/master/mibs/huawei/HUAWEI-MIB
        "Huawei": {
            "pattern": "huawei",
            "device": {
                "Switch": r"switch|[^a-zA-Z0-9](ce|s)\d+",
                "Router": r"[^a-zA-Z0-9](ar)\d+",
                "Storage": r"ism"
            }
        },

        #参考：https://github.com/librenms/librenms/blob/master/mibs/cisco/CISCO-PRODUCTS-MIB
        "Cisco": {
            "pattern": "cisco",
            "device": {
                "Switch": r"switch|catalyst|[^a-zA-Z0-9](cat|ciscoce)\d+",
                "Router": r"router|cisco\d+",
            }
        },

        "Dptech": {
            "pattern": "dptech",
            "device": {
                "Switch": r"lsw\d+"
            }
        },

        "ZTE": {
            "pattern": "zte",
            "device": {
                "Switch": r"switch|[^a-zA-Z0-9](ce|s|zxr10 )\d+",
                "Router": r"[^a-zA-Z0-9](ar)\d+"
            }
        },

        "Fiberhome": {
            "pattern": "wuhan research institute",
            "device": {
                "Switch": r"switch|[^a-zA-Z0-9](ce|s)\d+",
            }
        },

        "F5": {
            "pattern": "f5",
            "device": {
                "LoadBalancer": r"big-ip"
            }
        }
    }

    for vender in route_table:
        if route_table[vender]["pattern"] in device_info.lower():
            for device_type, pattern in route_table[vender]["device"].items():
                match = re.search(pattern, device_info, re.IGNORECASE)
                if match:
                    return getattr(sys.modules[__name__], "%s%sScan" %(vender, device_type))
    return ""

def get_vender(number):
    with open(str(Path(__file__).parent / "enterprise-numbers")) as fobj:
        for line in fobj:
            if number == line.split()[0]:
                return " ".join(line.split()[1:])
    return ""