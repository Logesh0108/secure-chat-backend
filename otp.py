import random
import smtplib
from email.message import EmailMessage
from datetime import datetime, timedelta

OTP_STORE = {}

def generate_otp(email: str):
    otp = random.randint(100000, 999999)
    expiry = datetime.utcnow() + timedelta(minutes=4)

    OTP_STORE[email] = {
        "otp": str(otp),
        "expiry": expiry
    }

    return otp

def send_email(email: str, otp: str):
    msg = EmailMessage()
    msg.set_content(f"Your Secure Chat OTP is {otp}. It expires in 4 minutes.")
    msg["Subject"] = "Secure Chat OTP"
    msg["From"] = "yourmail@gmail.com"
    msg["To"] = email

    server = smtplib.SMTP("smtp.gmail.com", 587)
    server.starttls()
    server.login("yourmail@gmail.com", "APP_PASSWORD")
    server.send_message(msg)
    server.quit()
