import GPSModule.GPSModule as gps
import EmailModule as email # Import your EmailModule to use the send_email function
import SmartCaneModule as smartcane # Import your fall detection module here
import serial
import asyncio

# Initialize the GPS port
GPSPort = serial.Serial('/dev/ttyACM0', 115200)

# Function to send email
def send_email_if_fall_detected():
    # Get the GPS data
    gps_data = gps.getGPS(GPSPort)
    print(gps_data)

    # Compose the email
    subject = "Fall Detected! GPS Information"
    body = f"Fall detected! Here is the GPS info:\n{gps_data}"
    recipient = "recipient_email@example.com"  # Replace with the actual recipient email

    # Send the email
    email.send_email(recipient, subject, body)
    print("Fall detected and email sent with GPS data.")

async def monitor_fall_detection():
    print("Monitoring fall detection...")
    while True:
        if await smartcane.fall_detection():  # If the fall_detection detects a fall
            send_email_if_fall_detected()
            await asyncio.sleep(1)  # Add a delay to avoid multiple email triggers
        await asyncio.sleep(1)  # Monitor fall detection every second

async def main():
    # Your other initialization steps if needed
    # Initialize sensors and GPIO
    smartcane.init_sensors()
    smartcane.setup_gpio()
    # Initialize fall detection monitoring as an async task
    asyncio.create_task(monitor_fall_detection())
    
    # Start other asynchronous tasks as required by your application
    await asyncio.sleep(1)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Program stopped.")
    finally:
        print("Cleanup completed.")


# Send a test email using the send_email function from EmailModule
recipient = "anirudhmenon1@gmail.com"
subject = "Test Email"
text = "This is a test email from the EmailModule."

email.send_email(recipient, subject, text)
