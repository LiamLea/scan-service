from kafka import KafkaProducer
from kafka import errors
from scan_service.lib.framework import BusinessException
import json
from .data_clean import process_data

def out_kafka(data, producer, topic):
    try:
        data = process_data(data)
        producer.send(topic, json.dumps(data).encode())
        producer.flush()

    except errors.NoBrokersAvailable:
        raise BusinessException("无法连接kafka")
    except TypeError as e:
        raise BusinessException("采集结果数据格式错误：%s" %str(e))
    except Exception as e:
        raise BusinessException("kafka异常: %s" %str(e))