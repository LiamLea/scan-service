from .scan_h3c_switch import H3cSwitchScan

class H3cRouterScan(H3cSwitchScan):
    def __init__(self, init_info):
        super(H3cRouterScan, self).__init__(init_info)
        self.device_type = "router"