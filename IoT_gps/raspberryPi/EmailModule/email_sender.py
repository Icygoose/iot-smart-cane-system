import smtplib

# Gmail mail settings
GmailMAIL_USER = 'anirudhmenon1@gmail.com'  # Replace with your actual email
GmailMAIL_PASS = 'sbvf gaac pyie qabw'      # Replace with your app-specific password

SMTP_SERVER = 'smtp.gmail.com'
SMTP_PORT = 465

# Function to send an email
def send_email(recipient, subject, text):
    smtpserver = smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT)  # Use SMTP_SSL for secure connection
    smtpserver.login(GmailMAIL_USER, GmailMAIL_PASS)
    
    header = 'To:' + recipient + '\n' + 'From: ' + GmailMAIL_USER
    header += '\n' + 'Subject: ' + subject + '\n'
    msg = header + '\n' + text + '\n\n'
    
    try:
        smtpserver.sendmail(GmailMAIL_USER, recipient, msg)
        print("Email sent successfully.")
    except Exception as e:
        print(f"Failed to send email: {e}")
    finally:
        smtpserver.close()

# Test the email sending functionality
if __name__ == "__main__":
    recipient = "anirudhmenon1@gmail.com"  # Replace with the email address you want to send a test email to
    subject = "Test Email"
    text = "This is a test email from the email_sender.py module."

    send_email(recipient, subject, text)