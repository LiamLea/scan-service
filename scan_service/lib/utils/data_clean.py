from scan_service.lib.vars import global_var
from scan_service.lib.framework import BusinessException

def process_data(data):

    try:
        if isinstance(data, dict):

            #清洗厂商名称
            if data.get("base_info"):
                for k,v in global_var.manufacturer_mapping.items():
                    if k in data["base_info"].get("manufacturer", "").lower():
                        data["base_info"]["manufacturer"] = v

                if not data["base_info"]["serial_number"]:
                    raise BusinessException("序列号为空")

            elif data.get("SystemInformation"):
                for k,v in global_var.manufacturer_mapping.items():
                    if k in data["SystemInformation"].get("Manufacturer", "").lower():
                        data["SystemInformation"]["Manufacturer"] = v
                if data.get("BIOSInformation") and not data["BIOSInformation"]["Serial Number"]:
                    raise BusinessException("序列号为空")

            # # 临时改动，解决数据过长问题
            # if data.get("system"):
            #     if data["system"].get("process"):
            #         data["system"].pop("process")
            #     if data["system"].get("daemon"):
            #         data["system"].pop("daemon")
            #     if data["system"].get("software"):
            #         data["system"].pop("software")
            # if data.get("kernel"):
            #     data["kernel"].pop("kernel")
            #     data["kernel"].pop("loaded_module")
    except Exception:
        pass

    return data
