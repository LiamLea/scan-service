try:
    from easysnmp import Session
except Exception:
    pass
from scan_service.lib.common import ScanViaSNMP
import hashlib
import datetime
import time
from scan_service.lib.framework import BusinessException


class SangforScan(ScanViaSNMP):
    def __init__(self, init_info):
        super(SangforScan, self).__init__(init_info)

    def get_disk(self):
        disk_list = []

        DiskPartition_list = self.snmp_walk('.1.3.6.1.4.1.35047.1.5.1.2', return_dict=True)
        TotalDisk_list = self.snmp_walk('.1.3.6.1.4.1.35047.1.5.1.3', return_dict=True)
        FreeDisk_list = self.snmp_walk('.1.3.6.1.4.1.35047.1.5.1.5', return_dict=True)
        disk_num = list(DiskPartition_list.keys())
        for i in disk_num:
            disk_dict = {}
            disk_dict['DiskPartition'] = DiskPartition_list[i]
            disk_dict['TotalDiskSize'] = TotalDisk_list[i]
            disk_dict['FreeDiskSize'] = FreeDisk_list[i]
            disk_list.append(disk_dict)
        return disk_list

    def get_memory(self):
        memory = {}
        MemoryTotal = self.snmp_walk('.1.3.6.1.4.1.35047.1.13.4')   #老版本不支持
        MemoryFree = self.snmp_walk('.1.3.6.1.4.1.35047.1.13.3')     #老版本不支持
        if MemoryTotal:
            memory['MemoryTotal'] = "%.2f" % (int(MemoryTotal[0]) / 1024 / 1024) + 'GB'
        else:
            memory['MemoryTotal'] = ''
        if MemoryFree:
            memory['MemoryFree'] = "%.2f" % (int(MemoryTotal[0]) / 1024 / 1024) + 'GB'
        else:
            memory['MemoryFree'] = ''
        MemoryUsage = self.snmp_walk('.1.3.6.1.4.1.35047.2.2.19.0')[0]
        memory['MemoryUsage'] = MemoryUsage
        return memory

    # 老版本不支持
    def get_fan(self):
        fan_list = []
        FanIndex_list = self.snmp_walk('.1.3.6.1.4.1.35047.1.14.1.2', return_dict=True)
        FanStatus_list = self.snmp_walk('.1.3.6.1.4.1.35047.1.14.1.4', return_dict=True)
        FanSpeed_list = self.snmp_walk('.1.3.6.1.4.1.35047.1.14.1.3', return_dict=True)
        fan_num = list(FanIndex_list.keys())
        for i in fan_num:
            fan_dict = {}
            fan_dict['FanIndex'] = FanIndex_list[i]
            fan_dict['FanStatus'] = FanStatus_list[i]
            fan_dict['FanSpeed'] = FanSpeed_list[i]
            fan_list.append(fan_dict)
        return fan_list

    # 老版本不支持
    def get_power(self):
        power_list = []
        PowerIndex_list = self.snmp_walk('.1.3.6.1.4.1.35047.1.15.1.2', return_dict=True)
        PowerStatus_list = self.snmp_walk('.1.3.6.1.4.1.35047.1.15.1.3', return_dict=True)
        power_num = list(PowerIndex_list.keys())
        for i in power_num:
            power_dict = {}
            power_dict['PowerIndex'] = PowerIndex_list[i]
            power_dict['PowerStatus'] = PowerStatus_list[i]
            power_list.append(power_dict)
        return power_list

    def get_cpu(self):
        cpu = {}
        cpu['CpuCount'] = self.snmp_walk('.1.3.6.1.4.1.35047.2.2.16.0')[0]
        cpu['CpuUsage'] = self.snmp_walk('.1.3.6.1.4.1.35047.2.2.20.0')[0]
        cpu['CpuCoreCount'] = self.snmp_walk('.1.3.6.1.4.1.35047.2.2.17.0')[0]
        CpuUsage1m = self.snmp_walk('.1.3.6.1.4.1.35047.1.16.1.3') #老版本不支持
        if CpuUsage1m:
            cpu['CpuUsage1m'] = CpuUsage1m[0]
        else:
            cpu['CpuUsage1m'] = ''
        CpuUsage5m = self.snmp_walk('.1.3.6.1.4.1.35047.1.16.1.4') #老版本不支持
        if CpuUsage5m:
            cpu['CpuUsage5m'] = CpuUsage5m[0]
        else:
            cpu['CpuUsage5m'] = ''
        CpuUsage15m = self.snmp_walk('.1.3.6.1.4.1.35047.1.16.1.5') #老版本不支持
        if CpuUsage15m:
            cpu['CpuUsage15m'] = CpuUsage15m[0]
        else:
            cpu['CpuUsage15m'] = ''
        return cpu

    def get_system(self):
        system = {}
        system['Manufacturer'] = 'Sangfor'
        system['Uptime'] = self.snmp_walk('.1.3.6.1.4.1.35047.1.2.0')[0]
        NodeName = self.snmp_walk('.1.3.6.1.4.1.35047.2.2.31') #老版本不支持
        if NodeName:
            system['NodeName'] = NodeName[0]
        else:
            system['NodeName'] = ''
        Edition = self.snmp_walk('.1.3.6.1.4.1.35047.2.2.40') #老版本不支持
        if Edition:
            system['Edition'] = Edition[0]
        else:
            system['Edition'] = ''
        system['SerialNum'] = self.snmp_walk('.1.3.6.1.4.1.35047.2.2.14.1.3.1')[0] #不确定
        system['ClusterStatus'] = self.snmp_walk('.1.3.6.1.4.1.35047.2.2.18.0')[0]
        return system

    def get_interface(self):
        interface_list = []
        InterfaceName_list = self.snmp_walk('.1.3.6.1.4.1.35047.2.2.7.1.2', return_dict=True)
        InterfaceSpeed_list = self.snmp_walk('.1.3.6.1.4.1.35047.2.2.7.1.3', return_dict=True)
        Interface_num = list(InterfaceName_list.keys())
        for i in Interface_num:
            interface_dict = {}
            interface_dict['InterfaceName'] = InterfaceName_list[i]
            interface_dict['InterfaceSpeed'] = InterfaceSpeed_list
            interface_list.append(interface_dict)
        return interface_list

    # 老版本不支持
    def get_cluster(self):
        cluster_info = {}
        cluster_info['ClusterName'] = self.snmp_walk('.1.3.6.1.4.1.35047.2.2.48')[0]
        cluster_info['ClusterMgmtIp'] = self.snmp_walk('.1.3.6.1.4.1.35047.2.2.49')[0]

        ClusterMbrName_list = self.snmp_walk('.1.3.6.1.4.1.3375.2.1.10.2.2.1.1', return_dict=True)
        ClusterMbrState_list = self.snmp_walk('.1.3.6.1.4.1.3375.2.1.10.2.2.1.8', return_dict=True)
        ClusterMbrStateReason_list = self.snmp_walk('.1.3.6.1.4.1.3375.2.1.10.2.2.1.2', return_dict=True)
        ClusterMbrMgmtIp_list = self.snmp_walk('.1.3.6.1.4.1.3375.2.1.10.2.2.1.2', return_dict=True)

        ClusterMbr_num = list(ClusterMbrName_list.keys())
        cluster_info['ClusterMember'] = []
        for i in ClusterMbr_num:
            member_dict = {}
            member_dict['ClusterMbrName'] = ClusterMbrName_list[i]
            member_dict['ClusterMbrState'] = ClusterMbrState_list[i]
            member_dict['ClusterMbrStateReason'] = ClusterMbrStateReason_list[i]
            member_dict['ClusterMbrMgmtIp'] = ClusterMbrMgmtIp_list[i]
            cluster_info['ClusterMember'].append(member_dict)
        return cluster_list

    def get_virtualserver(self):
        Virtualserver_list = []
        virtualserver_name_list = self.snmp_walk('.1.3.6.1.4.1.35047.2.2.11.1.2', return_dict=True)
        virtualserver_status_list = self.snmp_walk('.1.3.6.1.4.1.35047.2.2.11.1.3', return_dict=True)
        virtualserver_bitin_list = self.snmp_walk('.1.3.6.1.4.1.35047.2.2.11.1.4', return_dict=True)
        virtualserver_bitout_list = self.snmp_walk('.1.3.6.1.4.1.35047.2.2.11.1.5', return_dict=True)
        virtualserver_connnew_list = self.snmp_walk('.1.3.6.1.4.1.35047.2.2.11.1.8', return_dict=True)
        virtualserver_connmax_list = self.snmp_walk('.1.3.6.1.4.1.35047.2.2.11.1.10', return_dict=True)
        virtualserver_conntotal_list = self.snmp_walk('.1.3.6.1.4.1.35047.2.2.11.1.11', return_dict=True)
        virtualserver_ip_list = self.snmp_walk('.1.3.6.1.4.1.35047.2.2.11.1.16', return_dict=True) #老版本不支持
        virtualserver_healthstatus_list = self.snmp_walk('.1.3.6.1.4.1.35047.2.2.11.1.17', return_dict=True) #老版本不支持
        virtualserver_healthnodecnt_list = self.snmp_walk('.1.3.6.1.4.1.35047.2.2.11.1.18', return_dict=True) #老版本不支持

        Virtualserver_num = list(virtualserver_name_list.keys())
        for i in Virtualserver_num:
            Virtualserver_dict = {}
            Virtualserver_dict['virtualserver_name'] = virtualserver_name_list[i]
            Virtualserver_dict['virtualserver_status'] = virtualserver_status_list[i]
            Virtualserver_dict['virtualserver_bitin'] =virtualserver_bitin_list[i]
            Virtualserver_dict['virtualserver_bitout_list'] = virtualserver_bitout_list[i]
            Virtualserver_dict['virtualserver_connnew'] = virtualserver_connnew_list[i]
            Virtualserver_dict['virtualserver_connmax'] = virtualserver_connmax_list[i]
            Virtualserver_dict['virtualserver_conntotal'] = virtualserver_conntotal_list[i]
            Virtualserver_dict['virtualserver_ip'] = virtualserver_ip_list.get(i,'')
            Virtualserver_dict['virtualserver_healthstatus'] = virtualserver_healthstatus_list.get(i,'')
            Virtualserver_dict['virtualserver_healthnodecnt'] = virtualserver_healthnodecnt_list.get(i, '')
            Virtualserver_list.append(Virtualserver_dict)
        return Virtualserver_list

    def get_pool(self):
        Pool_list = []
        pool_name_list = self.snmp_walk('.1.3.6.1.4.1.35047.2.2.12.1.2', return_dict=True)
        pool_status_list = self.snmp_walk('.1.3.6.1.4.1.35047.2.2.12.1.4', return_dict=True)
        pool_bitin_list = self.snmp_walk('.1.3.6.1.4.1.35047.2.2.12.1.5', return_dict=True)
        pool_bitout_list = self.snmp_walk('.1.3.6.1.4.1.35047.2.2.12.1.6', return_dict=True)
        pool_connnew_list = self.snmp_walk('.1.3.6.1.4.1.35047.2.2.12.1.9', return_dict=True)
        pool_connmax_list = self.snmp_walk('.1.3.6.1.4.1.35047.2.2.12.1.11', return_dict=True)
        pool_conntotal_list = self.snmp_walk('.1.3.6.1.4.1.35047.2.2.12.1.12', return_dict=True)

        Pool_num = list(Pool_name_list.keys())
        for i in Pool_num:
            Pool_dict = {}
            Pool_dict['pool_name'] = pool_name_list[i]
            Pool_dict['pool_status'] = pool_status_list[i]
            Pool_dict['pool_bitin'] =pool_bitin_list[i]
            Pool_dict['pool_bitout'] = pool_bitout_list[i]
            Pool_dict['pool_connnew'] = pool_connnew_list[i]
            Pool_dict['pool_connmax'] = pool_connmax_list[i]
            Pool_dict['pool_conntotal'] = pool_conntotal_list[i]
            Pool_list.append(Pool_dict)
        return Pool_list

    def get_node(self):
        Node_list = []
        node_name_list = self.snmp_walk('.1.3.6.1.4.1.35047.2.2.13.1.2', return_dict=True)
        node_configstatus_list = self.snmp_walk('.1.3.6.1.4.1.35047.2.2.13.1.3', return_dict=True)
        node_healthstatus_list = self.snmp_walk('.1.3.6.1.4.1.35047.2.2.13.1.4', return_dict=True)
        node_bitin_list = self.snmp_walk('.1.3.6.1.4.1.35047.2.2.13.1.5', return_dict=True)
        node_bitout_list = self.snmp_walk('.1.3.6.1.4.1.35047.2.2.13.1.6', return_dict=True)
        node_connnew_list = self.snmp_walk('.1.3.6.1.4.1.35047.2.2.13.1.9', return_dict=True)
        node_connmax_list = self.snmp_walk('.1.3.6.1.4.1.35047.2.2.13.1.11', return_dict=True)
        node_conntotal_list = self.snmp_walk('.1.3.6.1.4.1.35047.2.2.13.1.12', return_dict=True)

        Pool_num = list(Pool_name_list.keys())
        for i in Pool_num:
            Node_dict = {}
            Node_dict['node_name'] = node_name_list[i]
            Node_dict['node_configstatus'] = node_configstatus_list[i]
            Node_dict['node_healthstatus'] =node_healthstatus_list[i]
            Node_dict['node_bitin'] = node_bitin_list[i]
            Node_dict['node_bitout'] = node_bitout_list[i]
            Node_dict['node_connnew'] = node_connnew_list[i]
            Node_dict['node_connmax'] = node_connmax_list[i]
            Node_dict['node_conntotal'] = node_conntotal_list[i]
            Node_list.append(Node_dict)
        return Node_list

    def format_out(self):
        try:
            data = {}
            data['DiskInformation'] = self.get_disk()
            data['MemoryInformation'] = self.get_memory()
            data['FanInformation'] = self.get_fan()
            data['PowerInformation'] = self.get_power()
            data['CpuInformation'] = self.get_cpu()
            data['SystemInformation'] = self.get_system()
            data['Interface'] = self.get_interface()
            data['Cluster'] = self.get_cluster()
            data['VirtualServer'] = self.get_virtualserver()
            data['Pool'] = self.get_pool()
            data['Node'] = self.get_node()
        except Exception as e:
            raise BusinessException(str(e))
        else:
            return data
