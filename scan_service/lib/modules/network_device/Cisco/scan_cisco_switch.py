from scan_service.lib.utils import size
from scan_service.lib.modules.network_device.scan_switch import SwitchScan

class CiscoSwitchScan(SwitchScan):

    def __init__(self, init_info):
        super(CiscoSwitchScan, self).__init__(init_info)

        # self.sysip = self.snmp_walk("1.3.6.1.2.1.4.20.1.1")[0]
        # self.sysip_mask = self.snmp_walk("1.3.6.1.2.1.4.20.1.3")[0]

    def get_system_info(self):
        ret = {
            "memory_info": {},
            "cpu_info": {}
        }

        memory_total = 0
        memory_used = 0
        memory_free = 0
        memory_used_info = self.snmp_walk("1.3.6.1.4.1.9.9.48.1.1.1.5")
        memory_free_info = self.snmp_walk("1.3.6.1.4.1.9.9.48.1.1.1.6")
        for memory_used_single in memory_used_info:
            memory_used = memory_used + int(memory_used_single)
        for memory_free_single in memory_free_info:
            memory_free = memory_free + int(memory_free_single)
        memory_total = memory_used + memory_free
        ret["memory_info"]["total"] = size(memory_total) if memory_total else memory_total
        ret["memory_info"]["used"] = size(memory_used) if memory_used else memory_used
        ret["memory_info"]["usage"] = "%s %%" % int(memory_used / memory_total * 100) if memory_total and memory_used else ""

        self.mapping["System_info"]["memory_info"]["total"] = "%s" %memory_total
        self.mapping["System_info"]["memory_info"]["used"] = "%s" %memory_used

        cpu_usage = self.snmp_walk("1.3.6.1.4.1.25506.8.35.18.1.3")[0]
        ret["cpu_info"]["usage"] = "%s %%" %cpu_usage if cpu_usage else ""
        return ret

    def get_vlan_info(self):
        ret = []
        # vlanid = self.snmp_walk("1.3.6.1.4.1.25506.8.35.2.1.1.1.1")
        vlan_name = self.snmp_walk("1.3.6.1.4.1.9.9.46.1.3.1.1.4", return_dict=True)
        vlan_type = self.snmp_walk("1.3.6.1.4.1.9.9.46.1.3.1.1.3", return_dict=True)
        vlan_status = self.snmp_walk("1.3.6.1.4.1.9.9.46.1.3.1.1.2", return_dict=True)


        """
        一个vlan只能有一个vlanif
        一个vlanif可以配置多个ip
        """
        #获取vlanid和vlanifindex的关系
        vlanid_if_dict = self.snmp_walk("1.3.6.1.4.1.9.9.46.1.3.1.1.18", return_dict=True)

        # #获取vlan的ip信息
        id_if_dict = self.snmp_walk("1.3.6.1.2.1.4.20.1.2", return_dict = True)
        id_ip_dict = self.snmp_walk("1.3.6.1.2.1.4.20.1.1", return_dict = True)
        id_mask_dict = self.snmp_walk("1.3.6.1.2.1.4.20.1.3", return_dict=True)
        if_ip_dict = {}
        for id in id_if_dict:
            ifindex = id_if_dict[id]
            if not if_ip_dict.get(ifindex, ""):
                if_ip_dict[ifindex] = []
            if id_ip_dict.get("id"):
                if_ip_dict[ifindex].append({
                    "ip": id_ip_dict[id],
                    "mask": id_mask_dict.get(id, ""),
                    "type": ""
                })

        #获取vlan（vlanid）和port（portindex）的关系
        port_vlan_dict = self.snmp_walk("1.3.6.1.4.1.9.5.1.9.3.1.3", return_dict=True)
        vlan_port_dict = {}

        for k,v in port_vlan_dict.items():
            if not vlan_port_dict.get(v):
                vlan_port_dict[v] = []
            vlan_port_dict[v].append(self.PORTINDEX_NAME_DICT.get(k.split(".")[-1], k.split(".")[-1]))

        for id in vlan_name:

            item = {
                "vlan_id": id.split(".")[-1],
                "vlan_name": vlan_name[id] if vlan_name[id] else "VLAN %s" %id.split(".")[-1],
                "vlan_type": vlan_type.get(id, ""),
                "vlan_status": vlan_status.get(id, ""),
                "vlan_ifName": self.IFINDEX_NAME_DICT.get(vlanid_if_dict.get(id, ""), ""),
                "port_list": vlan_port_dict.get(id.split(".")[-1], []),
                "ip": if_ip_dict.get(vlanid_if_dict.get(id, ""), [])
            }

            ret.append(item)

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

        fan_info = self.snmp_walk("1.3.6.1.4.1.9.9.13.1.4.1.3")
        ret["fan"]["number"] = len(fan_info)


        power_info = self.snmp_walk("1.3.6.1.4.1.9.9.13.1.5.1.3")
        ret["power"]["number"] = len(power_info)


        return ret

    def integrate_info(self, data):
        data["base_info"]["os_version"] = self.snmp_walk("1.3.6.1.4.1.9.5.1.3.1.1.20")[0]
        data["base_info"]["manufacturer"] = "Cisco"

        return data