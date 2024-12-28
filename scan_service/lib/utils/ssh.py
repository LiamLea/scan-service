import paramiko
from paramiko.ssh_exception import SSHException, AuthenticationException, NoValidConnectionsError
from scan_service.lib.framework import BusinessException
from scan_service.lib.framework import AuthException
import socket
import traceback

class SSH:

    def __init__(self, host, port, user, passwd, request_sudo = True):

        self.host = host
        self.port = port
        self.user = user
        self.passwd = passwd

        #建立ssh连接
        self.ssh_client = paramiko.SSHClient()
        self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        self.retries = 0

        while True:
            try:
                self.ssh_client.connect(hostname = self.host, port = self.port, username = self.user, password = self.passwd, look_for_keys = False, timeout = 30)
            except AuthenticationException:
                raise AuthException("ssh认证失败")
            except NoValidConnectionsError:
                raise AuthException("ssh连接失败，请检查ip或port是否有效")
            #当到目标机开启了防火墙（包被丢弃）时，就会出现socket timeout异常
            except socket.timeout:
                raise BusinessException("ssh tcp连接超时（30s），请检查网络是否可达")
            #SSHException包括banner timeout，authn timeout等
            except SSHException:
                if self.retries > 10:
                    raise BusinessException("ssh连接异常，请检查凭证、网络状况和目标机器sshd服务")
                self.ssh_client.close()
                self.retries += 1
            except Exception:
                raise BusinessException("无法建立ssh连接")
            else:
                break

        if request_sudo:
            #判断用户是否有sudo权限
            self.sudo = self.check_sudo(passwd)

            self.sudo_shell = self.check_shell()
        else:
            self.sudo = False
            self.sudo_shell = "/bin/bash"

    def exec_command(self, command, **kwargs):
        times = 0
        while True:
            try:
                result = self.ssh_client.exec_command(command, **kwargs)
            except EOFError:
                pass
            except SSHException:
                #这里要先close，否则会造成连接泄露
                self.ssh_client.close()
                self.ssh_client.connect(hostname=self.host, port=self.port, username=self.user, password=self.passwd)
            else:
                return result

            times += 1
            if times > 10:
                raise BusinessException("ssh连接异常（执行命令时）")

    def check_sudo(self, password):
        """
        检查用户是否有sudo权限
        :return: <BOOLEAN>
        """

        if self.user == "root":
            return False

        command = "sudo -S -p '' -i echo 'success'"

        for i in range(2):
            result = self.exec_command(command, timeout = 30)

            try:
                result[0].write('%s\n' % password)
                result[0].flush()
                output = result[1].read().decode().lower()
            except socket.timeout:
                raise BusinessException("该用户sudo权限存在问题，请检查")
            except Exception:
                raise BusinessException("ssh连接异常，请检查凭证、网络状况和目标机器sshd服务")

            if "success" in output:
                if i == 1:
                    return True
                else:
                    continue
            else:
                raise BusinessException("该用户无sudo权限")

    def check_shell(self):
        try:
            command = "$SHELL -c 'echo \"\"'"
            result = self.exec_command(command, timeout=30)
            output = result[1].channel.recv_exit_status()
            if output == 0:
                return "$SHELL"

            command = "/bin/bash -c 'echo \"\"'"
            result = self.exec_command(command, timeout=30)
            output = result[1].channel.recv_exit_status()
            if output == 0:
                return "/bin/bash"

            command = "/bin/sh -c 'echo \"\"'"
            result = self.exec_command(command, timeout=30)
            output = result[1].channel.recv_exit_status()
            if output == 0:
                return "/bin/sh"
        except Exception:
            raise BusinessException("ssh连接异常（检查shell时）")

    def get_file(self, remote_path, local_path):
        try:
            sftp_client = self.ssh_client.open_sftp()
            sftp_client.get(remote_path, local_path)
        except Exception:
            raise BusinessException("获取文件失败，远程路径：%s:%s/%s，本地路径：%s" %(self.host, self.port, remote_path, local_path))
        finally:
            sftp_client.close()

    def put_file(self, local_path, remote_path):
        try:
            sftp_client = self.ssh_client.open_sftp()
            sftp_client.put(local_path, remote_path)
        except Exception:
            raise BusinessException("拷贝文件失败，本地路径：%s，远程路径：%s:%s/%s" %(local_path, self.host, self.port, remote_path))
        finally:
            sftp_client.close()

    def __del__(self):
        self.ssh_client.close()
