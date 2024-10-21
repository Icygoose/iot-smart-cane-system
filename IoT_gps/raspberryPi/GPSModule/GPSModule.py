import serial
# This program takes serial port as an input in form
# Serial ser
# then outputs gps data in form
# [Latitude,Longitude]

# Quick Example
# ser=serial.Serial('/dev/ttyACM0',115200)
# print(getGPS(ser))

def getGPS(ser):
    lat=0.0
    lon=0.0
    latFind=False
    lonFind=False
    while not latFind or not lonFind:
        data=ser.readline().decode('utf-8', errors='ignore')
        if "Latitude" in data and latFind==False:
            lat=float(data.strip().split(":")[1])
            latFind=True
        if "Longitude" in data and lonFind==False:
            lon=float(data.strip().split(":")[1])
            lonFind=True
    return [lat,lon]


