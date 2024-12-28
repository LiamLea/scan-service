import re
from scan_service.lib.common import ParseViaSSH
import xmltodict
import json
from scan_service.lib.utils import parse_jdbc
from scan_service.lib.utils import get_ip_from_hostname

class TomcatParse(ParseViaSSH):
    def __init__(self, ssh, passwd):
        super(TomcatParse, self).__init__(ssh = ssh, passwd = passwd)

    def parse_tomcat(self, conf_list):
        ret = {
            "datasource": []
        }
        db_pattern = re.compile(r"<Resource[\s\S]*?/>")
        for conf in conf_list:
            for match in db_pattern.finditer(self.get_file_content(conf)):
                my_dict = xmltodict.parse(match.group())
                my_dict = json.loads(json.dumps(my_dict))
                jdbc_dict = parse_jdbc(my_dict["Resource"].get("@url", ""))

                if jdbc_dict:

                    item = {
                        "name": my_dict.get("@name", ""),
                        "driver": jdbc_dict["driver"],
                        "url": [],
                        "database": jdbc_dict["database"]
                    }

                    for url in jdbc_dict["url"]:
                        item["url"].append("%s:%s" %(get_ip_from_hostname(url.split(":")[0])[0], url.split(":")[1]))

                    ret["datasource"].append(item)

        return ret
