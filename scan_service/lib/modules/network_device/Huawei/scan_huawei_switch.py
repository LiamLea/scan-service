from scan_service.lib.utils import size
from scan_service.lib.modules.network_device.scan_switch import SwitchScan
from scan_service.lib.utils import get_portlist_from_hex
from scan_service.lib.framework import logger

class HuaweiSwitchScan(SwitchScan):
    def __init__(self, init_info):
        super(HuaweiSwitchScan, self).__init__(init_info)

    def get_system_info(self):
        ret = {
            "memory_info": {},
            "cpu_info": {}
        }
        result = self.snmp_walk("1.3.6.1.4.1.2011.6.3.5.1.1.2")[0].strip()
        memory_total = int(result) if result else ""
        result = self.snmp_walk("1.3.6.1.4.1.2011.6.3.5.1.1.3")[0].strip()
        try:
            memory_used = memory_total - int(result) if result else ""
        except Exception:
            logger.error("解析失败：", result)
            raise Exception("memory scan error")
        ret["memory_info"]["total"] = size(memory_total) if memory_total else memory_total
        ret["memory_info"]["used"] = size(memory_used) if memory_used else memory_used
        ret["memory_info"]["usage"] = "%s %%" % int(memory_used / memory_total * 100) if memory_total and memory_used else ""

        self.mapping["System_info"]["memory_info"]["total"] = "%s" %memory_total
        self.mapping["System_info"]["memory_info"]["used"] = "%s" %memory_used

        cpu_usage = self.snmp_walk("1.3.6.1.4.1.2011.6.3.4.1.2")[0]
        ret["cpu_info"]["usage"] = "%s %%" %cpu_usage if cpu_usage else ""
        return ret

    def get_vlan_info(self):
        ret = []
        # vlanid = self.snmp_walk("1.3.6.1.4.1.25506.8.35.2.1.1.1.1")
        vlan_name = self.snmp_walk("1.3.6.1.4.1.2011.5.25.42.3.1.1.1.1.17", return_dict=True)
        vlan_type = self.snmp_walk("1.3.6.1.4.1.2011.5.25.42.3.1.1.1.1.4", return_dict=True)
        #1.3.6.1.2.1.17.7.1.4.2.1.6
        vlan_status = self.snmp_walk("1.3.6.1.4.1.2011.5.25.42.3.1.1.1.1.12", return_dict=True)


        """
        一个vlan只能有一个vlanif
        一个vlanif可以配置多个ip
        """
        #获取vlanid和vlanifindex的关系
        vlanid_if_dict = {}
        tmp_dict = self.snmp_walk("1.3.6.1.4.1.2011.5.25.42.3.1.1.1.1.6", return_dict=True)
        for k,v in tmp_dict.items():
            if v != "-1":
                vlanid_if_dict[k] = v


        #获取vlan的ip信息
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
        #1.3.6.1.2.1.17.7.1.4.2.1.4
        vlan_port_dict = {}
        tmp_dict = self.snmp_walk("1.3.6.1.2.1.17.7.1.4.2.1.4", return_dict=True)
        for k,v in tmp_dict.items():
            tmp_list = []
            for port_index in get_portlist_from_hex(v, type="binary"):
                tmp_list.append(self.PORTINDEX_NAME_DICT.get(port_index, port_index))
            vlan_port_dict[k.split(".")[-1]] = tmp_list

        for id in vlan_name:
            item = {
                "vlan_id": id,
                "vlan_name": vlan_name[id] if vlan_name[id] else "VLAN %s" %id,
                "vlan_type": vlan_type.get(id, ""),
                "vlan_status": vlan_status.get(id, ""),
                "vlan_ifName": self.IFINDEX_NAME_DICT.get(vlanid_if_dict.get(id, ""), ""),
                "port_list": vlan_port_dict.get(id, []),
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

        ret["fan"]["slot_number"] = len(self.snmp_walk("1.3.6.1.4.1.2011.5.25.31.1.1.10.1.1"))
        ret["fan"]["number"] = len(self.snmp_walk("1.3.6.1.4.1.2011.5.25.31.1.1.10.1.7"))

        ret["power"]["slot_number"] = len(self.snmp_walk("1.3.6.1.4.1.2011.5.25.31.1.1.18.1.1"))
        ret["power"]["number"] = len(self.snmp_walk("1.3.6.1.4.1.2011.5.25.31.1.1.18.1.6"))

        return ret

    def integrate_info(self, data):
        data["base_info"]["manufacturer"] = "Huawei"
        return data