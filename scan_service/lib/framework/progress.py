from threading import Thread
from threading import Event
from kafka import KafkaProducer
from scan_service.lib.utils.kafka_utils import out_kafka
from scan_service.lib.vars import global_var
import time
from .concurrent_utility import result_queue
from .log_utility import logger

producer =  KafkaProducer(bootstrap_servers=global_var.global_config["kafka"]["server"], max_request_size=10000000)

def send_progress(result_q, event):
    while event.wait():
        time.sleep(5)
        future_dict = result_q.get()
        logger.debug("send_process 获取锁")
        if future_dict:
            try:
                out_kafka(future_dict, producer, global_var.global_config["kafka"]["topic"]["progress"])
            except Exception:
                pass
        else:
            event.clear()
        result_q.put(future_dict)
        logger.debug("send_process 释放锁")


event = Event()
progress_thread = Thread(target = send_progress, args = (result_queue, event))
progress_thread.daemon = True
progress_thread.start()

