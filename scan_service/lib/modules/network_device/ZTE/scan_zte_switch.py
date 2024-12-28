from scan_service.lib.utils import size
from scan_service.lib.modules.network_device.scan_switch import SwitchScan

class ZTESwitchScan(SwitchScan):

    def __init__(self, init_info):
        super(ZTESwitchScan, self).__init__(init_info)

    def integrate_info(self, data):
        data["base_info"]["manufacturer"] = "ZTE"
        return data