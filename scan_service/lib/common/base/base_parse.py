from scan_service.lib.utils import SHELL

class Parse:
    def __init__(self):
        pass

class ParseViaSSH(Parse, SHELL):
    def __init__(self, ssh, passwd):
        Parse.__init__(self)
        SHELL.__init__(self, ssh = ssh, passwd = passwd)