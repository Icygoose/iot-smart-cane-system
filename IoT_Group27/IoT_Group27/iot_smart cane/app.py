from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO, emit
import smtplib
import config
import time
from threading import Lock
from datetime import datetime, timedelta
import pytz
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import func
from math import radians, sin, cos, sqrt, atan2

app = Flask(__name__)
app.config.from_object('config.DevelopmentConfig')

db = SQLAlchemy(app)
socketio = SocketIO(app, async_mode='threading')  

last_fall_alert_time = 0
FALL_ALERT_INTERVAL = 60
in_fall_event = False  # Whether the device is currently in a fall event
fall_safe_start_time = None 
FALL_EVENT_RESET_TIME = 10 # Time in seconds after which the fall event is reset

# Define database models
class ObstacleEvent(db.Model):
    __tablename__ = 'obstacle_event'
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    middle_distance = db.Column(db.Float)
    bottom_distance = db.Column(db.Float)
    obstacle_detected = db.Column(db.Boolean)

class FallEvent(db.Model):
    __tablename__ = 'fall_event'
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)

class LightingEvent(db.Model):
    __tablename__ = 'lighting_event'
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(10))  # 'on' or'off'

class LocationEvent(db.Model):
    __tablename__ = 'location_event'
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)

# Flask route
@app.route('/')
def index():
    try:
        # Fetch data from database
        obstacle_events = ObstacleEvent.query.all()
        fall_events = FallEvent.query.all()
        lighting_events = LightingEvent.query.all()
        location_events = LocationEvent.query.all()
        
        # Obstacle detection statistics
        now = datetime.utcnow()
        obstacle_counts_per_hour = [0]*24
        fall_counts_per_hour = [0]*24

        for event in obstacle_events:
            if event.obstacle_detected:
                hours_ago = int((now - event.timestamp).total_seconds() // 3600)
                if 0 <= hours_ago < 24:
                    obstacle_counts_per_hour[23 - hours_ago] += 1  # Latest hour at index 23
        
        for event in fall_events:
            hours_ago = int((now - event.timestamp).total_seconds() // 3600)
            if 0 <= hours_ago < 24:
                fall_counts_per_hour[23 - hours_ago] += 1
        
        start_of_day = datetime(now.year, now.month, now.day)
        obstacle_events_today = ObstacleEvent.query.filter(
            ObstacleEvent.timestamp >= start_of_day,
            ObstacleEvent.obstacle_detected == True
        ).count()

        # Fall detection statistics
        falls_per_day = []
        for i in range(7):
            day = start_of_day - timedelta(days=i)
            next_day = start_of_day - timedelta(days=i-1)
            falls_count = FallEvent.query.filter(
                FallEvent.timestamp >= day,
                FallEvent.timestamp < next_day
            ).count()
            falls_per_day.append({'date': day.strftime('%Y-%m-%d'), 'count': falls_count})
        
        total_falls_this_week = sum(item['count'] for item in falls_per_day)
        
        # Top 3 fall locations
        fall_locations = db.session.query(
            func.round(FallEvent.latitude, 2).label('lat'),
            func.round(FallEvent.longitude, 2).label('lon'),
            func.count().label('count')
        ).group_by('lat', 'lon').order_by(func.count().desc()).limit(3).all()

        # GPS tracking analysis
        location_events = sorted(location_events, key=lambda x: x.timestamp)

        def haversine(lat1, lon1, lat2, lon2):
            R = 6371.0  # Earth radius in km
            lat1_rad = radians(lat1)
            lon1_rad = radians(lon1)
            lat2_rad = radians(lat2)
            lon2_rad = radians(lon2)
            dlon = lon2_rad - lon1_rad
            dlat = lat2_rad - lat1_rad
            a = sin(dlat / 2)**2 + cos(lat1_rad) * cos(lat2_rad) * sin(dlon / 2)**2
            c = 2 * atan2(sqrt(a), sqrt(1 - a))
            distance = R * c  # in km
            return distance

        def cluster_locations(events, distance_threshold=0.01, time_threshold=300):
            clusters = []
            current_cluster = []
            last_event = None
            for event in events:
                if last_event is None:
                    current_cluster.append(event)
                else:
                    dist = haversine(last_event.latitude, last_event.longitude, event.latitude, event.longitude)
                    time_diff = (event.timestamp - last_event.timestamp).total_seconds()
                    if dist <= distance_threshold and time_diff <= time_threshold:
                        current_cluster.append(event)
                    else:
                        if current_cluster:
                            clusters.append(current_cluster)
                        current_cluster = [event]
                last_event = event
            if current_cluster:
                clusters.append(current_cluster)
            return clusters

        clusters = cluster_locations(location_events)
        location_times = []
        for cluster in clusters:
            if len(cluster) >= 2:
                start_time = cluster[0].timestamp
                end_time = cluster[-1].timestamp
                total_time = (end_time - start_time).total_seconds()
                avg_lat = sum(event.latitude for event in cluster) / len(cluster)
                avg_lon = sum(event.longitude for event in cluster) / len(cluster)
                location_times.append({'lat': avg_lat, 'lon': avg_lon, 'time_spent': total_time})

        # Top 5 location times
        top_locations = sorted(location_times, key=lambda x: x['time_spent'], reverse=True)[:5]

        # Calculate daily distance and time spent
        daily_distance = 0.0
        daily_time = 0.0
        today_location_events = [event for event in location_events if event.timestamp >= start_of_day]

        if len(today_location_events) >= 2:
            for i in range(1, len(today_location_events)):
                event1 = today_location_events[i - 1]
                event2 = today_location_events[i]
                dist = haversine(event1.latitude, event1.longitude, event2.latitude, event2.longitude)
                if dist >= 0.01:
                    daily_distance += dist
                    time_diff = (event2.timestamp - event1.timestamp).total_seconds()
                    daily_time += time_diff

        # Render HTML template
        return render_template('index.html',
                               total_obstacle_events=len(obstacle_events) if obstacle_events else 0,
                               total_fall_events=len(fall_events) if fall_events else 0,
                               total_lighting_on=sum(1 for event in lighting_events if event.status == 'on') if lighting_events else 0,
                               total_lighting_off=sum(1 for event in lighting_events if event.status == 'off') if lighting_events else 0,
                               obstacle_counts_per_hour=obstacle_counts_per_hour,
                               fall_counts_per_hour=fall_counts_per_hour,
                               obstacle_events_today=obstacle_events_today,
                               total_falls_this_week=total_falls_this_week,
                               falls_per_day=falls_per_day,
                               fall_locations=fall_locations,
                               top_locations=top_locations,
                               daily_distance=daily_distance,
                               daily_time=daily_time
                               )
    except SQLAlchemyError as e:
        app.logger.error(f"Database error: {e}")
        return "Internal Server Error", 500
    
# Send email
def send_email(recipients, subject, text):
    try:
        smtpserver = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        smtpserver.login(config.EMAIL_ADDRESS, config.EMAIL_PASSWORD)
        
        recipients_str = ', '.join(recipients)
        
        message = f"Subject: {subject}\nTo: {recipients_str}\n\n{text}"
        
        smtpserver.sendmail(config.EMAIL_ADDRESS, recipients, message)
        smtpserver.quit()
        print("Email sent successfully to:", recipients_str)
    except Exception as e:
        print(f"Failed to send email: {e}")


# Send fall alert email
def send_fall_alert_email(data):
    gps_data = data.get('gps')
    perth_tz = pytz.timezone('Australia/Perth')
    timestamp = datetime.now(perth_tz).strftime('%Y-%m-%d %H:%M:%S')
    recipient = ['24071255@student.uwa.edu.au'] #Recipient email addresses

    subject = 'Fall Detected Alert!'

    if gps_data and gps_data.get('latitude') is not None and gps_data.get('longitude') is not None:
        latitude = gps_data['latitude']
        longitude = gps_data['longitude']
        body = (
            f"Fall detected at {timestamp}.\n"
            f"GPS Location:\n"
            f"Latitude: {latitude}\n"
            f"Longitude: {longitude}\n\n"
            f"Map Link: https://www.google.com/maps/search/?api=1&query={latitude},{longitude}"
        )
    else:
        body = f"Fall detected at {timestamp}.\nGPS data is not available."

    send_email(recipient, subject, body)

    # Send message to frontend
    recipients_str = ', '.join(recipient)
    socketio.emit('fall_alert_sent', {
    'message': f'Fall detected information has been sent to {recipients_str}.',
    'fallData': data
    })


# Listen for messages from server.py
@socketio.on('lighting_update_from_pi')
def handle_lighting_update_from_pi(data):
    print(f"Received lighting update from pi: {data}")
    emit('lighting_update', data, broadcast=True)
    
    with app.app_context():
        try:
            # 保存照明事件到数据库
            new_lighting_event = LightingEvent(
                timestamp=datetime.utcnow(),
                status=data.get('lighting_status')
            )
            db.session.add(new_lighting_event)
            db.session.commit()
        except SQLAlchemyError as e:
            app.logger.error(f"Error saving lighting event to database: {e}")
            db.session.rollback()

@socketio.on('obstacle_update_from_pi')
def handle_obstacle_update_from_pi(data):
    print(f"Received obstacle update from pi: {data}")
    emit('obstacle_update', data, broadcast=True)
    
    with app.app_context():
        try:
            # Save obstacle event to database
            new_obstacle_event = ObstacleEvent(
                timestamp=datetime.utcnow(),
                middle_distance=data.get('middle_distance'),
                bottom_distance=data.get('bottom_distance'),
                obstacle_detected=(data.get('obstacleDetected_status') == 'obstacle_detected')
            )
            db.session.add(new_obstacle_event)
            db.session.commit()
        except SQLAlchemyError as e:
            app.logger.error(f"Error saving obstacle event to database: {e}")
            db.session.rollback()

lock = Lock()

@socketio.on('falling_update_from_pi')
def handle_falling_update_from_pi(data):
    global in_fall_event, fall_safe_start_time, last_fall_alert_time
    print(f"Received falling update from pi: {data}")
    emit('falling_update', data, broadcast=True)
    
    # Save fall event to database and send email if necessary
    fall_status = data.get('fall_status')
    with app.app_context():
        try:
            if fall_status == 'fall_detected':
                gps_data = data.get('gps', {})
                new_fall_event = FallEvent(
                    timestamp=datetime.utcnow(),
                    latitude=gps_data.get('latitude'),
                    longitude=gps_data.get('longitude')
                )
                db.session.add(new_fall_event)
                db.session.commit()
        except SQLAlchemyError as e:
            app.logger.error(f"Error saving fall event to database: {e}")
            db.session.rollback()
    
    current_time = time.time()

    with lock:
        if fall_status == 'fall_detected':
            if not in_fall_event:
                # Check if it's been FALL_ALERT_INTERVAL seconds since last email
                if current_time - last_fall_alert_time >= FALL_ALERT_INTERVAL:
                    print("Starting new fall event and sending email.")
                    send_fall_alert_email(data)
                    last_fall_alert_time = current_time  # Update last_fall_alert_time
                    in_fall_event = True
                else:
                    print(f"Fall detected, but last email sent {current_time - last_fall_alert_time:.2f}s ago, not sending email.")
                    in_fall_event = True
            else:
                print("Fall event already in progress, not sending email.")
            # Reset fall_safe_start_time, no matter what the fall_status is
            fall_safe_start_time = None
            print("Reset fall_safe_start_time due to fall_detected.")
        elif fall_status == 'safe':
            if in_fall_event:
                if fall_safe_start_time is None:
                    # Start timer to end fall event
                    fall_safe_start_time = current_time
                    print("Fall status is safe, starting timer to end fall event.")
                elif current_time - fall_safe_start_time >= FALL_EVENT_RESET_TIME:
                    # Fall event has been going on for FALL_EVENT_RESET_TIME seconds, end it
                    in_fall_event = False
                    fall_safe_start_time = None
                    print("Fall event ended.")
                else:
                    print(f"Fall status is safe, {current_time - fall_safe_start_time:.2f}s elapsed, waiting to end fall event.")
            else:
                fall_safe_start_time = None
                print("Not in fall event, fall_safe_start_time set to None.")
        else:
            print(f"Unknown fall_status: {fall_status}")

            
@socketio.on('gps_update_from_pi')
def handle_gps_update_from_pi(data):
    print(f"Received GPS update from pi: {data}")
    emit('gps_update', data, broadcast=True)
    
    with app.app_context():
        try:
            # Save GPS data to database
            new_location_event = LocationEvent(
                timestamp=datetime.utcnow(),
                latitude=data.get('latitude'),
                longitude=data.get('longitude')
            )
            db.session.add(new_location_event)
            db.session.commit()
        except SQLAlchemyError as e:
            app.logger.error(f"Error saving GPS data to database: {e}")
            db.session.rollback()

# Handle frontend toggle command

@socketio.on('toggle_obstacle_detection')
def handle_toggle_obstacle_detection(status):
    print(f"Received toggle obstacle detection command: {status}")
    emit('toggle_obstacle_detection', {'status': status}, namespace='/', broadcast=True)

@socketio.on('toggle_fall_detection')
def handle_toggle_fall_detection(status):
    print(f"Received toggle fall detection command: {status}")
    emit('toggle_fall_detection', {'status': status}, namespace='/', broadcast=True)

@socketio.on('toggle_gps_tracking')
def handle_toggle_gps_tracking(status):
    print(f"Received toggle GPS tracking command: {status}")
    emit('toggle_gps_tracking', {'status': status}, namespace='/', broadcast=True)
    
@socketio.on('toggle_lighting')
def handle_toggle_lighting(status):
    print(f"Received toggle lighting command: {status}")
    emit('toggle_lighting', {'status': status}, namespace='/', broadcast=True)

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000)
