import time
import hashlib
from scan_service.lib.utils import string_to_bytes
from scan_service.lib.utils import WMIC

oslanguagename_dict = {"1": "Arabic",
                       "4": "Chinese (Simplified)– China",
                       "9": "English",
                       "1025": "Arabic – Saudi Arabia",
                       "1027": "Catalan",
                       "1028": "Chinese (Traditional) – Taiwan",
                       "1029": "Czech",
                       "1030": "Danish",
                       "1031": "German – Germany",
                       "1032": "Greek",
                       "1033": "English – United States",
                       "1034": "Spanish – Traditional Sort",
                       "1035": "Finnish",
                       "1036": "French – France",
                       "1037": "Hebrew",
                       "1038": "Hungarian",
                       "1039": "Icelandic",
                       "1040": "Italian – Italy",
                       "1041": "Japanese",
                       "1042": "Korean",
                       "1043": "Dutch – Netherlands",
                       "1044": "Norwegian – Bokmal",
                       "1045": "Polish",
                       "1046": "Portuguese – Brazil",
                       "1047": "Rhaeto-Romanic",
                       "1048": "Romanian",
                       "1049": "Russian",
                       "1050": "Croatian",
                       "1051": "Slovak",
                       "1052": "Albanian",
                       "1053": "Swedish",
                       "1054": "Thai",
                       "1055": "Turkish",
                       "1056": "Urdu",
                       "1057": "Indonesian",
                       "1058": "Ukrainian",
                       "1059": "Belarusian",
                       "1060": "Slovenian",
                       "1061": "Estonian",
                       "1062": "Latvian",
                       "1063": "Lithuanian",
                       "1065": "Persian",
                       "1066": "Vietnamese",
                       "1069": "Basque (Basque)",
                       "1070": "Serbian",
                       "1071": "Macedonian (North Macedonia)",
                       "1072": "Sutu",
                       "1073": "Tsonga",
                       "1074": "Tswana",
                       "1076": "Xhosa",
                       "1077": "Zulu",
                       "1078": "Afrikaans",
                       "1080": "Faeroese",
                       "1081": "Hindi",
                       "1082": "Maltese",
                       "1084": "Scottish Gaelic (United Kingdom)",
                       "1085": "Yiddish",
                       "1086": "Malay – Malaysia",
                       "2049": "Arabic",
                       "2052": "Chinese (Simplified) – PRC",
                       "2055": "German – Switzerland",
                       "2057": "English – United Kingdom",
                       "2058": "Spanish – Mexico",
                       "2060": "French – Belgium",
                       "2064": "Italian – Switzerland",
                       "2067": "Dutch – Belgium",
                       "2068": "Norwegian – Nynorsk",
                       "2070": "Portuguese – Portugal",
                       "2072": "Romanian – Moldova",
                       "2073": "Russian – Moldova",
                       "2074": "Serbian – Latin",
                       "2077": "Swedish – Finland",
                       "3073": "Arabic – Egypt",
                       "3076": "Chinese (Traditional) – Hong Kong SAR",
                       "3079": "German – Austria",
                       "3081": "English – Australia",
                       "3082": "Spanish – International Sort",
                       "3084": "French – Canada",
                       "3098": "Serbian – Cyrillic",
                       "4097": "Arabic – Libya",
                       "4100": "Chinese (Simplified) – Singapore",
                       "4103": "German – Luxembourg",
                       "4105": "English – Canada",
                       "4106": "Spanish – Guatemala",
                       "4108": "French – Switzerland",
                       "5121": "Arabic – Algeria",
                       "5127": "German – Liechtenstein",
                       "5129": "English – New Zealand",
                       "5130": "Spanish – Costa Rica",
                       "5132": "French – Luxembourg",
                       "6145": "Arabic – Morocco",
                       "6153": "English – Ireland",
                       "6154": "Spanish – Panama",
                       "7169": "Arabic – Tunisia",
                       "7177": "English – South Africa",
                       "7178": "Spanish – Dominican Republic",
                       "8193": "Arabic – Oman",
                       "8201": "English – Jamaica",
                       "8202": "Spanish – Venezuela",
                       "9217": "Arabic – Yemen",
                       "9226": "Spanish – Colombia",
                       "10241": "Arabic – Syria",
                       "10249": "English – Belize",
                       "10250": "Spanish – Peru",
                       "11265": "Arabic – Jordan",
                       "11273": "English – Trinidad",
                       "11274": "Spanish – Argentina",
                       "12289": "Arabic – Lebanon",
                       "12298": "Spanish – Ecuador",
                       "13313": "Arabic – Kuwait",
                       "13322": "Spanish – Chile",
                       "14337": "Arabic – U.A.E.",
                       "14346": "Spanish – Uruguay",
                       "15361": "Arabic – Bahrain",
                       "15370": "Spanish – Paraguay",
                       "16385": "Arabic – Qatar",
                       "16394": "Spanish – Bolivia",
                       "17418": "Spanish – El Salvador",
                       "18442": "Spanish – Honduras",
                       "19466": "Spanish – Nicaragua",
                       "20490": "Spanish – Puerto Rico"
                       }

