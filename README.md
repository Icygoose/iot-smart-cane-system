# IoT Smart Cane System

## Overview
The IoT Smart Cane is a technology-enhanced walking cane designed to improve safety and independence for elderly and visually impaired users. This system integrates multiple sensors, real-time monitoring, and alert capabilities to provide a comprehensive mobility aid solution.

## Features
- **Obstacle Detection**: Uses ultrasonic sensors to detect obstacles in the user's path and provides audio alerts
- **Fall Detection**: Monitors accelerometer and gyroscope data to detect falls and sends immediate alerts to caregivers
- **GPS Tracking**: Provides real-time location tracking for safety and navigation assistance
- **Automated Lighting**: Includes smart LED lights that automatically activate in low-light conditions for improved visibility
- **Web Dashboard**: A responsive web interface for monitoring cane status, viewing historical data, and receiving notifications

## System Architecture
The system consists of two main components:
1. **Raspberry Pi Module** (server.py): Controls sensors, processes data, and communicates with the web server
2. **Flask Web Application** (app.py): Provides the user interface and data visualization

## Hardware Components
- Raspberry Pi 4
- Ultrasonic sensors (HC-SR04)
- Accelerometer (LIS3DH)
- Gyroscope (MPU6050)
- GPS module
- VEML6030 light sensor
- LED lights
- Buzzers for audio alerts
- Push-button switch

## Software Dependencies
- Python 3.7+
- Flask and Flask-SocketIO
- SQLAlchemy for database management
- RPi.GPIO for hardware interfacing
- SMBus for I2C communication
- PySerial for GPS communication
- Socket.IO for real-time communication
- ApexCharts for data visualization

## Installation and Setup

### Prerequisites
- Raspberry Pi with Raspbian OS
- Python 3.7 or higher
- Web server (for hosting the Flask application)

### Raspberry Pi Setup
1. Clone the repository:
   ```
   git clone https://github.com/yourusername/IoT_Group27.git
   cd IoT_Group27
   ```

2. Install required packages:
   ```
   pip install -r iot_smart\ cane/requirements.txt
   ```

3. Connect hardware components according to the pinout configuration in server.py

4. Update the configuration in config.py with your email credentials for alert notifications

5. Run the Raspberry Pi server:
   ```
   python server.py
   ```

### Web Application Setup
1. Navigate to the web application directory:
   ```
   cd iot_smart\ cane
   ```

2. Initialize the database:
   ```
   python -c "from app import db; db.create_all()"
   ```

3. Start the Flask application:
   ```
   python app.py
   ```

4. Access the web dashboard at http://localhost:5000

## Usage
- The dashboard provides controls to enable/disable each module (Obstacle Detection, Fall Detection, GPS Tracking, Lighting)
- Real-time data from the sensors is displayed on the dashboard
- Fall alerts are sent via email to configured recipients
- Historical data analysis is available on the Data Analysis section

## Project Structure
```
IoT_Group27/
├── server.py                  # Raspberry Pi main script
├── iot_smart cane/            # Web application folder
│   ├── app.py                 # Flask application
│   ├── config.py              # Configuration file
│   ├── requirements.txt       # Python dependencies
│   ├── static/                # Static assets
│   │   ├── css/               # CSS stylesheets
│   │   │   └── style.css      # Main stylesheet
│   │   └── js/                # JavaScript files
│   │       └── script.js      # Main script file
│   └── templates/             # HTML templates
│       └── index.html         # Dashboard template
```

## Data Flow
1. Sensors collect data (obstacle distance, acceleration, gyroscope, GPS coordinates, light levels)
2. Raspberry Pi processes sensor data and makes decisions (e.g., activate buzzer, turn on LEDs)
3. Data is sent to the Flask server via Socket.IO
4. Flask server stores data in the database and updates the web interface
5. In case of fall detection, alert emails are sent to configured recipients

## Troubleshooting
- Ensure all hardware connections are secure
- Check that the correct GPIO pins are defined in server.py
- Verify network connectivity between the Raspberry Pi and the web server
- Check serial port configuration for GPS module
- Ensure email configuration is correct in config.py

## Contributors
- CITS5506 IoT Project - Group 27

## License
This project is licensed under the MIT License - see the LICENSE file for details.
