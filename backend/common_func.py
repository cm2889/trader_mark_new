from threading import Thread
from django.template.loader import render_to_string
from django.core.mail import EmailMultiAlternatives, get_connection
from django.core.exceptions import ObjectDoesNotExist

from backend.models import UserMenuPermission, EmailConfiguration


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

        # Get active email config
        try:
            config = EmailConfiguration.objects.get(is_active=True)
        except ObjectDoesNotExist:
            print("No active email configuration found. Email not sent.")
            return

        # Prepare email backend connection from DB settings
        connection = get_connection(
            host=config.email_host,
            port=config.email_port,
            username=config.email_host_user,
            password=config.email_host_password,
            use_tls=config.use_tls,
            use_ssl=config.use_ssl,
        )

        # Build the email
        email = EmailMultiAlternatives(
            subject=subject,
            from_email=f"{config.email_from_name} <{config.email_host_user}>",
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