characterset_dict = {"932": "Japanese",
                     "936": "GBK - Simplified Chinese",
                     "949": "Korean",
                     "950": "BIG5 - Traditional Chinese",
                     "1200": "UTF-16LE Unicode little-endian",
                     "1201": "UTF-16BE Unicode big-endian",
                     "1251": "Cyrillic (Windows)",
                     "1252": "Western European (Windows)",
                     "1253": "Greek (Windows)",
                     "1254": "Turkish (Windows)",
                     "1255": "Hebrew (Windows)",
                     "1256": "Arabic (Windows)",
                     "1257": "Baltic (Windows)",
                     "1258": "Vietnamese (Windows)",
                     "65000": "UTF-7 Unicode",
                     "65001": "UTF-8 Unicode",
                     "10000": "Macintosh Roman encoding",
                     "10007": "Macintosh Cyrillic encoding",
                     "10029": "Macintosh Central European encoding",
                     "20127": "US-ASCII",
                     "28591": "ISO-8859-1"
                     }

logontype = {
    "0": "Local System",
    "2": "Interactive",  # (Local logon)
    "3": "Network",  # (Remote logon)
    "4": "Batch",  # (Scheduled task)
    "5": "Service",  # (Service account logon)
    "7": "Unlock",  # (Screen saver)
    "8": "NetworkCleartext",  # (Cleartext network logon)
    "9": "NewCredentials",  # (RunAs using alternate credentials)
    "10": "RemoteInteractive",  # (RDP\TS\RemoteAssistance)
    "11": "CachedInteractive"  # (Local w\cached credentials)
}

