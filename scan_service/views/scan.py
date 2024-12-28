from scan_service.lib.utils import out_kafka
from scan_service.lib.vars import global_var
import importlib
from scan_service.lib.framework import BusinessException
from scan_service.lib.framework import AuthException
from scan_service.lib.framework import format_result
from scan_service.lib.framework import logger
from scan_service.lib.framework import format_future_result
import json
import traceback
import time

from flask import Blueprint
from flask import request
from scan_service.lib.framework import process_queues
from scan_service.lib.framework import result_queue
from scan_service.lib.framework import lock
from scan_service.lib.framework import event
from scan_service.lib.framework import producer
from .common import build_reponse
from scan_service.lib.modules import get_progress
import os
from pathlib import Path

blue_scan = Blueprint(name = "scan", import_name = __name__)

@blue_scan.route("/scan/nmap", methods = ["GET", "POST"])
def scan():

    try:
        data = json.loads(request.data.decode())

        logger.info("接收nmap扫描请求：%s" %json.dumps(data))

        #检查参数
        if not isinstance(data.get("id"), str):
            raise BusinessException("传参错误，缺少参数：str(id)")
        if not isinstance(data.get("params"), dict):
            raise BusinessException("传参错误，缺少参数：dict(params)")
        if not isinstance(data["params"].get("hosts"), str):
            raise BusinessException("传参错误，缺少参数：str(params.hosts)")
        if not data["params"]["hosts"]:
            raise BusinessException("传参错误，hosts不能为空")

        future_dict = result_queue.get()
        logger.debug("/scan/nmap 获取锁")

        if future_dict.get(data["id"]):
            result_queue.put(future_dict)
            logger.debug("/scan/nmap 释放锁")
            raise BusinessException("id=%s正在执行中" %data["id"])


        # #该文件用于保存nmap执行的进度，后续用于查询
        # progress_file = "/tmp/nmap_output/" + time.strftime('%Y-%m-%d-%H-%M-%S') + ".pro"

        future_dict[data["id"]] = format_future_result(id = data["id"], task_id = data.get("taskId", ""), total = 1, type = "nmap")

        result_queue.put(future_dict)
        logger.debug("/scan/nmap 释放锁")

        #开始发送进度
        event.set()

        task = {
            "func": run_scan,
            "args": {
                "params": data["params"],
                # "progress_file": progress_file,
                # kafka_producer从进程中获取
                "task_id": data.get("taskId", "0")
            },
            "id": data["id"]
        }

        logger.info("开始nmap扫描，id: %s，参数: %s" %(data["id"], data["params"]))

        with lock:
            process_queues[global_var.task_number].put(task)
            global_var.task_number = global_var.task_number + 1

        return build_reponse(format_result())

    except Exception as e:

        future_dict = result_queue.get()
        logger.debug("/scan/nmap 获取锁")
        if future_dict.get(data["id"]):
            future_dict.pop(data["id"])
        result_queue.put(future_dict)
        logger.debug("/scan/nmap 释放锁")

        logger.error("/scan/nmap接口调用异常：%s" %traceback.format_exc())
        return build_reponse(format_result(success = 0, message = "接口调用异常：%s" %str(e)))

