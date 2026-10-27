# BosswerkMI600
This little python script will readout quick and dirty the current values of the solar inverter Bosswerk MI600.


1. ping the MI600 IP if the coverter is available
2. use requests to get the HTML code of the web interface of the converter
3. find position of "var webdata_now_p =" / "var webdata_today_e =" / "var webdata_total_e ="
4. find following the next two " and read the values in between

5. check if the values are logical and if yes use
6. a mqtt script to send the values to your mqtt broker (if defined)
7. send data via influxdb (if defined)

Note:
Sometimes the converter has a timeout of some seconds or minutes. I do not know what the converter is doing in this time. Maybe there is an upload to Solarman???

I started to use the script from https://github.com/fr00sch/bosswerk_mi600_solar. But because it use selenium there is a high cpu workload if the script is working. So I switched to my solution with less impact of workload. I have reused some script parts from https://github.com/fr00sch/bosswerk_mi600_solar


## config
Use environment variables:

* `BOSSWERKIP` (required) - inverter IP/hostname
* `BOSSWERK_USER` / `BOSSWERK_PW` - HTTP basic auth for the inverter web UI (default `admin`/`admin`)
* `BOSSWERK_INFLUXDB_HOST` / `BOSSWERK_INFLUXDB_PORT` - InfluxDB 2.x host/port. Write is skipped unless both this and `BOSSWERK_INFLUXDB_TOKEN` are set.
* `BOSSWERK_INFLUXDB_TOKEN` - InfluxDB 2.x API token
* `BOSSWERK_INFLUXDB_ORG` - InfluxDB org (default `dholz`)
* `BOSSWERK_INFLUXDB_BUCKET` - InfluxDB bucket (default `vzlogger`)
* `BOSSWERK_MQTT_TOPIC` - set to enable MQTT publishing
* `BOSSWERK_MQTT_HOST` / `BOSSWERK_MQTT_PORT` - MQTT broker (default `localhost:1883`)
* `BOSSWERK_MQTT_USER` / `BOSSWERK_MQTT_PW` - MQTT credentials
* `BOSSWERK_IGNORE_CONNECTION_ERRORS` - `true` to log inverter connection/data errors and exit 0 instead of failing (default `false`)

Data is written to InfluxDB as measurement `solarinverter` (tag `device=MI600`, fields `power`, `today_kwh`, `total_kwh`).

## Systemd:
cp templates/bosswerkmi600* /etc/systemd/system
# put secrets (BOSSWERK_INFLUXDB_TOKEN etc.) in /etc/bosswerkmi600.env (chmod 600, not tracked in git)
systemctl daemon-reload
systemctl enable bosswerkmi600.service
systemctl enable bosswerkmi600.timer
systemctl start bosswerkmi600.timer
