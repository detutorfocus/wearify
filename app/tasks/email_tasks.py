from app.tasks import celery_app


@celery_app.task(queue="emails", max_retries=3, default_retry_delay=60)
def send_verification_email(user_id: str, email: str):
    try:
        from sendgrid import SendGridAPIClient
        from sendgrid.helpers.mail import Mail
        from app.core.config import settings
        from app.utils.helpers import generate_email_token

        token = generate_email_token(user_id)
        verify_url = f"{settings.FRONTEND_URL}/verify-email?token={token}"

        message = Mail(
            from_email=(settings.MAIL_FROM, settings.MAIL_FROM_NAME),
            to_emails=email,
            subject="Verify your Wearify account",
            html_content=f"""
            <div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto">
              <h2 style="color:#C9A84C">Welcome to Wearify!</h2>
              <p>Click below to verify your email address:</p>
              <a href="{verify_url}" style="background:#C9A84C;color:#0C0C10;padding:12px 28px;
                border-radius:4px;text-decoration:none;font-weight:bold;display:inline-block">
                Verify Email
              </a>
              <p style="color:#888;font-size:12px;margin-top:24px">
                This link expires in 24 hours.
              </p>
            </div>
            """,
        )
        sg = SendGridAPIClient(settings.SENDGRID_API_KEY)
        sg.send(message)
    except Exception as exc:
        raise send_verification_email.retry(exc=exc)


@celery_app.task(queue="emails", max_retries=3, default_retry_delay=60)
def send_order_confirmation_email(order_id: str, customer_email: str, order_total: float):
    try:
        from sendgrid import SendGridAPIClient
        from sendgrid.helpers.mail import Mail
        from app.core.config import settings

        message = Mail(
            from_email=(settings.MAIL_FROM, settings.MAIL_FROM_NAME),
            to_emails=customer_email,
            subject=f"Order #{order_id[:8].upper()} Confirmed — Wearify",
            html_content=f"""
            <div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto">
              <h2 style="color:#C9A84C">Order Confirmed!</h2>
              <p>Your order <strong>#{order_id[:8].upper()}</strong> has been confirmed.</p>
              <p>Total: <strong>₦{order_total:,.0f}</strong></p>
              <a href="{settings.FRONTEND_URL}/orders/{order_id}"
                style="background:#C9A84C;color:#0C0C10;padding:12px 28px;border-radius:4px;
                text-decoration:none;display:inline-block">
                Track Order
              </a>
            </div>
            """,
        )
        sg = SendGridAPIClient(settings.SENDGRID_API_KEY)
        sg.send(message)
    except Exception as exc:
        raise send_order_confirmation_email.retry(exc=exc)


@celery_app.task(queue="emails")
def send_password_reset_email(email: str, reset_token: str):
    from sendgrid import SendGridAPIClient
    from sendgrid.helpers.mail import Mail
    from app.core.config import settings

    reset_url = f"{settings.FRONTEND_URL}/reset-password?token={reset_token}"
    message = Mail(
        from_email=(settings.MAIL_FROM, settings.MAIL_FROM_NAME),
        to_emails=email,
        subject="Reset your Wearify password",
        html_content=f"""
        <div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto">
          <h2>Password Reset</h2>
          <p>Click below to reset your password. This link expires in 1 hour.</p>
          <a href="{reset_url}" style="background:#C9A84C;color:#0C0C10;
            padding:12px 28px;border-radius:4px;text-decoration:none;display:inline-block">
            Reset Password
          </a>
        </div>
        """,
    )
    sg = SendGridAPIClient(settings.SENDGRID_API_KEY)
    sg.send(message)