@blue_scan.route("/scan/deploy", methods = ["GET", "POST"])
def deploy():

    try:
        data = json.loads(request.data.decode())

        # logger.debug("接收部署请求：%s" %json.dumps(data))
        logger.info("接收部署请求：%s" %(data if data.get("params") and data.copy().pop("params") else data))

        future_dict = result_queue.get()
        logger.debug("/scan/deploy 获取锁")

        if future_dict.get(data["id"]):
            result_queue.put(future_dict)
            logger.debug("/scan/deploy 释放锁")
            raise BusinessException("id=%s正在执行中" %data["id"])

        #检查参数
        if not isinstance(data.get("id"), str):
            raise BusinessException("传参错误，缺少参数：str(id)")
        if not isinstance(data.get("params", {}), list):
            raise BusinessException("传参错误，缺少参数：list(params)")
        if not data["params"]:
            raise BusinessException("params参数为空")
        for item in data["params"]:
            if not item.get("type"):
                raise BusinessException("传参错误，缺少参数：str(type)")
            elif not item.get("credential"):
                raise BusinessException("传参错误，缺少参数：dict(credential)")
            elif not item["credential"].get("host"):
                raise BusinessException("传参错误，缺少参数：str(credential.hosts)")


        future_dict[data["id"]] = format_future_result(data["id"], data.get("taskId", ""), len(data["params"]), type = "deploy")

        result_queue.put(future_dict)
        logger.debug("/scan/deploy 释放锁")

        #开始发送进度
        out_kafka({"id": data["id"], "task_id": data.get("taskId", ""), "status": "0"}, producer, global_var.global_config["kafka"]["topic"]["host_deploy"])
        out_kafka({"id": data["id"], "task_id": data.get("taskId", ""), "status": "0"}, producer, global_var.global_config["kafka"]["topic"]["software_deploy"])
        event.set()

        hosts = []
        try:
            for param in data["params"]:
                hosts.append({param["type"]: param["credential"]["host"]})
                task = {
                    "func": run_deploy,
                    "args": {
                        "credentials": [{"type": param["type"], "credential": param["credential"]}],
                        #kafka_producer从进程中获取
                        "task_id": data.get("taskId", "0")
                    },
                    "id": data["id"]
                }

                with lock:
                    process_queues[global_var.task_number].put(task)
                    global_var.task_number = global_var.task_number + 1

        except KeyError as e:
            raise BusinessException("传参错误，缺少参数：%s" %str(e))

        logger.info("开始部署，id: %s, 主机: %s" % (data["id"], hosts))

        return build_reponse(format_result())

    except Exception as e:

        future_dict = result_queue.get()
        logger.debug("/scan/deploy 获取锁")
        if future_dict.get(data["id"]):
            future_dict.pop(data["id"])
        result_queue.put(future_dict)
        logger.debug("/scan/deploy 释放锁")

        logger.error("/scan/deploy接口调用异常：%s" %traceback.format_exc())
        return build_reponse(format_result(success = 0, message = "部署接口异常：%s" %e))

