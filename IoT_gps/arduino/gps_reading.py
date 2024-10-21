import serial
import pynmea2
import csv

# Set up the serial connection to the TTGO T-Beam
ser = serial.Serial('COM7', 115200, timeout=1)  # Ensure the baud rate matches your GPS module's rate

# Open a CSV file to store GPS data
with open('./gps_data.csv', 'w', newline='') as csvfile:
    writer = csv.writer(csvfile)
    writer.writerow(['Latitude', 'Longitude'])  # Write the CSV header

    try:
        while True:
            # Read data from the TTGO T-Beam
            data = ser.readline().decode('utf-8', errors='ignore').strip()
            
            # Check if the data starts with $GNRMC (an NMEA sentence containing GPS data)
            if data.startswith("$GNRMC"):
                try:
                    # Parse the NMEA sentence
                    msg = pynmea2.parse(data)
                    latitude = msg.latitude
                    longitude = msg.longitude
                    
                    # Display the GPS data
                    print(f"Latitude: {latitude}, Longitude: {longitude}")
                    
                    # Write data to the CSV file
                    writer.writerow([latitude, longitude])
                except pynmea2.ParseError as e:
                    print(f"Parse error: {e}")
    except KeyboardInterrupt:
        print("Program interrupted by user.")
    finally:
        # Clean up
        ser.close()
        print("Serial port closed.")