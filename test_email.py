import smtplib
from email.mime.text import MIMEText

# Add the app's directory to the Python path
import sys
sys.path.insert(0, './innovation-engine')

from app import get_settings, save_setting

def send_test_email():
    """
    Connects to the configured SMTP server and sends a test email.
    """
    print("🚀 Starting SMTP email test with new password...")

    # 1. Save SMTP settings for the test
    print("   - Temporarily saving SMTP settings...")
    save_setting('smtp_server', 'smtp.gmail.com')
    save_setting('smtp_port', '587')
    save_setting('smtp_username', 'patanyaseen0852@gmail.com')
    save_setting('smtp_password', 'omddoupmdiatcwsy') # Using the new App Password
    save_setting('smtp_sender_name', 'Innovation Engine')

    # 2. Retrieve SMTP settings
    print("   - Fetching settings from the database...")
    settings = get_settings()
    smtp_server = settings.get('smtp_server')
    smtp_port = settings.get('smtp_port')
    smtp_username = settings.get('smtp_username')
    smtp_password = settings.get('smtp_password')
    smtp_sender_name = settings.get('smtp_sender_name')

    # 3. Construct the email
    recipient = "patanyaseen07@gmail.com"
    subject = "Test - Innovation Engine Email"
    body = "This is a test email to confirm the SMTP settings are working correctly."

    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = f"{smtp_sender_name} <{smtp_username}>"
    msg['To'] = recipient
    
    print(f"   - Preparing to send email to: {recipient}")

    # 4. Connect and send
    try:
        with smtplib.SMTP(smtp_server, int(smtp_port)) as server:
            print("   - Connecting to the server...")
            server.starttls()
            print("   - Starting TLS...")
            server.login(smtp_username, smtp_password)
            print("   - Logging in...")
            server.sendmail(smtp_username, [recipient], msg.as_string())
            print("   - Email sent!")
        
        print("\n" + "="*50)
        print("🎉 SUCCESS: The test email was sent successfully!")
        print("="*50)

    except smtplib.SMTPAuthenticationError as e:
        print("\n❌ ERROR: SMTP Authentication Failed.")
        print("   - The App Password or username may still be incorrect.")
        print(f"   - Exact Error: {e}")
    except Exception as e:
        print("\n❌ ERROR: An unexpected error occurred.")
        print(f"   - Exact Error: {e}")
    finally:
        # 5. Clean up the password from the database
        print("\n   - Cleaning up sensitive credentials from the database...")
        save_setting('smtp_password', '')
        print("   - Credentials cleared.")

send_test_email()
