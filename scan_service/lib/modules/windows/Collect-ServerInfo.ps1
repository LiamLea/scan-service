<#
.SYNOPSIS
Collect-ServerInfo.ps1 - PowerShell script to collect information about Windows servers

.DESCRIPTION 
This PowerShell script runs a series of WMI and other queries to collect information
about Windows servers.

.OUTPUTS
Each server's results are output to HTML.

.PARAMETER -Verbose
See more detailed progress as the script is running.

.EXAMPLE
.\Collect-ServerInfo.ps1 SERVER1
Collect information about a single server.

.EXAMPLE
"SERVER1","SERVER2","SERVER3" | .\Collect-ServerInfo.ps1
Collect information about multiple servers.

.EXAMPLE
Get-ADComputer -Filter {OperatingSystem -Like "Windows Server*"} | %{.\Collect-ServerInfo.ps1 $_.DNSHostName}
Collects information about all servers in Active Directory.


.NOTES
Written by Paul Cunningham
Technical Consultant/Director at LockLAN Systems Pty Ltd - https://www.locklan.com.au
Microsoft MVP, Office Servers and Services - http://exchangeserverpro.com

You can also find me on:

* Twitter: https://twitter.com/paulcunningham
* Twitter: https://twitter.com/ExchServPro
* LinkedIn: http://au.linkedin.com/in/cunninghamp/
* Github: https://github.com/cunninghamp

License:

The MIT License (MIT)

Copyright (c) 2016 Paul Cunningham

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

Change Log:
V1.00, 20/04/2015 - First release
V1.01, 01/05/2015 - Updated with better error handling
#>


[CmdletBinding()]

Param (

    [parameter(ValueFromPipeline=$True)]
    [string[]]$ComputerName

)

Begin
{
    #Initialize
    Write-Verbose "Initializing"

}

