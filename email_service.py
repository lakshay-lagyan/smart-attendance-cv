import os
import random
import string
from datetime import datetime, timedelta
from flask import current_app

class EmailService:
    """Email service for sending verification codes and notifications"""
    
    def __init__(self):
        self.enabled = os.getenv('EMAIL_ENABLED', 'false').lower() == 'true'
        self.smtp_host = os.getenv('SMTP_HOST', 'smtp.gmail.com')
        self.smtp_port = int(os.getenv('SMTP_PORT', 587))
        self.smtp_user = os.getenv('SMTP_USER', '')
        self.smtp_password = os.getenv('SMTP_PASSWORD', '')
        self.from_email = os.getenv('FROM_EMAIL', 'noreply@smartattendance.com')
        self.from_name = os.getenv('FROM_NAME', 'Smart Attendance System')
    
    def generate_verification_code(self, length=6):
        """Generate a random verification code"""
        return ''.join(random.choices(string.digits, k=length))
    
    def send_verification_code(self, to_email, code, user_name):
        """Send verification code to user's email"""
        if not self.enabled:
            current_app.logger.info(f'Email service disabled. Verification code for {to_email}: {code}')
            return True
        
        try:
            import smtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart
            
            subject = 'Verify Your Email - Smart Attendance System'
            
            html_body = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                    .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                    .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
                    .code-box {{ background: white; border: 2px dashed #667eea; padding: 20px; text-align: center; margin: 20px 0; border-radius: 8px; }}
                    .code {{ font-size: 32px; font-weight: bold; letter-spacing: 8px; color: #667eea; }}
                    .footer {{ text-align: center; margin-top: 20px; color: #666; font-size: 14px; }}
                    .button {{ display: inline-block; background: #667eea; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; margin: 20px 0; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>Email Verification</h1>
                    </div>
                    <div class="content">
                        <p>Hello {user_name},</p>
                        <p>Thank you for joining Smart Attendance System! Your signup request has been approved by the administrator.</p>
                        <p>Please verify your email address using the verification code below:</p>
                        
                        <div class="code-box">
                            <div class="code">{code}</div>
                        </div>
                        
                        <p>This code will expire in 24 hours.</p>
                        <p>If you didn't request this verification, please ignore this email.</p>
                        
                        <div class="footer">
                            <p>&copy; 2024 Smart Attendance System. All rights reserved.</p>
                        </div>
                    </div>
                </div>
            </body>
            </html>
            """
            
            message = MIMEMultipart('alternative')
            message['Subject'] = subject
            message['From'] = f'{self.from_name} <{self.from_email}>'
            message['To'] = to_email
            
            html_part = MIMEText(html_body, 'html')
            message.attach(html_part)
            
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                if self.smtp_user and self.smtp_password:
                    server.login(self.smtp_user, self.smtp_password)
                server.send_message(message)
            
            current_app.logger.info(f'Verification email sent to {to_email}')
            return True
            
        except Exception as e:
            current_app.logger.error(f'Failed to send verification email to {to_email}: {str(e)}')
            return False
    
    def send_approval_notification(self, to_email, user_name):
        """Send approval notification without verification (direct approval)"""
        if not self.enabled:
            current_app.logger.info(f'Email service disabled. Approval notification for {to_email}')
            return True
        
        try:
            import smtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart
            
            subject = 'Account Approved - Smart Attendance System'
            
            html_body = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                    .header {{ background: linear-gradient(135deg, #10b981 0%, #059669 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                    .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
                    .button {{ display: inline-block; background: #10b981; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; margin: 20px 0; }}
                    .footer {{ text-align: center; margin-top: 20px; color: #666; font-size: 14px; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>✓ Account Approved!</h1>
                    </div>
                    <div class="content">
                        <p>Hello {user_name},</p>
                        <p>Great news! Your account has been approved by the administrator.</p>
                        <p>You can now log in to the Smart Attendance System and start using all features.</p>
                        
                        <div style="text-align: center;">
                            <a href="{os.getenv('APP_URL', 'http://localhost:5000')}/login" class="button">Login Now</a>
                        </div>
                        
                        <div class="footer">
                            <p>&copy; 2024 Smart Attendance System. All rights reserved.</p>
                        </div>
                    </div>
                </div>
            </body>
            </html>
            """
            
            message = MIMEMultipart('alternative')
            message['Subject'] = subject
            message['From'] = f'{self.from_name} <{self.from_email}>'
            message['To'] = to_email
            
            html_part = MIMEText(html_body, 'html')
            message.attach(html_part)
            
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                if self.smtp_user and self.smtp_password:
                    server.login(self.smtp_user, self.smtp_password)
                server.send_message(message)
            
            current_app.logger.info(f'Approval notification sent to {to_email}')
            return True
            
        except Exception as e:
            current_app.logger.error(f'Failed to send approval notification to {to_email}: {str(e)}')
            return False

# Create global instance
email_service = EmailService()
