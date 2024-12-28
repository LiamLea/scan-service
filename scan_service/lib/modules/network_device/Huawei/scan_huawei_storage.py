import copy
from scan_service.lib.utils import MyList
from scan_service.lib.utils import size
from scan_service.lib.common import ScanViaSNMP

from scan_service.lib.modules.network_device.Huawei.oid_map import storage_product_model_huawei
from scan_service.lib.modules.network_device.Huawei.oid_map import host_running_status_map
from scan_service.lib.modules.network_device.Huawei.oid_map import host_os_map
from scan_service.lib.modules.network_device.Huawei.oid_map import controller_role_map
from scan_service.lib.modules.network_device.Huawei.oid_map import controller_master_map
from scan_service.lib.modules.network_device.Huawei.oid_map import fd_host_port_status
from scan_service.lib.modules.network_device.Huawei.oid_map import raid_level_map
from scan_service.lib.modules.network_device.Huawei.oid_map import lun_write_policy_map
from scan_service.lib.modules.network_device.Huawei.oid_map import lun_prefecth_strategy_map
from scan_service.lib.modules.network_device.Huawei.oid_map import lun_smart_tier_strategy_map
from scan_service.lib.modules.network_device.Huawei.oid_map import fc_port_configured_rate_map
from scan_service.lib.modules.network_device.Huawei.oid_map import fc_port_model_map
from scan_service.lib.modules.network_device.Huawei.oid_map import fc_port_logical_type_map
from scan_service.lib.modules.network_device.Huawei.oid_map import eth_port_type_map
from scan_service.lib.modules.network_device.Huawei.oid_map import health_status_map
import datetime