@blue_scan.route("/scan/bulk", methods = ["GET", "POST"])
def bulk():
    try:
        data = json.loads(request.data.decode())

        # logger.debug("接收部署请求：%s" %json.dumps(data))
        logger.info("接收部署请求：%s" %(data if data.get("params") and data.copy().pop("params") else data))

        #检查参数
        if not isinstance(data.get("id"), str):
            raise BusinessException("传参错误，缺少参数：str(id)")
        if not isinstance(data.get("params", {}).get("credentials", {}), list):
            raise BusinessException("传参错误，缺少参数：list(params.credentials)")
        if not isinstance(data.get("params", {}).get("hosts", []), dict):
            raise BusinessException("传参错误，缺少参数：dict(params.hosts)")
        if not data["params"]["hosts"]:
            raise BusinessException("传参错误，hosts不能为空")
        if not data["params"]["credentials"]:
            credential_empty = True
            for host,credential in data["params"]["hosts"].items():
                if credential:
                    credential_empty = False
                    break
            if credential_empty:
                raise BusinessException("传参错误，credential都为空")

        future_dict = result_queue.get()
        logger.debug("/scan/bulk 获取锁")

        if future_dict.get(data["id"]):
            result_queue.put(future_dict)
            logger.debug("/scan/bulk 释放锁")
            raise BusinessException("id=%s正在执行中" %data["id"])

        num1 = 0
        num2 = 0
        for k,v in data["params"]["hosts"].items():
            if v:
                num1 += 1
            else:
                num2 += 1
        future_dict[data["id"]] = format_future_result(data["id"], data.get("taskId", ""), len(data["params"]["credentials"]) * num2 + num1, type="deploy")
        result_queue.put(future_dict)
        logger.debug("/scan/bulk 释放锁")

        #开始发送进度
        out_kafka({"id": data["id"], "task_id": data.get("taskId", ""), "status": "0"}, producer, global_var.global_config["kafka"]["topic"]["host_deploy"])
        out_kafka({"id": data["id"], "task_id": data.get("taskId", ""), "status": "0"}, producer, global_var.global_config["kafka"]["topic"]["software_deploy"])
        event.set()

        hosts = []
        try:

            for host,match_credential in data["params"]["hosts"].items():

                if match_credential:
                    hosts.append({match_credential["type"]: host})
                    match_credential["host"] = host
                    credentials = [ {"type": match_credential.pop("type"), "credential": match_credential} ]

                    for credential in data["params"]["credentials"]:
                        credential = credential.copy()
                        credential["host"] = host
                        credentials.append({"type": credential.pop("type"), "credential": credential})
                    task = {
                        "func": run_deploy,
                        "args": {
                            "credentials": credentials,
                            # kafka_producer从进程中获取
                            "task_id": data.get("taskId", "0")
                        },
                        "id": data["id"]
                    }
                    with lock:
                        process_queues[global_var.task_number].put(task)
                        global_var.task_number = global_var.task_number + 1

                else:
                    for credential in data["params"]["credentials"]:
                        credential = credential.copy()
                        credential["host"] = host
                        hosts.append({credential["type"]: host})

                        task = {
                            "func": run_deploy,
                            "args": {
                                "credentials": [{"type": credential.pop("type"), "credential": credential}],
                                #kafka_producer从进程中获取
                                "task_id": data.get("taskId", "0")
                            },
                            "id": data["id"]
                        }

                        with lock:
                            process_queues[global_var.task_number].put(task)
                            global_var.task_number = global_var.task_number + 1

        except KeyError as e:
            raise BusinessException("传参错误，缺少参数：%s" %str(e))

        logger.info("开始部署，id: %s, 主机: %s" % (data["id"], hosts))

        return build_reponse(format_result())

    except Exception as e:

        future_dict = result_queue.get()
        logger.debug("/scan/bulk 获取锁")
        if future_dict.get(data["id"]):
            future_dict.pop(data["id"])
        result_queue.put(future_dict)
        logger.debug("/scan/bulk 释放锁")

        logger.error("/scan/bulk接口调用异常：%s" %traceback.format_exc())
        return build_reponse(format_result(success = 0, message = "部署接口异常：%s" %e))


@blue_scan.route("/scan/certificate_test", methods = ["GET", "POST"])
def certificate_test():
    try:
        data = json.loads(request.data.decode())

        logger.info("接收凭证测试请求：%s" %json.dumps(data))

        #检查参数
        if not isinstance(data.get("id"), str):
            raise BusinessException("传参错误，缺少参数：str(id)")
        if not data["hosts"]:
            raise BusinessException("传参错误，hosts不能为空")

        future_dict = result_queue.get()
        logger.debug("/scan/certificate_test 获取锁")

        if future_dict.get(data["id"]):
            result_queue.put(future_dict)
            logger.debug("/scan/certificate_test 释放锁")
            raise BusinessException("id=%s正在执行中" %data["id"])

        future_dict[data["id"]] = format_future_result(data["id"], data.get("taskId", ""), len(data["hosts"]), data.get("type", ""))
        result_queue.put(future_dict)
        logger.debug("/scan/certificate_test 释放锁")

        event.set()

        hosts = []
        try:

            for host,match_credential in data["hosts"].items():

                if match_credential:
                    hosts.append({match_credential["type"]: host})
                    match_credential["host"] = host
                    type = match_credential.pop("type")

                    task = {
                        "func": run_test,
                        "args": {
                            "credential": match_credential,
                            "type": type
                        },
                        "id": data["id"]
                    }
                    with lock:
                        process_queues[global_var.task_number].put(task)
                        global_var.task_number = global_var.task_number + 1
                else:
                    raise BusinessException("主机凭证不能为空")


        except KeyError as e:
            raise BusinessException("传参错误，缺少参数：%s" %str(e))

        logger.info("开始凭证测试，id: %s, 主机: %s" % (data["id"], hosts))

        return build_reponse(format_result())

    except Exception as e:

        future_dict = result_queue.get()
        logger.debug("/scan/certificate_test 获取锁")
        if future_dict.get(data["id"]):
            future_dict.pop(data["id"])
        result_queue.put(future_dict)
        logger.debug("/scan/certificate_test 释放锁")

        logger.error("/scan/certificate_test接口调用异常：%s" %traceback.format_exc())
        return build_reponse(format_result(success = 0, message = "凭证测试接口异常：%s" %e))


