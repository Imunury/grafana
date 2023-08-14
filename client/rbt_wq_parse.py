import pandas as pd
import pika
import json
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import time
import numpy as np

credentials = pika.PlainCredentials('eco0', '820429ape')
connection = pika.BlockingConnection(pika.ConnectionParameters('125.136.64.124', port=5505, credentials=credentials))
channel = connection.channel()

channel.queue_declare(queue='chilseo_1_water_quality_queue')

last_message = None  # Define a global variable to store the last sent message

class MyHandler(FileSystemEventHandler):
    def on_modified(self, event):
        global last_message
        if event.src_path.endswith('230808.csv'):
            df = pd.read_csv('230808.csv')
            data_keys = ["DATE", "TIME", "temp_deg_c", "ph_units", "spcond_us_cm", "turb_ntu", "bg_ppb", "chl_ug_l", "hd0_mg_l", "hd0_sat", "ph_mv"]
            
            # DataFrame에서 마지막 행만 선택
            last_row = df.iloc[-1]
            message = {k: int(v) if isinstance(v, np.int64) else v for k, v in zip(data_keys, last_row)}
            # If the message is the same as the last sent message, do nothing
            if message == last_message:
                return
            print(message)
            channel.basic_publish(exchange='',
                                  routing_key='chilseo_1_water_quality_queue',
                                  body=json.dumps(message))
            last_message = message  # Update the last sent message

observer = Observer()
observer.schedule(MyHandler(), path='.', recursive=False)
observer.start()

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    observer.stop()
observer.join()

connection.close()
