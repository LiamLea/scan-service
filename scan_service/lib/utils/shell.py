from scan_service.lib.utils import MyList
from scan_service.lib.vars import global_var
import re
import subprocess
from scan_service.lib.framework import BusinessException
import socket
from scan_service.lib.framework import logger

class SHELL:

    def __init__(self, ssh = "", passwd = "", local = False):
        # self.local是一个开关，用于控制是远程shell还是本地shell
        self.local = local
        self.ssh = ssh
        self.sudo_passwd = passwd
        self.comment_pattern = re.compile(r"^\s*#")

    def exec_shell(self, command, get_error=False, get_comments = False, timeout = 30, get_dict = False):

        if self.local:

            result = subprocess.run(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if get_error:
                ret = [i for i in result.stderr.decode().split('\n') if i != '']
                return ret
            else:
                ret = [i for i in result.stdout.decode().split('\n') if i != '']
                return ret

        else:

            """
            封装执行shell命令的方法，实现了下面的功能：
                1.从位置参数获取ssh信息，建立ssh连接
                2.如果用户有sudo权限，执行命令时就会使用sudo功能
                3.以列表的形式返回执行结果

            :param command: <STRING>
                            需要执行的命令

            :param get_error: <BOOLEAN>
                            默认False，获取的是标准输出
                            True，获取的是标准

            :return: <LIST>
            """
            ssh = self.ssh
            sudo_passwd = self.sudo_passwd
            sudo_shell = self.ssh.sudo_shell

            try:
                if ssh.sudo == True:

                    command = "sudo -S -p '' %s -c 'source /etc/profile &>/dev/null;export LANG=en_US.UTF-8;%s'" % (sudo_shell, command.replace("'", "'\\''"))
                    result = ssh.exec_command(command, timeout = timeout)

                    result[0].write('%s\n' % sudo_passwd)
                    result[0].flush()

                else:
                    command = "source /etc/profile &>/dev/null;" + command
                    result = ssh.exec_command(command, timeout = timeout, environment = {"LANG": "en_US.UTF-8"})

                if get_dict:
                    ret = {
                        "return_code": result[1].channel.recv_exit_status(),
                        "stdout": result[1].read().decode(),
                        "stderr": result[2].read().decode()
                    }
                    return ret

                if get_error:
                    ret = [i for i in result[2].read().decode().split('\n') if i.strip() != '']
                else:
                    ret = [i for i in result[1].read().decode().split('\n') if i.strip() != '']

            except socket.timeout:
                ret = []
                logger.error("host：%s，shell命令执行超时：%s" %(self.ssh.host, command))

            except Exception:
                ret = []
                logger.error("host：%s，shell命令执行失败：%s" % (self.ssh.host, command))
                # raise BusinessException("shell命令执行失败：%s" %command)

            if not get_comments:
                ret = [ i for i in ret if not self.comment_pattern.search(i) ]

            if get_dict:
                return {}
            return MyList(ret)

    def get_file_content(self, filename, type = "", comments = "#", timeout = 30):
        """
        封装执行shell命令的方法，实现了下面的功能：
            1.从位置参数获取ssh信息，建立ssh连接
            2.通过cat命令获取文本内容
            3.以字符串的形式返回文本内容

        :param command: <STRING>

        :return: <LIST>
        """
        ssh = self.ssh
        sudo_passwd = self.sudo_passwd

        # 用于过滤注释行和空行
        if type == "xml":
            pattern = "<!--[\s\S]*?-->(\s*)?|(?:^|\n)\s*(?=\n)"
        else:
            pattern = r"(?:^|\n)(\s*[%s].*|\s*)(?=\n)" %comments

        try:
            if ssh.sudo == True:
                command = "sudo -S -p '' -i cat %s" % filename
                result = ssh.exec_command(command, timeout = timeout, environment = {"LANG": "en_US.UTF-8"})
                result[0].write('%s\n' % sudo_passwd)
                result[0].flush()

            else:
                result = ssh.exec_command("cat %s" % filename, timeout = timeout, environment = {"LANG": "en_US.UTF-8"})

            ret = re.sub(pattern, "", result[1].read().decode())

        except socket.timeout:
            logger.error("host：%s，读取文件超时：%s" % (self.ssh.ssh_client._transport.sock.getpeername()[0], filename))

        except Exception:
            logger.error("host：%s，读取文件内容失败：%s" % (self.ssh.ssh_client._transport.sock.getpeername()[0], filename))
            # raise BusinessException("读取文件内容失败：%s" %filename)

        return ret

    def check_file_attribute(self, filename, attribute):
        result = self.exec_shell("[ -%s %s ] && echo 1 || echo 0" % (attribute, filename))
        if result[0] == "1":
            return True
        else:
            return False

    def find_file(self, dir, pattern):
        result = self.exec_shell('find %s -regextype posix-extended -regex  "%s"' % (dir, pattern))
        return result

    def get_local_ip(self):
        """
        不采集 虚拟接口和down 的ip地址
        """
        command = r'echo "";for i in `ls /sys/class/net | grep -v lo`;do path=`readlink "/sys/class/net/$i"`;if ! echo $path | grep -q virtual && ! cat /sys/class/net/$i/operstate | grep -q down;then ip addr show $i;fi;done'
        result = ' '.join(self.exec_shell(command))

        pattern = r"inet\s+(%s)" %global_var.ip_pattern
        local_ip = [item.group(1) for item in list(re.finditer(pattern, result)) if not global_var.except_ip_match.search(item.group(1))]

        return list(set(local_ip))

    def get_ip_from_hostname(self, hostname):
        """
        解析域名，获取ip列表
        先用getent命令获取
        如果获取不到，用ping命令获取
        如果依然获取不到，则返回域名
        """
        ret = []

        #如果hostname本身就是ip地址，则直接返回一个列表
        if global_var.ip_match.search(hostname):
            return [hostname]

        result = self.exec_shell("getent ahostsv4 %s" %hostname)
        for line in result:
            ret.append(line.split()[0])

        if not ret:
            result = self.exec_shell("ping -c 1 %s" %hostname)
            ip = re.search(global_var.ip_pattern, ''.join(result))
            if ip:
                ret.append(ip.group())
            else:
                ret.append(hostname)

        return list(set(ret))