Process
{

    #---------------------------------------------------------------------
    # Process each ComputerName
    #---------------------------------------------------------------------

    if (!($PSCmdlet.MyInvocation.BoundParameters[“Verbose”].IsPresent))
    {
        #Write-Host "Processing $ComputerName"
		#Write-Host "Processing $user"
		#Write-Host "Processing $password"
		
    }

    Write-Verbose "=====> Processing $ComputerName <====="
    Write-Host "start collect"

    $htmlreport = @()
    $htmlbody = @()
    $htmlfile = "$($ComputerName).html"
    $spacer = "<br />"
	
	
    #---------------------------------------------------------------------
    # Do 10 pings and calculate the fastest response time
    # Not using the response time in the report yet so it might be
    # removed later.
    #---------------------------------------------------------------------
    
    try
    {
        $bestping = (Test-Connection -ComputerName $ComputerName -Count 10 -ErrorAction STOP | Sort ResponseTime)[0].ResponseTime
    }
    catch
    {
        Write-Warning $_.Exception.Message
        $bestping = "Unable to connect"
    }

    if ($bestping -eq "Unable to connect")
    {
        if (!($PSCmdlet.MyInvocation.BoundParameters[“Verbose”].IsPresent))
        {
            Write-Host "Unable to connect to $ComputerName"
        }

        "Unable to connect to $ComputerName"
    }
    else
    {

        #---------------------------------------------------------------------
        # Collect computer system information and convert to HTML fragment
        #---------------------------------------------------------------------
    
        Write-Verbose "Collecting computer system information"

        $subhead = "<h3>Computer System Information</h3>"
        $htmlbody += $subhead
    
        try
        {
            $csinfo = Get-WmiObject Win32_ComputerSystem -ComputerName $ComputerName -ErrorAction STOP |
                Select-Object Name,Manufacturer,Model,
                            @{Name='Physical Processors';Expression={$_.NumberOfProcessors}},
                            @{Name='Total Physical Memory (Gb)';Expression={
                                $tpm = $_.TotalPhysicalMemory/1GB;
                                "{0:F0}" -f $tpm
                            }},
                            DnsHostName,Domain,SystemType,Status

            $timezone =  Get-WmiObject Win32_TimeZone -ComputerName $ComputerName -ErrorAction STOP | select-object Caption 
		    $memoryslotnumber =  Get-WmiObject Win32_PhysicalMemoryArray -ComputerName $ComputerName -ErrorAction STOP | select-object MemoryDevices
            $csinfo | Add-Member NoteProperty -Name "Timezone" -Value $timezone.Caption
			$csinfo | Add-Member NoteProperty -Name "Total DIMM Slots Number" -Value $memoryslotnumber.MemoryDevices

            $htmlbody += $csinfo | ConvertTo-Html -Fragment
            $htmlbody += $spacer
       
        }
        catch
        {
            Write-Warning $_.Exception.Message
            $htmlbody += "<p>An error was encountered. $($_.Exception.Message)</p>"
            $htmlbody += $spacer
			$csinfo = @{}
        }


        #---------------------------------------------------------------------
        # Collect operating system information and convert to HTML fragment
        #---------------------------------------------------------------------
    
        Write-Verbose "Collecting operating system information"

        $subhead = "<h3>Operating System Information</h3>"
        $htmlbody += $subhead
    
        try
        {
            $osinfo = Get-WmiObject Win32_OperatingSystem -ComputerName $ComputerName -ErrorAction STOP | 
                Select-Object @{Name='Operating System';Expression={$_.Caption}},
                            @{Name='Architecture';Expression={$_.OSArchitecture}},
                            Version,Organization,
                            @{Name='Install Date';Expression={
                                $installdate = [datetime]::ParseExact($_.InstallDate.SubString(0,8),"yyyyMMdd",$null);
                                $installdate.ToShortDateString()
                            }},
							@{Name='FreePhysicalMemory (GB)';Expression={
                                $_.FreePhysicalMemory/1Mb -as [int]
                            }},
							@{Name='FreeVirtualMemory (GB)';Expression={
                                $_.FreeVirtualMemory/1Mb -as [int]
                            }},
							@{Name='TotalVirtualMemorySize (GB)';Expression={
                                $_.TotalVirtualMemorySize/1Mb -as [int]
                            }},
                            WindowsDirectory,SystemDirectory,Manufacturer,
							SerialNumber,Status,
                            @{Name='Lastbootuptime';Expression={
                                $lastbootuptime = [management.managementdatetimeconverter]::todatetime($_.LastBootUpTime)
                                $lastbootuptime.ToString()
                            }},
                            CountryCode,Oslanguage,Codeset

            $oslanguagename = @{ 
                "1"="Arabic" 
                "4"="Chinese (Simplified)– China"
                "9"="English"
                "1025"="Arabic – Saudi Arabia"
                "1026"="Bulgarian"
                "1027"="Catalan"
                "1028"="Chinese (Traditional) – Taiwan"
                "1029"="Czech"
                "1030"="Danish"
                "1031"="German – Germany"
                "1032"="Greek"
                "1033"="English – United States"
                "1034"="Spanish – Traditional Sort"
                "1035"="Finnish"
                "1036"="French – France"
                "1037"="Hebrew"
                "1038"="Hungarian"
                "1039"="Icelandic"
                "1040"="Italian – Italy"
                "1041"="Japanese"
                "1042"="Korean"
                "1043"="Dutch – Netherlands"
                "1044"="Norwegian – Bokmal"
                "1045"="Polish"
                "1046"="Portuguese – Brazil"
                "1047"="Rhaeto-Romanic"
                "1048"="Romanian"
                "1049"="Russian"
                "1050"="Croatian"
                "1051"="Slovak"
                "1052"="Albanian"
                "1053"="Swedish"
                "1054"="Thai"
                "1055"="Turkish"
                "1056"="Urdu"
                "1057"="Indonesian"
                "1058"="Ukrainian"
                "1059"="Belarusian"
                "1060"="Slovenian"
                "1061"="Estonian"
                "1062"="Latvian"
                "1063"="Lithuanian"
                "1065"="Persian"
                "1066"="Vietnamese"
                "1069"="Basque (Basque)"
                "1070"="Serbian"
                "1071"="Macedonian (North Macedonia)"
                "1072"="Sutu"
                "1073"="Tsonga"
                "1074"="Tswana"
                "1076"="Xhosa"
                "1077"="Zulu"
                "1078"="Afrikaans"
                "1080"="Faeroese"
                "1081"="Hindi"
                "1082"="Maltese"
                "1084"="Scottish Gaelic (United Kingdom)"
                "1085"="Yiddish"
                "1086"="Malay – Malaysia"
                "2049"="Arabic"
                "2052"="Chinese (Simplified) – PRC"
                "2055"="German – Switzerland"
                "2057"="English – United Kingdom"
                "2058"="Spanish – Mexico"
                "2060"="French – Belgium"
                "2064"="Italian – Switzerland"
                "2067"="Dutch – Belgium"
                "2068"="Norwegian – Nynorsk"
                "2070"="Portuguese – Portugal"
                "2072"="Romanian – Moldova"
                "2073"="Russian – Moldova"
                "2074"="Serbian – Latin"
                "2077"="Swedish – Finland"
                "3073"="Arabic – Egypt"
                "3076"="Chinese (Traditional) – Hong Kong SAR"
                "3079"="German – Austria"
                "3081"="English – Australia"
                "3082"="Spanish – International Sort"
                "3084"="French – Canada"
                "3098"="Serbian – Cyrillic"
                "4097"="Arabic – Libya"
                "4100"="Chinese (Simplified) – Singapore"
                "4103"="German – Luxembourg"
                "4105"="English – Canada"
                "4106"="Spanish – Guatemala"
                "4108"="French – Switzerland"
                "5121"="Arabic – Algeria"
                "5127"="German – Liechtenstein"
                "5129"="English – New Zealand"
                "5130"="Spanish – Costa Rica"
                "5132"="French – Luxembourg"
                "6145"="Arabic – Morocco"
                "6153"="English – Ireland"
                "6154"="Spanish – Panama"
                "7169"="Arabic – Tunisia"
                "7177"="English – South Africa"
                "7178"="Spanish – Dominican Republic"
                "8193"="Arabic – Oman"
                "8201"="English – Jamaica"
                "8202"="Spanish – Venezuela"
                "9217"="Arabic – Yemen"
                "9226"="Spanish – Colombia"
                "10241"="Arabic – Syria"
                "10249"="English – Belize"
                "10250"="Spanish – Peru"
                "11265"="Arabic – Jordan"
                "11273"="English – Trinidad"
                "11274"="Spanish – Argentina"
                "12289"="Arabic – Lebanon"
                "12298"="Spanish – Ecuador"
                "13313"="Arabic – Kuwait"
                "13322"="Spanish – Chile"
                "14337"="Arabic – U.A.E."
                "14346"="Spanish – Uruguay"
                "15361"="Arabic – Bahrain"
                "15370"="Spanish – Paraguay"
                "16385"="Arabic – Qatar"
                "16394"="Spanish – Bolivia"
                "17418"="Spanish – El Salvador"
                "18442"="Spanish – Honduras"
                "19466"="Spanish – Nicaragua"
                "20490"="Spanish – Puerto Rico"
            }

            $characterset = @{ 
                "932"="Japanese" 
                "936"="GBK - Simplified Chinese"
                "949"="Korean"
                "950"="BIG5 - Traditional Chinese"
                "1200"="UTF-16LE Unicode little-endian"
                "1201"="UTF-16BE Unicode big-endian"
                "1251"="Cyrillic (Windows)"
                "1252"="Western European (Windows)"
                "1253"="Greek (Windows)"
                "1254"="Turkish (Windows)"
                "1255"="Hebrew (Windows)"
                "1256"="Arabic (Windows)"
                "1257"="Baltic (Windows)"
                "1258"="Vietnamese (Windows)"
                "65000"="UTF-7 Unicode"
                "65001"="UTF-8 Unicode"
                "10000"="Macintosh Roman encoding"
                "10007"="Macintosh Cyrillic encoding"
                "10029"="Macintosh Central European encoding"
                "20127"="US-ASCII"
                "28591"="ISO-8859-1"
            }

            $osinfo | Add-Member -MemberType NoteProperty -Name "Oslanguagename" -Value $oslanguagename[$osinfo.oslanguage.tostring()]
            $osinfo | Add-Member -MemberType NoteProperty -Name "Characterset" -Value $characterset[$osinfo.codeset.tostring()]


            $htmlbody += $osinfo | ConvertTo-Html -Fragment
            $htmlbody += $spacer
        }
        catch
        {
            Write-Warning $_.Exception.Message
            $htmlbody += "<p>An error was encountered. $($_.Exception.Message)</p>"
            $htmlbody += $spacer
			$osinfo = @{}
        }


        #---------------------------------------------------------------------
        # Collect physical memory information and convert to HTML fragment
        #---------------------------------------------------------------------

        Write-Verbose "Collecting physical memory information"

        $subhead = "<h3>Physical Memory Information</h3>"
        $htmlbody += $subhead

        try
        {
            $memorybanks = @()
            $physicalmemoryinfo = @(Get-WmiObject Win32_PhysicalMemory -ComputerName $ComputerName -ErrorAction STOP |
                Select-Object DeviceLocator,Manufacturer,Speed,Capacity,Name)

            foreach ($bank in $physicalmemoryinfo)
            {
                $memObject = New-Object PSObject
				$memObject | Add-Member NoteProperty -Name "Name" -Value $bank.Name
                $memObject | Add-Member NoteProperty -Name "Device Locator" -Value $bank.DeviceLocator
                $memObject | Add-Member NoteProperty -Name "Manufacturer" -Value $bank.Manufacturer
                $memObject | Add-Member NoteProperty -Name "Speed" -Value $bank.Speed
                $memObject | Add-Member NoteProperty -Name "Capacity (GB)" -Value ("{0:F0}" -f $bank.Capacity/1GB)

                $memorybanks += $memObject
            }

            $htmlbody += $memorybanks | ConvertTo-Html -Fragment
            $htmlbody += $spacer
        }
        catch
        {
            Write-Warning $_.Exception.Message
            $htmlbody += "<p>An error was encountered. $($_.Exception.Message)</p>"
            $htmlbody += $spacer
        }


        #---------------------------------------------------------------------
        # Collect pagefile information and convert to HTML fragment
        #---------------------------------------------------------------------

        $subhead = "<h3>PageFile Information</h3>"
        $htmlbody += $subhead

        Write-Verbose "Collecting pagefile information"

        try
        {
            $pagefileinfo = Get-WmiObject Win32_PageFileUsage -ComputerName $ComputerName -ErrorAction STOP |
                Select-Object @{Name='Pagefile Name';Expression={$_.Name}},
                            @{Name='Allocated Size (Mb)';Expression={$_.AllocatedBaseSize}},
							@{Name='Install Date';Expression={
                                $installdate = [datetime]::ParseExact($_.InstallDate.SubString(0,8),"yyyyMMdd",$null);
                                $installdate.ToShortDateString()
                            }},
							PeakUsage

            $htmlbody += $pagefileinfo | ConvertTo-Html -Fragment
            $htmlbody += $spacer
        }
        catch
        {
            Write-Warning $_.Exception.Message
            $htmlbody += "<p>An error was encountered. $($_.Exception.Message)</p>"
            $htmlbody += $spacer
			$pagefileinfo = @{}
        }


        #---------------------------------------------------------------------
        # Collect BIOS information and convert to HTML fragment
        #---------------------------------------------------------------------

        $subhead = "<h3>BIOS Information</h3>"
        $htmlbody += $subhead

        Write-Verbose "Collecting BIOS information"

        try
        {
            $biosinfo = Get-WmiObject Win32_Bios -ComputerName $ComputerName -ErrorAction STOP |
                Select-Object Status,Version,Manufacturer,
                            @{Name='Release Date';Expression={
                                $releasedate = [datetime]::ParseExact($_.ReleaseDate.SubString(0,8),"yyyyMMdd",$null);
                                $releasedate.ToShortDateString()
                            }},
                            @{Name='Serial Number';Expression={$_.SerialNumber}},
							Name

            $htmlbody += $biosinfo | ConvertTo-Html -Fragment
            $htmlbody += $spacer
        }
        catch
        {
            Write-Warning $_.Exception.Message
            $htmlbody += "<p>An error was encountered. $($_.Exception.Message)</p>"
            $htmlbody += $spacer
			$biosinfo = @{}
        }


        #---------------------------------------------------------------------
        # Collect logical disk information and convert to HTML fragment
        #---------------------------------------------------------------------

        $subhead = "<h3>Logical Disk Information</h3>"
        $htmlbody += $subhead

        Write-Verbose "Collecting logical disk information"

        try
        {
            $diskinfo = Get-WmiObject Win32_LogicalDisk -ComputerName $ComputerName -ErrorAction STOP | 
                Select-Object DeviceID,FileSystem,VolumeName,
                @{Expression={$_.Size /1Gb -as [int]};Label="Total Size (GB)"},
                @{Expression={$_.Freespace / 1Gb -as [int]};Label="Free Space (GB)"}

            $htmlbody += $diskinfo | ConvertTo-Html -Fragment
            $htmlbody += $spacer
        }
        catch
        {
            Write-Warning $_.Exception.Message
            $htmlbody += "<p>An error was encountered. $($_.Exception.Message)</p>"
            $htmlbody += $spacer
			$diskinfo = @()
        }


        #---------------------------------------------------------------------
        # Collect volume information and convert to HTML fragment
        #---------------------------------------------------------------------

        $subhead = "<h3>Volume Information</h3>"
        $htmlbody += $subhead

        Write-Verbose "Collecting volume information"

        try
        {
            $volinfo = Get-WmiObject Win32_Volume -ComputerName $ComputerName -ErrorAction STOP | 
                Select-Object Label,Name,DeviceID,SystemVolume,
                @{Expression={$_.Capacity /1Gb -as [int]};Label="Total Size (GB)"},
                @{Expression={$_.Freespace / 1Gb -as [int]};Label="Free Space (GB)"},
				FileSystem,BootVolume,DriveType,SerialNumber

            $htmlbody += $volinfo | ConvertTo-Html -Fragment
            $htmlbody += $spacer
        }
        catch
        {
            Write-Warning $_.Exception.Message
            $htmlbody += "<p>An error was encountered. $($_.Exception.Message)</p>"
            $htmlbody += $spacer
			$volinfo = @()
        }


        #---------------------------------------------------------------------
        # Collect network interface information and convert to HTML fragment
        #---------------------------------------------------------------------    

        $subhead = "<h3>Network Interface Information</h3>"
        $htmlbody += $subhead

        Write-Verbose "Collecting network interface information"

        try
        {
            $nics = @()
			$ports = @()
            $nicinfo = @(Get-WmiObject Win32_NetworkAdapter -ComputerName $ComputerName -ErrorAction STOP | Where {$_.PhysicalAdapter} |
                Select-Object Name,AdapterType,MACAddress,PNPDeviceID,
                @{Name='ConnectionName';Expression={$_.NetConnectionID}},
                @{Name='Enabled';Expression={$_.NetEnabled}},
                @{Name='Speed';Expression={$_.Speed/1000000}},
                InterfaceIndex)

            $portinfo = @(Get-WmiObject Win32_NetworkAdapter -ComputerName $ComputerName -ErrorAction STOP |  Where {$_.Manufacturer -ne 'Microsoft' -and $_.PNPDeviceID -notlike 'ROOT\*' -and $_.PhysicalAdapter} |
                Select-Object Name)

            $nwinfo = Get-WmiObject Win32_NetworkAdapterConfiguration -ComputerName $ComputerName -ErrorAction STOP |
                Select-Object Description, DHCPServer,  
                @{Name='IpAddress';Expression={$_.IpAddress -join '; '}},  
                @{Name='IpSubnet';Expression={$_.IpSubnet -join '; '}},  
                @{Name='DefaultIPgateway';Expression={$_.DefaultIPgateway -join '; '}},  
                @{Name='DNSServerSearchOrder';Expression={$_.DNSServerSearchOrder -join '; '}}

            foreach ($nic in $nicinfo)
            {
                $nicObject = New-Object PSObject
                $nicObject | Add-Member NoteProperty -Name "Connection Name" -Value $nic.connectionname
                $nicObject | Add-Member NoteProperty -Name "Adapter Name" -Value $nic.Name
                $nicObject | Add-Member NoteProperty -Name "Adapter Type" -Value $nic.AdapterType
                $nicObject | Add-Member NoteProperty -Name "MAC" -Value $nic.MACAddress
                $nicObject | Add-Member NoteProperty -Name "Enabled" -Value $nic.Enabled
                $nicObject | Add-Member NoteProperty -Name "Speed (Mbps)" -Value $nic.Speed
				$nicObject | Add-Member NoteProperty -Name "PNPDeviceID" -Value $nic.PNPDeviceID
                $nicObject | Add-Member NoteProperty -Name "InterfaceIndex" -Value $nic.InterfaceIndex
        
                $ipaddress = ($nwinfo | Where {$_.Description -eq $nic.Name}).IpAddress
				$ipsubnet = ($nwinfo | Where {$_.Description -eq $nic.Name}).IpSubnet
				$defaultipgateway = ($nwinfo | Where {$_.Description -eq $nic.Name}).DefaultIPgateway
				$dnsserversearchorder = ($nwinfo | Where {$_.Description -eq $nic.Name}).DNSServerSearchOrder
                $nicObject | Add-Member NoteProperty -Name "IPAddress" -Value $ipaddress
				$nicObject | Add-Member NoteProperty -Name "IpSubnet" -Value $ipsubnet
				$nicObject | Add-Member NoteProperty -Name "DefaultIPgateway" -Value $defaultipgateway
				$nicObject | Add-Member NoteProperty -Name "DNSServerSearchOrder" -Value $dnsserversearchorder				

                $nics += $nicObject
				if($portinfo.Name -contains  $nic.Name){
				    $ports += $nicObject
				}
            }
			
            
            
            $htmlbody += $nics | ConvertTo-Html -Fragment
            $htmlbody += $spacer
        }
        catch
        {
            Write-Warning $_.Exception.Message
            $htmlbody += "<p>An error was encountered. $($_.Exception.Message)</p>"
            $htmlbody += $spacer
        }


        #---------------------------------------------------------------------
        # Collect software information and convert to HTML fragment
        #---------------------------------------------------------------------

        $subhead = "<h3>Software Information</h3>"
        $htmlbody += $subhead
 
        Write-Verbose "Collecting software information"
        
        try
        {
            $software = Get-WmiObject Win32_Product -ComputerName $ComputerName -ErrorAction STOP | Select-Object Vendor,Name,Version,IdentifyingNumber,InstallLocation,
			                    @{Name='Install Date';Expression={
                                $installdate = [datetime]::ParseExact($_.InstallDate.SubString(0,8),"yyyyMMdd",$null);
                                $installdate.ToShortDateString()}} | Sort-Object Vendor,Name

            $htmlbody += $software | ConvertTo-Html -Fragment
            $htmlbody += $spacer 
        
        }
        catch
        {
            Write-Warning $_.Exception.Message
            $htmlbody += "<p>An error was encountered. $($_.Exception.Message)</p>"
            $htmlbody += $spacer
			$software = @()
        }
       
        #---------------------------------------------------------------------
        # Collect cpu information and convert to HTML fragment
        #---------------------------------------------------------------------

        $subhead = "<h3>CPU Information</h3>"
        $htmlbody += $subhead

        Write-Verbose "Collecting cpu information"

        try
        {
            $cpuinfo = Get-WmiObject Win32_processor -ComputerName $ComputerName -ErrorAction STOP |
                Select-Object Name,Architecture,Manufacturer,NumberOfCores,NumberOfLogicalProcessors,
				@{Name='Max Speed (Mhz)';Expression={$_.MaxClockSpeed}},
				@{Name='Current Speed (Mhz)';Expression={$_.CurrentClockSpeed}}

            $htmlbody += $cpuinfo | ConvertTo-Html -Fragment
            $htmlbody += $spacer
        }
        catch
        {
            Write-Warning $_.Exception.Message
            $htmlbody += "<p>An error was encountered. $($_.Exception.Message)</p>"
            $htmlbody += $spacer
			$cpuinfo = @{}
        }

        #---------------------------------------------------------------------
        # Collect usergroup information and convert to HTML fragment
        #---------------------------------------------------------------------

        $subhead = "<h3>User Group Information</h3>"
        $htmlbody += $subhead

        Write-Verbose "Collecting user group information"

        try
        {
            $usergroupinfo =  Get-WmiObject Win32_groupuser  -ComputerName $ComputerName -ErrorAction STOP |select-object @{Name='UserName';Expression={($_.PartComponent -split "Name=")[1].replace('"','') }},@{Name='GroupName';Expression={($_.GroupComponent -split "Name=")[1].replace('"','') }}

            $htmlbody += $userinfo | ConvertTo-Html -Fragment
            $htmlbody += $spacer
        }
        catch
        {
            Write-Warning $_.Exception.Message
            $htmlbody += "<p>An error was encountered. $($_.Exception.Message)</p>"
            $htmlbody += $spacer
			$usergroupinfo = @()
        }

        #---------------------------------------------------------------------
        # Collect process information and convert to HTML fragment
        #---------------------------------------------------------------------

        $subhead = "<h3>process Information</h3>"
        $htmlbody += $subhead
 
        Write-Verbose "Collecting process information"
        
        try
        {
            $process = Get-WmiObject Win32_process -ComputerName $ComputerName -ErrorAction STOP | Select-Object Name,ParentProcessId,ProcessId,Path

            $htmlbody += $process | ConvertTo-Html -Fragment
            $htmlbody += $spacer 
        
        }
        catch
        {
            Write-Warning $_.Exception.Message
            $htmlbody += "<p>An error was encountered. $($_.Exception.Message)</p>"
            $htmlbody += $spacer
			$process = @()
        }
		
		#---------------------------------------------------------------------
        # Collect service information and convert to HTML fragment
        #---------------------------------------------------------------------

        $subhead = "<h3>service Information</h3>"
        $htmlbody += $subhead
 
        Write-Verbose "Collecting service information"
        
        try
        {
            $service = Get-WmiObject Win32_service -ComputerName $ComputerName -ErrorAction STOP | Select-Object Name,ProcessId,ExitCode,StartMode,State

            $htmlbody += $service | ConvertTo-Html -Fragment
            $htmlbody += $spacer 
        
        }
        catch
        {
            Write-Warning $_.Exception.Message
            $htmlbody += "<p>An error was encountered. $($_.Exception.Message)</p>"
            $htmlbody += $spacer
			$service = @()
        }
		
		#---------------------------------------------------------------------
        # Collect environmentvariable information and convert to HTML fragment
        #---------------------------------------------------------------------

        $subhead = "<h3>environmentvariable Information</h3>"
        $htmlbody += $subhead
 
        Write-Verbose "Collecting environmentvariable information"
        
        try
        {
            $environmentvariable = Get-WmiObject Win32_Environment -ComputerName $ComputerName -ErrorAction STOP | Select-Object Name, VariableValue

            $htmlbody += $environmentvariable | ConvertTo-Html -Fragment
            $htmlbody += $spacer 
        
        }
        catch
        {
            Write-Warning $_.Exception.Message
            $htmlbody += "<p>An error was encountered. $($_.Exception.Message)</p>"
            $htmlbody += $spacer
			$environmentvariable = @()
        }
		
		#---------------------------------------------------------------------
        # Collect route information and convert to HTML fragment
        #---------------------------------------------------------------------

        $subhead = "<h3>route Information</h3>"
        $htmlbody += $subhead
 
        Write-Verbose "Collecting route information"
        
        try
        {
            $route =  Get-WmiObject Win32_IP4RouteTable -ComputerName $ComputerName -ErrorAction STOP | select-object Destination,Mask,NextHop,InterfaceIndex

            $htmlbody += $route | ConvertTo-Html -Fragment
            $htmlbody += $spacer 
        
        }
        catch
        {
            Write-Warning $_.Exception.Message
            $htmlbody += "<p>An error was encountered. $($_.Exception.Message)</p>"
            $htmlbody += $spacer
			$route = @()
        }

        #---------------------------------------------------------------------
        # Collect loggedon user information and convert to HTML fragment
        #---------------------------------------------------------------------

        $subhead = "<h3>loggedon user Information</h3>"
        $htmlbody += $subhead
 
        Write-Verbose "Collecting logon user information"
        
        try
        {
            $regexa = '.+Domain="(.+)",Name="(.+)"$' 
            $regexd = '.+LogonId="(\d+)"$' 
 
            $logontype = @{ 
                "0"="Local System" 
                "2"="Interactive" #(Local logon) 
                "3"="Network" # (Remote logon) 
                "4"="Batch" # (Scheduled task) 
                "5"="Service" # (Service account logon) 
                "7"="Unlock" #(Screen saver) 
                "8"="NetworkCleartext" # (Cleartext network logon) 
                "9"="NewCredentials" #(RunAs using alternate credentials) 
                "10"="RemoteInteractive" #(RDP\TS\RemoteAssistance) 
                "11"="CachedInteractive" #(Local w\cached credentials) 
            } 
 
            $logon_sessions = Get-WmiObject win32_logonsession -ComputerName $ComputerName
            $logon_users = Get-WmiObject win32_loggedonuser -ComputerName $ComputerName
 
            $session_user = @{} 
 
            $logon_users |% { 
                $_.antecedent -match $regexa > $nul 
                $username = $matches[1] + "\" + $matches[2] 
                $_.dependent -match $regexd > $nul 
                $session = $matches[1] 
                $session_user[$session] += $username 
            } 
 
 
            $loggedonusers = @()
            foreach ($session in $logon_sessions)
			{
                $session |%{ 
                     $starttime = [management.managementdatetimeconverter]::todatetime($_.starttime) 
                     #$starttime = [System.DateTime]::ParseExact($_.starttime.split(".")[0],'yyyyMMddHHmmss',$null)

                     $loggedonuser = New-Object -TypeName psobject 
                     $loggedonuser | Add-Member -MemberType NoteProperty -Name "Session" -Value $_.logonid 
                     $loggedonuser | Add-Member -MemberType NoteProperty -Name "User" -Value $session_user[$_.logonid] 
                     $loggedonuser | Add-Member -MemberType NoteProperty -Name "Type" -Value $logontype[$_.logontype.tostring()] 
                     $loggedonuser | Add-Member -MemberType NoteProperty -Name "Auth" -Value $_.authenticationpackage 
                     $loggedonuser | Add-Member -MemberType NoteProperty -Name "StartTime" -Value $starttime.ToString()
				$loggedonusers += $loggedonuser
                }
            }
        }
        catch
        {
            Write-Warning $_.Exception.Message
            $htmlbody += "<p>An error was encountered. $($_.Exception.Message)</p>"
            $htmlbody += $spacer
			$loggedonusers = @{}
        }

        #---------------------------------------------------------------------
        # Collect eventlog information and convert to HTML fragment
        #---------------------------------------------------------------------

        $subhead = "<h3>eventlog Information</h3>"
        $htmlbody += $subhead
 
        Write-Verbose "Collecting eventlog information"
        
        try
        {
            $eventlog =  Get-WmiObject Win32_NTEventlogFile -ComputerName $ComputerName -ErrorAction STOP | Select-Object LogfileName,NumberOfRecords,
                @{Name='Logfilepath';Expression={$_.Name}},
                @{Name='FileSize';Expression={$_.FileSize/1024}}

            $htmlbody += $eventlog | ConvertTo-Html -Fragment
            $htmlbody += $spacer 
        }
        catch
        {
            Write-Warning $_.Exception.Message
            $htmlbody += "<p>An error was encountered. $($_.Exception.Message)</p>"
            $htmlbody += $spacer
			$eventlog = @()
        }


        #---------------------------------------------------------------------
        # Collect ntp information and convert to HTML fragment
        #---------------------------------------------------------------------

        $subhead = "<h3>ntp Information</h3>"
        $htmlbody += $subhead
 
        Write-Verbose "Collecting ntp information"
        
        try
        {
            $namespace = "root\Default"
            $HKLM = "&H80000002"
            $strKeyPath='SYSTEM\CurrentControlSet\Services\W32Time\Parameters'
            $oreg = get-wmiobject -list -namespace $namespace -ComputerName $ComputerName -ErrorAction STOP| where-object { $_.name -eq "StdRegProv" }
            $ntpserver = $oreg.GetStringValue($HKLM, $strKeyPath, 'NtpServer')
            
            $strKeyPath='SYSTEM\CurrentControlSet\Services\W32Time\Parameters'
            $type = $oreg.GetStringValue($HKLM, $strKeyPath, 'Type')
            
            $strKeyPath='SYSTEM\CurrentControlSet\Services\W32Time\TimeProviders\NtpServer'
            $enabled = $oreg.GetDWORDValue($HKLM, $strKeyPath, 'Enabled')

            $strKeyPath='SYSTEM\CurrentControlSet\Services\W32Time\Config'
            $AnnounceFlags = $oreg.GetDWORDValue($HKLM, $strKeyPath, 'AnnounceFlags')
            
            $ntp = New-Object -TypeName psobject 
            $ntp | Add-Member -MemberType NoteProperty -Name "Ntpserver" -Value $ntpserver.svalue 
            $ntp | Add-Member -MemberType NoteProperty -Name "Type" -Value $type.svalue 
            $ntp | Add-Member -MemberType NoteProperty -Name "Enabled" -Value $enabled.uvalue 
            $ntp | Add-Member -MemberType NoteProperty -Name "AnnounceFlags" -Value $AnnounceFlags.uvalue

            foreach ($eachservice in $service)
            {
                $w32timeservice = ''
                if($eachservice.name -eq 'W32Time' ){$w32timeservice = $eachservice.State;break}
            }
            $ntp | Add-Member -MemberType NoteProperty -Name "W32timeservice" -Value $w32timeservice 
            $htmlbody += $ntp | ConvertTo-Html -Fragment
            $htmlbody += $spacer 
        }
        catch
        {
            Write-Warning $_.Exception.Message
            $htmlbody += "<p>An error was encountered. $($_.Exception.Message)</p>"
            $htmlbody += $spacer
			$ntp = @{}
        }


        #---------------------------------------------------------------------
        # Collect snmp information and convert to HTML fragment
        #---------------------------------------------------------------------

        $subhead = "<h3>snmp Information</h3>"
        $htmlbody += $subhead
 
        Write-Verbose "Collecting snmp information"
        
        try
        {
            $snmp = New-Object -TypeName psobject 

            $State = ''
            $StartMode = ''
            $ProcessId = ''
            $ExitCode = ''
            foreach ($eachservice in $service)
            {
                $snmpservice = ''
                if($eachservice.name -eq 'SNMP' ){
                    $State = $eachservice.State
                    $StartMode = $eachservice.StartMode
                    $ProcessId = $eachservice.ProcessId
                    $ExitCode = $eachservice.ExitCode
                    break}
            }
            $snmp | Add-Member -MemberType NoteProperty -Name "State" -Value $State
            $snmp | Add-Member -MemberType NoteProperty -Name "StartMode" -Value $StartMode
            $snmp | Add-Member -MemberType NoteProperty -Name "ProcessId" -Value $ProcessId
            $snmp | Add-Member -MemberType NoteProperty -Name "ExitCode" -Value $ExitCode 


            $htmlbody += $snmp | ConvertTo-Html -Fragment
            $htmlbody += $spacer 
        }
        catch
        {
            Write-Warning $_.Exception.Message
            $htmlbody += "<p>An error was encountered. $($_.Exception.Message)</p>"
            $htmlbody += $spacer
			$snmp = @{}
        }

        #---------------------------------------------------------------------
        # Collect ProcessHandleQuota information and convert to HTML fragment
        #---------------------------------------------------------------------

        $subhead = "<h3>ProcessHandleQuota Information</h3>"
        $htmlbody += $subhead
 
        Write-Verbose "Collecting ProcessHandleQuota information"
        
        try
        {
            $namespace = "root\Default"
            $HKLM = "&H80000002"
            $strKeyPath = 'SOFTWARE\Microsoft\Windows NT\CurrentVersion\Windows'
            $oreg = get-wmiobject -list -namespace $namespace -ComputerName $ComputerName -ErrorAction STOP| where-object { $_.name -eq "StdRegProv" }
            
            $GDIProcessHandleQuota = $oreg.GetDWORDValue($HKLM, $strKeyPath, 'GDIProcessHandleQuota')
            $USERProcessHandleQuota = $oreg.GetDWORDValue($HKLM, $strKeyPath, 'USERProcessHandleQuota')
            
            
            $ProcessHandleQuota = New-Object -TypeName psobject 
            $ProcessHandleQuota | Add-Member -MemberType NoteProperty -Name "GDIProcessHandleQuota" -Value $GDIProcessHandleQuota.uvalue 
            $ProcessHandleQuota | Add-Member -MemberType NoteProperty -Name "USERProcessHandleQuota" -Value $USERProcessHandleQuota.uvalue 


            $htmlbody += $ProcessHandleQuota | ConvertTo-Html -Fragment
            $htmlbody += $spacer 
        }
        catch
        {
            Write-Warning $_.Exception.Message
            $htmlbody += "<p>An error was encountered. $($_.Exception.Message)</p>"
            $htmlbody += $spacer
			$ProcessHandleQuota = @{}
        }

        #---------------------------------------------------------------------
        # Collect firewall status and convert to HTML fragment
        #---------------------------------------------------------------------

        $subhead = "<h3>firewall status Information</h3>"
        $htmlbody += $subhead
 
        Write-Verbose "Collecting firewall status information"
        
        try
        {
            $namespace = "root\Default"
            $HKLM = "&H80000002"
            $strKeyPath = 'SYSTEM\CurrentControlSet\Services\SharedAccess\Parameters\FirewallPolicy\StandardProfile'
            $oreg = get-wmiobject -list -namespace $namespace -ComputerName $ComputerName -ErrorAction STOP| where-object { $_.name -eq "StdRegProv" }
            
            $EnableFirewall = $oreg.GetDWORDValue($HKLM, $strKeyPath, 'EnableFirewall')
                  
            $Firewallstatus = New-Object -TypeName psobject 
            $Firewallstatus | Add-Member -MemberType NoteProperty -Name "EnableFirewall" -Value $EnableFirewall.uvalue  

            $htmlbody += $Firewallstatus | ConvertTo-Html -Fragment
            $htmlbody += $spacer 
        }
        catch
        {
            Write-Warning $_.Exception.Message
            $htmlbody += "<p>An error was encountered. $($_.Exception.Message)</p>"
            $htmlbody += $spacer
			$Firewallstatus = @{}
        }

        #---------------------------------------------------------------------
        # Collect firewall rules and convert to HTML fragment
        #---------------------------------------------------------------------

        $subhead = "<h3>firewall rules Information</h3>"
        $htmlbody += $subhead
 
        Write-Verbose "Collecting firewall rules information"
        
        try
        {
            $Firewallrules = @()
            $namespace = "root\Default"
            $HKLM = "&H80000002"
            $strKeyPath = 'SYSTEM\CurrentControlSet\Services\SharedAccess\Parameters\FirewallPolicy\FirewallRules'
            $oreg = get-wmiobject -list -namespace $namespace -ComputerName $ComputerName -ErrorAction STOP| where-object { $_.name -eq "StdRegProv" }
            
            
            foreach ($ruleuname in $oreg.EnumValues($HKLM, $strKeyPath).sNames)
            {
                $rule = New-Object -TypeName psobject
                $getrule = $oreg.GetStringValue($HKLM, $strKeyPath,$ruleuname).sValue.split("|")
                $getrulestring = $oreg.GetStringValue($HKLM, $strKeyPath,$ruleuname).sValue
                
                if($getrulestring -match 'Action' ){             
                    $rule | Add-Member NoteProperty -Name "Action" -Value ($getrule -match 'Action').split('=')[1]
                }
                else{
                    $rule | Add-Member NoteProperty -Name "Action" -Value ''
                }
                if($getrulestring -match 'Active' ){
                    $rule | Add-Member NoteProperty -Name "Active" -Value ($getrule -match 'Active').split('=')[1]
                }
                else{
                    $rule | Add-Member NoteProperty -Name "Active" -Value ''
                }
                if($getrulestring -match 'Dir' ){
                    $rule | Add-Member NoteProperty -Name "Dir" -Value ($getrule -match 'Dir').split('=')[1]
                }
                else{
                    $rule | Add-Member NoteProperty -Name "Dir" -Value ''
                }
                if($getrulestring -match 'Protocol' ){
                    $rule | Add-Member NoteProperty -Name "Protocol" -Value ($getrule -match 'Protocol').split('=')[1]
                }
                else{
                    $rule | Add-Member NoteProperty -Name "Protocol" -Value ''
                }
                if($getrulestring -match 'LPort' ){
                    $rule | Add-Member NoteProperty -Name "LPort" -Value ($getrule -match 'LPort').split('=')[1]
				}
                else{
                    $rule | Add-Member NoteProperty -Name "LPort" -Value ''
                }
                if($getrulestring -match 'App' ){
                    $rule | Add-Member NoteProperty -Name "App" -Value ($getrule -match 'App').split('=')[1]
                }
                else{
                    $rule | Add-Member NoteProperty -Name "App" -Value ''
                }
                if($getrulestring -match 'Svc' ){
                    $rule | Add-Member NoteProperty -Name "Svc" -Value ($getrule -match 'Svc').split('=')[1]
                }
                else{
                    $rule | Add-Member NoteProperty -Name "Svc" -Value ''
                }
                if($getrulestring -match 'Name' ){
                    $rule | Add-Member NoteProperty -Name "Name" -Value ($getrule -match 'Name').split('=')[1]
                }
                else{
                    $rule | Add-Member NoteProperty -Name "Name" -Value ''
                }
                if($getrulestring -match 'Desc' ){
                    $rule | Add-Member NoteProperty -Name "Desc" -Value ($getrule -match 'Desc').split('=')[1]
                }
                else{
                    $rule | Add-Member NoteProperty -Name "Desc" -Value ''
                }
                if($getrulestring -match 'EmbedCtxt' ){
                    $rule | Add-Member NoteProperty -Name "EmbedCtxt" -Value ($getrule -match 'EmbedCtxt').split('=')[1]
                }
                else{
                    $rule | Add-Member NoteProperty -Name "EmbedCtxt" -Value ''
                }
                $Firewallrules += $rule
            }
            

            $htmlbody += $Firewallrules | ConvertTo-Html -Fragment
            $htmlbody += $spacer 
        }
        catch
        {
            Write-host $_.Exception.Message
            $htmlbody += "<p>An error was encountered. $($_.Exception.Message)</p>"
            $htmlbody += $spacer
			$Firewallrules = @{}
        }
        #---------------------------------------------------------------------
        # Generate the HTML report and output to file
        #---------------------------------------------------------------------
	
        Write-Verbose "Producing HTML report"
    
        $reportime = Get-Date

        #Common HTML head and styles
	    $htmlhead="<html>
				    <style>
				    BODY{font-family: Arial; font-size: 8pt;}
				    H1{font-size: 20px;}
				    H2{font-size: 18px;}
				    H3{font-size: 16px;}
				    TABLE{border: 1px solid black; border-collapse: collapse; font-size: 8pt;}
				    TH{border: 1px solid black; background: #dddddd; padding: 5px; color: #000000;}
				    TD{border: 1px solid black; padding: 5px; }
				    td.pass{background: #7FFF00;}
				    td.warn{background: #FFE600;}
				    td.fail{background: #FF0000; color: #ffffff;}
				    td.info{background: #85D4FF;}
				    </style>
				    <body>
				    <h1 align=""center"">Server Info: $ComputerName</h1>
				    <h3 align=""center"">Generated: $reportime</h3>"

        $htmltail = "</body>
			    </html>"

        $jsonbody = @{SystemInformation=$csinfo;
		              OperatingSystemInformation=$osinfo;
					  PageFileInformation=$pagefileinfo;
			          PhysicalMemoryInformation=$memorybanks;
			          BIOSInformation=$biosinfo;
			          LogicalDiskInformation=$diskinfo;
			          VolumeInformation=$volinfo;
			          NetworkInterfaceInformation=$nics;
					  PortInformation=$ports;
					  CpuInformation=$cpuinfo;
					  UserGroupInformation=$usergroupinfo;
			          SoftwareInformation=$software;
					  ProcessInformation=$process;
					  ServiceInformation=$service;
					  EnvironmentVariable=$environmentvariable;
					  Route=$route;
                      Loggedonuser=$loggedonusers;
                      Eventlog=$eventlog;
                      Ntp=$ntp;
                      Snmp=$snmp;
                      ProcessHandleQuota=$ProcessHandleQuota;
                      Firewallrules=$Firewallrules;
                      Firewallstatus=$Firewallstatus
					  }

        #$jsonbody | ConvertTo-Json | Out-File windowsinfo.json -Encoding Utf8
		
		$jsonbodynew = $jsonbody | select $jsonbody.Columns.ColumnName|ConvertTo-Json
        Write-Host $jsonbodynew
        Write-Host "end collect"


        $htmlreport = $htmlhead + $htmlbody + $htmltail

        $htmlreport | Out-File $htmlfile -Encoding Utf8
    }

}

End
{
    #Wrap it up
    Write-Verbose "=====> Finished <====="
}