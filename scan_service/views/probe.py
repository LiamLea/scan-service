from scan_service.lib.framework import BusinessException
from scan_service.lib.framework import format_result
from scan_service.lib.modules import RunUrlProbeScan
import json
from scan_service.lib.framework import logger
from flask import Blueprint
from flask import request
import traceback

blue_probe = Blueprint(name = "probe", import_name = __name__)

@blue_probe.route("/probe/url", methods = ["GET", "POST"])
def probe_url():

    try:
        data = json.loads(request.data.decode())

        logger.info("接收url探测请求：%s" % data)

        result = RunUrlProbeScan(data["params"]["url"]).start()

        logger.info("url探测完成：%s" %data)

        return format_result(result = result)

    except BusinessException as e:
        logger.error("探测失败：%s" %traceback.format_exc())
        return format_result(success = 0, message = str(e))

    except Exception as e:
        logger.error("接口异常：%s" %traceback.format_exc())
        return format_result(success = 0, message = "接口异常：%s" %str(e))


