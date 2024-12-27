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
    [string[]]$ComputerName,
    [string[]]$user,
    [string[]]$password

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
    Write-Host "start test"

	#---------------------------------------------------------------------
    # credential
    #---------------------------------------------------------------------
    $pwd = $password | ConvertTo-SecureString  -AsPlainText -Force
	$c = New-Object System.Management.Automation.PSCredential($user,$pwd)
	
    #---------------------------------------------------------------------
    # Do 10 pings and calculate the fastest response time
    # Not using the response time in the report yet so it might be
    # removed later.
    #---------------------------------------------------------------------
    
    try
    {
        $bestping = (Test-Connection -ComputerName $ComputerName -Count 3 -ErrorAction STOP | Sort ResponseTime)[0].ResponseTime
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
            $csinfo = Get-WmiObject Win32_ComputerSystem -ComputerName $ComputerName -ErrorAction STOP -Credential $c|
                Select-Object Name
            Write-Host "test success"
        }
        catch
        {
			Write-Host "Unable to connect to $ComputerName"
        }

        
    }

}

End
{
    #Wrap it up
    Write-Host "finish test"
}
