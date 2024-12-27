from .scan_fiberhome_switch import FiberhomeSwitchScan

class FiberhomeRouterScan(FiberhomeSwitchScan):
    def __init__(self, init_info):
        super(FiberhomeRouterScan, self).__init__(init_info)
        self.device_type = "router"