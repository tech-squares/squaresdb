from django.core.management.base import BaseCommand, CommandError

from squaresdb.gate.models import PaymentMethod, SubscriptionPeriod, SubscriptionPayment

import reversion

class Command(BaseCommand):
    help = 'Copies subscriptions between periods'

    def add_arguments(self, parser):
        parser.add_argument('from')
        parser.add_argument('to')
        parser.add_argument('--comment')

    def handle(self, *args, **options):
        try:
            from_period = SubscriptionPeriod.objects.get(slug=options['from'])
            to_period = SubscriptionPeriod.objects.get(slug=options['to'])
        except SubscriptionPeriod.DoesNotExist:
            raise CommandError('Period %s or %s does not exist' %
                               (options['from'], options['to']))

        comment = options['comment']
        if not comment:
            comment = "bulk sub copy from %s to %s" % (options['from'], options['to'])

        payment_type = PaymentMethod.objects.get(slug='cash')
        from_payments = SubscriptionPayment.objects.filter(periods=from_period)
        from_payments = from_payments.select_related('person')
        paid_emails = []
        no_emails = []
        with reversion.create_revision(atomic=True):
            reversion.set_comment("bulk sub copy: " + comment)
            for payment in from_payments:
                # Copy the sub
                kwargs = dict(person=payment.person, payment_type=payment_type,
                              amount=0, notes=comment)
                new_pay = SubscriptionPayment(**kwargs)
                new_pay.save()
                new_pay.periods.add(to_period)

                # Build a list of emails
                name = payment.person.name
                assert '"' not in name
                assert '<' not in payment.person.email
                assert '>' not in payment.person.email
                emails = payment.person.email.split(',')
                for email in emails:
                    if email:
                        email_str = '"%s" <%s>' % (name, email.strip())
                        paid_emails.append(email_str)
                    else:
                        no_emails.append(name)

        msg = 'Copied %d subscriptions' % (len(from_payments, ))
        self.stdout.write(self.style.SUCCESS(msg))
        self.stdout.write(self.style.SUCCESS("Emails: ") + ', '.join(paid_emails))
        self.stdout.write(self.style.WARNING("No emails: ") + ', '.join(no_emails))
