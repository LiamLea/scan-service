from scan_service.lib.utils import size
from scan_service.lib.modules.network_device.scan_switch import SwitchScan

class DptechSwitchScan(SwitchScan):

    def __init__(self, init_info):
        super(DptechSwitchScan, self).__init__(init_info)

    def get_system_info(self):
        ret = {
            "memory_info": {},
            "cpu_info": {}
        }
        memory_total = self.snmp_walk("1.3.6.1.4.1.31648.3.10")[0]
        usage_rate = self.snmp_walk("1.3.6.1.4.1.31648.3.15.5")[0]
        memory_used = int(int(memory_total) * 1024 * 1024 * int(usage_rate) * 0.01)
        ret["memory_info"]["total"] = size(int(memory_total) * 1024 * 1024) if memory_total else memory_total
        ret["memory_info"]["used"] = size(int(memory_used)) if memory_used else memory_used
        ret["memory_info"]["usage"] = "%s %%" %usage_rate if usage_rate else ""

        cpu_usage = self.snmp_walk("1.3.6.1.4.1.31648.3.15.3")[0]
        ret["cpu_info"]["usage"] = "%s %%" %cpu_usage if cpu_usage else ""

        self.mapping["System_info"]["memory_info"]["total"] = "%s" %(int(memory_total) * 1024 * 1024) if memory_total else memory_total
        self.mapping["System_info"]["memory_info"]["used"] = "%s" %(int(memory_used) * 1024 * 1024) if memory_total else memory_total

        return ret

    def get_hardware_extra_info(self):

        ret = {
            "power": {
                "slot_number": "",
                "number": "",
            },
            "fan": {
                "slot_number": "",
                "number": "",
            }
        }


        fan_info = self.snmp_walk("1.3.6.1.4.1.31648.3.15.12.1.3")
        ret["fan"]["number"] = len(fan_info)


        power_info = self.snmp_walk("1.3.6.1.4.1.31648.3.15.11.1.3")
        ret["power"]["number"] = len(power_info)

        return ret

    def integrate_info(self, data):
        data["base_info"]["manufacturer"] = "DPtech"
        return data