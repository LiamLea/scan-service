from scan_service.lib.vars import global_var
from yaml import load
from pathlib import Path
try:
    from yaml import CLoader as Loader, CDumper as Dumper
except ImportError:
    from yaml import Loader, Dumper

path = str(Path(__file__).parent / "settings.yaml")
# 读取配置文件
with open(path, encoding="utf8") as f:
    global_var.global_config = load(f, Loader = Loader)

from views import app

if __name__ == '__main__':

    for process in global_var.processes:
        process.start()
    #启动服务
    app.run(host = global_var.global_config["server"]["ip"], port = global_var.global_config["server"]["port"])