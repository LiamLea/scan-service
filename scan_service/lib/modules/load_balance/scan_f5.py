try:
    from easysnmp import Session
except Exception:
    pass
import hashlib
import datetime
import time
from scan_service.lib.framework import BusinessException

virtualservertype = {'0': 'poolbased', '1': 'ipforward', '2': 'l2forward',
                     '3': 'reject', '4': 'fastl4', '5': 'fasthttp', '6': 'stateless',
                     '7': 'dhcpRelay', '8': 'internal'}
poolmember_monitor_state = {'0': 'unchecked', '1': 'checking', '2': 'inband',
                            '3': 'forceup', '4': 'up', '19': 'down', '20': 'forceDown',
                            '22': 'iruleDown', '23': 'inbandDown', '24': 'downManualResume', '25': 'disable'}
interface_status = {'0': 'up', '1': 'down',  '2': 'disabled', '3': 'uninitialized', '4': 'loopback', '5': 'unpopulated'}
pool_lb_mode = {'0': 'roundRobin', '1': 'ratioMember', '2': 'leastConnMember', '3': 'observedMember',
                '4': 'predictiveMember',
                '5': 'ratioNodeAddress', '6': 'leastConnNodeAddress', '7': 'fastestNodeAddress',
                '8': 'observedNodeAddress',
                '9': 'predictiveNodeAddress', '10': 'dynamicRatio', '11': 'fastestAppResponse', '12': 'leastSessions',
                '13': 'dynamicRatioMember', '14': 'l3Addr', '15': 'weightedLeastConnMember',
                '16': 'weightedLeastConnNodeAddr',
                '17': 'ratioSession'}
protocol_type = {'6': 'TCP', '17': 'UDP', '132': 'SCTP', '50': 'IPsec ESP', '51': 'IPsec AH'}
#snat_type = {'0': 'none', '1': 'snat', '2': 'lsn', '3': 'automap'}
virtualserver_enable = {'0': 'none', '1': 'enabled', '2': 'disabled', '3': 'disabledbyparent'}
virtualserver_avail = {'0': 'error', '1': 'available', '2': 'not currently available', '3': 'not available', '4': 'unknown', '5': 'unlicensed'}
profile_type = {'0': 'auth', '1': 'http', '2': 'serverssl', '3': 'clientssl', '4': 'fastl4',
                '5': 'tcp', '6': 'udp', '7': 'ftp', '8': 'persist', '9': 'connpool',
                '10': 'stream', '11': 'xml', '12': 'fasthttp', '13': 'iiop', '14': 'rtsp',
                '15': 'user', '16': 'httpclass', '17': 'dns', '18': 'sctp', '19': 'instance',
                '20': 'sipp', '21': 'dos', '62': 'pptp'}

def convertip(n):
    a = n.split(" ")
    lst = []
    for i in a:
        if i:
            lst.append(str(int(i, 16)))
    return ".".join(lst)


def convertmac(n):
    a = n.split(" ")
    lst = []
    for i in a:
        if i:
            lst.append(i)
    return ":".join(lst)


