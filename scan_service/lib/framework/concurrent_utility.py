from concurrent.futures import ThreadPoolExecutor
from multiprocessing import Queue
from multiprocessing import Process
from scan_service.lib.vars import global_var
from threading import Lock
from threading import Thread
from scan_service.lib.utils import MyInt
from kafka import KafkaProducer
import time
from functools import partial
from .log_utility import logger
from scan_service.lib.utils.kafka_utils import out_kafka
import os
from .exception import BusinessException
from pathlib import Path
import shutil

def task(task_q, result_q):

    thread_pool = ThreadPoolExecutor(int(global_var.global_config["arguments"]["threads"]))
    producer =  KafkaProducer(bootstrap_servers=global_var.global_config["kafka"]["server"], max_request_size=10000000)

    def clean_result(id):
        time.sleep(10)
        future_dict = result_q.get()
        logger.debug("clean_result 获取锁，id：%s" % id)
        if future_dict.get(id):
            logger.info("成功清除扫描结果，id: %s，内容：%s" % (id, future_dict.pop(id)))
        result_q.put(future_dict)
        logger.debug("clean_result 释放锁，id：%s" % id)

    # 回调函数
    def when_finshed(future, id, stime):

        future_dict = result_q.get()

        try:
            if future.exception():
                logger.debug("when_finished 获取锁，exception：%s" % future.exception())
                future_dict[id]["status"]["failed"] += 1

                #如果凭证错误
                if future.exception().args[0] == "0":
                    future_dict[id]["errorMsg"]["auth_failed"].append(future.exception().args[1])

                #如果部署失败
                elif future.exception().args[0] == "1":
                    future_dict[id]["status"]["progress"] += 1

                    future_dict[id]["errorMsg"]["deploy_failed"].append(
                        {
                            "ip": future.exception().args[1],
                            "msg": future.exception().args[2],
                            "type": future.exception().args[3]
                        }
                    )
                    future_dict[id]["failed_ip"].append(future.exception().args[1])

                #如果nmap扫描失败
                else:
                    future_dict[id]["errorMsg"]["namp_failed"] = str(future.exception())

            else:
                logger.debug("when_finished 获取锁，result：%s" % {"ip": future.result().get("ip"), "type": future.result().get("type")})
                future_dict[id]["status"]["success"] += 1
                future_dict[id]["status"]["progress"] += 1
                result = future.result()
                future_dict[id]["result"].append(result)

                #记录成功的ip，用于处理auth_failed的中的ip
                if result.get("ip"):
                    future_dict[id]["success_ip"].append(result["ip"])

                # #如果部署成功，且操作系统类型为linux，则执行软件部署
                # if result.get("os_type") == "Linux":
                #     credential = result["credential"].copy()
                #     args["credentials"] = [ {"type": "software", "credential": credential} ]
                #     args["kafka_producer"] = producer
                #     args["id"] = id
                #     logger.info("开始部署，id: %s, ip：%s，类型：%s" % (id, credential.get("host", ""), "software"))
                #     thread_pool.submit(func, **args)

            # 判断是否扫描完成
            if future_dict[id]["status"]["total"] == (future_dict[id]["status"]["failed"] + future_dict[id]["status"]["success"]):
                future_dict[id]["status"]["done"] = 1
                future_dict[id]["status"]["time"] = int(time.time()) - stime
                future_dict[id]["errorMsg"]["auth_failed"] = [ip for ip in list(set(future_dict[id]["errorMsg"]["auth_failed"])) if ip not in future_dict[id]["success_ip"]  and ip not in future_dict[id]["failed_ip"]]
                # if future_dict[id]["type"] != "nmap" and future_dict[id]["type"] != "certificate_test":
                if future_dict[id]["type"] == "deploy":
                    out_kafka({"id": id, "task_id": future_dict[id].get("task_id", ""), "status": "1"}, producer, global_var.global_config["kafka"]["topic"]["host_deploy"])
                    out_kafka({"id": id, "task_id": future_dict[id].get("task_id", ""), "status": "1"}, producer, global_var.global_config["kafka"]["topic"]["software_deploy"])
                elif future_dict[id]["type"] == "nmap":
                    try:
                        os.remove("/tmp/nmap_output/" + id + ".pro")
                    except Exception:
                        pass
                elif future_dict[id]["type"] == "scripts":
                    try:
                        dir_name = ".tmp_%s" % id
                        parent_path = Path(Path(__file__).parent.parent.parent / dir_name)
                        shutil.rmtree(parent_path)
                    except Exception:
                        pass

                out_kafka(future_dict, producer, global_var.global_config["kafka"]["topic"]["progress"])
                logger.info("本批次扫描完成，id：%s，扫描时间（秒）：%s，结果：%s" % (id, future_dict[id]["status"]["time"], future_dict[id]))

                #启动一个线程，如果结果在一定时间内没有被取出，则自动清除结果
                Thread(target = clean_result, args = (id,)).start()
        except Exception as e:
            result_q.put(future_dict)
            logger.debug("when_finished 释放锁")
            raise BusinessException(e)

        result_q.put(future_dict)
        logger.debug("when_finished 释放锁")

    while True:
        task = task_q.get()
        new_when_finished = partial(when_finshed, id = task["id"], stime = int(time.time()))
        thread_pool.submit(task["func"], **task["args"], kafka_producer = producer, id = task["id"]).add_done_callback(new_when_finished)

result_queue = Queue()
result_queue.put({})

#用于保存给 各个进程分发任务的队列
process_queues = []

#创建线程锁，该线程锁用于在flask主线程中 通过一个全局数，均匀分配任务
lock = Lock()

#保存创建的所有进程
global_var.processes = []

#全局数，用于分发任务，比如有10个进程，则这个数的最大值就是9，当9+1就会溢出变成0
global_var.task_number = MyInt(0, max = global_var.global_config["arguments"]["processes"])

for i in range(int(global_var.global_config["arguments"]["processes"])):
    q = Queue()
    process = Process(target=task, args=(q, result_queue))
    process.daemon = True
    process_queues.append(q)
    global_var.processes.append(process)

# 异步执行时，用于汇总执行结果，通过队列在多进程之间传递
def format_future_result(id, task_id, total, type = ""):
    ret = {
        #id标识该部署的批次
        "id": id,
        "type": type,
        "task_id": task_id,
        "status": {
            # 0表示该部署批次还没有全部完成
            "done": 0,

            # 该批次的主机的总量，当是多凭证部署时，这个total是真正的数量（但不是用户想要看到的数量）
            "total": total,

            # 用于判断该批次是否执行完成
            "success": 0,
            "failed": 0,

            # 当前的执行进度
            "progress": 0
        },

        "errorMsg": {
            "deploy_failed": [],
            "auth_failed": [],

            #nmap部署失败的信息
            "namp_failed": ""
        },

        # 部署成功后的结果
        "result": [],           #如果是部署，返回凭证
                                #如果是nmap，返回扫描结果

        # 部署成功的ip，用于清洗凭证错误的信息（部署时使用）
        "success_ip": [],
        "failed_ip": []

        #用于获取执行进度（nmap扫描时需要该文件）
        # "progress_file": progress_file
    }
    return ret