@blue_scan.route("/scan/test", methods = ["GET", "POST"])
def test():

    try:
        data = json.loads(request.data.decode())

        logger.info("接收测试请求：%s" %data)

        #检查参数
        if not isinstance(data.get("params"), dict):
            raise BusinessException("传参错误，缺少参数：dict(params)")
        if not isinstance(data.get("params", {}).get("type"), str):
            raise BusinessException("传参错误，缺少参数：str(params.type)")
        if not isinstance(data.get("params", {}).get("credential"), dict):
            raise BusinessException("传参错误，缺少参数：dict(params.credential")

        logger.info("执行凭证测试，类型: %s" %data["params"]["type"])
        ret = run_test(data["params"]["type"], data["params"]["credential"])
        logger.info("返回测试结果: %s" %ret)

        return build_reponse(format_result(result = ret))

    except BusinessException as e:
        logger.info("测试失败，原因：%s" %str(e))
        return build_reponse(format_result(success=0, message=str(e)))

    except Exception as e:

        logger.error("/scan/test接口调用异常：%s" %traceback.format_exc())
        return build_reponse(format_result(success = 0, message = str(e)))

@blue_scan.route("/scan/query", methods = ["GET", "POST"])
def query():

    try:
        data = json.loads(request.data.decode())

        #检查参数
        if not isinstance(data.get("id"), str):
            raise BusinessException("传参错误，缺少参数：str(id)")

        future_dict = result_queue.get()
        logger.debug("/scan/query 获取锁")

        ret = future_dict.get(data["id"])

        result_queue.put(future_dict)
        logger.debug("/scan/query 释放锁")

        if ret:
            success = 1

            if ret["status"]["done"]:
                future_dict.pop(data["id"])
                logger.info("成功获取扫描结果，id：%s，结果：%s" %(data["id"], ret))

            else:
                logger.info("当前扫描还未结束，id：%s，进度：%s" %(data["id"], ret))

            if ret["type"] == "nmap" and not ret["status"]["done"]:
                ret["status"]["progress"] = get_progress(data["id"])

            return build_reponse(format_result(success = success, message = ret["errorMsg"], result = ret["result"], status = ret["status"]))

        else:

            #打印错误日志
            logger.info("查询id不存在：%s" %data["id"])

            return build_reponse(format_result(success = 0, message = "查询id不存在"))

    except Exception as e:

        logger.error("/scan/query接口调用异常：%s" %traceback.format_exc())

        return build_reponse(format_result(success = 0, message = "接口异常：%s" %str(e)))

#执行nmap扫描
def run_scan(params, task_id, id, kafka_producer):

    try:
        stime = int(time.time())
        from scan_service.lib import RunNmapScan
        scan = RunNmapScan(id, params)
        result = scan.start()
        result["task_id"] = task_id
        duration = int(time.time()) - stime
        # out_kafka(result, kafka_producer, global_var.global_config["kafka"]["topic"]["nmap"])
        logger.info("nmap扫描成功，id: %s, 扫描时间（秒）: %s, 结果：%s" %(id, duration, result))

    except Exception as e:

        logger.error("nmap扫描失败，id: %s, 参数: %s，错误信息: %s" %(id, params["hosts"], traceback.format_exc()))
        raise BusinessException(str(e))

    return result

