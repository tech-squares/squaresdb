import logging

from django.conf import settings
from django.core.mail.backends import smtp
from django.core.mail.message import sanitize_address

logger = logging.getLogger(__name__)

class ForcedRecipientEmailBackend(smtp.EmailBackend):
    def _send(self, email_message):
        """A helper method that does the actual sending.
        """
        if not email_message.recipients():
            return False
        if settings.EMAIL_FORCED_RECIPIENTS_LABEL not in email_message.to:
            email_message.to.append(settings.EMAIL_FORCED_RECIPIENTS_LABEL)
        from_email = sanitize_address(email_message.from_email, email_message.encoding)
        recipients = [sanitize_address(addr, email_message.encoding)
                      for addr in settings.EMAIL_FORCED_RECIPIENTS]
        logger.debug("Sending '%s' from '%s' to '%s' recpts '%s'",
            email_message.subject, email_message.from_email,
            email_message.to, recipients)
        message = email_message.message()
        try:
            self.connection.sendmail(from_email, recipients, message.as_bytes(linesep='\r\n'))
        except smtplib.SMTPException:
            if not self.fail_silently:
                raise
            return False
        return True

class AutoBccEmailBackend(smtp.EmailBackend):
    def _send(self, email_message):
        if settings.EMAIL_AUTO_BCC not in email_message.bcc:
            email_message.bcc.extend(settings.EMAIL_AUTO_BCC)
        logger.debug("Sending '%s' from '%s' to '%s' bcc '%s'",
            email_message.subject, email_message.from_email,
            email_message.to, email_message.bcc)
        return super(AutoBccEmailBackend,self)._send(email_message)
