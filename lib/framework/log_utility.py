import logging

# logging.basicConfig(
#     datefmt = '%Y-%m-%d %H:%M:%S',
#     format = "%(asctime)s - %(name)s  - %(levelname)s[line:%(lineno)d] - %(module)s.%(funcName)s: %(message)s"
# )

sh = logging.StreamHandler()
formatter = logging.Formatter("%(asctime)s - %(name)s  - %(levelname)s[line:%(lineno)d] - %(module)s.%(funcName)s: %(message)s")
formatter.datefmt = "%Y-%m-%d %H:%M:%S"
sh.setFormatter(formatter)

logger = logging.getLogger("scan_service")
logging.getLogger("werkzeug").disabled = True
logging.getLogger("paramiko").disabled = True
logging.getLogger("paramiko.transport").disabled = True
logging.getLogger("paramiko.sftp").disabled = True

logger.setLevel(logging.DEBUG)
logger.addHandler(sh)

def record_log(type, params):
    def wrapper(func):
        def  new_func(*args, **kwargs):
            func(*args, **kwargs)

        return new_func()

    return wrapper()