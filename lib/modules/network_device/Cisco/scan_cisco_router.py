from .scan_cisco_switch import CiscoSwitchScan

class CiscoRouterScan(CiscoSwitchScan):
    def __init__(self, init_info):
        super(CiscoRouterScan, self).__init__(init_info)
        self.device_type = "router"