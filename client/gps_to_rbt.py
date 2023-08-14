import serial
import pynmea2
from datetime import datetime
import json
import pika
from logging.handlers import RotatingFileHandler
import logging

# GPS 모듈이 연결된 시리얼 포트를 설정합니다. 이는 시스템에 따라 다르므로 변경하셔야 합니다.
port = "COM7"

# 시리얼 포트를 연다.
ser = serial.Serial(port, baudrate=9600, timeout=0.5)

# RabbitMQ 서버와의 연결을 설정합니다.
credentials = pika.PlainCredentials('eco0', '820429ape')
connection = pika.BlockingConnection(pika.ConnectionParameters('125.136.64.124', port=5505, credentials=credentials))
channel = connection.channel()
channel.queue_declare(queue='chilseo_1_gps_queue')

# 로깅 설정
logger = logging.getLogger('gps_logger')
logger.setLevel(logging.INFO)
handler = RotatingFileHandler('gps_data.log', maxBytes=10*1024*1024, backupCount=5)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

counter = 0

while True:
    data = ser.readline()
    if data[0:6] == b'$GNGGA':
        counter += 1
        if counter % 2 == 0:  # Every 40th message is processed
            msg = pynmea2.parse(data.decode('utf-8'))
            data_dict = {
                'timestamp': str(datetime.now()),
                'lat': round(msg.latitude, 5),
                'lon': round(msg.longitude, 5),
                'altitude': msg.altitude,
                'sats': msg.num_sats,
            }
            logger.info(f"Data: {data_dict}")  # Data logging
            print(data_dict)
            channel.basic_publish(exchange='',
                                  routing_key='chilseo_1_gps_queue',
                                  body=json.dumps(data_dict))

connection.close()
