import paramiko
from paramiko.ssh_exception import SSHException, AuthenticationException, NoValidConnectionsError
import socket
from pathlib import Path
import os
path = Path(__file__).parent.parent
print(path)

host = "3.1.5.19"
port = "22"
user = "root"
passwd = "Cangoal_123"

ssh_client = paramiko.SSHClient()
ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh_client.connect(hostname = host, port = port, username = user, password = passwd, look_for_keys = False, timeout = 30)
result = ssh_client.exec_command("source /etc/profile &>/dev/null;/tmp/.tmp_730c85f74eb1435ead76a29c47635131/123", timeout = 10, environment = {"LANG": "en_US.UTF-8"})
print(result[2].read().decode())

# print(result[1])
# result
# sftp_client = ssh_client.open_sftp()
# sftp_client.put("D:\codes\scan_service", "/tmp/a_dir")
# # ssh_client.exec_command()