#执行部署
def run_deploy(credentials, kafka_producer, task_id, id):
    credential_num = len(credentials)
    for i in range(credential_num):

        try:
            scan_type = credentials[i]["type"]
            credential = credentials[i]["credential"]
            if scan_type == "software":
                kafka_topic = global_var.global_config["kafka"]["topic"]["software_deploy"]
            else:
                kafka_topic = global_var.global_config["kafka"]["topic"]["host_deploy"]

            stime = int(time.time())
            module = importlib.import_module("lib.modules")
            scan = getattr(module, "Run" + scan_type[0].upper() + scan_type[1:].lower() + "Scan")(credential)
            result = scan.start()

            #添加task_id
            if isinstance(result, dict):
                result["task_id"] = task_id
            elif isinstance(result, list):
                for item in result:
                    item["task_id"] = task_id

            if result:
                out_kafka(result, kafka_producer, kafka_topic)

            # else:
            #     raise BusinessException("扫描结果为空")
            duration = int(time.time()) - stime
            logger.info("部署成功，id: %s, ip：%s，类型：%s，部署时间（秒）：%s" %(id, credential.get("host", ""), scan_type, duration))

        except AuthException as e:
            if i == credential_num -1:
                raise BusinessException("0", credential["host"], str(e), scan_type)
            else:
                continue

        except Exception as e:
            logger.error("部署失败，id: %s, ip：%s，参数: %s，错误信息：%s" %(id, credential.get("host", ""), scan_type, traceback.format_exc()))
            raise BusinessException("1", credential["host"], str(e), scan_type)

        if isinstance(result, dict) and result.get("os_type", "") == "Linux":
            logger.info("开始部署，id: %s, ip：%s，类型：%s" % (id, credential.get("host", ""), "software"))
            run_deploy([{"type": "software", "credential": credential}], kafka_producer, task_id, id)

        # return {"ip": credential["host"], "duration": duration, "type": scan_type, "credential": credential, "os_type": result.get("os_type", "")}
        return {"ip": credential["host"], "duration": duration, "type": scan_type, "credential": credential}

#执行凭证测试
def run_test(type, credential, kafka_producer, id):
    try:
        module = importlib.import_module("lib.modules")
        scan = getattr(module, "Run" + type[0].upper() + type[1:].lower() + "Test")(credential)
        result = scan.start()

    except Exception as e:
        logger.error("凭证测试失败，id: %s, ip：%s，参数: %s，错误信息：%s" %(id, credential.get("host", ""), type, traceback.format_exc()))
        raise BusinessException("1", credential["host"], str(e), type)

    #return result
    return {"ip": credential["host"]}