class WindowsScan():
    def __init__(self, init_info):
        for k,v in init_info.items():
            setattr(self, k ,v)

    def format_out(self):
        result = {}
        result['SystemInformation'] = self.get_computer_system()
        result['OperatingSystemInformation'] = self.get_operating_system()
        result['PhysicalMemoryInformation'] = self.get_physicalmemory_information()
        result['PageFileInformation'] = self.get_pagefile_information()
        result['BIOSInformation'] = self.get_bios_information()
        result['LogicalDiskInformation'] = self.get_logicaldisk_information()
        result['VolumeInformation'] = self.get_volume_information()
        result['NetworkInterfaceInformation'], result['PortInformation'] = self.get_networkinterface_information()
        result['SoftwareInformation'] = self.get_software_information()
        result['CpuInformation'] = self.get_cpu_information()
        result['UserGroupInformation'] = self.get_groupuser_information()
        result['ProcessInformation'] = self.get_process_information()
        result['ServiceInformation'], result['Snmp'] = self.get_service_information()
        result['EnvironmentVariable'] = self.get_environmentvariable_information()
        result['Route'] = self.get_route_information()
        result['Loggedonuser'] = self.get_loggedon_user_information()
        result['Eventlog'] = self.get_eventlog_information()
        result['Ntp'] = {}
        result['ProcessHandleQuota'] = {}
        result['Firewallrules'] = {}
        result['Firewallstatus'] = {}
        further_data = self.further_data_processing(result, self.wmic.credential_dict['host'])
        return further_data

    def totime(self, datestr):
        date = time.strptime(datestr.split('.')[0].replace('*','0'), "%Y%m%d%H%M%S")
        date = time.strftime('%Y/%m/%d %H:%M:%S', date)
        return date

    def todate(self, datestr):
        date = time.strptime(datestr.split('.')[0], "%Y%m%d")
        date = time.strftime('%y/%m/%d', date)
        return date

    def get_computer_system(self):
        Win32_ComputerSystem = self.wmic.query("SELECT * FROM Win32_ComputerSystem")[0]
        Win32_TimeZone = self.wmic.query("SELECT Caption FROM Win32_TimeZone")[0]
        Win32_PhysicalMemoryArray = self.wmic.query("SELECT MemoryDevices FROM Win32_PhysicalMemoryArray")
        slot_number = 0
        for Win32_PhysicalMemory in Win32_PhysicalMemoryArray:
            slot_number += int(Win32_PhysicalMemory['MemoryDevices'])
        SystemInformation = {'Name': Win32_ComputerSystem['Name'],
                             'Manufacturer': Win32_ComputerSystem['Manufacturer'],
                             'Model': Win32_ComputerSystem['Model'],
                             'Physical Processors': Win32_ComputerSystem['NumberOfProcessors'],
                             'Total Physical Memory (Gb)': "%.2f" % (
                                         int(Win32_ComputerSystem['TotalPhysicalMemory']) / 1024 ** 3) + 'GB',
                             'DnsHostName': Win32_ComputerSystem['DNSHostName'],
                             'Domain': Win32_ComputerSystem['Domain'],
                             'SystemType': Win32_ComputerSystem['SystemType'],
                             'Status': Win32_ComputerSystem['Status'],
                             'Timezone': Win32_TimeZone['Caption'],
                             'Total DIMM Slots Number': slot_number}
        return SystemInformation

    def get_operating_system(self):
        Win32_OperatingSystem = self.wmic.query("SELECT * FROM Win32_OperatingSystem")[0]
        operatingsysteminformation = {'Operating System': Win32_OperatingSystem['Caption'],
                                      'Architecture': Win32_OperatingSystem.get('OSArchitecture', ''),
                                      'Version': Win32_OperatingSystem['Version'],
                                      'Organization': Win32_OperatingSystem['Organization'],
                                      'Install Date': self.totime(Win32_OperatingSystem['InstallDate']),
                                      'FreePhysicalMemory (GB)': "%.2f" % (
                                                  int(Win32_OperatingSystem['FreePhysicalMemory']) / 1024 ** 2) + 'GB',
                                      'FreeVirtualMemory (GB)': "%.2f" % (
                                                  int(Win32_OperatingSystem['FreeVirtualMemory']) / 1024 ** 2) + 'GB',
                                      'TotalVirtualMemorySize (GB)': "%.2f" % (int(
                                          Win32_OperatingSystem['TotalVirtualMemorySize']) / 1024 ** 2) + 'GB',
                                      'WindowsDirectory': Win32_OperatingSystem['WindowsDirectory'],
                                      'SystemDirectory': Win32_OperatingSystem['SystemDirectory'],
                                      'Manufacturer': Win32_OperatingSystem['Manufacturer'],
                                      'SerialNumber': Win32_OperatingSystem['SerialNumber'],
                                      'Status': Win32_OperatingSystem['Status'],
                                      'Lastbootuptime': self.totime(Win32_OperatingSystem['LastBootUpTime']),
                                      'CountryCode': Win32_OperatingSystem['CountryCode'],
                                      'Oslanguagename': oslanguagename_dict[Win32_OperatingSystem['OSLanguage']],
                                      'Characterset': characterset_dict[Win32_OperatingSystem['CodeSet']]}
        return operatingsysteminformation

    def get_physicalmemory_information(self):
        Win32_PhysicalMemorys = self.wmic.query("SELECT * FROM Win32_PhysicalMemory")
        physicalmemoryinformations = []
        for Win32_PhysicalMemory in Win32_PhysicalMemorys:
            physicalmemoryinformation = {'Name': Win32_PhysicalMemory['Name'],
                                         'Device Locator': Win32_PhysicalMemory['DeviceLocator'],
                                         'Manufacturer': Win32_PhysicalMemory['Manufacturer'],
                                         'Speed': Win32_PhysicalMemory['Speed'],
                                         'Capacity (GB)': "%.2f" % (
                                                     int(Win32_PhysicalMemory['Capacity']) / 1024 ** 3) + 'GB'
                                         }
            physicalmemoryinformations.append(physicalmemoryinformation)
        return physicalmemoryinformations

    def get_pagefile_information(self):
        Win32_PageFileUsage = self.wmic.query("SELECT * FROM Win32_PageFileUsage")[0]
        pagefileinformation = {'Pagefile Name': Win32_PageFileUsage['Name'],
                               'Allocated Size (Mb)': Win32_PageFileUsage['AllocatedBaseSize'],
                               'Install Date': self.totime(Win32_PageFileUsage['InstallDate']),
                               'PeakUsage': Win32_PageFileUsage['PeakUsage']
                               }
        return pagefileinformation

    def get_bios_information(self):
        Win32_Bios = self.wmic.query("SELECT * FROM Win32_Bios")[0]
        biosinformation = {'Status': Win32_Bios['Status'],
                           'Version': Win32_Bios['Version'],
                           'Manufacturer': Win32_Bios['Manufacturer'],
                           'Release Date': self.totime(Win32_Bios['ReleaseDate']),
                           'Serial Number': Win32_Bios['SerialNumber'],
                           'Name': Win32_Bios['Name']
                           }
        return biosinformation

    def get_logicaldisk_information(self):
        Win32_LogicalDisks = self.wmic.query("SELECT * FROM Win32_LogicalDisk")
        logicaldiskinformations = []
        for Win32_LogicalDisk in Win32_LogicalDisks:
            logicaldiskinformation = {'DeviceID': Win32_LogicalDisk['DeviceID'],
                                      'FileSystem': Win32_LogicalDisk['FileSystem'],
                                      'VolumeName': Win32_LogicalDisk['VolumeName'],
                                      'Total Size (GB)': "%.2f" % (int(Win32_LogicalDisk['Size']) / 1024 ** 3) + 'GB',
                                      'Free Space (GB)': "%.2f" % (
                                                  int(Win32_LogicalDisk['FreeSpace']) / 1024 ** 3) + 'GB'
                                      }
            logicaldiskinformations.append(logicaldiskinformation)
        return logicaldiskinformations

    def get_volume_information(self):
        Win32_Volumes = self.wmic.query("SELECT * FROM Win32_Volume")
        volumeinformations = []
        for Win32_Volume in Win32_Volumes:
            volumeinformation = {'Label': Win32_Volume['Label'],
                                 'Name': Win32_Volume['Name'],
                                 'DeviceID': Win32_Volume['DeviceID'],
                                 'SystemVolume': Win32_Volume.get('SystemVolume', ''),
                                 'Total Size (GB)': "%.2f" % (int(Win32_Volume['Capacity']) / 1024 ** 3) + 'GB',
                                 'Free Space (GB)': "%.2f" % (int(Win32_Volume['FreeSpace']) / 1024 ** 3) + 'GB',
                                 'FileSystem': Win32_Volume['FileSystem'],
                                 'BootVolume': Win32_Volume.get('BootVolume', ''),
                                 'DriveType': Win32_Volume['DriveType'],
                                 'SerialNumber': Win32_Volume['SerialNumber']
                                 }
            volumeinformations.append(volumeinformation)
        return volumeinformations

    def get_networkinterface_information(self):
        Win32_NetworkAdapters = self.wmic.query("SELECT * FROM Win32_NetworkAdapter")
        Win32_NetworkAdapterConfigurations = self.wmic.query("SELECT * FROM Win32_NetworkAdapterConfiguration")
        networkinterfaceinformations = []
        portinformations = []
        for Win32_NetworkAdapter in Win32_NetworkAdapters:
            if Win32_NetworkAdapter.get('PhysicalAdapter', True):
                networkinterfaceinformation = {'Adapter Name': Win32_NetworkAdapter['Name'],
                                               'Adapter Type': Win32_NetworkAdapter['AdapterType'],
                                               'MAC': Win32_NetworkAdapter['MACAddress'],
                                               'PNPDeviceID': Win32_NetworkAdapter['PNPDeviceID'],
                                               'Connection Name': Win32_NetworkAdapter['NetConnectionID'],
                                               'Enabled': Win32_NetworkAdapter.get('NetEnabled', ''),
                                               'Speed (Mbps)': int(Win32_NetworkAdapter['Speed']) / 1000000,
                                               'InterfaceIndex': Win32_NetworkAdapter['InterfaceIndex']
                                               }
                for Win32_NetworkAdapterConfiguration in Win32_NetworkAdapterConfigurations:
                    if Win32_NetworkAdapterConfiguration['Description'] == networkinterfaceinformation['Adapter Name']:
                        networkinterfaceinformation['IPAddress'] = Win32_NetworkAdapterConfiguration['IPAddress']
                        networkinterfaceinformation['IpSubnet'] = Win32_NetworkAdapterConfiguration['IPSubnet']
                        networkinterfaceinformation['DefaultIPgateway'] = Win32_NetworkAdapterConfiguration[
                            'DefaultIPGateway']
                        networkinterfaceinformation['DNSServerSearchOrder'] = Win32_NetworkAdapterConfiguration[
                            'DNSServerSearchOrder']
                        break
                networkinterfaceinformations.append(networkinterfaceinformation)
                Manufacturer = Win32_NetworkAdapter.get('Manufacturer')
                if not Manufacturer:
                    Manufacturer = ''
                PNPDeviceID = Win32_NetworkAdapter.get('PNPDeviceID')
                if not PNPDeviceID:
                    PNPDeviceID = ''
                if Manufacturer != 'Microsoft' and 'ROOT\\' not in PNPDeviceID:
                    portinformations.append(networkinterfaceinformation)
        return networkinterfaceinformations, portinformations

    def get_software_information(self):
        try:
            Win32_Products = self.wmic.query("SELECT * FROM Win32_Product")
            productinformations = []
            for Win32_Product in Win32_Products:
                productinformation = {'Vendor': Win32_Product['Vendor'],
                                      'Name': Win32_Product['Name'],
                                      'Version': Win32_Product['Version'],
                                      'IdentifyingNumber': Win32_Product['IdentifyingNumber'],
                                      'InstallLocation': Win32_Product['InstallLocation'],
                                      'Install Date': self.todate(Win32_Product['InstallDate'])
                                      }
                productinformations.append(productinformation)
        except Exception:
            productinformations = []
        return productinformations

    def get_cpu_information(self):
        Win32_processors = self.wmic.query("SELECT * FROM Win32_processor")
        cpuinformations = []
        for Win32_processor in Win32_processors:
            cpuinformation = {'Name': Win32_processor['Name'],
                              'Architecture': Win32_processor['Architecture'],
                              'Manufacturer': Win32_processor['Manufacturer'],
                              'NumberOfCores': Win32_processor.get('NumberOfCores', ''),
                              'NumberOfLogicalProcessors': Win32_processor.get('NumberOfLogicalProcessors', ''),
                              # 'Max Speed (Mhz)': Win32_processor['MaxClockSpeed'],
                              'Current Speed (Mhz)': Win32_processor['CurrentClockSpeed']
                              }
            cpuinformations.append(cpuinformation)
        return cpuinformations

    def get_groupuser_information(self):
        Win32_groupusers = self.wmic.query("SELECT * FROM Win32_groupuser")
        groupuserinformations = []
        for Win32_groupuser in Win32_groupusers:
            groupuserinformation = {'UserName': Win32_groupuser['PartComponent'].split('Name=')[1].replace('\"', ''),
                                    'GroupName': Win32_groupuser['GroupComponent'].split('Name=')[1].replace('\"', '')
                                    }
            groupuserinformations.append(groupuserinformation)
        return groupuserinformations

    def get_process_information(self):
        Win32_processes = self.wmic.query("SELECT * FROM Win32_process")
        processinformations = []
        for Win32_process in Win32_processes:
            processinformation = {'Name': Win32_process['Name'],
                                  'ParentProcessId': Win32_process['ParentProcessId'],
                                  'ProcessId': Win32_process['ProcessId'],
                                  'Path': Win32_process['ExecutablePath']
                                  }
            processinformations.append(processinformation)
        return processinformations

    def get_service_information(self):
        Win32_services = self.wmic.query("SELECT * FROM Win32_service")
        serviceinformations = []
        snmpinformation = {}
        for Win32_service in Win32_services:
            serviceinformation = {'Name': Win32_service['Name'],
                                  'ProcessId': Win32_service['ProcessId'],
                                  'ExitCode': Win32_service['ExitCode'],
                                  'StartMode': Win32_service['StartMode'],
                                  'State': Win32_service['State']
                                  }
            if serviceinformation['Name'] == 'SNMP':
                snmpinformation = {
                    'ProcessId': Win32_service['ProcessId'],
                    'ExitCode': Win32_service['ExitCode'],
                    'StartMode': Win32_service['StartMode'],
                    'State': Win32_service['State']
                }
            serviceinformations.append(serviceinformation)
        return serviceinformations, snmpinformation

    def get_environmentvariable_information(self):
        Win32_Environments = self.wmic.query("SELECT * FROM Win32_Environment")
        environmentvariables = []
        for Win32_Environment in Win32_Environments:
            environmentvariable = {'Name': Win32_Environment['Name'],
                                   'VariableValue': Win32_Environment['VariableValue']
                                   }
            environmentvariables.append(environmentvariable)
        return environmentvariables

    def get_route_information(self):
        Win32_IP4RouteTables = self.wmic.query("SELECT * FROM Win32_IP4RouteTable")
        route_informations = []
        for Win32_IP4RouteTable in Win32_IP4RouteTables:
            route_information = {'Destination': Win32_IP4RouteTable['Destination'],
                                 'Mask': Win32_IP4RouteTable['Mask'],
                                 'NextHop': Win32_IP4RouteTable['NextHop'],
                                 'InterfaceIndex': Win32_IP4RouteTable['InterfaceIndex']
                                 }
            route_informations.append(route_information)
        return route_informations

    def get_loggedon_user_information(self):
        win32_logonsessions = self.wmic.query("SELECT * FROM win32_logonsession")
        win32_loggedonusers = self.wmic.query("SELECT * FROM win32_loggedonuser")
        loggedonusers = []
        session_users = {}
        for win32_loggedonuser in win32_loggedonusers:
            antecedent = win32_loggedonuser['Antecedent']
            username = antecedent.split(',')[0].split('Domain=')[1].replace('\"', '') + '\\' + \
                       antecedent.split(',')[1].split('Name=')[1].replace('\"', '')
            dependent = win32_loggedonuser['Dependent']
            session = dependent.split('LogonId=')[1].replace('\"', '')
            # if session in session_users.keys():
            #    session_users[session].append(username)
            # else:
            session_users[session] = username
        for win32_logonsession in win32_logonsessions:
            loggedonuser = {'Session': win32_logonsession['LogonId'],
                            'User': session_users[win32_logonsession['LogonId']] if session_users.get(
                                win32_logonsession['LogonId']) else '',
                            'Type': logontype[win32_logonsession['LogonType']],
                            'Auth': win32_logonsession['AuthenticationPackage'],
                            'StartTime': self.totime(win32_logonsession['StartTime'])
                            }
            loggedonusers.append(loggedonuser)
        return loggedonusers

    def get_eventlog_information(self):
        Win32_NTEventlogFiles = self.wmic.query("SELECT * FROM Win32_NTEventlogFile")
        eventlog_informations = []
        for Win32_NTEventlogFile in Win32_NTEventlogFiles:
            eventlog_information = {'LogfileName': Win32_NTEventlogFile['LogfileName'],
                                    'NumberOfRecords': Win32_NTEventlogFile['NumberOfRecords'],
                                    'Logfilepath': Win32_NTEventlogFile['Name'],
                                    'FileSize': "%.2f" % (int(Win32_NTEventlogFile['FileSize']) / 1024) + 'KB'
                                    }
            eventlog_informations.append(eventlog_information)
        return eventlog_informations

    def further_data_processing(self, data, host):
        # collect time
        collect_time = time.strftime('%Y.%m.%d %H:%M:%S', time.localtime(time.time()))
        data['collect_time'] = collect_time
        # collect uuid
        uuid = hashlib.md5(data['BIOSInformation']['Serial Number'].encode("utf8")).hexdigest()
        data['uuid'] = uuid
        cpu_core_number = 0
        for cpu in data['CpuInformation']:
            if cpu['NumberOfCores']:
                cpu_core_number += int(cpu['NumberOfCores'])
            cpu['Speed (Mhz)'] = float(cpu['Name'].split('@ ')[1].split('GHz')[0]) * 1024
        if cpu_core_number == 0:
            data['SystemInformation']['Cpu core number'] = ''
        else:
            data['SystemInformation']['Cpu core number'] = cpu_core_number
        data['SystemInformation']['Cpu number'] = len(data['CpuInformation'])
        data['SystemInformation']['Physical memory number'] = len(data['PhysicalMemoryInformation'])
        total_size = 0
        free_size = 0
        for logicaldisk in data['LogicalDiskInformation']:
            total_size += float(logicaldisk['Total Size (GB)'].split('GB')[0])
            free_size += float(logicaldisk['Free Space (GB)'].split('GB')[0])
        data['SystemInformation']['Total Logical Disk (Gb)'] = str(total_size) + 'GB'
        data['SystemInformation']['Free Logical Disk (Gb)'] = str(free_size) + 'GB'
        data['SystemInformation']['Logical Disk number'] = len(data['LogicalDiskInformation'])
        repeat_device_list = []
        interface_number = 0
        for port in data['PortInformation']:
            if port.get('PNPDeviceID') and port['PNPDeviceID'].split('\\')[1] not in repeat_device_list:
                interface_number += 1
                repeat_device_list.append(port['PNPDeviceID'].split('\\')[1])
            if port['Speed (Mbps)'] == 9223372036854.775:
                port['Speed (Mbps)'] = 0
        for Interface in data['NetworkInterfaceInformation']:
            if Interface['Speed (Mbps)'] == 9223372036854.775:
                Interface['Speed (Mbps)'] = 0
        data['SystemInformation']['Networkcard number'] = interface_number
        data['SystemInformation']['Port number'] = len(data['PortInformation'])
        slots_number = 0
        if isinstance(data['SystemInformation']['Total DIMM Slots Number'], list):
            for num in data['SystemInformation']['Total DIMM Slots Number']:
                slots_number += num
        elif isinstance(data['SystemInformation']['Total DIMM Slots Number'], int):
            slots_number = data['SystemInformation']['Total DIMM Slots Number']

        data['SystemInformation']['Total DIMM Slots Number'] = slots_number
        # collect virtualization
        virtualization = dict()
        model = data['SystemInformation']['Model']
        if 'Virtual' in model:
            virtualization['virtual'] = 'YES'
            virtualization['virtual_type'] = model
        else:
            virtualization['virtual'] = 'NO'
            virtualization['virtual_type'] = ''
        data['virtualization'] = virtualization
        # collect hardware
        hardware = dict()
        hardware['part_type1'] = [{}, {}]
        hardware['part_type2'] = [{}, {}]
        data['hardware'] = hardware
        # collect scanip
        data['scan_ip'] = host
        data['os_type'] = 'Windows'
        data['mac'] = ''
        data['netmask'] = ''
        get_macnetmask_flag = 0
        for interface in data['NetworkInterfaceInformation']:
            i = 0
            for ip in interface['IPAddress']:
                if host in ip:
                    data['mac'] = interface['MAC']
                    data['netmask'] = interface['IpSubnet'][i]
                    get_macnetmask_flag = 1
                    break
                i += 1
            if get_macnetmask_flag:
                break
        for route in data['Route']:
            if route['Destination'] == '0.0.0.0':
                interface_index = route['InterfaceIndex']
                break
        for interface in data['NetworkInterfaceInformation']:
            if interface['InterfaceIndex'] == interface_index:
                sysip = interface['IPAddress'][0].split(',')[0]
                sysip_mac = interface['MAC']
                sysip_netmask = interface['IpSubnet'][0].split(',')[0]
                data['SystemInformation']['sysip'] = sysip
                data['SystemInformation']['sysip_mac'] = sysip_mac
                data['SystemInformation']['sysip_netmask'] = sysip_netmask
                break
        if type(data['SoftwareInformation']) == dict:
            data['SoftwareInformation'] = [data['SoftwareInformation']]
        data['mapping'] = self.get_mapping(data)
        if not data['OperatingSystemInformation']['Architecture']:
            data['OperatingSystemInformation']['Architecture'] = data['SystemInformation']['SystemType'].split(' ')[0]
        data['network'] = {'ip': []}
        for interface in data['NetworkInterfaceInformation']:
            host_ip = interface['IPAddress']
            host_mask = interface['IpSubnet']
            if host_ip != 'NULL' and host_mask != 'NULL':
                ip_info = {'ip': host_ip[0].split(',')[0],
                           'mask': host_mask[0].split(',')[0]}
                data['network']['ip'].append(ip_info)
        return data

    def get_mapping(self, data):
        data_mapping = {}
        data_mapping['SystemInformation'] = {}
        data_mapping['SystemInformation']['Total Physical Memory (Gb)'] = string_to_bytes(
            data['SystemInformation']['Total Physical Memory (Gb)'])
        data_mapping['SystemInformation']['Total Logical Disk (Gb)'] = string_to_bytes(
            data['SystemInformation']['Total Logical Disk (Gb)'])
        data_mapping['SystemInformation']['Free Logical Disk (Gb)'] = string_to_bytes(
            data['SystemInformation']['Free Logical Disk (Gb)'])
        data_mapping['OperatingSystemInformation'] = {}
        data_mapping['OperatingSystemInformation']['FreePhysicalMemory (GB)'] = string_to_bytes(
            data['OperatingSystemInformation']['FreePhysicalMemory (GB)'])
        data_mapping['LogicalDiskInformation'] = []
        for disk in data['LogicalDiskInformation']:
            disk_size = {}
            disk_size['Free Space (GB)'] = string_to_bytes(disk['Free Space (GB)'])
            disk_size['Total Size (GB)'] = string_to_bytes(disk['Total Size (GB)'])
            data_mapping['LogicalDiskInformation'].append(disk_size)
        data_mapping['VolumeInformation'] = []
        for volume in data['VolumeInformation']:
            volume_size = {}
            volume_size['Free Space (GB)'] = string_to_bytes(volume['Free Space (GB)'])
            volume_size['Total Size (GB)'] = string_to_bytes(volume['Total Size (GB)'])
            data_mapping['VolumeInformation'].append(volume_size)
        return data_mapping


'''
credential = {
    "host": "192.168.41.158",
    "username": "administrator",
    "password": "jsepc123!"
}

instance = WindowsScan(credential)
print(instance.format_out())
'''
