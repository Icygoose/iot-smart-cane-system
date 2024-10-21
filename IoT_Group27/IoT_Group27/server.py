import asyncio
import json
import RPi.GPIO as GPIO
import time
import smbus
import socketio
import serial
from datetime import datetime
import pytz

# 定义珀斯时区为全局变量
perth_tz = pytz.timezone('Australia/Perth')

# Socket.IO Server 
sio = socketio.AsyncClient()

# Flask-SocketIO Server URL
FLASK_SERVER_URL = 'http://172.20.10.3:5000'  

# GPIO 
BUZZER_PIN_OBSTACLE = 15  
BUZZER_PIN_FALL = 16   
PIN_TRIGGER_MID = 7
PIN_ECHO_MID = 11
PIN_TRIGGER_BOTTOM = 12
PIN_ECHO_BOTTOM = 13
LED_PINS = [33, 35, 38]  
SWITCH_PIN = 36   

# I2C
ACCEL_I2C_ADDR = 0x18  
GYRO_I2C_ADDR = 0x68  
bus = smbus.SMBus(1)

# VEML6030 I2C address
VEML6030_ADDRESS = 0x48

# VEML6030 register addresses
REGISTER_CTRL = 0x00
REGISTER_WHITE = 0x04

# Set light intensity threshold
LIGHT_THRESHOLD = 100

active_flags = {
    'obstacle': False, 
    'falling': False, 
    'gps': False, 
    'lighting_on': False, 
    'latest_gps': None,
    'manual_override': False
}