@blue_scan.route("/run/scripts", methods = ["GET", "POST"])
def sctipts():
    try:
        data = json.loads(request.data.decode())

        # logger.debug("接收部署请求：%s" %json.dumps(data))
        logger.info("接收脚本执行请求：%s" %(data if data.get("params") and data.copy().pop("params") else data))

        #检查参数
        if not isinstance(data.get("id"), str):
            raise BusinessException("传参错误，缺少参数：str(id)")
        if not isinstance(data.get("params", {}).get("credentials", {}), list):
            raise BusinessException("传参错误，缺少参数：list(params.credentials)")
        if not isinstance(data.get("params", {}).get("hosts", []), dict):
            raise BusinessException("传参错误，缺少参数：dict(params.hosts)")
        if not data["params"]["hosts"]:
            raise BusinessException("传参错误，hosts不能为空")
        if not data["params"]["credentials"]:
            credential_empty = True
            for host,credential in data["params"]["hosts"].items():
                if credential:
                    credential_empty = False
                    break
            if credential_empty:
                raise BusinessException("传参错误，credential都为空")

        future_dict = result_queue.get()
        logger.debug("/run/scripts 获取锁")

        if future_dict.get(data["id"]):
            result_queue.put(future_dict)
            logger.debug("/run/scripts 释放锁")
            raise BusinessException("id=%s正在执行中" %data["id"])

        num1 = 0
        num2 = 0
        for k,v in data["params"]["hosts"].items():
            if v:
                num1 += 1
            else:
                num2 += 1
        future_dict[data["id"]] = format_future_result(data["id"], data.get("taskId", ""), len(data["params"]["credentials"]) * num2 + num1, type="scripts")
        result_queue.put(future_dict)
        logger.debug("/run/scripts 释放锁")

        dir_name = ".tmp_%s" %data["id"]
        parent_path = Path(Path(__file__).parent.parent / dir_name)
        if not os.path.isdir(str(parent_path)):
            os.mkdir(str(parent_path))
        for task_dict in data["params"]["tasks"]:
            with open(str(parent_path/task_dict["id"]), "w", encoding="utf8", newline='\n') as fobj:
                fobj.write(task_dict["script"])
            if task_dict["rollback"]:
                with open(str(parent_path / str("rollback_" + task_dict["id"])), "w", encoding="utf8", newline='\n') as fobj:
                    fobj.write(task_dict["rollback"])

        #开始发送进度
        event.set()

        hosts = []
        try:

            for host,match_credential in data["params"]["hosts"].items():

                if match_credential:
                    hosts.append(host)
                    match_credential["host"] = host
                    credentials = [ match_credential ]

                    for credential in data["params"]["credentials"]:
                        credential = credential.copy()
                        credential["host"] = host
                        credentials.append(credential)
                    task = {
                        "func": run_scripts,
                        "args": {
                            "credentials": credentials,
                            "task_id": data.get("taskId", "0"),
                            "sudo": int(data["params"]["sudo"]),
                            "tasks": data["params"]["tasks"]
                        },
                        "id": data["id"]
                    }
                    with lock:
                        process_queues[global_var.task_number].put(task)
                        global_var.task_number = global_var.task_number + 1

                else:
                    for credential in data["params"]["credentials"]:
                        credential = credential.copy()
                        credential["host"] = host
                        hosts.append({credential["type"]: host})

                        task = {
                            "func": run_deploy,
                            "args": {
                                "credentials": [credential],
                                "task_id": data.get("taskId", "0"),
                                "sudo": int(data["params"]["sudo"]),
                                "tasks": data["params"]["tasks"]
                            },
                            "id": data["id"]
                        }

                        with lock:
                            process_queues[global_var.task_number].put(task)
                            global_var.task_number = global_var.task_number + 1

        except KeyError as e:
            raise BusinessException("传参错误，缺少参数：%s" %str(e))

        logger.info("开始执行脚本，id: %s, 主机: %s" % (data["id"], hosts))

        return build_reponse(format_result())

    except Exception as e:

        future_dict = result_queue.get()
        logger.debug("/run/scripts 获取锁")
        if future_dict.get(data["id"]):
            future_dict.pop(data["id"])
        result_queue.put(future_dict)
        logger.debug("/run/scripts 释放锁")

        logger.error("/run/scripts接口调用异常：%s" %traceback.format_exc())
        return build_reponse(format_result(success = 0, message = "脚本执行接口异常：%s" %e))

from scan_service.lib.modules import RunScripts
#执行脚本任务
def run_scripts(credentials, kafka_producer, task_id, id, tasks, sudo):
    credential_num = len(credentials)
    for i in range(credential_num):

        try:
            credential = credentials[i]

            stime = int(time.time())
            instance = RunScripts(credential, tasks, id, sudo)
            result = instance.start()

            duration = int(time.time()) - stime
            logger.info("脚本执行完成，id: %s, ip：%s，部署时间（秒）：%s" %(id, credential.get("host", ""), duration))

        except AuthException as e:
            if i == credential_num -1:
                raise BusinessException("0", credential["host"], str(e))
            else:
                continue

        except Exception as e:
            logger.error("脚本执行失败，id: %s, ip：%s，错误信息：%s" %(id, credential.get("host", ""), traceback.format_exc()))
            raise BusinessException("1", credential["host"], str(e), "run_scripts")

        # return {"ip": credential["host"], "duration": duration, "type": scan_type, "credential": credential, "os_type": result.get("os_type", "")}
        return {"ip": credential["host"], "duration": duration, "type": "run_scripts", "credential": credential, "tasks": result}