from .scan_dptech_switch import DptechSwitchScan

class DptechRouterScan(DptechSwitchScan):
    def __init__(self, init_info):
        super(DptechRouterScan, self).__init__(init_info)
        self.device_type = "router"