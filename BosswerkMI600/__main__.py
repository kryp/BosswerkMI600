# -*- coding: utf-8 -*-
import requests
import urllib3
import os
import time, json, sys, re
from datetime import datetime
import subprocess

bosswerkIP = os.environ['BOSSWERKIP']
htaccess_user = os.environ.get('BOSSWERK_USER', 'admin')
htaccess_pw = os.environ.get('BOSSWERK_PW', 'admin')

mqtt_topic = os.environ.get('BOSSWERK_MQTT_TOPIC', None)
mqtt_host = os.environ.get('BOSSWERK_MQTT_HOST', 'localhost')
mqtt_port = int(os.environ.get('BOSSWERK_MQTT_PORT', '1883'))
mqtt_username = os.environ.get('BOSSWERK_MQTT_USER', None)
mqtt_password = os.environ.get('BOSSWERK_MQTT_PW', None)

# InfluxDB 2.x (token auth). Write is skipped unless a token is configured.
influxdbhost = os.environ.get('BOSSWERK_INFLUXDB_HOST', None)
influxdbport = os.environ.get('BOSSWERK_INFLUXDB_PORT', '8086')
influxdbtoken = os.environ.get('BOSSWERK_INFLUXDB_TOKEN', None)
influxdborg = os.environ.get('BOSSWERK_INFLUXDB_ORG', 'dholz')
influxdbucket = os.environ.get('BOSSWERK_INFLUXDB_BUCKET', 'vzlogger')
influxdburl = f"http://{influxdbhost}:{influxdbport}"

webinterface_url = f'http://{bosswerkIP}/status.html'
ping_try_count = 3

# Inverter presents a self-signed/plain-http endpoint on the LAN; suppress the noise.
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

try:
    from paho.mqtt import client as mqtt
except ImportError:
    mqtt = None
    print("could not find paho.mqtt: pip install paho-mqtt")


def connectMQTT():
    # https://github.com/fr00sch/bosswerk_mi600_solar
    client = mqtt.Client()
    if mqtt_username:
        client.username_pw_set(mqtt_username, mqtt_password)
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(mqtt_host, mqtt_port, 60)
    return client


def sendData(client, webdata_now_p, webdata_today_e, webdata_total_e):
    # https://github.com/fr00sch/bosswerk_mi600_solar
    startmsg = json.dumps({"device": {"status": {
        "clientname": 'MI600', "status": 'Online',
        "power": webdata_now_p, "today": webdata_today_e, "total": webdata_total_e,
        "lastDateUpdate": datetime.today().strftime('%Y-%m-%d %H:%M:%S')}}},
        skipkeys=True, allow_nan=False)
    client.publish(mqtt_topic, startmsg, qos=0, retain=False)
    client.disconnect()


def on_connect(client, userdata, flags, rc):
    print("Connected with result code " + str(rc))
    client.subscribe("$SYS/#")


def on_message(client, userdata, msg):
    print(msg.topic + ":" + str(msg.payload))


def ping_ip(current_ip_address):
    try:
        result = subprocess.run(
            ["ping", "-c", "1", "-W", "2", current_ip_address],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return result.returncode == 0
    except Exception:
        return False


def find_target_value(target, hp_source):
    find_target = hp_source.find(target)
    if find_target < 0:
        return None
    find_value_start = hp_source.find("\"", find_target)
    find_value_end = hp_source.find("\"", find_value_start + 1)
    if find_value_start < 0 or find_value_end < 0:
        return None
    return hp_source[find_value_start + 1:find_value_end]


def writeInflux(power, today, total):
    if not influxdbhost or not influxdbtoken:
        return
    line = f"solarinverter,device=MI600 power={float(power)},today_kwh={float(today)},total_kwh={float(total)}"
    try:
        r = requests.post(
            f"{influxdburl}/api/v2/write?org={influxdborg}&bucket={influxdbucket}&precision=s",
            headers={"Authorization": f"Token {influxdbtoken}"},
            data=line, timeout=5)
        if r.status_code >= 300:
            print(f"influx write failed: {r.status_code} {r.text}")
    except requests.exceptions.RequestException as e:
        print(f"influx write error: {e}")


def get_Solar_values():
    # The inverter's wifi stick sometimes stalls mid-response. requests raises that as
    # ConnectionError (not Timeout) while reading the body, so catch every request error
    # and retry once before giving up on this run.
    r = None
    for attempt in range(1, 3):
        try:
            r = requests.get(webinterface_url, verify=False, auth=(htaccess_user, htaccess_pw), timeout=5)
            break
        except requests.exceptions.RequestException as e:
            print(f"inverter request failed (attempt {attempt}/2): {e}")
            time.sleep(2)
    if r is None:
        return

    if r.status_code != 200:
        print(r.status_code)
        r.close()
        return

    hp_source = r.text
    if 'ERROR:404 Not Found' in hp_source:
        print("inverter returned 404 for status.html")
        r.close()
        return

    power = find_target_value("var webdata_now_p =", hp_source)
    today = find_target_value("var webdata_today_e =", hp_source)
    total = find_target_value("var webdata_total_e =", hp_source)
    r.close()

    # inverter reports "---" for any value while it's offline/asleep
    if any(v is None or '---' in v for v in (power, today, total)):
        print(f"incomplete data from inverter: power={power} today={today} total={total}")
        return

    data = (power, today, total)
    print(data)

    writeInflux(power, today, total)

    if mqtt_topic and mqtt:
        client = connectMQTT()
        sendData(client, power, today, total)


if __name__ == '__main__':
    getDataCountPing = 0
    while getDataCountPing < ping_try_count:
        if ping_ip(bosswerkIP):
            get_Solar_values()
            break
        else:
            getDataCountPing += 1
            time.sleep(3)
            if getDataCountPing == ping_try_count:
                startmsg = json.dumps(
                    {"device": {
                        "status": {
                            "clientname": 'MI600',
                            "status": "Offline",
                            "power": 0.0,
                            "lastDateUpdate": datetime.today().strftime('%Y-%m-%d %H:%M:%S')
                        }
                    }},
                    skipkeys=True, allow_nan=False)
                print(startmsg)
                if mqtt_topic and mqtt:
                    client = connectMQTT()
                    client.publish(mqtt_topic, startmsg, qos=0, retain=False)
                    client.disconnect()
