# Scan Service


<!-- @import "[TOC]" {cmd="toc" depthFrom=1 depthTo=6 orderedList=false} -->

<!-- code_chunk_output -->

- [Scan Service](#scan-service)
    - [依赖的python模块](#依赖的python模块)
    - [使用的mibs库](#使用的mibs库)
    - [使用的oid](#使用的oid)
      - [1.交换机](#1交换机)
    - [脚本说明](#脚本说明)
    - [文件信息说明](#文件信息说明)
    - [系统命令说明](#系统命令说明)
    - [已测试的操作系统版本](#已测试的操作系统版本)
    - [已测试的软件版本](#已测试的软件版本)

<!-- /code_chunk_output -->

### 依赖的python模块
* subprocess32
* xmltodict
* kafka-python
* paramiko
* pymysql
* flask
* easysnmp
* pyyaml

### 使用的mibs库
* 地址：[librenms](https://github.com/librenms/librenms/tree/master/mibs)
  * 需要保留的mibs库
    * cisco/CISCO-PRODUCTS-MIB
    * cisco/CISCO-SMI
    * cisco/CISCO-DOCS-EXT-MIB
    * cisco/CISCO-VTP-MIB
    * cisco/cisco/CISCO-STACK-MIB
    * cisco/CISCO-ENVMON-MIB
  * 需要添加的mibs库
    * [h3c/hh3c-splat-vlan.mib、h3c/hh3c-splat-inf.mib](https://github.com/netdisco/netdisco-mibs)
```shell
$vim /etc/snmp/snmp.conf

mibdirs +/usr/share/snmp/mibs/huawei:/usr/share/snmp/mibs/cisco
mibreplacewithlatest yes
mibs ALL
```

### 使用的oid

#### 1.交换机

* 基础信息

|指标|通用oid|h3c|huawei|cisco|dptech|
|-|-|-|-|-|-|
|设备型号|1.3.6.1.2.1.47.1.1.1.1.13|
|设备序列号|1.3.6.1.2.1.47.1.1.1.1.11|
|端口数量|1.3.6.1.2.1.2.1|
|启动时间|1.3.6.1.2.1.1.3|
|主机名|1.3.6.1.2.1.1.5|
|底座mac地址|1.0.8802.1.1.2.1.3.2|
|ip信息|1.3.6.1.2.1.4.20.1|

* 系统信息

|指标|通用oid|h3c|huawei|cisco|dptech|
|-|-|-|-|-|-|
|系统信息（内存等）||1.3.6.1.4.1.25506.8.35.18.1|1.3.6.1.4.1.2011.6.3.5.1.1|1.3.6.1.4.1.9.9.48.1.1.1|1.3.6.1.4.1.31648.3|

* 接口信息

|指标|通用oid|h3c|huawei|cisco|dptech|
|-|-|-|-|-|-|
|接口基本信息|1.3.6.1.2.1.2.2.1|
|接口流量信息|1.3.6.1.2.1.31.1.1.1|
|接口与端口的映射|1.3.6.1.2.1.17.1.4.1.2|

* mac表信息

|指标|通用oid（有多个时，只要满足其中一个）|h3c|huawei|cisco|dptech|
|-|-|-|-|-|-|
|mac地址|1.3.6.1.2.1.17.4.3.1.2</br>1.3.6.1.2.1.17.7.1.2.2.1.2|
|mac地址状态|1.3.6.1.2.1.17.4.3.1.3</br>1.3.6.1.2.1.17.7.1.2.2.1.3|

* arp表信息

|指标|通用oid|h3c|huawei|cisco|dptech|
|-|-|-|-|-|-|
|arp信息|1.3.6.1.2.1.3.1.1|

* vlan信息

|指标|通用oid|h3c|huawei|cisco|dptech|
|-|-|-|-|-|-|
|vlan信息||1.3.6.1.4.1.25506.8.35.2.1.1.1|1.3.6.1.4.1.2011.5.25.42.3.1.1.1.1|1.3.6.1.4.1.9.9.46.1.3.1.1|
|获取vlan接口信息||1.3.6.1.4.1.25506.8.35.2.1.2.1.9|1.3.6.1.4.1.2011.5.25.42.3.1.1.1.1.6|1.3.6.1.4.1.9.9.46.1.3.1.1.18|
|获取vlan ip信息||1.3.6.1.4.1.25506.8.35.2.1.5.1|1.3.6.1.2.1.4.20.1|1.3.6.1.2.1.4.20.1|
|获取vlan portlist信息||1.3.6.1.4.1.25506.8.35.2.1.1.1.19|1.3.6.1.2.1.17.7.1.4.2.1.4|1.3.6.1.4.1.9.5.1.9.3.1.3|

* 路由表信息

|指标|通用oid|h3c|huawei|cisco|dptech|
|-|-|-|-|-|-|
|判断是否开启路由|1.3.6.1.2.1.4.1|
|获取路由信息|1.3.6.1.2.1.4.24|

* 获取相邻节点信息

|指标|通用oid|h3c|huawei|cisco|dptech|
|-|-|-|-|-|-|
|获取lldp信息|1.0.8802.1.1.2.1.4.1.1|

* 硬件信息

|指标|通用oid|h3c|huawei|cisco|dptech|
|-|-|-|-|-|-|
|风扇信息||1.3.6.1.4.1.25506.8.35.9.1.1.1.2|1.3.6.1.4.1.2011.5.25.31.1.1.10.1|1.3.6.1.4.1.9.9.13.1.4.1.3|1.3.6.1.4.1.31648.3.15.12.1.3|
|电源信息||1.3.6.1.4.1.25506.8.35.9.1.2.1.2|1.3.6.1.4.1.2011.5.25.31.1.1.18.1|1.3.6.1.4.1.9.9.13.1.5.1.3|1.3.6.1.4.1.31648.3.15.11.1.3|
|物理端口|1.3.6.1.2.1.17.1.4.1.1|

### 脚本说明
|采集对象|采集内容|采集手段|访问路径|读写方式|
|-|-|-|-|-|
|OS|环境信息|ssh脚本|/etc/</br>/proc/</br>/sys/</br>相关系统命令|只读|
|weblogic|安装信息和配置信息|ssh脚本|weblogic安装路径|只读|
|oracle|安装信息和配置信息|ssh脚本|oracle安装路径|只读|
|nginx|安装信息和配置信息|ssh脚本|nginx安装路径|只读|
|apache|安装信息和配置信息|ssh脚本|apache安装路径|只读|
|mysql|安装信息和配置信息|ssh脚本|mysql安装路径|只读|
|postgresql|安装信息和配置信息|ssh脚本|postgresql安装路径|只读|
|ESXi|ESXi系统信息|ssh脚本|esxicli命令|只读|
|交换机|交换机信息|snmp|oid|只读|
|F5|环境信息和配置信息|snmp|oid|只读|

### 文件信息说明
|目录|说明|
|-|-|
|/etc/|获取相关软件的配置信息|
|/proc/|获取进程详细信息和内核参数信息|
|/sys/|获取相关硬件信息|
|相关软件的安装目录|软件：nginx、apache、mysql、oracle、pg等|

### 系统命令说明
|命令|说明|
|-|-|
|rpm/dpkg|获取软件安装情况|
|date|获取当前时区|
|ntpq|获取时间服务器信息|
|ps|获取进程信息|
|ss|获取套接字信息|
|ip、hostname|获取网络信息|
|dmidecode|获取硬件信息|
|sysctl|获取内核参数|
|lsmod|获取加载的模块|
|yum/apt-get|获取软件仓库信息|
|lscpu|获取cpu信息|
|systemctl|获取守护进程信息|
|df|获取文件系统信息|
|lvs、vgs、pvs|获取逻辑卷信息|
|firwall-cmd|获取防火墙信息|
|who、lastlog|获取登录信息|
|selinux|获取selinux信息|
|jps、jinfo、jmap、jstat|获取JVM信息|

### 已测试的操作系统版本
|操作系统类型|版本号|说明|
|-|-|-|
|cenots|7</br>6.8||
|Ubuntu|18.04.2 LTS||
|ESXi|6.5.0</br>5.5.0||

### 已测试的软件版本
|软件名称|软件版本|说明|
|-|-|-|
|oracle|12c</br>11g||
|weblogic|12.2.1.4.0||
|nginx|1.16.1||
|httpd|2.4.6||
|mysql|5.6.46||
