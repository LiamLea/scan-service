import hashlib
import time
from scan_service.lib.utils import MyList
from scan_service.lib.utils import size
from scan_service.lib.utils import seconds_format
from scan_service.lib.utils import get_speed_type
from scan_service.lib.common import ScanViaSNMP
from scan_service.lib.utils import get_portlist_from_hex
from scan_service.lib.utils import string_to_bytes
import datetime
import re
from scan_service.lib.framework import logger

class SwitchScan(ScanViaSNMP):

    def __init__(self, init_info):
        super(SwitchScan, self).__init__(init_info)
        self.device_type = "switch"
        self.total_in_bytes = 0
        self.total_out_bytes = 0

        self.total_packages = 0
        self.total_discards = 0

        #用于保存，ifindex和ifname的映射关系
        self.IFINDEX_NAME_DICT = {}
        #用于保存,portindex和ifname的映射关系
        self.PORTINDEX_NAME_DICT = {}
        self.PORTINDEX_IFINDEX_DICT = {}

        self.IF_MAC_DICT = {}

        self.sysip = ""
        self.sysip_mask = ""
        self.sysip_mac = ""

        self.ip_list = []

        ip_if_dict = self.snmp_walk("1.3.6.1.2.1.4.20.1.2", return_dict = True)
        ip_mask_dict = self.snmp_walk("1.3.6.1.2.1.4.20.1.3", return_dict = True)
        self.if_inet_dict = {}
        for ip,ifindex in ip_if_dict.items():
            if ip.strip() != "127.0.0.1":
                self.if_inet_dict[ifindex] = {"ip": ip, "mask": ip_mask_dict.get(ip, "255.255.255.0")}
                self.ip_list.append({"ip": ip, "mask": ip_mask_dict.get(ip, "255.255.255.0")})

        self.mapping = {
            "Interface_list": [],
            "System_info": {
                "memory_info": {
                    "total": "",
                    "used": ""
                }
            },
            "base_info": {
                "total_input": "",
                "total_output": ""
            },
            "hardware": {
                "port": []
            }
        }

    def get_base_info(self):

        # sysObjectID = MyList(self.snmp_walk("1.3.6.1.2.1.1.2")[0].split("."))[-1]
        # entPhysicalModelName = self.snmp_walk("1.3.6.1.2.1.47.1.1.1.1.13")[0]
        entPhysicalSerialNum = self.snmp_walk("1.3.6.1.2.1.47.1.1.1.1.11")[0]
        port_num = self.snmp_walk("1.3.6.1.2.1.2.1")[0]

        temp_list = MyList(self.snmp_walk("1.3.6.1.2.1.1.3")[0].split(":"))
        temp_list = [i for i in temp_list if i.strip() != "" ]
        # uptime = "%s days %s hours %s minutes" % (temp_list[-4], temp_list[-3], temp_list[-2])
        try:
            uptime = (datetime.datetime.now() - datetime.timedelta(days = int(temp_list[-4]) if temp_list[-4] else 0,
                                                               hours = int(temp_list[-3]) if temp_list[-3] else 0,
                                                               minutes = int(temp_list[-2]) if temp_list[-2] else 0,
                                                               seconds = float(temp_list[-1])
                                                               )).strftime('%Y-%m-%d %H:%M:%S')
        except Exception:
            logger.error("解析失败：", temp_list)
            raise Exception("list index out of range")

        name = self.snmp_walk("1.3.6.1.2.1.1.5")[0]
        sys_descr = self.snmp_walk("1.3.6.1.2.1.1.1")[0]
        match = re.search(r"version\s*([\d.]+)", sys_descr, re.IGNORECASE)

        ret = {
            "model": self.snmp_walk("1.3.6.1.2.1.1.2")[0],
            "manufacturer": "",
            "device_type": self.device_type,
            "name": name,
            "serial_number": entPhysicalSerialNum,
            "os_version": match.group(1) if match else "",
            "sysip": "",
            "sysip_mask": "",
            "port_num": port_num,
            "uptime": uptime,
            "total_input": "",
            "total_output": "",
            "total_discard": "",
            "chassis_mac": self.snmp_walk("1.0.8802.1.1.2.1.3.2")[0].strip().replace(" ", ":"),
        }

        return ret

    def get_system_info(self):

        ret = {
            "memory_info": {},
            "cpu_info": {}
        }

        return ret

    def get_interface_info(self):

        ret = {}

        # 接口索引
        if_index_list = self.snmp_walk("1.3.6.1.2.1.2.2.1.1")

        if_index_name_dict = self.snmp_walk("1.3.6.1.2.1.2.2.1.2", return_dict=True)
        if_index_type_dict = self.snmp_walk("1.3.6.1.2.1.2.2.1.3", return_dict=True)
        ifHighSpeed_dict = self.snmp_walk("1.3.6.1.2.1.31.1.1.1.15", return_dict=True)
        self.IF_MAC_DICT = if_mac_dict = self.snmp_walk("1.3.6.1.2.1.2.2.1.6", return_dict=True)
        ifAdminStatus_dict = self.snmp_walk("1.3.6.1.2.1.2.2.1.7", return_dict=True)
        ifOperStatus_dict = self.snmp_walk("1.3.6.1.2.1.2.2.1.8", return_dict=True)
        ifHCInOctets_dict = self.snmp_walk("1.3.6.1.2.1.31.1.1.1.6", return_dict=True)
        ifHCOutOctets_dict = self.snmp_walk("1.3.6.1.2.1.31.1.1.1.10", return_dict=True)

        ifInDiscards_dict = self.snmp_walk("1.3.6.1.2.1.2.2.1.13", return_dict=True)
        ifOutDiscards_dict = self.snmp_walk("1.3.6.1.2.1.2.2.1.19", return_dict=True)
        ifInUcast_dict = self.snmp_walk("1.3.6.1.2.1.2.2.1.11", return_dict=True)
        ifOutUcast_dict = self.snmp_walk("1.3.6.1.2.1.2.2.1.17", return_dict=True)
        ifInMulti_dict = self.snmp_walk("1.3.6.1.2.1.31.1.1.1.2", return_dict=True)
        ifOutMulti_dict = self.snmp_walk("1.3.6.1.2.1.31.1.1.1.4", return_dict=True)
        ifInBroad_dict = self.snmp_walk("1.3.6.1.2.1.31.1.1.1.3", return_dict=True)
        ifOutBroad_dict = self.snmp_walk("1.3.6.1.2.1.31.1.1.1.5", return_dict=True)

        self.IFINDEX_NAME_DICT = if_index_name_dict
        self.PORTINDEX_NAME_DICT = {}

        # 端口索引
        self.PORTINDEX_IFINDEX_DICT = self.snmp_walk("1.3.6.1.2.1.17.1.4.1.2", return_dict=True)
        if_port_dict = {}
        for k, v in self.PORTINDEX_IFINDEX_DICT.items():
            self.PORTINDEX_NAME_DICT[k] = if_index_name_dict.get(v, "")
            if_port_dict[v] = k

        for index in if_index_list:
            self.total_in_bytes += int(ifHCInOctets_dict.get(index, "0"))
            self.total_out_bytes += int(ifHCOutOctets_dict.get(index, "0"))

            packages = int(ifInUcast_dict.get(index, 0)) + int(ifOutUcast_dict.get(index, 0)) + int(ifInMulti_dict.get(index, 0)) + int(ifOutMulti_dict.get(index, 0)) + int(ifInBroad_dict.get(index, 0)) + int(ifOutBroad_dict.get(index, 0))
            discard_packages = int(ifInDiscards_dict.get(index, 0)) + int(ifOutDiscards_dict.get(index, 0))

            self.total_packages += packages
            self.total_discards += discard_packages

            item = {
                "ifIndex": index,
                "ifName": if_index_name_dict.get(index, ""),
                "ifType": if_index_type_dict.get(index, ""),
                "ifHighSpeed": ifHighSpeed_dict.get(index, ""),
                "mac": if_mac_dict.get(index, "").strip().replace(" ", ":"),
                "ifAdminStatus": ifAdminStatus_dict.get(index, ""),
                "ifOperStatus": ifOperStatus_dict.get(index, ""),
                "ifHCInOctets": size(int(ifHCInOctets_dict.get(index, "0"))),
                "ifHCOutOctets": size(int(ifHCOutOctets_dict.get(index, "0"))),
                "ifInDiscards": ifInDiscards_dict.get(index, "0"),
                "ifOutDiscards": ifOutDiscards_dict.get(index, "0"),
                "discard": "%.2f%%" % (discard_packages / packages * 100) if packages != 0 else "0.00%",
                "portIndex": if_port_dict.get(index, ""),
            }

            self.mapping["Interface_list"].append({"ifHCInOctets": "%s" %int(ifHCInOctets_dict.get(index, "0")), "ifHCOutOctets": "%s" %int(ifHCOutOctets_dict.get(index, "0"))})

            # ret.append(item)
            ret[item["ifIndex"]] = item

        return ret

    def get_mac_info(self):

        ret = []

        mac_dict = self.snmp_walk("1.3.6.1.2.1.17.4.3.1.2", return_dict=True)
        if not mac_dict:
            mac_dict = self.snmp_walk("1.3.6.1.2.1.17.7.1.2.2.1.2", return_dict=True)

        mac_status_dict = self.snmp_walk("1.3.6.1.2.1.17.4.3.1.3", return_dict=True)
        if not mac_status_dict:
            mac_status_dict = self.snmp_walk("1.3.6.1.2.1.17.7.1.2.2.1.3", return_dict=True)

        for key in mac_dict:
            item = {}
            key_list = key.split('.')
            item["mac"] = ("%.2x:%.2x:%.2x:%.2x:%.2x:%.2x" % (int(key_list[0]),
                                                              int(key_list[1]),
                                                              int(key_list[2]),
                                                              int(key_list[3]),
                                                              int(key_list[4]),
                                                              int(key_list[5]))).upper()
            item["vlan_id"] = ""
            item["ifIndex"] = mac_dict[key]
            item["ifName"] = self.PORTINDEX_NAME_DICT.get(mac_dict[key], "")
            item["state"] = mac_status_dict.get(key, "")

            ret.append(item)

        return ret

    def get_arp_info(self):
        ret = []

        if_index_dict = self.snmp_walk("1.3.6.1.2.1.3.1.1.1", return_dict=True)
        ip_dict = self.snmp_walk("1.3.6.1.2.1.3.1.1.3", return_dict=True)
        mac_dict = self.snmp_walk("1.3.6.1.2.1.3.1.1.2", return_dict=True)

        for id in if_index_dict:

            ip = ""
            if ip_dict.get(id, ""):
                tmp_list = ip_dict[id].split(":")
                ip = "%s.%s.%s.%s" %(int(tmp_list[0], 16), int(tmp_list[1], 16), int(tmp_list[2], 16), int(tmp_list[3], 16))

            item = {
                "ip": ip,
                "mac": mac_dict.get(id, "").strip().replace(" ", ":"),
                "ifName": self.IFINDEX_NAME_DICT.get(if_index_dict.get(id, ""), "")
            }
            ret.append(item)

        return ret

    def get_vlan_info(self):
        return []

    def get_route_info(self):
        ret = []

        # #判断是否开启了路由转发功能
        # ipforwarding_status = self.snmp_walk("1.3.6.1.2.1.4.1")[0]
        # if "notForwarding" in ipforwarding_status:
        #     for ifindex in self.if_inet_dict:
        #         self.sysip = self.if_inet_dict[ifindex]["ip"]
        #         self.sysip_mask = self.if_inet_dict[ifindex]["mask"]
        #         self.sysip_mac = self.IF_MAC_DICT.get(ifindex, "")
        #         if "vlan" in self.IFINDEX_NAME_DICT.get(ifindex, "").lower():
        #             break
        #     return ret

        dst_dict = self.snmp_walk("1.3.6.1.2.1.4.24.4.1.1", return_dict=True)
        mask_dict = self.snmp_walk("1.3.6.1.2.1.4.24.4.1.2", return_dict=True)
        # ipCidrRouteTos_dict = self.snmp_walk("1.3.6.1.2.1.4.24.4.1.3", return_dict = True,)
        nextHop_dict = self.snmp_walk("1.3.6.1.2.1.4.24.4.1.4", return_dict=True)
        ifIndex_dict = self.snmp_walk("1.3.6.1.2.1.4.24.4.1.5", return_dict=True)
        type_dict = self.snmp_walk("1.3.6.1.2.1.4.24.4.1.6", return_dict=True)
        proto_dict = self.snmp_walk("1.3.6.1.2.1.4.24.4.1.7", return_dict=True)
        age_dict = self.snmp_walk("1.3.6.1.2.1.4.24.4.1.8", return_dict=True)
        # ipCidrRouteNextHopAS_dict = self.snmp_walk("1.3.6.1.2.1.4.24.4.1.10", return_dict = True)
        # status_dict = self.snmp_walk("1.3.6.1.2.1.4.24.4.1.16", return_dict = True)

        for id in dst_dict:
            item = {
                "Destination": dst_dict.get(id, ""),
                "Mask": mask_dict.get(id, ""),
                "NextHop": nextHop_dict.get(id, ""),
                "IfName": self.IFINDEX_NAME_DICT.get(ifIndex_dict.get(id, ""), ""),
                "Type": type_dict.get(id, ""),
                "Protocol": proto_dict.get(id, ""),
                "Age": seconds_format(age_dict.get(id, 0)),
                # "ipCidrRouteNextHopAS": ipCidrRouteNextHopAS_dict.get(id, ""),
                # "Status": status_dict.get(id, "")
            }

            if not self.sysip and  item["Destination"] == "0.0.0.0":
                self.sysip = self.if_inet_dict.get(ifIndex_dict.get(id, ""), {}).get("ip", "")
                self.sysip_mask = self.if_inet_dict.get(ifIndex_dict.get(id, ""), {}).get("mask", "")
                self.sysip_mac = self.IF_MAC_DICT.get(ifIndex_dict.get(id, "")).strip().replace(" ", ":")

            ret.append(item)

        return ret

    def get_agg_link_info(self):

        ret = []

        agg_link_mode_dict = self.snmp_walk("1.3.6.1.4.1.25506.8.25.1.1.1.3", return_dict=True)
        agg_link_portlist_dict = self.snmp_walk("1.3.6.1.4.1.25506.8.25.1.1.1.4", return_dict=True)
        agg_link_state_dict = self.snmp_walk("1.3.6.1.4.1.25506.8.25.1.1.1.5", return_dict=True)
        agg_portlist_selected_dict = self.snmp_walk("1.3.6.1.4.1.25506.8.25.1.1.1.6", return_dict=True)

        for id in agg_link_mode_dict:
            item = {
                "agg_link_id": id,
                "agg_link_mode": agg_link_mode_dict.get(id, ""),
                "agg_link_state": agg_link_state_dict.get(id, ""),
            }

            portlist1 = []
            for port in get_portlist_from_hex(agg_link_portlist_dict.get(id, ""), reverse=True):
                port_name = self.PORTINDEX_NAME_DICT.get(port, "")
                if port_name:
                    portlist1.append(port_name)
            item["agg_link_portlist"] = portlist1

            portlist2 = []
            for port in get_portlist_from_hex(agg_portlist_selected_dict.get(id, ""), reverse=True):
                port_name = self.PORTINDEX_NAME_DICT.get(port, "")
                if port_name:
                    portlist2.append(port_name)
            item["agg_portlist_selected"] = portlist2

            ret.append(item)

        return ret

    def get_lldp_rem_device_info(self):
        ret = []

        # 对端设备端口
        remote_interface_dict = self.snmp_walk("1.0.8802.1.1.2.1.4.1.1.7", return_dict=True)
        # 对端设备标识，这里的值为chassis MAC地址
        remote_mac_dict = self.snmp_walk("1.0.8802.1.1.2.1.4.1.1.5", return_dict=True)
        # 对端设备的系统名称
        remote_system_name_dict = self.snmp_walk("1.0.8802.1.1.2.1.4.1.1.9", return_dict=True)
        # 对端设备的系统描述
        remote_system_desc_dict = self.snmp_walk("1.0.8802.1.1.2.1.4.1.1.10", return_dict=True)

        for id in remote_interface_dict:
            item = {
                "remote_interface": remote_interface_dict.get(id, ""),
                "remote_mac": remote_mac_dict.get(id, "").strip().replace(" ", ":"),
                "remote_system_name": remote_system_name_dict.get(id, ""),
                "remote_system_desc": remote_system_desc_dict.get(id, "").split(",")[0],
                "local_interface": self.PORTINDEX_NAME_DICT.get(id.split(".")[1], ""),
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

        return ret

    def get_hardware_info(self, interface_info, lldp_info, mac_table):

        hardware_info = self.get_hardware_extra_info()

        ret = {
            "port": [],
            "fan": hardware_info["fan"],
            "power": hardware_info["power"],
        }

        neighborhood_device = {}
        for lldp_item in lldp_info:
            neighborhood_device[lldp_item["local_interface"]] = {
                "remote_interface": lldp_item["remote_interface"],
                "remote_mac": lldp_item["remote_mac"]
            }
        for mac_item in mac_table:
            if not neighborhood_device.get(mac_item["ifName"]):
                neighborhood_device[mac_item["ifName"]] = {
                    "remote_interface": "",
                    "remote_mac": mac_item["mac"]
                }

        if_name_match = re.compile("(\d/)?\d/\d")
        port_list = self.snmp_walk("1.3.6.1.2.1.17.1.4.1.1")
        for port_index in port_list:
            if_index = self.PORTINDEX_IFINDEX_DICT.get(port_index, "")
            if not if_index:
                 continue
            item = {
                "index": port_index,
                "name": self.IFINDEX_NAME_DICT.get(if_index, ""),
                "mac": self.IF_MAC_DICT.get(if_index, "").strip().replace(" ", ":"),
                "ip": self.if_inet_dict.get(if_index, {}).get("ip", ""),
                "type": interface_info.get(if_index, {}).get("type", ""),
                "bandwidth_type": get_speed_type(interface_info.get(if_index, {}).get("ifHighSpeed", "0")) if interface_info.get(if_index, {}).get("ifHighSpeed", "").strip() else "unknown",
                "status": interface_info.get(if_index, {}).get("ifOperStatus", ""),
                "ifHCInOctets": interface_info.get(if_index, {}).get("ifHCInOctets", ""),
                "ifHCOutOctets": interface_info.get(if_index, {}).get("ifHCOutOctets", ""),
                "discard": interface_info.get(if_index, {}).get("discard", "0.00%"),
            }
            item["remote_interface"] = neighborhood_device.get(item["name"], {}).get("remote_interface", "")
            item["remote_mac"] = neighborhood_device.get(item["name"], {}).get("remote_mac", "")

            self.mapping["hardware"]["port"].append(
                {
                    "bandwidth_type": interface_info.get(if_index, {}).get("ifHighSpeed", "0"),
                    "ifHCInOctets": string_to_bytes(item["ifHCInOctets"]),
                    "ifHCOutOctets": string_to_bytes(item["ifHCOutOctets"])
                }
            )

            match = if_name_match.search(item["name"])
            if match:
                item["slot"] = match.group().split("/")[-2]
                item["chassis"] = MyList(match.group().split("/"))[-3]
            else:
                item["slot"] = ""
                item["chassis"] = ""

            ret["port"].append(item)

        return ret

    def integrate_info(self, data):
        return data

    def format_out(self):
        base_info = self.get_base_info()
        system_info = self.get_system_info()
        interface_info = self.get_interface_info()
        mac_info = self.get_mac_info()
        arp_info = self.get_arp_info()
        vlan_info = self.get_vlan_info()
        agg_link_info = self.get_agg_link_info()
        lldp_rem_device = self.get_lldp_rem_device_info()
        route_info = self.get_route_info()
        hardware_info = self.get_hardware_info(interface_info, lldp_rem_device, mac_info)

        base_info["total_input"] = size(self.total_in_bytes)
        base_info["total_output"] = size(self.total_out_bytes)

        self.mapping["base_info"]["total_input"] = "%s" %self.total_in_bytes
        self.mapping["base_info"]["total_output"] = "%s" %self.total_out_bytes


        base_info["total_discard"] = "%.2f%%" % (self.total_discards / self.total_packages * 100) if self.total_packages else ""

        #获取sysip信息
        if not self.sysip:
            for ifindex in self.if_inet_dict:
                if self.if_inet_dict[ifindex]["ip"] == self.scan_ip:
                    self.sysip = self.if_inet_dict[ifindex]["ip"]
                    self.sysip_mask = self.if_inet_dict[ifindex]["mask"]
                    self.sysip_mac = self.IF_MAC_DICT.get(ifindex, "")

        base_info["sysip"] = self.sysip
        base_info["sysip_mask"] = self.sysip_mask
        base_info["sysip_mac"] = self.sysip_mac
        base_info["sys_ipv6"] = ""

        interface_info_list = []
        for index in interface_info:
            interface_info_list.append(interface_info[index])

        network_info = {
            "ip": self.ip_list
        }

        result = {
            "os_type": self.device_type,
            "collect_time": time.strftime('%Y-%m-%d %H:%M:%S %a'),
            "uuid": hashlib.md5(base_info["serial_number"].encode()).hexdigest(),
            "base_info": base_info,
            "System_info": system_info,
            "Interface_list": interface_info_list,
            "MAC_table": mac_info,
            "ARP_table": arp_info,
            "Vlan_info": vlan_info,
            "Agg_link_info": agg_link_info,
            "Route_info": route_info,
            "LLDP_remote_device": lldp_rem_device,
            "hardware": hardware_info,
            # "neighborhood_device": self.get_neighborhood_device(lldp_rem_device, mac_info),
            "network": network_info,
            # "physical_module": physical_module_info,
            "mapping": self.mapping,
            "scan_ip": self.scan_ip
        }

        result = self.integrate_info(result)


        return result