# app/utils/email.py
from threading import Thread
from flask import current_app, render_template
from flask_mail import Message
from .. import mail

def send_async_email(app, msg):
    """Background thread for sending email."""
    with app.app_context():
        try:
            mail.send(msg)
        except Exception as e:
            print(f"Failed to send email: {e}")

def send_email(to, subject, template, **kwargs):
    """Prepare and send an email in a background thread."""
    app = current_app._get_current_object()
    msg = Message(
        subject,
        sender=('SCNFBS Admin', app.config['MAIL_USERNAME']),
        recipients=[to]
    )
    msg.html = render_template(template, **kwargs)
    thr = Thread(target=send_async_email, args=[app, msg])
    thr.start()
    return thr