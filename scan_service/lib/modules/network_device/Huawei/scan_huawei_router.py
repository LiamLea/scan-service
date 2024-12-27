from .scan_huawei_switch import HuaweiSwitchScan

class HuaweiRouterScan(HuaweiSwitchScan):
    def __init__(self, init_info):
        super(HuaweiRouterScan, self).__init__(init_info)
        self.device_type = "router"