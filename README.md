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


## Systemd:
cp templates/bosswerkmi600* /etc/systemd/system
systemctl daemon-reload
systemctl enable bosswerkmi600.service
systemctl enable bosswerkmi600.timer
systemctl start bosswerkmi600.timer