def days_hours_minutes(seconds):
    td = datetime.timedelta(seconds=int(seconds))
    result = "%s days %s hours %s minutes" % (td.days, td.seconds // 3600, (td.seconds // 60) % 60)
    return result

class F5LoadBalancerScan():
    def __init__(self, init_info):
        self.credential_dict  = init_info["credential"]

    def get_disk(self, session, session2, model):
        disk_num = int(session.get('.1.3.6.1.4.1.3375.2.1.7.3.1.0').value)
        disk_list = []

        DiskPartition_list = session.walk('.1.3.6.1.4.1.3375.2.1.7.3.2.1.1')
        TotalBlocks_list = session.walk('.1.3.6.1.4.1.3375.2.1.7.3.2.1.3')
        FreeBlocks_list = session.walk('.1.3.6.1.4.1.3375.2.1.7.3.2.1.4')
        BlockSize_list = session.walk('.1.3.6.1.4.1.3375.2.1.7.3.2.1.2')
        for i in range(0, disk_num):
            disk_dict = {}
            disk_dict['DiskPartition'] = DiskPartition_list[i].value
            disk_dict['TotalBlock'] = int(TotalBlocks_list[i].value)
            disk_dict['FreeBlock'] = int(FreeBlocks_list[i].value)
            disk_dict['BlockSize'] = int(BlockSize_list[i].value)
            disk_list.append(disk_dict)
        return disk_list

    def get_memory(self, session, session2, model):
        memory = {}
        if model == 'virtual':
            TMMMemoryTotal = int(session.get('.1.3.6.1.4.1.3375.2.1.1.2.1.143.0').value)
            TMMMemoryUsed = int(session.get('.1.3.6.1.4.1.3375.2.1.1.2.1.144.0').value)
            NonTMMMemoryTotal = int(session.get('.1.3.6.1.4.1.3375.2.1.1.2.20.48.0').value)
            NonTMMMemoryUsed = int(session.get('.1.3.6.1.4.1.3375.2.1.1.2.20.49.0').value)
        elif model == '1600_3600_6900':
            TMMMemoryTotal = int(session.get('.1.3.6.1.4.1.3375.2.1.1.2.1.143.0').value)
            TMMMemoryUsed = int(session.get('.1.3.6.1.4.1.3375.2.1.1.2.1.144.0').value)
            NonTMMMemoryTotal = int(session.get('.1.3.6.1.4.1.3375.2.1.1.2.20.42.0').value)
            NonTMMMemoryUsed = int(session.get('.1.3.6.1.4.1.3375.2.1.1.2.20.43.0').value)
        elif model == '3400':
            TMMMemoryTotal = int(session.get('.1.3.6.1.4.1.3375.2.1.1.2.1.44.0').value)
            TMMMemoryUsed = int(session.get('.1.3.6.1.4.1.3375.2.1.1.2.1.45.0').value)
            NonTMMMemoryTotal = int(session.get('.1.3.6.1.4.1.3375.2.1.7.1.1.0').value)
            NonTMMMemoryUsed = int(session.get('.1.3.6.1.4.1.3375.2.1.7.1.2.0').value)        
        MemoryTotal = TMMMemoryTotal + NonTMMMemoryTotal
        MemoryUsed = TMMMemoryUsed + NonTMMMemoryUsed
        if model == '3400':
            memory['MemoryTotal'] = "%.2f" % (MemoryTotal / 1024 / 1024 / 1024) + 'GB'
            memory['MemoryUsed'] = "%.2f" % (MemoryUsed / 1024 / 1024 / 1024) + 'GB'
            memory['TMMMemoryTotal'] = "%.2f" % (TMMMemoryTotal / 1024 / 1024 / 1024) + 'GB'
            memory['TMMMemoryUsed'] = "%.2f" % (TMMMemoryUsed / 1024 / 1024 / 1024) + 'GB'
            memory['NonTMMMemoryTotal'] = "%.2f" % (NonTMMMemoryTotal / 1024 / 1024 / 1024) + 'GB'
            memory['NonTMMMemoryUsed'] = "%.2f" % (NonTMMMemoryUsed / 1024 / 1024 / 1024) + 'GB'
        else:
            memory['MemoryTotal'] = "%.2f" % (MemoryTotal / 1024 / 1024) + 'GB'
            memory['MemoryUsed'] = "%.2f" % (MemoryUsed / 1024 / 1024) + 'GB'
            memory['TMMMemoryTotal'] = "%.2f" % (TMMMemoryTotal / 1024 / 1024) + 'GB'
            memory['TMMMemoryUsed'] = "%.2f" % (TMMMemoryUsed / 1024 / 1024) + 'GB'
            memory['NonTMMMemoryTotal'] = "%.2f" % (NonTMMMemoryTotal / 1024 / 1024) + 'GB'
            memory['NonTMMMemoryUsed'] = "%.2f" % (NonTMMMemoryUsed / 1024 / 1024) + 'GB'
        memory['MemoryUsage'] = "%.2f" % (MemoryUsed / MemoryTotal * 100) + '%'
        memory['TMMMemoryusage'] = "%.2f" % (TMMMemoryUsed / TMMMemoryTotal * 100) + '%'
        memory['NoneTMMMemoryusage'] = "%.2f" % (NonTMMMemoryUsed / NonTMMMemoryTotal * 100) + '%'
        return memory

    def get_fan(self, session, session2, model):
        fan_num = int(session.get('.1.3.6.1.4.1.3375.2.1.3.2.1.1.0').value)
        fan_list = []
        FanIndex_list = session.walk('.1.3.6.1.4.1.3375.2.1.3.2.1.2.1.1')
        FanStatus_list = session.walk('.1.3.6.1.4.1.3375.2.1.3.2.1.2.1.2')
        FanSpeed_list = session.walk('.1.3.6.1.4.1.3375.2.1.3.2.1.2.1.3')

        for i in range(0, fan_num):
            fan_dict = {}
            fan_dict['FanIndex'] = FanIndex_list[i].value
            fan_dict['FanStatus'] = FanStatus_list[i].value
            fan_dict['FanSpeed'] = FanSpeed_list[i].value
            fan_list.append(fan_dict)
        return fan_list

    def get_power(self, session, session2, model):
        power_num = int(session.get('.1.3.6.1.4.1.3375.2.1.3.2.2.1.0').value)
        power_list = []
        PowerIndex_list = session.walk('.1.3.6.1.4.1.3375.2.1.3.2.2.2.1.1')
        PowerStatus_list = session.walk('.1.3.6.1.4.1.3375.2.1.3.2.2.2.1.2')

        for i in range(0, power_num):
            power_dict = {}
            power_dict['PowerIndex'] = PowerIndex_list[i].value
            power_dict['PowerStatus'] = PowerStatus_list[i].value
            power_list.append(power_dict)
        return power_list

    def get_cpu(self, session, session2, model):
        cpu = {}
        cpu['CpuCount'] = int(session.get('.1.3.6.1.4.1.3375.2.1.1.2.1.38.0').value)
        if model == '3400':
            cpu_user_init = session.get('.1.3.6.1.4.1.3375.2.1.7.2.2.1.3').value
            cpu_nice_init = session.get('.1.3.6.1.4.1.3375.2.1.7.2.2.1.4').value
            cpu_system_init = session.get('.1.3.6.1.4.1.3375.2.1.7.2.2.1.5').value
            cpu_idle_init = session.get('.1.3.6.1.4.1.3375.2.1.7.2.2.1.6').value
            cpu_irq_init = session.get('.1.3.6.1.4.1.3375.2.1.7.2.2.1.7').value
            cup_softirq_init = session.get('.1.3.6.1.4.1.3375.2.1.7.2.2.1.8').value
            cpu_iowait_init = session.get('.1.3.6.1.4.1.3375.2.1.7.2.2.1.9').value
            time.sleep(10)
            cpu_user_ter = session.get('.1.3.6.1.4.1.3375.2.1.7.2.2.1.3').value
            cpu_nice_ter = session.get('.1.3.6.1.4.1.3375.2.1.7.2.2.1.4').value
            cpu_system_ter = session.get('.1.3.6.1.4.1.3375.2.1.7.2.2.1.5').value
            cpu_idle_ter = session.get('.1.3.6.1.4.1.3375.2.1.7.2.2.1.6').value
            cpu_irq_ter = session.get('.1.3.6.1.4.1.3375.2.1.7.2.2.1.7').value
            cup_softirq_ter = session.get('.1.3.6.1.4.1.3375.2.1.7.2.2.1.8').value
            cpu_iowait_ter = session.get('.1.3.6.1.4.1.3375.2.1.7.2.2.1.9').value
            delta_cpu_user_ter = int(cpu_user_ter) - int(cpu_user_init)
            delta_cpu_nice_ter = int(cpu_nice_ter) - int(cpu_nice_init)
            delta_cpu_system_ter = int(cpu_system_ter) - int(cpu_system_init)
            delta_cpu_idle_ter = int(cpu_idle_ter) - int(cpu_idle_init)
            delta_cpu_irq_ter = int(cpu_irq_ter) - int(cpu_irq_init)
            delta_cpu_softirq_ter = int(cpu_softirq_ter) - int(cpu_softirq_init)
            delta_cpu_iowait_ter = int(cpu_iowait_ter) - int(cpu_iowait_init)
            cpu['CpuUsage10s'] = "%.2f" % ((delta_cpu_user_ter + delta_cpu_nice_ter + delta_cpu_system_ter)/(delta_cpu_user_ter + delta_cpu_nice_ter + delta_cpu_system_ter + delta_cpu_idle_ter + delta_cpu_irq_ter + delta_cpu_softirq_ter + delta_cpu_iowait_ter)*100) + '%'
            cpu['CpuUsage1m'] = ''
            cpu['CpuUsage5m'] = ''
        else:
            cpu['CpuUsage10s'] = session.get('.1.3.6.1.4.1.3375.2.1.1.2.20.13.0').value + '%'
            cpu['CpuUsage1m'] = session.get('.1.3.6.1.4.1.3375.2.1.1.2.20.29.0').value + '%'
            cpu['CpuUsage5m'] = session.get('.1.3.6.1.4.1.3375.2.1.1.2.20.37.0').value + '%'

        total_init = session.get('.1.3.6.1.4.1.3375.2.1.1.2.1.41.0').value
        idle_init = session.get('.1.3.6.1.4.1.3375.2.1.1.2.1.42.0').value
        slp_init = session.get('.1.3.6.1.4.1.3375.2.1.1.2.1.43.0').value

        time.sleep(2)
        total_ter = session.get('.1.3.6.1.4.1.3375.2.1.1.2.1.41.0').value
        idle_ter = session.get('.1.3.6.1.4.1.3375.2.1.1.2.1.42.0').value
        slp_ter = session.get('.1.3.6.1.4.1.3375.2.1.1.2.1.43.0').value

        delta_tm_total = int(total_ter) - int(total_init)
        delta_tm_idle = int(idle_ter) - int(idle_init)
        delta_sleep = int(slp_ter) - int(slp_init)
        cpu_consum = delta_tm_total - delta_tm_idle - delta_sleep
        cpu['TMMCpuusage'] = "%.2f" % (cpu_consum / delta_tm_total * 100) + '%'

        return cpu

    def get_system(self, session, session2, model):
        system = {}
        system['Name'] = session.get('.1.3.6.1.4.1.3375.2.1.6.1.0').value
        system['NodeName'] = session.get('.1.3.6.1.4.1.3375.2.1.6.2.0').value
        system['Release'] = session.get('.1.3.6.1.4.1.3375.2.1.6.3.0').value
        system['Version'] = session.get('.1.3.6.1.4.1.3375.2.1.6.4.0').value
        system['Machine'] = session.get('.1.3.6.1.4.1.3375.2.1.6.5.0').value
        if model == 'virtual':
            uptime = session.get('.1.3.6.1.4.1.3375.2.1.6.7.0').value
        else:
            uptime = (session.get('.1.3.6.1.4.1.3375.2.1.6.6.0').value)*100
        #system['Uptime'] = days_hours_minutes(uptime)
        system['Uptime'] = (datetime.datetime.now() - datetime.timedelta(seconds = int(float(uptime)))).strftime('%Y-%m-%d %H:%M:%S') if uptime else ""
        sysAdminIpNumber = int(session.get('.1.3.6.1.4.1.3375.2.1.2.1.1.1.0').value)
        system['AdminIp'] = []
        if model == 'virtual':
            system['Syncstatus'] = session.get('.1.3.6.1.4.1.3375.2.1.14.1.2.0').value
        else:
            system['Syncstatus'] = ''
        sysAdminIpAddr_list = session2.walk('.1.3.6.1.4.1.3375.2.1.2.1.1.2.1.2')
        sysAdminIpNetmask_list = session2.walk('.1.3.6.1.4.1.3375.2.1.2.1.1.2.1.4')
        for i in range(0, sysAdminIpNumber):
            ip_dict = {}
            ip_dict['Ip'] = convertip(sysAdminIpAddr_list[i].value.strip("\""))
            ip_dict['Netmask'] = convertip(sysAdminIpNetmask_list[i].value.strip("\""))
            system['AdminIp'].append(ip_dict)
        return system

    def get_product(self, session, session2, model):
        product = {}
        product['Name'] = session.get('.1.3.6.1.4.1.3375.2.1.4.1.0').value
        product['Version'] = session.get('.1.3.6.1.4.1.3375.2.1.4.2.0').value
        product['Build'] = session.get('.1.3.6.1.4.1.3375.2.1.4.3.0').value
        product['Edition'] = session.get('.1.3.6.1.4.1.3375.2.1.4.4.0').value
        product['Date'] = session.get('.1.3.6.1.4.1.3375.2.1.4.5.0').value
        if model == '3400':
            product['SerialNum'] = ''
            product['Model'] = session.get('.1.3.6.1.4.1.3375.2.1.3.3.2.0').value
        else:
            product['SerialNum'] = session.get('.1.3.6.1.4.1.3375.2.1.3.3.3.0').value
            product['Model'] = session.get('.1.3.6.1.4.1.3375.2.1.3.5.2.0').value
        product['Manufacturer'] = 'F5'
        product['Edition'] =  product['Name'] + ' ' + product['Version'] + ' ' + 'bulid' + product['Build'] + ' ' + product['Edition']
        return product

    def get_system_traffic_statistics(self, session, session2, model):
        system_traffic_statistics = {}
        system_traffic_statistics['ClientBytesIn'] = session.get('.1.3.6.1.4.1.3375.2.1.1.2.1.3.0').value
        system_traffic_statistics['ClientBytesOut'] = session.get('.1.3.6.1.4.1.3375.2.1.1.2.1.5.0').value
        system_traffic_statistics['ClientMaxConns'] = session.get('.1.3.6.1.4.1.3375.2.1.1.2.1.6.0').value
        system_traffic_statistics['ClientTotConns'] = session.get('.1.3.6.1.4.1.3375.2.1.1.2.1.7.0').value
        system_traffic_statistics['ClientCurConns'] = session.get('.1.3.6.1.4.1.3375.2.1.1.2.1.8.0').value
        system_traffic_statistics['ServerBytesIn'] = session.get('.1.3.6.1.4.1.3375.2.1.1.2.1.10.0').value
        system_traffic_statistics['ServerBytesOut'] = session.get('.1.3.6.1.4.1.3375.2.1.1.2.1.12.0').value
        system_traffic_statistics['ServerMaxConns'] = session.get('.1.3.6.1.4.1.3375.2.1.1.2.1.13.0').value
        system_traffic_statistics['ServerTotConns'] = session.get('.1.3.6.1.4.1.3375.2.1.1.2.1.14.0').value
        system_traffic_statistics['ServerCurConns'] = session.get('.1.3.6.1.4.1.3375.2.1.1.2.1.15.0').value
        return system_traffic_statistics

    def get_vlan(self, session, session2, model):
        vlan_num = int(session.get('.1.3.6.1.4.1.3375.2.1.2.13.1.1.0').value)
        vlan_list = []
        VlanVname_list = session.walk('.1.3.6.1.4.1.3375.2.1.2.13.1.2.1.1')
        VlanId_list = session.walk('.1.3.6.1.4.1.3375.2.1.2.13.1.2.1.2')

        for i in range(0, vlan_num):
            vlan_dict = {}
            vlan_dict['VlanName'] = VlanVname_list[i].value
            vlan_dict['VlanId'] = VlanId_list[i].value
            vlan_list.append(vlan_dict)
        return vlan_list

    def get_interface(self, session, session2, model):
        interface_num = int(session.get('.1.3.6.1.4.1.3375.2.1.2.4.1.1.0').value)
        interface_list = []
        InterfaceName_list = session.walk('.1.3.6.1.4.1.3375.2.1.2.4.1.2.1.1')
        InterfaceMaxSpeed_list = session.walk('.1.3.6.1.4.1.3375.2.1.2.4.1.2.1.2')
        InterfaceMacAddr_list = session2.walk('.1.3.6.1.4.1.3375.2.1.2.4.1.2.1.6')
        InterfaceStatus_list = session.walk('.1.3.6.1.4.1.3375.2.1.2.4.1.2.1.17')

        for i in range(0, interface_num):
            interface_dict = {}
            interface_dict['InterfaceName'] = InterfaceName_list[i].value
            interface_dict['InterfaceMaxSpeed'] = InterfaceMaxSpeed_list[i].value
            interface_dict['InterfaceMacAddr'] = convertmac(InterfaceMacAddr_list[i].value.strip("\""))
            interface_dict['InterfaceStatus'] = interface_status[InterfaceStatus_list[i].value]
            interface_list.append(interface_dict)
        return interface_list

    def get_cluster(self, session, session2, model):
        cluster_num = int(session.get('.1.3.6.1.4.1.3375.2.1.10.1.1.0').value)
        cluster_list = []
        if cluster_num != 0:
            ClusterName_list = session.walk('.1.3.6.1.4.1.3375.2.1.10.1.2.1.1')
            ClusterFloatMgmtIp_list = session.walk('.1.3.6.1.4.1.3375.2.1.10.1.2.1.4')
            ClusterFloatMgmtNetmask_list = session.walk('.1.3.6.1.4.1.3375.2.1.10.1.2.1.6')
            ClusterAvailabilityState_list = session.walk('.1.3.6.1.4.1.3375.2.1.10.1.2.1.10')
            ClusterEnabledStat_list = session.walk('.1.3.6.1.4.1.3375.2.1.10.1.2.1.11')
            ClusterStatusReason_list = session.walk('.1.3.6.1.4.1.3375.2.1.10.1.2.1.13')

        for i in range(0, cluster_num):
            cluster_dict = {}
            cluster_dict['ClusterName'] = ClusterName_list[i].value
            cluster_dict['ClusterFloatMgmtIp'] = ClusterFloatMgmtIp_list[i].value
            cluster_dict['ClusterFloatMgmtNetmask'] = ClusterFloatMgmtNetmask_list[i].value
            cluster_dict['ClusterAvailabilityState'] = ClusterAvailabilityState_list[i].value
            cluster_dict['ClusterEnabledStat'] = ClusterEnabledStat_list[i].value
            cluster_dict['ClusterStatusReason'] = ClusterStatusReason_list[i].value
            cluster_dict['ClusterMember'] = []
            cluster_list.append(cluster_dict)

        cluster_member_num = int(session.get('.1.3.6.1.4.1.3375.2.1.10.2.1.0').value)
        if cluster_member_num != 0:
            ClusterMbrCluster_list = session.walk('.1.3.6.1.4.1.3375.2.1.10.2.2.1.1')
            ClusterMbrState_list = session.walk('.1.3.6.1.4.1.3375.2.1.10.2.2.1.8')
            ClusterMbrSlotId_list = session.walk('.1.3.6.1.4.1.3375.2.1.10.2.2.1.2')
            ClusterMbrMgmtAddr_list = session2.walk('.1.3.6.1.4.1.3375.2.1.10.2.2.1.12')

        for i in range(0, cluster_member_num):
            cluster_name = ClusterMbrCluster_list[i].value
            member_dict = {}
            for cluster_info in cluster_list:
                if cluster_info['ClusterName'] == cluster_name:
                    member_dict['ClusterMbrSlotId'] = ClusterMbrSlotId_list[i].value
                    member_dict['ClusterState'] = ClusterMbrState_list[i].value
                    member_dict['ClusterMbrMgmtAddr'] = convertip(ClusterMbrMgmtAddr_list[i].value.strip("\""))
                    cluster_info['ClusterMember'].append(member_dict)
                    break
        return cluster_list

    def get_virtualserver_rule(self, session, session2):
        virtualserver_rule_num = int(session.get('.1.3.6.1.4.1.3375.2.2.10.8.1.0').value)
        virtualserver_rule_list = []
        VirtualServerName_list = session.walk('.1.3.6.1.4.1.3375.2.2.10.8.2.1.1')
        VirtualServRuleName_list = session.walk('.1.3.6.1.4.1.3375.2.2.10.8.2.1.2')
        VirtualServRulePriority_list = session.walk('.1.3.6.1.4.1.3375.2.2.10.8.2.1.3')
        for i in range(0, virtualserver_rule_num):
            virtualserver_rule_dict = {}
            virtualserver_rule_dict['VirtualServerName'] = VirtualServerName_list[i].value
            virtualserver_rule_dict['VirtualServRuleName'] = VirtualServRuleName_list[i].value
            virtualserver_rule_dict['VirtualServRulePriority'] = VirtualServRulePriority_list[i].value
            virtualserver_rule_list.append(virtualserver_rule_dict)
        return virtualserver_rule_list

    def get_virtualserver_status(self, session, session2):
        virtualserver_status_num = int(session.get('.1.3.6.1.4.1.3375.2.2.10.13.1.0').value)
        virtualserver_status_list = []
        VirtualServerName_list = session.walk('.1.3.6.1.4.1.3375.2.2.10.13.2.1.1')
        VirtualServAvailState_list = session.walk('.1.3.6.1.4.1.3375.2.2.10.13.2.1.2')
        VirtualServEnableState_list = session.walk('.1.3.6.1.4.1.3375.2.2.10.13.2.1.3')
        for i in range(0, virtualserver_status_num):
            virtualserver_status_dict = {}
            virtualserver_status_dict['VirtualServerName'] = VirtualServerName_list[i].value
            virtualserver_status_dict['VirtualServAvailState'] = virtualserver_avail[VirtualServAvailState_list[i].value]
            virtualserver_status_dict['VirtualServEnableState'] = virtualserver_enable[VirtualServEnableState_list[i].value]
            virtualserver_status_list.append(virtualserver_status_dict)
        return virtualserver_status_list

    def get_virtualserver_profile(self, session, session2):
        virtualserver_profile_num = int(session.get('.1.3.6.1.4.1.3375.2.2.10.5.1.0').value)
        virtualserver_profile_list = []
        VirtualServerName_list = session.walk('.1.3.6.1.4.1.3375.2.2.10.5.2.1.1')
        VirtualServProfileName_list = session.walk('.1.3.6.1.4.1.3375.2.2.10.5.2.1.2')
        VirtualServProfileType_list = session.walk('.1.3.6.1.4.1.3375.2.2.10.5.2.1.3')
        for i in range(0, virtualserver_profile_num):
            virtualserver_profile_dict = {}
            virtualserver_profile_dict['VirtualServerName'] = VirtualServerName_list[i].value
            virtualserver_profile_dict['VirtualServProfileName'] = VirtualServProfileName_list[i].value
            virtualserver_profile_dict['VirtualServProfileType'] = profile_type[VirtualServProfileType_list[i].value]
            virtualserver_profile_list.append(virtualserver_profile_dict)
        return virtualserver_profile_list

    def get_virtualserver(self, session, session2, model):
        if model == 'virtual':
            snat_type = {'0': 'none', '1': 'snat', '2': 'lsn', '3': 'automap'}
        else:
            snat_type = {'0': 'none', '1': 'transaddr', '2': 'snatpool', '3': 'automap'}
        Virtualserver_num = int(session.get('.1.3.6.1.4.1.3375.2.2.10.1.1.0').value)
        virtualserver_rule_list = self.get_virtualserver_rule(session, session2)
        virtualserver_profile_list = self.get_virtualserver_profile(session, session2)
        virtualserver_status_list = self.get_virtualserver_status(session, session2)
        Virtualserver_list = []
        if Virtualserver_num != 0:
            VirtualServName_list = session.walk('.1.3.6.1.4.1.3375.2.2.10.1.2.1.1')
            VirtualServAddr_list = session2.walk('.1.3.6.1.4.1.3375.2.2.10.1.2.1.3')
            VirtualServWildmask_list = session2.walk('.1.3.6.1.4.1.3375.2.2.10.1.2.1.5')
            VirtualServPort_list = session.walk('.1.3.6.1.4.1.3375.2.2.10.1.2.1.6')
            VirtualServIpProto_list = session.walk('.1.3.6.1.4.1.3375.2.2.10.1.2.1.7')
            VirtualServType_list = session.walk('.1.3.6.1.4.1.3375.2.2.10.1.2.1.15')
            VirtualServConnLimit_list = session.walk('.1.3.6.1.4.1.3375.2.2.10.1.2.1.10')
            VirtualServDefaultPool_list = session.walk('.1.3.6.1.4.1.3375.2.2.10.1.2.1.19')
            if model == 'virtual':
                VirtualServSnatType_list = session.walk('.1.3.6.1.4.1.3375.2.2.10.1.2.1.30')
            else:
                VirtualServSnatType_list = session.walk('.1.3.6.1.4.1.3375.2.2.10.1.2.1.16')

        for i in range(0, Virtualserver_num):
            Virtualserver_dict = {}
            Virtualserver_dict['VirtualServName'] = VirtualServName_list[i].value
            Virtualserver_dict['VirtualServAddr'] = convertip(VirtualServAddr_list[i].value.strip("\""))
            Virtualserver_dict['VirtualServWildmask'] = convertip(VirtualServWildmask_list[i].value.strip("\""))
            Virtualserver_dict['VirtualServPort'] = VirtualServPort_list[i].value
            Virtualserver_dict['VirtualServIpProto'] = protocol_type[VirtualServIpProto_list[i].value]
            Virtualserver_dict['VirtualServType'] = virtualservertype[VirtualServType_list[i].value]
            Virtualserver_dict['VirtualServConnLimit'] = VirtualServConnLimit_list[i].value
            Virtualserver_dict['VirtualServDefaultPool'] = VirtualServDefaultPool_list[i].value
            Virtualserver_dict['VirtualServSnatType'] = snat_type[VirtualServSnatType_list[i].value]
            Virtualserver_dict['VirtualServRule'] = []
            Virtualserver_dict['VirtualServProfile'] = []
            for virtualserver_rule in virtualserver_rule_list:
                if virtualserver_rule['VirtualServerName'] == VirtualServName_list[i].value:
                    Virtualserver_dict['VirtualServRule'].append(virtualserver_rule)
            for virtualserver_profile in virtualserver_profile_list:
                if virtualserver_profile['VirtualServerName'] == VirtualServName_list[i].value:
                    Virtualserver_dict['VirtualServProfile'].append(virtualserver_profile)
            for virtualserver_status in virtualserver_status_list:
                if virtualserver_status['VirtualServerName'] == VirtualServName_list[i].value:
                    Virtualserver_dict['VirtualServAvailState'] = virtualserver_status['VirtualServAvailState']
                    Virtualserver_dict['VirtualServEnableState'] = virtualserver_status['VirtualServEnableState']
            Virtualserver_list.append(Virtualserver_dict)
        return Virtualserver_list

    def get_pool_status(self, session, session2):
        pool_status_num = int(session.get('.1.3.6.1.4.1.3375.2.2.5.5.1.0').value)
        pool_status_list = []
        PoolName_list = session.walk('.1.3.6.1.4.1.3375.2.2.5.5.2.1.1')
        PoolAvailState_list = session.walk('.1.3.6.1.4.1.3375.2.2.5.5.2.1.2')
        PoolEnableState_list = session.walk('.1.3.6.1.4.1.3375.2.2.5.5.2.1.3')
        for i in range(0, pool_status_num):
            pool_status_dict = {}
            pool_status_dict['PoolName'] = PoolName_list[i].value
            pool_status_dict['PoolAvailState'] = virtualserver_avail[PoolAvailState_list[i].value]
            pool_status_dict['PoolEnableState'] = virtualserver_enable[PoolEnableState_list[i].value]
            pool_status_list.append(pool_status_dict)
        return pool_status_list

    def get_poolmember_status(self, session, session2):
        poolmember_status_num = int(session.get('.1.3.6.1.4.1.3375.2.2.5.6.1.0').value)
        poolmember_status_list = []
        PoolmemberAddr_list = session2.walk('.1.3.6.1.4.1.3375.2.2.5.6.2.1.3')
        PoolmemberPort_list = session.walk('.1.3.6.1.4.1.3375.2.2.5.6.2.1.4')
        PoolmemberAvailState_list = session.walk('.1.3.6.1.4.1.3375.2.2.5.6.2.1.5')
        PoolmemberEnableState_list = session.walk('.1.3.6.1.4.1.3375.2.2.5.6.2.1.6')
        for i in range(0, poolmember_status_num):
            poolmember_status_dict = {}
            poolmember_status_dict['PoolAddr'] = PoolmemberAddr_list[i].value
            poolmember_status_dict['PoolPort'] = PoolmemberPort_list[i].value
            poolmember_status_dict['PoolmemberAvailState'] = virtualserver_avail[PoolmemberAvailState_list[i].value]
            poolmember_status_dict['PoolmemberEnableState'] = virtualserver_enable[PoolmemberEnableState_list[i].value]
            poolmember_status_list.append(poolmember_status_dict)
        return poolmember_status_list

    def get_pool(self, session, session2, model):
        pool_status_list = self.get_pool_status(session, session2)
        poolmember_status_list = self.get_poolmember_status(session, session2)
        pool_num = int(session.get('.1.3.6.1.4.1.3375.2.2.5.1.1.0').value)
        pool_list = []
        if pool_num != 0:
            PoolName_list = session.walk('.1.3.6.1.4.1.3375.2.2.5.1.2.1.1')
            PoolActiveMemberCnt_list = session.walk('.1.3.6.1.4.1.3375.2.2.5.1.2.1.8')
            PoolMonitorRule_list = session.walk('.1.3.6.1.4.1.3375.2.2.5.1.2.1.17')
            PoolMemberCnt_list = session.walk('.1.3.6.1.4.1.3375.2.2.5.1.2.1.23')
            PoolLbMode_list = session.walk('.1.3.6.1.4.1.3375.2.2.5.1.2.1.2')
            PoolLbMode_list = session.walk('.1.3.6.1.4.1.3375.2.2.5.1.2.1.2')

        for i in range(0, pool_num):
            pool_dict = {}
            pool_dict['PoolName'] = PoolName_list[i].value
            pool_dict['PoolActiveMemberCnt'] = PoolActiveMemberCnt_list[i].value
            pool_dict['PoolMonitorRule'] = PoolMonitorRule_list[i].value
            pool_dict['PoolMemberCnt'] = PoolMemberCnt_list[i].value
            pool_dict['PoolLbMode'] = pool_lb_mode[PoolLbMode_list[i].value]
            for pool_status in pool_status_list:
                if pool_status['PoolName'] == PoolName_list[i].value:
                    pool_dict['PoolAvailState'] = pool_status['PoolAvailState']
                    pool_dict['PoolEnableState'] = pool_status['PoolEnableState']
            pool_dict['PoolMember'] = []
            
            pool_list.append(pool_dict)

            pool_member_num = int(session.get('.1.3.6.1.4.1.3375.2.2.5.3.1.0').value)
            if pool_member_num != 0:
                PoolMemberPoolName_list = session.walk('.1.3.6.1.4.1.3375.2.2.5.3.2.1.1')
                PoolMemberAddr_list = session2.walk('.1.3.6.1.4.1.3375.2.2.5.3.2.1.3')
                PoolMemberPort_list = session.walk('.1.3.6.1.4.1.3375.2.2.5.3.2.1.4')
                PoolMemberMonitorRule_list = session.walk('.1.3.6.1.4.1.3375.2.2.5.3.2.1.14')
                #PoolMemberMonitorState_list = session.walk('.1.3.6.1.4.1.3375.2.2.5.3.2.1.10')

            for i in range(0, pool_member_num):
                member_dict = {}
                pool_name = PoolMemberPoolName_list[i].value
                for pool_info in pool_list:
                    if pool_info['PoolName'] == pool_name:
                        member_dict['PoolMemberPoolName'] = PoolMemberPoolName_list[i].value
                        member_dict['PoolMemberAddr'] = convertip(PoolMemberAddr_list[i].value.strip("\""))
                        member_dict['PoolMemberPort'] = PoolMemberPort_list[i].value
                        if PoolMemberMonitorRule_list[i].value:
                            member_dict['PoolMemberMonitorRule'] = PoolMemberMonitorRule_list[i].value
                        else:
                            member_dict['PoolMemberMonitorRule'] = pool_info['PoolMonitorRule']
                        for poolmember_status in poolmember_status_list:
                            if poolmember_status['PoolAddr'] == PoolMemberAddr_list[i].value and poolmember_status['PoolPort'] == PoolMemberPort_list[i].value:
                                member_dict['PoolMemberAvailState'] = poolmember_status['PoolmemberAvailState']
                                member_dict['PoolMemberEnableState'] = poolmember_status['PoolmemberEnableState']
                        pool_info['PoolMember'].append(member_dict)
                        break
        return pool_list

    def further_data_processing(self, data, scanip):
        data['scan_ip'] = scanip
        data['os_type'] = 'Load_Balance'
        collect_time = time.strftime('%Y.%m.%d %H:%M:%S', time.localtime(time.time()))
        data['collect_time'] = collect_time
        uuid = hashlib.md5(data['ProductInformation']['SerialNum'].encode("utf8")).hexdigest()
        data['uuid'] = uuid
        data['netmask'] = ''
        for ipinfo in data['SystemInformation']['AdminIp']:
            if ipinfo['Ip'] == scanip:
                data['netmask'] = ipinfo['Netmask']
                break
        total_disk_capacity = 0
        for disk in data['DiskInformation']:
            total_disk_capacity += disk['TotalBlock']* disk['BlockSize']
            disk['BlockSize'] = '%.2f' % (disk['BlockSize']/1024) + 'Kb'
        data['SystemInformation']['total_disk_capacity'] = str(total_disk_capacity/(1024**3)) + 'Gb'
        data['SystemInformation']['disk_num'] = len(data['DiskInformation'])
        data['SystemInformation']['interface_num'] = len(data['Interface'])
        return data

    def format_out(self):
        try:
            session = Session(**self.credential_dict)
            session2 = Session(**self.credential_dict, use_sprint_value=True)
            model = 'virtual'
            result = session.get('.1.3.6.1.4.1.3375.2.1.3.5.2.0').value
            if "No Such" in result or "NOSUCH" not in result:
                result = session.get('.1.3.6.1.4.1.3375.2.1.3.3.2.0').value
            if '1600' in result or '3600' in result or '6900' in result:
                model = '1600_3600_6900'
            elif '3400' in result:
                model = '3400'
            data = {}
            data['DiskInformation'] = self.get_disk(session, session2, model)
            data['MemoryInformation'] = self.get_memory(session, session2, model)
            data['FanInformation'] = self.get_fan(session, session2, model)
            data['PowerInformation'] = self.get_power(session, session2, model)
            data['CpuInformation'] = self.get_cpu(session, session2, model)
            data['SystemInformation'] = self.get_system(session, session2, model)
            data['ProductInformation'] = self.get_product(session, session2, model)
            data['Vlan'] = self.get_vlan(session, session2, model)
            data['Interface'] = self.get_interface(session, session2, model)
            data['Cluster'] = self.get_cluster(session, session2, model)
            data['VirtualServer'] = self.get_virtualserver(session, session2, model)
            data['Pool'] = self.get_pool(session, session2, model)
            data['SystemTrafficStatistics'] = self.get_system_traffic_statistics(session, session2, model)
            hostname = self.credential_dict["hostname"]
            further_data = self.further_data_processing(data, hostname)
        except Exception as e:
            raise BusinessException(str(e))
        else:
            return further_data
