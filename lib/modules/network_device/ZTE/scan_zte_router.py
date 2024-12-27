from .scan_zte_switch import ZTESwitchScan

class ZTERouterScan(ZTESwitchScan):
    def __init__(self, init_info):
        super(ZTERouterScan, self).__init__(init_info)
        self.device_type = "router"