class HuaweiStorageScan(ScanViaSNMP):

    def __init__(self, init_info):
        super(HuaweiStorageScan, self).__init__(init_info)
        self.sysip = ""
        self.sysip_mac = ""
        self.sysip_mask = ""

    def get_base_info(self):
        storage_name = self.snmp_walk("1.3.6.1.2.1.1.5")[0]
        manufacturer = "Unknown Manufacturer"
        if "huawei" in storage_name.lower():
            manufacturer = "Huawei"

        model_key = self.snmp_walk("1.3.6.1.4.1.34774.4.1.1.2")[0]
        storage_model = storage_product_model_huawei.get(model_key, "")
        serial_number = self.snmp_walk("1.3.6.1.4.1.34774.4.1.1.1")[0]

        software_version = self.snmp_walk("1.3.6.1.4.1.34774.4.1.1.6")[0]

        host_number = len(self.snmp_walk("1.3.6.1.4.1.34774.4.1.23.4.5.1.1"))
        controller_number = len(self.snmp_walk("1.3.6.1.4.1.34774.4.1.23.5.2.1.1"))
        lun_number = len(self.snmp_walk("1.3.6.1.4.1.34774.4.1.19.9.4.1.1"))

        # port number = com + eth + fc + fcoe + pci + sas
        port_com_num = len(self.snmp_walk("1.3.6.1.4.1.34774.4.1.23.5.7.1.1"))
        port_eth_num = len(self.snmp_walk("1.3.6.1.4.1.34774.4.1.23.5.8.1.1"))
        port_fc_num = len(self.snmp_walk("1.3.6.1.4.1.34774.4.1.23.5.9.1.1"))
        port_fcoe_num = len(self.snmp_walk("1.3.6.1.4.1.34774.4.1.23.5.10.1.1"))
        port_pci_num = len(self.snmp_walk("1.3.6.1.4.1.34774.4.1.23.5.11.1.1"))
        port_sas_num = len(self.snmp_walk("1.3.6.1.4.1.34774.4.1.23.5.12.1.1"))
        port_total_number = port_com_num + port_eth_num + port_fc_num + port_fcoe_num + port_pci_num + port_sas_num
        catbinet_total_number = ""
        disk_total_number = len(self.snmp_walk("1.3.6.1.4.1.34774.4.1.23.5.1.1.1"))
        storage_used = int(self.snmp_walk("1.3.6.1.4.1.34774.4.1.1.4")[0]) * 1048576
        storage_capacity = int(self.snmp_walk("1.3.6.1.4.1.34774.4.1.1.5")[0]) * 1048576
        storage_available = storage_capacity - storage_used
        power_number = len(self.snmp_walk("1.3.6.1.4.1.34774.4.1.23.5.3.1.1"))
        fan_number = len(self.snmp_walk("1.3.6.1.4.1.34774.4.1.23.5.4.1.1"))

        self.sysip = self.snmp_walk("1.3.6.1.2.1.4.20.1.1")[0]
        self.sysip_mask = self.snmp_walk("1.3.6.1.2.1.4.20.1.3")[0]
        port_num = self.snmp_walk("1.3.6.1.2.1.2.1")[0]

        temp_list = MyList(self.snmp_walk("1.3.6.1.2.1.1.3")[0].split(":"))
        # uptime = "%s days %s hours %s minutes" % (temp_list[-4], temp_list[-3], temp_list[-2])
        uptime = (datetime.datetime.now() - datetime.timedelta(days = int(temp_list[-4]) if temp_list[-4] else 0,
                                                               hours = int(temp_list[-3]) if temp_list[-3] else 0,
                                                               minutes = int(temp_list[-2]) if temp_list[-2] else 0,
                                                               seconds = float(temp_list[-1])
                                                               )).strftime('%Y-%m-%d %H:%M:%S')

        ret = {
            "manufacturer": manufacturer,
            "name": storage_name,
            "model": storage_model,
            "serial_number": serial_number,
            "software_version": software_version,
            "sysip": self.sysip,
            "sys_mac": self.get_sys_mac(self.sysip),
            "sysip_mask": self.sysip_mask,
            "uptime": uptime,
            "port_num": port_num,
            "host_number": host_number,
            "controller_number": controller_number,
            "LUN_number": lun_number,
            "Port_totalNumber": port_total_number,
            "catbinet_totalNumber": "",
            "disk_totalNumber": disk_total_number,
            "storage_capacity": size(storage_capacity),
            "storage_available": size(storage_available),
            "power_number": power_number,
            "fan_number": fan_number,
            "lun_list": list(),
            "host_list": list(),
            "controller_list": list(),
            "storage_pool_list": list(),
            "disk_domain_info": list(),
            "fc_port_list": list(),
            "eth_port_list": list()
        }

        return ret

    def get_sys_mac(self, sysip):
        ip_mac = ""
        all_ips = self.snmp_walk("1.3.6.1.4.1.34774.4.1.23.5.8.1.6")
        all_macs = self.snmp_walk("1.3.6.1.4.1.34774.4.1.23.5.8.1.12")

        if all_ips and sysip in all_ips:
            ip_index = all_ips.index(sysip)
            ip_mac = all_macs[ip_index]

        return ip_mac

    def get_hosts_info(self):
        # hwInfoHostTable and hwInfoHostGroupTable
        host_list = list()
        host_group_list = self.snmp_walk("1.3.6.1.4.1.34774.4.1.23.4.6.1.3")
        host_group_str = ",".join(host_group_list)

        host_id_dict = self.snmp_walk("1.3.6.1.4.1.34774.4.1.23.4.5.1.1", return_dict=True)
        host_name_dict = self.snmp_walk("1.3.6.1.4.1.34774.4.1.23.4.5.1.2", return_dict=True)
        host_status_dict = self.snmp_walk("1.3.6.1.4.1.34774.4.1.23.4.5.1.5", return_dict=True)
        host_os_dict = self.snmp_walk("1.3.6.1.4.1.34774.4.1.23.4.5.1.6", return_dict=True)
        host_ip_dict = self.snmp_walk("1.3.6.1.4.1.34774.4.1.23.4.5.1.7", return_dict=True)

        host_id_key_list = list(host_id_dict.keys())
        for host_id_key in host_id_key_list:
            host_info = dict()
            host_info["hostID"] = host_id_dict[host_id_key]
            host_info["hostName"] = host_name_dict[host_id_key]
            host_info["host_status"] = host_running_status_map.get(str(host_status_dict[host_id_key]), "unknown host running status")
            host_info["os_type"] = host_os_map.get(str(host_os_dict[host_id_key]), "unknown host OS")
            host_info["sysip"] = host_ip_dict[host_id_key]
            if host_name_dict[host_id_key] in host_group_str:
                host_info["IsInHostGroup"] = "True"
            else:
                host_info["IsInHostGroup"] = "False"
            host_info["starter_number"] = ""
            host_list.append(host_info)

        return host_list

    def get_controller_info(self):
        """entity controller控制器列表{
            控制器ID controllerID:用于内部索引
            控制器名称controller_name
            控制器位置controller_position
            控制器角色controller_role：0普通成员/1集群主/2集群备
            IP地址controller_IP
            cpu信息controller_mac
            cpu使用率controller_CPUUsage
            内存使用率controller_memoryUsage
            系统软件版本software_version
            控制器状态controller_status:
        }
        """
        # hwStorageControllerTable and hwInfoControllerTable
        controller_list = list()

        controller_id_dict = self.snmp_walk("1.3.6.1.4.1.34774.4.1.23.5.2.1.1", return_dict=True)
        controller_position_dict = self.snmp_walk("1.3.6.1.4.1.34774.4.1.23.5.2.1.5", return_dict=True)
        controller_role_dict = self.snmp_walk("1.3.6.1.4.1.34774.4.1.23.5.2.1.6", return_dict=True)
        controller_ip = ""
        controller_cpu_dict = self.snmp_walk("1.3.6.1.4.1.34774.4.1.23.5.2.1.4", return_dict=True)
        controller_cpu_usage_dict = self.snmp_walk("1.3.6.1.4.1.34774.4.1.23.5.2.1.8", return_dict=True)
        controller_memory_usage_dict = self.snmp_walk("1.3.6.1.4.1.34774.4.1.23.5.2.1.9", return_dict=True)
        controller_software_version_dict = self.snmp_walk("1.3.6.1.4.1.34774.4.1.23.5.2.1.11", return_dict=True)

        storage_controller_id_dict = self.snmp_walk("1.3.6.1.4.1.34774.4.1.19.8.12.1.1", return_dict=True)
        storage_controller_name_dict = self.snmp_walk("1.3.6.1.4.1.34774.4.1.19.8.12.1.2", return_dict=True)
        storage_controller_position_dict = self.snmp_walk("1.3.6.1.4.1.34774.4.1.19.8.12.1.3", return_dict=True)
        storage_controller_status_dict = self.snmp_walk("1.3.6.1.4.1.34774.4.1.19.8.12.1.8", return_dict=True)

        controller_id_key_list = list(controller_id_dict.keys())

        for controller_id_key in controller_id_key_list:
            controller_info = dict()
            controller_info["controllerID"] = controller_id_dict[controller_id_key]
            controller_info["controller_position"] = controller_position_dict[controller_id_key]
            controller_info["controller_role"] = \
                controller_role_map.get(str(controller_role_dict[controller_id_key]), "unknown controller role")
            # if controller_role == "0":
            #     controller_info["controller_role"] = "普通成员"
            # if controller_role == "1":
            #     controller_info["controller_role"] = "集群主"
            # if controller_role == "2":
            #     controller_info["controller_role"] = "集群备"

            controller_info["controller_mac"] = controller_cpu_dict[controller_id_key]
            controller_info["controller_CPUUsage"] = str(controller_cpu_usage_dict[controller_id_key]) + "%"
            controller_info["controller_memoryUsage"] = str(controller_memory_usage_dict[controller_id_key]) + "%"
            controller_info["software_version"] = controller_software_version_dict[controller_id_key]

            storage_controller_position = controller_position_dict[controller_id_key]
            storage_controller_position_index = \
                list(storage_controller_position_dict.keys())[list(storage_controller_position_dict.values()).index(storage_controller_position)]
            controller_info["controller_name"] = storage_controller_name_dict[storage_controller_position_index]
            controller_info["controller_status"] = \
                controller_master_map.get(str(storage_controller_status_dict[storage_controller_position_index]), "unknown controller master")
            controller_list.append(controller_info)

        return controller_list

    def get_lun_info(self):
        """entity LUN卷{
           LUNID
           LUN名称 LUN_name
           类型LUN_type
           LUN的wwn LUN_wwn
           LUN容量LUN_capacity
           LUN已分配容量 LUN_capacity_assigned
           LUN归属存储池 LUN_attribute_pool_name
           LUN归属控制器节点IDLUN_attribute_controllerID
           SmartTier策略SmartTier_strategy
           LUN扇区大小:lun_sector_size
           CHUNK大小lun_CHUNK_size
           LUN的缓存写策略lun_write_policy
           LUN的缓存预取策略lun_prefetch_policy
           LUN的读/写Cache策略lun_cache_write_read_policy
           LUN的使用类型 lun_usage_type
        }
        """
        # hwPerfLunTable
        # hwStorageLunTable and hwInfoStoragePoolTable
        # hwInfoLunTable 1.3.6.1.4.1.34774.4.1.23.4.8 ----- invalid
        lun_list = list()

        lun_id_dict = self.snmp_walk("1.3.6.1.4.1.34774.4.1.19.9.4.1.1", return_dict=True)
        lun_name_dict = self.snmp_walk("1.3.6.1.4.1.34774.4.1.19.9.4.1.2", return_dict=True)
        lun_type_dict = ""
        lun_wwn_dict = self.snmp_walk("1.3.6.1.4.1.34774.4.1.19.9.4.1.3", return_dict=True)
        lun_capacity_dict = self.snmp_walk("1.3.6.1.4.1.34774.4.1.19.9.4.1.5", return_dict=True)
        lun_capacity_assigned_dict = ""
        lun_attribute_pool_id_dict =  self.snmp_walk("1.3.6.1.4.1.34774.4.1.19.9.4.1.4", return_dict=True)
        lun_controller_id_dict = self.snmp_walk("1.3.6.1.4.1.34774.4.1.19.9.4.1.6", return_dict=True)
        lun_smarttier_dict = ""
        lun_sector_size_dict = ""
        lun_chunk_size_dict = ""
        lun_write_policy_dict = self.snmp_walk("1.3.6.1.4.1.34774.4.1.19.9.4.1.8", return_dict=True)
        lun_prefetch_policy_dict = self.snmp_walk("1.3.6.1.4.1.34774.4.1.19.9.4.1.9", return_dict=True)
        lun_cache_read_or_write_policy_dict = ""
        lun_usage_type_dict = ""

        # storage id name smarttier_strategy
        storage_pool_id = self.snmp_walk("1.3.6.1.4.1.34774.4.1.23.4.2.1.1", return_dict=True)
        storage_pool_name = self.snmp_walk("1.3.6.1.4.1.34774.4.1.23.4.2.1.2", return_dict=True)
        storage_pool_smarttier_strategy = self.snmp_walk("1.3.6.1.4.1.34774.4.1.23.4.2.1.16", return_dict=True)

        storage_pool_id_keys_list = list(storage_pool_id.keys())
        storage_pool_info_dict = dict()
        for storage_pool_id_key in storage_pool_id_keys_list:
            if storage_pool_id[storage_pool_id_key] not in storage_pool_info_dict:
                storage_pool_info_dict[storage_pool_id[storage_pool_id_key]] = dict()
                storage_pool_info_dict[storage_pool_id[storage_pool_id_key]]["pool_name"] = \
                    storage_pool_name.get(storage_pool_id_key, "")
                storage_pool_info_dict[storage_pool_id[storage_pool_id_key]]["smarttier_strategy"] = \
                    storage_pool_smarttier_strategy.get(storage_pool_id_key, "")
            elif storage_pool_id[storage_pool_id_key] in storage_pool_info_dict:
                storage_pool_info_dict[storage_pool_id[storage_pool_id_key]]["pool_name"] = \
                    storage_pool_name.get(storage_pool_id_key, "")
                storage_pool_info_dict[storage_pool_id[storage_pool_id_key]]["smarttier_strategy"] = \
                    storage_pool_smarttier_strategy.get(storage_pool_id_key, "")

        lun_id_keys_list = list(lun_id_dict.keys())

        for lun_id_key in lun_id_keys_list:
            lun_info = dict()
            lun_info["lun_ID"] = lun_id_dict[lun_id_key]
            lun_info["lun_name"] = lun_name_dict[lun_id_key]
            lun_info["lun_type"] = ""
            lun_info["lun_wwn"] = lun_wwn_dict[lun_id_key]
            lun_info["lun_capacity"] = size(int(lun_capacity_dict[lun_id_key]) * 1024)
            lun_info["lun_capacity_assigned"] = ""
            lun_info["lun_attribute_pool_name"] = \
                storage_pool_info_dict[lun_attribute_pool_id_dict[lun_id_key]]["pool_name"]
            lun_info["lun_attribute_controllerID"] = lun_controller_id_dict[lun_id_key]
            smarttier_strategy = storage_pool_info_dict[lun_attribute_pool_id_dict[lun_id_key]]["smarttier_strategy"]
            lun_info["lun_smarttier_strategy"] = \
                lun_smart_tier_strategy_map.get(str(smarttier_strategy), "unknown smart tier strategy")
            lun_info["lun_sector_size"] = ""
            lun_info["lun_chunk_size"] = ""
            lun_info["lun_write_policy"] = \
                lun_write_policy_map.get(lun_prefetch_policy_dict[lun_id_key], "unknown write policy")
            lun_info["lun_prefetch_policy"] = \
                lun_prefecth_strategy_map.get(lun_prefetch_policy_dict[lun_id_key], "unknown prefetch policy")
            lun_info["lun_cache_write_read_policy"] = ""
            lun_info["lun_usage_type"] = ""

            lun_list.append(lun_info)

        return lun_list

    def get_storage_pool_info(self):
        """entity pool存储池列表{
          存储池总量pool_total_number
          存储池ID poolID
          存储池名称pool_name
          存储池所在磁盘域名称ID/名称：diskDomain
          存储池健康状态pool_status
          存储池容量阈值pool_capacity_shreshold
          存储池可用容量pool_available
          存储池数据保护容量pool_capacity_protected
          存储层pool_layers:3个
          Extent块大小extent_block_size
          存储池迁移粒度pool_migration_granularity
          存储池已配置Lun容量:pool_configured_lun
        }
        """
        # hwInfoStoragePoolTable
        storage_pool_list = list()

        storage_pool_id_dict = self.snmp_walk("1.3.6.1.4.1.34774.4.1.23.4.2.1.1", return_dict=True)
        storage_pool_name_dict = self.snmp_walk("1.3.6.1.4.1.34774.4.1.23.4.2.1.2", return_dict=True)
        # storage_pool_diskDomain_dict = self.snmp_walk("1.3.6.1.4.1.34774.4.1.23.4.2.1.4", return_dict=True)
        storage_pool_status_dict = self.snmp_walk("1.3.6.1.4.1.34774.4.1.23.4.2.1.5", return_dict=True)
        storage_pool_capacity_shreshold_dict = self.snmp_walk("1.3.6.1.4.1.34774.4.1.23.4.2.1.14", return_dict=True)
        storage_pool_total_dict = self.snmp_walk("1.3.6.1.4.1.34774.4.1.23.4.2.1.7", return_dict=True)
        storage_pool_available_dict = self.snmp_walk("1.3.6.1.4.1.34774.4.1.23.4.2.1.9", return_dict=True)
        storage_pool_capacity_protected_dict = self.snmp_walk("1.3.6.1.4.1.34774.4.1.23.4.2.1.10", return_dict=True)
        # storage_pool_layer0_dict = self.snmp_walk("1.3.6.1.4.1.34774.4.1.23.4.2.1.11", return_dict=True)
        # storage_pool_layer1_dict = self.snmp_walk("1.3.6.1.4.1.34774.4.1.23.4.2.1.12", return_dict=True)
        # storage_pool_layer2_dict = self.snmp_walk("1.3.6.1.4.1.34774.4.1.23.4.2.1.13", return_dict=True)
        # storage_pool_extent_block_size_dict = "" # 与粒度是一回事？
        storage_pool_migration_granularity_dict = self.snmp_walk("1.3.6.1.4.1.34774.4.1.23.4.2.1.15", return_dict=True)

        # 1.3.6.1.4.1.34774.4.1.23.4.2.1.23 不存在！！！
        storage_pool_configured_lun_dict = self.snmp_walk("1.3.6.1.4.1.34774.4.1.23.4.2.1.23", return_dict=True)

        storage_pool_id_key_list = list(storage_pool_id_dict.keys())

        for storage_pool_id_key in storage_pool_id_key_list:
            storage_pool = dict()
            storage_pool["pool_total_number"] = storage_pool_total_dict[storage_pool_id_key]
            storage_pool["poolID"] = storage_pool_id_dict[storage_pool_id_key]
            storage_pool["pool_name"] = storage_pool_name_dict[storage_pool_id_key]
            storage_pool["pool_status"] = health_status_map.get(str(storage_pool_status_dict[storage_pool_id_key]), "unknown status")
            storage_pool["pool_capacity_shreshold"] = str(storage_pool_capacity_shreshold_dict[storage_pool_id_key]) + "%"
            storage_pool["pool_available"] = storage_pool_available_dict[storage_pool_id_key]
            if storage_pool_available_dict[storage_pool_id_key]:
                storage_pool["pool_available"] = size(int(storage_pool_available_dict[storage_pool_id_key]) * 1048576)
            else:
                storage_pool["pool_available"] = ""
            storage_pool["pool_capacity_protected"] = size(int(storage_pool_capacity_protected_dict[storage_pool_id_key]) * 1048576)

            # if storage_pool_layer0_dict[storage_pool_id_key]:
            #     storage_pool_layer0 = size(int(storage_pool_layer0_dict[storage_pool_id_key]) * 1048576)
            # else:
            #     storage_pool_layer0 = ""
            # if storage_pool_layer1_dict[storage_pool_id_key]:
            #     storage_pool_layer1 = size(int(storage_pool_layer1_dict[storage_pool_id_key]) * 1048576)
            # else:
            #     storage_pool_layer1 = ""
            # if storage_pool_layer2_dict[storage_pool_id_key]:
            #     storage_pool_layer2 = size(int(storage_pool_layer2_dict[storage_pool_id_key]) * 1048576)
            # else:
            #     storage_pool_layer2 = ""
            # storage_pool["pool_layers"] = [storage_pool_layer0, storage_pool_layer1, storage_pool_layer2]

            storage_pool["pool_layers"] = list()

            storage_pool["pool_migration_granularity"] = size(int(storage_pool_migration_granularity_dict[storage_pool_id_key]) * 1024)
            if storage_pool_configured_lun_dict.get(storage_pool_id_key, 0) != 0:
                storage_pool["pool_configured_lun"] = size(int(storage_pool_configured_lun_dict[storage_pool_id_key]) * 1048576)
            else:
                storage_pool["pool_configured_lun"] = 'no oid'
            storage_pool_list.append(storage_pool)

        return storage_pool_list

    def get_storage_layer_info(self):
        """entity 存储层{
          ID：storage_layerID不用显示，用于跟存储池关联
          存储层名称storage_layer_name：Tier0
          裸容量storage_layer_raw_capacity：
          用户容量storage_layer_user_capacity:
          可用容量storage_layer_avaliable
          硬盘域数量storage_layer_disk_number:
          RAID级别storage_layer_raid_level

          存储层Tier1
          。。。。
          存储层Tier2
        }
        """
        # hwInfoStorageTierTable and hwInfoStoragePoolTable
        storage_pool_layer = dict()

        storage_layer_id_dict = self.snmp_walk("1.3.6.1.4.1.34774.4.1.23.4.3.1.1", return_dict=True)
        storage_layer_name_dict = self.snmp_walk("1.3.6.1.4.1.34774.4.1.23.4.3.1.2", return_dict=True)
        # storage_layer_raw_capacity_dict = self.snmp_walk("1.3.6.1.4.1.34774.4.1.23.4.3.1.1", return_dict=True)
        storage_layer_user_capacity_dict = self.snmp_walk("1.3.6.1.4.1.34774.4.1.23.4.3.1.6", return_dict=True)
        storage_layer_avaliable_dict = self.snmp_walk("1.3.6.1.4.1.34774.4.1.23.4.3.1.8", return_dict=True)
        storage_layer_disk_number_dict = self.snmp_walk("1.3.6.1.4.1.34774.4.1.23.4.3.1.10", return_dict=True)
        storage_layer_raid_level_dict = self.snmp_walk("1.3.6.1.4.1.34774.4.1.23.4.3.1.9", return_dict=True)

        storage_pool_id_dict = self.snmp_walk("1.3.6.1.4.1.34774.4.1.23.4.2.1.1", return_dict=True)
        storage_pool_tier0_dict = self.snmp_walk("1.3.6.1.4.1.34774.4.1.23.4.2.1.11", return_dict=True)
        storage_pool_tier1_dict = self.snmp_walk("1.3.6.1.4.1.34774.4.1.23.4.2.1.12", return_dict=True)
        storage_pool_tier2_dict = self.snmp_walk("1.3.6.1.4.1.34774.4.1.23.4.2.1.13", return_dict=True)
        storage_layer_tier_pool_id_dict = self.snmp_walk("1.3.6.1.4.1.34774.4.1.23.4.3.1.3", return_dict=True)

        storage_layer_id_key_list = list(storage_layer_id_dict.keys())
        # storage_pool_id_key_list = storage_pool_id_dict.keys()
        for storage_layer_id_key in storage_layer_id_key_list:
            storage_layer = dict()
            storage_layer_name = storage_layer_name_dict[storage_layer_id_key]

            storage_layer_tier_pool_id = storage_layer_tier_pool_id_dict[storage_layer_id_key]
            storage_tier_pool_id_key = \
                list(storage_pool_id_dict.keys())[list(storage_pool_id_dict.values()).index(storage_layer_tier_pool_id)]

            if storage_layer_name == "tier0":
                storage_layer["storage_layer_name"] = "tier0"
                storage_layer["storage_layer_raw_capacity"] = \
                    size(int(storage_pool_tier0_dict[storage_tier_pool_id_key]) * 1048576)
            if storage_layer_name == "tier1":
                storage_layer["storage_layer_name"] = "tier1"
                storage_layer["storage_layer_raw_capacity"] = \
                    size(int(storage_pool_tier1_dict[storage_tier_pool_id_key]) * 1048576)
            if storage_layer_name == "tier2":
                storage_layer["storage_layer_name"] = "tier2"
                storage_layer["storage_layer_raw_capacity"] = \
                    size(int(storage_pool_tier2_dict[storage_tier_pool_id_key]) * 1048576)
            storage_layer["storage_layerID"] = storage_layer_id_dict[storage_layer_id_key]
            storage_layer["storage_layer_user_capacity"] = \
                size(int(storage_layer_user_capacity_dict[storage_layer_id_key]) * 1048576)
            storage_layer["storage_layer_avaliable"] = \
                size(int(storage_layer_avaliable_dict[storage_layer_id_key]) * 1048576)
            storage_layer["storage_layer_disk_number"] = storage_layer_disk_number_dict[storage_layer_id_key]
            storage_layer["storage_layer_raid_level"] = \
                raid_level_map.get(str(storage_layer_raid_level_dict[storage_layer_id_key]), "")

            if storage_layer_tier_pool_id in storage_pool_layer:
                storage_pool_layer[storage_layer_tier_pool_id].append(storage_layer)
            else:
                storage_pool_layer[storage_layer_tier_pool_id] = list()
                storage_pool_layer[storage_layer_tier_pool_id].append(storage_layer)

        return storage_pool_layer

    def get_fc_port_info(self):
        """entity FC端口列表{
          端口所属主机FC_port_attribute_host
          端口ID/位置FC_port_position:XXX0.A1.P0
          端口wwpn FC_port_wwpn
          健康状态 FC_port_status
          端口配置速率FC_port_configured_speed
          主机端口模式 FC_port_model
          端口逻辑类型 FC_port_logical_type
        }
        """
        # hwStorageFCPortTable
        fc_port_list = list()

        fc_port_id_dict = self.snmp_walk("1.3.6.1.4.1.34774.4.1.19.8.7.1.1", return_dict=True)
        fc_port_to_host_dict = self.snmp_walk("1.3.6.1.4.1.34774.4.1.19.8.7.1.3", return_dict=True)
        # fc_port_position_dict = self.snmp_walk("1.3.6.1.4.1.34774.4.1.23.5.9.1.2", return_dict=True)
        fc_port_wwn_dict = self.snmp_walk("1.3.6.1.4.1.34774.4.1.19.8.7.1.7", return_dict=True)
        fc_port_status_dict = self.snmp_walk("1.3.6.1.4.1.34774.4.1.19.8.7.1.4", return_dict=True)
        fc_port_configured_speed_dict = self.snmp_walk("1.3.6.1.4.1.34774.4.1.19.8.7.1.5", return_dict=True)
        fc_port_model_dict = self.snmp_walk("1.3.6.1.4.1.34774.4.1.19.8.7.1.6", return_dict=True)
        fc_port_logical_type_dict = self.snmp_walk("1.3.6.1.4.1.34774.4.1.19.8.7.1.8", return_dict=True)

        fc_port_id_key_list = list(fc_port_id_dict.keys())
        for fc_port_id_key in fc_port_id_key_list:
            fc_port = dict()
            fc_port["FC_port_attribute_host"] = fc_port_to_host_dict[fc_port_id_key]
            fc_port["FC_port_position"] = fc_port_id_dict[fc_port_id_key]
            fc_port["FC_port_wwpn"] = fc_port_wwn_dict[fc_port_id_key]
            fc_port["FC_port_status"] = fd_host_port_status.get(str(fc_port_status_dict[fc_port_id_key]), "unknown status")
            fc_port["FC_port_configured_speed"] = fc_port_configured_rate_map.get(str(fc_port_configured_speed_dict[fc_port_id_key]), "unknown configured speed")
            fc_port["FC_port_model"] = fc_port_model_map.get(str(fc_port_model_dict[fc_port_id_key]), "unknown mode")
            fc_port["FC_port_logical_type"] = fc_port_logical_type_map.get(str(fc_port_logical_type_dict[fc_port_id_key]), "unknown fc logic type")

            fc_port_list.append(fc_port)

        return fc_port_list

    def get_disk_domain_info(self):
        # hwInfoDiskDomainTable and hwInfoStoragePoolTable
        disk_domain_list = list()

        disk_domain_id_dict = self.snmp_walk("1.3.6.1.4.1.34774.4.1.23.4.1.1.1", return_dict=True)
        disk_domain_tier0_dict = self.snmp_walk("1.3.6.1.4.1.34774.4.1.23.4.1.1.9", return_dict=True)
        disk_domain_tier1_dict = self.snmp_walk("1.3.6.1.4.1.34774.4.1.23.4.1.1.15", return_dict=True)
        disk_domain_tier2_dict = self.snmp_walk("1.3.6.1.4.1.34774.4.1.23.4.1.1.21", return_dict=True)
        disk_domain_capacity_dict = self.snmp_walk("1.3.6.1.4.1.34774.4.1.23.4.1.1.7", return_dict=True)
        storage_pool_disk_domain_id_list = self.snmp_walk("1.3.6.1.4.1.34774.4.1.23.4.2.1.3")

        disk_domain_id_key_list = list(disk_domain_id_dict.keys())

        for disk_domain_id_key in list(disk_domain_id_key_list):
            disk_domain_single = dict()
            disk_domain_single["disk_domainID"] = disk_domain_id_dict[disk_domain_id_key]
            disk_domain_single["disk_domain_total_number"] = int(disk_domain_tier0_dict[disk_domain_id_key]) + int(disk_domain_tier1_dict[disk_domain_id_key]) + int(disk_domain_tier2_dict[disk_domain_id_key])
            disk_domain_single["disk_domain_capacity_assigned"] = size(int(disk_domain_capacity_dict[disk_domain_id_key]) * 1046576)
            disk_domain_single["domain_pool_number"] = storage_pool_disk_domain_id_list.count(disk_domain_id_dict[disk_domain_id_key])
            disk_domain_single["disk_number_info_in_domain"] = dict()
            disk_domain_list.append(disk_domain_single)

        return disk_domain_list

    def get_disk_info_in_domain(self):
        """磁盘逻辑类型统计disk_totalNumber_logicalType：按照逻辑类型归类统计
        空闲盘总数disk_number_idle:
        成员盘总数disk_number_member
        热备盘总数disk_number_hot_standby
        缓存盘总数disk_number_cache
        磁盘类型disk_totalNumber_physicalType：按照数量归类统计
        FC盘disk_number_FC:
        SAS盘 disk_number_SAS
        disk_number_SATA
        """
        # hwInfoDiskTable
        disk_info = dict()
        # disk_number_list = list()
        # disk_id_list = list()

        # disk_id_dict = self.snmp_walk("1.3.6.1.4.1.34774.4.1.23.5.1.1.1", return_dict=True)
        disk_type_dict = self.snmp_walk("1.3.6.1.4.1.34774.4.1.23.5.1.1.5", return_dict=True)
        disk_role_dict = self.snmp_walk("1.3.6.1.4.1.34774.4.1.23.5.1.1.7", return_dict=True)

        disk_domain_dict = self.snmp_walk("1.3.6.1.4.1.34774.4.1.23.5.1.1.17", return_dict=True)

        # disk_id_key_list = list(disk_id_dict.keys())
        disk_domain_key_list = list(disk_domain_dict.keys())

        disk_totalNumber_logicalType = {"disk_number_idle": 0, "disk_number_member": 0, "disk_number_hot_standby": 0, "disk_number_cache": 0}
        disk_totalNumber_physicalType = {"disk_number_FC": 0,"disk_number_SAS": 0, "disk_number_SATA": 0}

        for disk_domain_key in disk_domain_key_list:
            if disk_domain_dict[disk_domain_key] not in disk_info:
                disk_info[disk_domain_dict[disk_domain_key]] = dict()
                disk_info[disk_domain_dict[disk_domain_key]]["disk_totalNumber_logicalType"] = disk_totalNumber_logicalType
                if int(disk_role_dict[disk_domain_key]) == 1:
                    disk_info[disk_domain_dict[disk_domain_key]]["disk_totalNumber_logicalType"]["disk_number_idle"] += 1
                if int(disk_role_dict[disk_domain_key]) == 2:
                    disk_info[disk_domain_dict[disk_domain_key]]["disk_totalNumber_logicalType"]["disk_number_member"] += 1
                if int(disk_role_dict[disk_domain_key]) == 3:
                    disk_info[disk_domain_dict[disk_domain_key]]["disk_totalNumber_logicalType"]["disk_number_hot_standby"] += 1
                if int(disk_role_dict[disk_domain_key]) == 4:
                    disk_info[disk_domain_dict[disk_domain_key]]["disk_totalNumber_logicalType"]["disk_number_cache"] += 1

                disk_info[disk_domain_dict[disk_domain_key]]["disk_totalNumber_physicalType"] = disk_totalNumber_physicalType
                if int(disk_type_dict[disk_domain_key]) == 0:
                    disk_info[disk_domain_dict[disk_domain_key]]["disk_totalNumber_physicalType"]["disk_number_FC"] += 1
                if int(disk_type_dict[disk_domain_key]) == 1:
                    disk_info[disk_domain_dict[disk_domain_key]]["disk_totalNumber_physicalType"]["disk_number_SAS"] += 1
                if int(disk_type_dict[disk_domain_key]) == 2:
                    disk_info[disk_domain_dict[disk_domain_key]]["disk_totalNumber_physicalType"]["disk_number_SATA"] += 1

        return disk_info

    def get_eth_port_info(self):
        # hwInfoPortEthTable
        eth_port_list = list()
        invalid_speed = 4294967295

        eth_port_id_dict = self.snmp_walk("1.3.6.1.4.1.34774.4.1.23.5.8.1.1", return_dict=True)
        eth_port_position_dict = self.snmp_walk("1.3.6.1.4.1.34774.4.1.23.5.8.1.2", return_dict=True)
        eth_port_status_dict = self.snmp_walk("1.3.6.1.4.1.34774.4.1.23.5.8.1.3", return_dict=True)
        eth_port_type_dict = self.snmp_walk("1.3.6.1.4.1.34774.4.1.23.5.8.1.5", return_dict=True)
        eth_port_ipv4_dict = self.snmp_walk("1.3.6.1.4.1.34774.4.1.23.5.8.1.6", return_dict=True)
        eth_port_ipv6_dict = self.snmp_walk("1.3.6.1.4.1.34774.4.1.23.5.8.1.9", return_dict=True)
        eth_port_mac_dict = self.snmp_walk("1.3.6.1.4.1.34774.4.1.23.5.8.1.12", return_dict=True)
        eth_port_speed_dict = self.snmp_walk("1.3.6.1.4.1.34774.4.1.23.5.8.1.16", return_dict=True)

        eth_port_id_key_list = list(eth_port_id_dict.keys())

        for eth_port_id_key in eth_port_id_key_list:
            eth_port = dict()
            eth_port["eth_port_position"] = eth_port_position_dict[eth_port_id_key]
            eth_port["eth_port_status"] = health_status_map.get(str(eth_port_status_dict[eth_port_id_key]), "unknown status")
            eth_port["eth_port_type"] = eth_port_type_map.get(str(eth_port_type_dict[eth_port_id_key]), "unknown port type")
            if eth_port_ipv4_dict.get(eth_port_id_key, "") and eth_port_ipv6_dict.get(eth_port_id_key, ""):
                eth_port["eth_port_ip"] = eth_port_ipv4_dict[eth_port_id_key] + "," + eth_port_ipv6_dict[eth_port_id_key]
            elif eth_port_ipv4_dict.get(eth_port_id_key, "") and not eth_port_ipv6_dict.get(eth_port_id_key, ""):
                eth_port["eth_port_ip"] = eth_port_ipv4_dict[eth_port_id_key]
            elif not eth_port_ipv4_dict.get(eth_port_id_key, "") and eth_port_ipv6_dict.get(eth_port_id_key, ""):
                eth_port["eth_port_ip"] = eth_port_ipv6_dict[eth_port_id_key]
            else:
                eth_port["eth_port_ip"] = ""
            eth_port["eth_port_mac"] = eth_port_mac_dict[eth_port_id_key]
            if int(eth_port_speed_dict[eth_port_id_key]) != invalid_speed:
                eth_port["eth_port_speed"] = size(int(eth_port_speed_dict[eth_port_id_key]) * 1048576) + "bps"
            elif int(eth_port_speed_dict[eth_port_id_key]) == invalid_speed:
                eth_port["eth_port_speed"] = "invalid speed"
            else:
                eth_port["eth_port_speed"] = "unknown"

            eth_port_list.append(eth_port)

        return eth_port_list

    def format_out(self):
        base_info = self.get_base_info()
        hosts_info = self.get_hosts_info()
        controller_info = self.get_controller_info()
        storage_pool_info = self.get_storage_pool_info()
        lun_info = self.get_lun_info()
        storage_layer_info = self.get_storage_layer_info()
        fc_port_info = self.get_fc_port_info()
        disk_domain_info = self.get_disk_domain_info()
        disk_number_info_in_domain = self.get_disk_info_in_domain()
        eth_port_info = self.get_eth_port_info()

        # add storage_layer in storage_layers of storage_pool_info
        storage_layer_pool_id_keys = list(storage_layer_info.keys())
        for storage_pool in storage_pool_info:
            for storage_layer_pool_id_key in storage_layer_pool_id_keys:
                if storage_pool["poolID"] == storage_layer_pool_id_key:
                    storage_pool["pool_layers"] = storage_layer_info[storage_layer_pool_id_key]

        result = copy.deepcopy(base_info)

        result["lun_list"] = lun_info
        result["host_list"] = hosts_info
        result["controller_list"] = controller_info
        result["storage_pool_list"] = storage_pool_info
        for disk_domain in disk_domain_info:
            if disk_number_info_in_domain.get(disk_domain["disk_domainID"], {}):
                disk_domain["disk_number_info_in_domain"] = disk_number_info_in_domain[disk_domain["disk_domainID"]]
        # result["disk_info"]["disk_list"] = disk_info
        result["disk_domain_info"] = disk_domain_info
        result["fc_port_list"] = fc_port_info
        result["eth_port_list"] = eth_port_info

        return result
