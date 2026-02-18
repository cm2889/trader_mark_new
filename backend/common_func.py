from threading import Thread
from django.conf import settings
from django.template.loader import render_to_string
from django.core.mail import EmailMultiAlternatives, get_connection

from backend.models import UserMenuPermission


def checkUserPermission(request, access_type, menu_url):
    try:
        user_permissions = {
            "can_view": "can_view",
            "can_add": "can_add",
            "can_update": "can_update",
            "can_delete": "can_delete",
        }

        if request.user.is_superuser:
            return True

        check_user_permission = UserMenuPermission.objects.filter(
            user_id=request.user.id, is_active=True, **{user_permissions[access_type]: True}, menu__menu_url=menu_url,
        )

        if check_user_permission:
            return True
        else:
            return False
    except Exception:
        return False


def send_email(mail_to, cc_list, bcc_list, subject, template, context):
    def send_email_thread(mail_to, cc_list, bcc_list, subject, template, context):
        # Remove duplicates between TO and CC
        mail_to_set = set(mail_to or [])
        cc_list_set = set(cc_list or [])
        cc_list_set -= mail_to_set

        mail_to = list(mail_to_set)
        cc_list = list(cc_list_set)

        # Render HTML content
        html_body = render_to_string(template, context)

        # Read email config from Django settings (.env)
        email_host = getattr(settings, 'EMAIL_HOST', '')
        email_port = getattr(settings, 'EMAIL_PORT', 587)
        email_host_user = getattr(settings, 'EMAIL_HOST_USER', '')
        email_host_password = getattr(settings, 'EMAIL_HOST_PASSWORD', '')
        email_use_tls = getattr(settings, 'EMAIL_USE_TLS', True)
        email_use_ssl = getattr(settings, 'EMAIL_USE_SSL', False)

        if not email_host_user:
            print("EMAIL_HOST_USER not configured in .env. Email not sent.")
            return

        # Prepare email backend connection from Django settings
        connection = get_connection(
            host=email_host,
            port=email_port,
            username=email_host_user,
            password=email_host_password,
            use_tls=email_use_tls,
            use_ssl=email_use_ssl,
        )

        # Build the email
        email = EmailMultiAlternatives(
            subject=subject,
            from_email=email_host_user,
            to=mail_to,
            cc=cc_list,
            bcc=bcc_list or [],
            body=subject,
            connection=connection
        )
        email.attach_alternative(html_body, "text/html")

        # Send email
        try:
            email.send()
            print(f"Email sent to {mail_to}")
        except Exception as e:
            print(f"Error sending email: {e}")

    # Start async thread
    Thread(target=send_email_thread, args=(mail_to, cc_list, bcc_list, subject, template, context)).start()
