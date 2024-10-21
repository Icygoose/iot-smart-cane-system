import serial
import pynmea2
import csv

# Set up the serial connection to the TTGO T-Beam
ser = serial.Serial('COM7', 115200)  # Ensure the baud rate matches your GPS module's rate

while True:
    data = ser.readline().decode('utf-8', errors='ignore')
    print(data)