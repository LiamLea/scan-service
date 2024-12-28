from scan_service.lib.utils import size
from scan_service.lib.modules.network_device.scan_switch import SwitchScan

class H3cSwitchScan(SwitchScan):
    def __init__(self, init_info):
        super(H3cSwitchScan, self).__init__(init_info)

    def get_system_info(self):
        ret = {
            "memory_info": {},
            "cpu_info": {}
        }
        memory_total = self.snmp_walk("1.3.6.1.4.1.25506.8.35.18.1.14")[0].rstrip("byte").strip()
        memory_used = self.snmp_walk("1.3.6.1.4.1.25506.8.35.18.1.15")[0].rstrip("byte").strip()
        memory_usage = self.snmp_walk("1.3.6.1.4.1.25506.8.35.18.1.16")[0].rstrip("byte").strip()
        ret["memory_info"]["total"] = size(int(memory_total)) if memory_total else memory_total
        ret["memory_info"]["used"] = size(int(memory_used)) if memory_used else memory_used
        ret["memory_info"]["usage"] = "%s %%" %memory_usage if memory_usage else ""

        self.mapping["System_info"]["memory_info"]["total"] = "%s" %int(memory_total) if memory_total else memory_total
        self.mapping["System_info"]["memory_info"]["used"] = "%s" %int(memory_used) if memory_total else memory_total

        cpu_usage = self.snmp_walk("1.3.6.1.4.1.25506.8.35.18.1.3")[0]
        ret["cpu_info"]["usage"] = "%s %%" %cpu_usage if cpu_usage else ""
        return ret

    def get_vlan_info(self):
        ret = []
        # vlanid = self.snmp_walk("1.3.6.1.4.1.25506.8.35.2.1.1.1.1")
        vlan_name = self.snmp_walk("1.3.6.1.4.1.25506.8.35.2.1.1.1.2", return_dict=True)
        vlan_type = self.snmp_walk("1.3.6.1.4.1.25506.8.35.2.1.1.1.4", return_dict=True)
        vlan_status = self.snmp_walk("1.3.6.1.4.1.25506.8.35.2.1.1.1.13", return_dict=True)


        """
        一个vlan只能有一个vlanif
        一个vlanif可以配置多个ip
        """
        #获取vlanid和vlanifindex的关系
        vlanid_if_dict = self.snmp_walk("1.3.6.1.4.1.25506.8.35.2.1.2.1.9", return_dict=True)

        #获取vlan的ip信息
        vlanif_ip_dict = self.snmp_walk("1.3.6.1.4.1.25506.8.35.2.1.5.1.2", return_dict=True)
        vlanif_mask_dict = self.snmp_walk("1.3.6.1.4.1.25506.8.35.2.1.5.1.3", return_dict=True)
        vlanif_type_dict = self.snmp_walk("1.3.6.1.4.1.25506.8.35.2.1.5.1.4", return_dict=True)

        #key.split(".")[0]为vlanifindex
        vlanif_dict = {}
        for key in vlanif_ip_dict:
            index = key.split(".")[0]
            if not vlanif_dict.get(index, ""):
                vlanif_dict[index] = []
            vlanif_dict[index].append({
                "ip": vlanif_ip_dict[key],
                "mask": vlanif_mask_dict[key],
                "type": vlanif_type_dict[key]
            })

        #获取vlan（vlanid）和port（portindex）的关系
        vlan_port_dict = self.snmp_walk("1.3.6.1.4.1.25506.8.35.2.1.1.1.19", return_dict=True)
        for id in vlan_port_dict:
            tmp_list  = []
            for port_index in vlan_port_dict[id].split(","):
                item = self.IFINDEX_NAME_DICT.get(port_index, port_index)
                if item:
                    tmp_list.append(item)
            vlan_port_dict[id] = tmp_list

        for id in vlan_name:
            item = {
                "vlan_id": id,
                "vlan_name": vlan_name[id] if vlan_name[id] else "VLAN %s" %id ,
                "vlan_type": vlan_type.get(id, ""),
                "vlan_status": vlan_status.get(id, ""),
                "vlan_ifName": self.IFINDEX_NAME_DICT.get(vlanid_if_dict.get(id, ""), ""),
                "port_list": vlan_port_dict.get(id, []),
                "ip": vlanif_dict.get(vlanid_if_dict.get(id, ""), [])
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

        fan_info = self.snmp_walk("1.3.6.1.4.1.25506.8.35.9.1.1.1.2")
        ret["fan"]["slot_number"] = len(fan_info)
        ret["fan"]["number"] = len([i for i in fan_info if "not-install" in i])

        power_info  = self.snmp_walk("1.3.6.1.4.1.25506.8.35.9.1.2.1.2")
        ret["power"]["slot_number"] = len(power_info)
        ret["power"]["number"] = len([i for i in power_info if "not-install" in i])

        return ret

    def integrate_info(self, data):
        data["base_info"]["os_version"] = self.snmp_walk("1.3.6.1.4.1.25506.8.35.18.1.4")[0]
        data["base_info"]["manufacturer"] = "H3C"
        return data