import psycopg2
import pika
import json
import datetime
import math

# PostgreSQL 서버와의 연결을 설정합니다. 
conn = psycopg2.connect(host='localhost', user='eco0', password='820429ape', dbname='chilseo_1')
cur = conn.cursor()
# RabbitMQ 서버와의 연결을 설정합니다.
credentials = pika.PlainCredentials('eco0', '820429ape')
connection = pika.BlockingConnection(pika.ConnectionParameters('localhost', port=5672, credentials=credentials))
channel = connection.channel()

# 이전 GPS 위치와 시간을 저장할 전역 변수
prev_lat, prev_lon, prev_time = None, None, None

def haversine(lat1, lon1, lat2, lon2):
    # haversine 공식을 이용하여 두 GPS 위치간의 거리를 계산
    R = 6371  # 지구 반지름(킬로미터)
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c * 1000  # 미터로 변환

def gps_callback(ch, method, properties, body):
    global prev_lat, prev_lon, prev_time

    # GPS 데이터를 Python 딕셔너리로 변환합니다.
    data = json.loads(body)

    # GPS 데이터를 데이터베이스에 저장합니다.
    sql = """INSERT INTO gps_data(timestamp, lat, lon, altitude, sats) VALUES (%s, %s, %s, %s, %s)"""
    params = (data['timestamp'], data['lat'], data['lon'], data['altitude'], data['sats'])
    cur.execute(sql, params)

    # 현재 GPS 위치와 시간을 얻습니다.
    lat, lon = float(data['lat']), float(data['lon'])
    time = datetime.datetime.strptime(data['timestamp'], "%Y-%m-%d %H:%M:%S.%f")

    # 이전 GPS 위치가 있는 경우, 이를 사용하여 현재 속도를 계산합니다.
    if prev_lat is not None and prev_lon is not None and prev_time is not None:
        # 이전 위치와의 거리를 계산합니다.
        distance = haversine(prev_lat, prev_lon, lat, lon)  # 미터 단위

        # 이전 시간과의 차이를 계산합니다.
        time_diff = (time - prev_time).total_seconds()

        # 속도를 계산합니다. 이는 m/s 단위입니다.
        speed = distance / time_diff if time_diff > 0 else 0

        # 속도를 노트(kn) 단위로 변환합니다.
        speed_kn = speed * 1.94384  # 1 m/s = 1.94384 kn

        # 속도를 데이터베이스에 저장합니다.
        sql = """INSERT INTO speed_data(timestamp, speed) VALUES (%s, %s)"""
        params = (time, speed_kn)
        cur.execute(sql, params)

    # 현재 GPS 위치와 시간을 저장합니다.
    prev_lat, prev_lon, prev_time = lat, lon, time

    conn.commit()

def water_quality_callback(ch, method, properties, body):
    # 수질 데이터를 Python 딕셔너리로 변환합니다.
    data = json.loads(body)
    # date와 time 필드를 조합하여 timestamp 값을 생성합니다.
    date_str = data['DATE']
    time_str = data['TIME']
    # 날짜를 "%m/%d/%y" 형식으로 파싱합니다.
    date = datetime.datetime.strptime(date_str, "%m/%d/%y").date()
    # 시간을 "14:23:36" 형식으로 변환합니다.
    time = datetime.datetime.strptime(time_str, "%H:%M:%S").time()
    # 날짜와 시간을 조합하여 timestamp 값을 생성합니다.
    timestamp = datetime.datetime.combine(date, time)
    sql = """INSERT INTO water_quality(timestamp, temp_deg_c, ph_units, spcond_us_cm, turb_ntu, bg_ppb, chl_ug_l, hd0_mg_l, hd0_sat, ph_mv) 
             VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"""
    params = (timestamp, data['temp_deg_c'], data['ph_units'], data['spcond_us_cm'], data['turb_ntu'], data['bg_ppb'], data['chl_ug_l'], data['hd0_mg_l'], data['hd0_sat'], data['ph_mv'])
    cur.execute(sql, params)
    conn.commit()
# GPS 데이터를 받으면 gps_callback 함수를 실행하도록 설정합니다.
channel.basic_consume(queue='chilseo_1_gps_queue', on_message_callback=gps_callback, auto_ack=True)
# 수질 데이터를 받으면 water_quality_callback 함수를 실행하도록 설정합니다.
channel.basic_consume(queue='chilseo_1_water_quality_queue', on_message_callback=water_quality_callback, auto_ack=True)
channel.start_consuming()
# 연결을 닫습니다.
cur.close()
conn.close()
connection.close()