# GPIO Initializing
def setup_gpio():
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BOARD)  
    for pin in LED_PINS:
        GPIO.setup(pin, GPIO.OUT)
    GPIO.setup(SWITCH_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.setup(BUZZER_PIN_OBSTACLE, GPIO.OUT)
    GPIO.setup(BUZZER_PIN_FALL, GPIO.OUT)
    GPIO.setup(PIN_TRIGGER_MID, GPIO.OUT)
    GPIO.setup(PIN_ECHO_MID, GPIO.IN)
    GPIO.setup(PIN_TRIGGER_BOTTOM, GPIO.OUT)
    GPIO.setup(PIN_ECHO_BOTTOM, GPIO.IN)
    print("GPIO Setup Complete.")

# Sensor Initialization
def init_sensors():
    bus.write_byte_data(ACCEL_I2C_ADDR, 0x20, 0x57)
    bus.write_byte_data(ACCEL_I2C_ADDR, 0x23, 0x00)
    bus.write_byte_data(GYRO_I2C_ADDR, 0x15, 0x09)
    bus.write_byte_data(GYRO_I2C_ADDR, 0x16, 0x18)
    print("Accelerometer and Gyroscope Initialization Complete.")
    
    # Configure VEML6030 light sensor
    bus.write_byte_data(VEML6030_ADDRESS, REGISTER_CTRL, 0x00)  # Configure register
    print("VEML6030 Light Sensor Initialization Complete.")

# LED 
def control_leds(state):
    active_flags['lighting_on'] = state
    for pin in LED_PINS:
        GPIO.output(pin, GPIO.HIGH if state else GPIO.LOW)
    print(f"LED {'ON' if state else 'OFF'}")

# Get Distance
def get_distance(PIN_TRIGGER, PIN_ECHO):
    GPIO.output(PIN_TRIGGER, GPIO.LOW)
    time.sleep(0.1)
    GPIO.output(PIN_TRIGGER, GPIO.HIGH)
    time.sleep(0.00001)
    GPIO.output(PIN_TRIGGER, GPIO.LOW)

    timeout = time.time() + 1
    pulse_start_time = time.time()
    while GPIO.input(PIN_ECHO) == 0 and time.time() < timeout:
        pulse_start_time = time.time()

    if time.time() >= timeout:
        print("Waiting for ECHO HIGH timeout")
        return None

    timeout = time.time() + 1
    pulse_end_time = time.time()
    while GPIO.input(PIN_ECHO) == 1 and time.time() < timeout:
        pulse_end_time = time.time()

    if time.time() >= timeout:
        print("Waiting for ECHO LOW timeout")
        return None

    pulse_duration = pulse_end_time - pulse_start_time
    distance = round(pulse_duration * 17150, 2)

    print(f"FROM PIN_TRIGGER {PIN_TRIGGER} GET DISTANCE: {distance} cm")
    return distance

# Get Acceleration
def read_acceleration():
    x = (bus.read_byte_data(ACCEL_I2C_ADDR, 0x29) << 8) | bus.read_byte_data(ACCEL_I2C_ADDR, 0x28)
    y = (bus.read_byte_data(ACCEL_I2C_ADDR, 0x2B) << 8) | bus.read_byte_data(ACCEL_I2C_ADDR, 0x2A)
    z = (bus.read_byte_data(ACCEL_I2C_ADDR, 0x2D) << 8) | bus.read_byte_data(ACCEL_I2C_ADDR, 0x2C)

    scale = 0.000061 * 9.81
    x = (x if x < 32768 else x - 65536) * scale
    y = (y if y < 32768 else y - 65536) * scale
    z = (z if z < 32768 else z - 65536) * scale

    print(f"Acceleration - X: {x:.2f}, Y: {y:.2f}, Z: {z:.2f}")
    return x, y, z

# Get Gyroscope Data
def read_gyro_data():
    x_rate = (bus.read_byte_data(GYRO_I2C_ADDR, 0x1D) << 8) | bus.read_byte_data(GYRO_I2C_ADDR, 0x1E)
    y_rate = (bus.read_byte_data(GYRO_I2C_ADDR, 0x1F) << 8) | bus.read_byte_data(GYRO_I2C_ADDR, 0x20)
    z_rate = (bus.read_byte_data(GYRO_I2C_ADDR, 0x21) << 8) | bus.read_byte_data(GYRO_I2C_ADDR, 0x22)

    sensitivity = 0.061
    x_rate = (x_rate if x_rate < 32768 else x_rate - 65536) * sensitivity
    y_rate = (y_rate if y_rate < 32768 else y_rate - 65536) * sensitivity
    z_rate = (z_rate if z_rate < 32768 else z_rate - 65536) * sensitivity

    print(f"Gyroscope - X: {x_rate:.2f}, Y: {y_rate:.2f}, Z: {z_rate:.2f}")
    return x_rate, y_rate, z_rate

# GPS
def getGPS(ser):
    lat = 0.0
    lon = 0.0
    latFind = False
    lonFind = False
    while not latFind or not lonFind:
        data = ser.readline().decode('utf-8', errors='ignore')
        if "Latitude" in data and not latFind:
            lat = float(data.strip().split(":")[1])
            latFind = True
        if "Longitude" in data and not lonFind:
            lon = float(data.strip().split(":")[1])
            lonFind = True
    return [lat, lon]


# Lighting Button Monitor
async def monitor_button_state():
    while True:
        switch_state = GPIO.input(SWITCH_PIN)
        if switch_state == GPIO.LOW:
            await asyncio.sleep(0.1)  
            if GPIO.input(SWITCH_PIN) == GPIO.LOW:
                active_flags['manual_override'] = not active_flags['manual_override']  # 切换手动覆盖状态
                active_flags['lighting_on'] = not active_flags['lighting_on']  # 切换 LED 状态
                control_leds(active_flags['lighting_on'])  # 根据新的状态更新 LED

                await sio.emit('lighting_update_from_pi', {
                    'module_type': 'lighting',
                    'lighting_status': 'on' if active_flags['lighting_on'] else 'off'
                })
                
                print(f"Manual override: {'Activated' if active_flags['manual_override'] else 'Deactivated'}")

                while GPIO.input(SWITCH_PIN) == GPIO.LOW:
                    await asyncio.sleep(0.1)
        await asyncio.sleep(0.1)

# Obstacle Detection
async def obstacle_detection():
    print("Obstacle Detection Started.")
    while active_flags['obstacle']:
        distance_middle = get_distance(PIN_TRIGGER_MID, PIN_ECHO_MID)
        distance_bottom = get_distance(PIN_TRIGGER_BOTTOM, PIN_ECHO_BOTTOM)

        obstacle_detected = False

        if distance_middle is not None and distance_bottom is not None:
            if distance_middle < 30 or distance_bottom < 30:
                obstacle_detected = True
            if obstacle_detected:
                GPIO.output(BUZZER_PIN_OBSTACLE, GPIO.HIGH)
                print("Buzzers On - Obstacle Detected!")
            else:
                GPIO.output(BUZZER_PIN_OBSTACLE, GPIO.LOW)
                print("Buzzers Off - Safe.")
        else:
            print("Error getting distance.")

        timestamp = datetime.now(perth_tz).strftime('%Y-%m-%d %H:%M:%S')
        
        data_to_send = {
            'module_type': 'obstacle',
            'obstacleDetected_status': 'obstacle_detected' if obstacle_detected else 'safe',
            'middle_distance': distance_middle,
            'bottom_distance': distance_bottom,
            'timestamp': timestamp
        }

        await sio.emit('obstacle_update_from_pi', data_to_send)

        if not active_flags['obstacle']:
            break  
        await asyncio.sleep(1)  

# Fall Detection
async def fall_detection():
    print("Fall Detection Started.")
    prev_acc_x, prev_acc_y, prev_acc_z = read_acceleration()
    prev_gyro_x, prev_gyro_y, prev_gyro_z = read_gyro_data()

    while active_flags['falling']:
        acc_x, acc_y, acc_z = read_acceleration()
        gyro_x, gyro_y, gyro_z = read_gyro_data()

        fall_detected = False

        delta_acc_x = abs(acc_x - prev_acc_x)
        delta_acc_y = abs(acc_y - prev_acc_y)
        delta_acc_z = abs(acc_z - prev_acc_z)
        delta_gyro_x = abs(gyro_x - prev_gyro_x)
        delta_gyro_y = abs(gyro_y - prev_gyro_y)
        delta_gyro_z = abs(gyro_z - prev_gyro_z)

        # Set angular velocity thresholds
        threshold_gyro_x = 150  # X-axis angular velocity threshold
        threshold_gyro_y = 120  # Y-axis angular velocity threshold
        threshold_gyro_z = 200  # Z-axis angular velocity threshold

        # Detect sudden change in any axis
        if (delta_acc_x > 9 or delta_acc_y > 9 or delta_acc_z > 9 or
            delta_gyro_x > threshold_gyro_x or delta_gyro_y > threshold_gyro_y or delta_gyro_z > threshold_gyro_z):
            fall_detected = True
        
        if fall_detected:
            GPIO.output(BUZZER_PIN_FALL, GPIO.HIGH)
            print("Buzzers On - Fall Detected!")
        else:
            GPIO.output(BUZZER_PIN_FALL, GPIO.LOW)
            print("Buzzers Off - Safe.")

        data_to_send = {
            'module_type': 'falling',
            'fall_status': 'fall_detected' if fall_detected else 'safe',
            'acceleration': {'x': acc_x, 'y': acc_y, 'z': acc_z},
            'gyroscope': {'x': gyro_x, 'y': gyro_y, 'z': gyro_z},
            'timestamp': datetime.now(perth_tz).strftime('%Y-%m-%d %H:%M:%S')
        }

        latest_gps = active_flags.get('latest_gps')
        if active_flags.get('gps') and latest_gps:
            data_to_send['gps'] = latest_gps
        else:
            data_to_send['gps'] = None
        
        print(f"Data to send from fall_detection: {data_to_send}")
        
        await sio.emit('falling_update_from_pi', data_to_send)

        if not active_flags['falling']:
            break  
        prev_acc_x, prev_acc_y, prev_acc_z = acc_x, acc_y, acc_z
        prev_gyro_x, prev_gyro_y, prev_gyro_z = gyro_x, gyro_y, gyro_z

        await asyncio.sleep(0.5)

# GPS Tracking
async def gps_tracking():
    print("GPS Tracking Started.")
    try:
        # 替换 '/dev/ttyACM0' 为您的 GPS 模块的正确串口
        gps_serial = serial.Serial('/dev/ttyACM0', 115200, timeout=1)
        while active_flags['gps']:
            try:
                lat, lon = getGPS(gps_serial)
                timestamp = datetime.now(perth_tz).strftime('%Y-%m-%d %H:%M:%S')
                print(f"GPS Data - Latitude: {lat}, Longitude: {lon}, Time: {timestamp}")
                
                active_flags['latest_gps'] = {'latitude': lat, 'longitude': lon}
                
                data_to_send = {
                    'module_type': 'gps',
                    'latitude': lat,
                    'longitude': lon,
                    'timestamp': timestamp
                }
                await sio.emit('gps_update_from_pi', data_to_send)
            except Exception as e:
                print(f"Error getting GPS data: {e}")
            await asyncio.sleep(1)
        gps_serial.close()
        print("GPS Tracking Stopped.")
    except serial.SerialException as e:
        print(f"Serial exception: {e}")

# Light Sensor Monitor
async def light_sensor_monitor():
    print("Light Sensor Monitor Started.")
    while True:
        try:
            # Read light sensor value
            data = bus.read_i2c_block_data(VEML6030_ADDRESS, REGISTER_WHITE, 2)
            white_light = (data[1] << 8) | data[0]  # Convert to integer
            print(f"Current light intensity: {white_light} lux")

            # Check light intensity if manual_override is not active
            if not active_flags['manual_override']:
                if white_light < LIGHT_THRESHOLD:
                    print("Light is low, turning ON the LED")
                    if not active_flags['lighting_on']:
                        control_leds(True)
                        active_flags['lighting_on'] = True
                        # 发送照明状态到前端
                        await sio.emit('lighting_update_from_pi', {
                            'module_type': 'lighting',
                            'lighting_status': 'on'
                        })
                else:
                    print("Light is sufficient, turning OFF the LED")
                    if active_flags['lighting_on']:
                        control_leds(False)
                        active_flags['lighting_on'] = False
                        # 发送照明状态到前端
                        await sio.emit('lighting_update_from_pi', {
                            'module_type': 'lighting',
                            'lighting_status': 'off'
                        })
            else:
                print("Manual override is active. Skipping automatic control.")

            await asyncio.sleep(1)  # Read the light value every second
        except Exception as e:
            print(f"Error in light_sensor_monitor: {e}")
            await asyncio.sleep(1)


# Socket.IO Event Handlers
@sio.event
async def connect():
    print('Connected to Flask-SocketIO Server')

@sio.event
async def disconnect():
    print('Disconnected from Flask-SocketIO Server')

@sio.on('toggle_lighting')
async def handle_toggle_lighting(data):
    try:
        status = data['status']
        active_flags['manual_override'] = True  # 前端覆盖手动控制

        active_flags['lighting_on'] = status == 'on'
        control_leds(active_flags['lighting_on'])

        await sio.emit('lighting_update_from_pi', {
            'module_type': 'lighting',
            'lighting_status': 'on' if active_flags['lighting_on'] else 'off'
        })

        print(f"Lighting toggled from frontend. Manual override activated.")
    except Exception as e:
        print(f"Error handling toggle_lighting event: {e}")

@sio.on('toggle_obstacle_detection')
async def handle_toggle_obstacle_detection(data):
    try:
        status = data['status']
        if status == 'on':
            active_flags['obstacle'] = True
            asyncio.create_task(obstacle_detection())
            print("Obstacle Detection Started.")
        else:
            active_flags['obstacle'] = False
            GPIO.output(BUZZER_PIN_OBSTACLE, GPIO.LOW)
            print("Obstacle Detection Stopped.")
    except Exception as e:
        print(f"Error handling toggle_obstacle_detection event: {e}")

@sio.on('toggle_fall_detection')
async def handle_toggle_fall_detection(data):
    try:
        status = data['status']
        if status == 'on':
            active_flags['falling'] = True
            asyncio.create_task(fall_detection())
            print("Fall Detection Started.")
        else:
            active_flags['falling'] = False
            GPIO.output(BUZZER_PIN_FALL, GPIO.LOW)
            print("Fall Detection Stopped.")
    except Exception as e:
        print(f"Error handling toggle_fall_detection event: {e}")

@sio.on('toggle_gps_tracking')
async def handle_toggle_gps_tracking(data):
    try:
        status = data['status']
        if status == 'on':
            active_flags['gps'] = True
            asyncio.create_task(gps_tracking())
            print("GPS Tracking Started.")
        else:
            active_flags['gps'] = False
            print("GPS Tracking Stopped.")
    except Exception as e:
        print(f"Error handling toggle_gps_tracking event: {e}")


# Main Function
async def main():
    try:
        print("Starting Server.")
        setup_gpio()
        init_sensors()

        await sio.connect(FLASK_SERVER_URL)

        asyncio.create_task(monitor_button_state())
        asyncio.create_task(light_sensor_monitor())  # 启动灯光传感器监控

        await sio.wait()
    except asyncio.CancelledError:
        print("Cancelled Error caught, shutting down gracefully...")
    except Exception as e:
        print(f"Unexpected error occurred: {e}")
    finally:
        GPIO.cleanup()
        print("GPIO Cleanup Complete.")

if __name__ == '__main__':
    try:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        print("Server Stopped.")
    finally:
        GPIO.cleanup()
        print("GPIO Cleanup Complete.")
