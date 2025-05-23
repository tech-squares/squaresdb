import decimal
import logging

from typing import Any, Dict, List, Optional, Tuple # pylint:disable=unused-import

from django import forms
from django.conf import settings
from django.core import mail
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import select_template
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

import reversion

import squaresdb.money.models as money_models

logger = logging.getLogger(__name__)

class TransactionForm(forms.ModelForm):
    class Meta:
        model = money_models.Transaction
        fields = ['person_name', 'email', 'notes', ]
        labels = dict(person_name='Contact name')


class ProductLineItemForm(forms.ModelForm):
    count = forms.IntegerField(min_value=0)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs, )
        product = self.initial['product']
        self.fields['product'].disabled = True
        self.fields['count'].widget.attrs.update(size=3)

        # Replace price_each with proper validation
        max_value = (product.high if product.high and product.high <= money_models.MAX_AMOUNT
                     else None)
        self.fields['price_each'] = forms.DecimalField(min_value=product.low, max_value=max_value)
        # Caps the field at $999.99
        self.fields['price_each'].widget.attrs.update(size=5)
        if product.price():
            self.fields['price_each'].disabled = True


    def save(self, commit=True):
        super().save(commit=False)
        self.instance.amount = self.instance.count * self.instance.price_each
        self.instance.account_name = self.instance.product.account_name
        self.instance.label = self.instance.product.label
        if self.instance.count != 1:
            self.instance.label += f" ({self.instance.count}x${self.instance.price_each})"
        if commit:
            self.instance.save()
        return self.instance

    class Meta:
        model = money_models.ProductLineItem
        fields = ['product', 'count', 'price_each', ]
        widgets = dict(
            product=forms.HiddenInput(),
        )

class LineItemDescriptor:
    """View-related functions for a LineItem subclass"""

    @classmethod
    def build_formset(cls, post=None, ):
        """Return a formset for this type of LineItem"""
        raise NotImplementedError

    @classmethod
    def save_txn(cls, txn, ):
        """Given a transaction, perform final validation and create secondary rows

        Return True if this transaction can be finalized or False if it needs review.
        Any issues with it should be recorded in the transaction's admin_notes field.

        For some subtypes, `return True` may be a fine implementation.
        """
        raise NotImplementedError

_lineitem_descs: Dict[str,LineItemDescriptor] = {}
def register_lineitem(cls, ):
    _lineitem_descs[cls.name] = cls

@register_lineitem
class ProductLineItemDescriptor(LineItemDescriptor):
    """View-related functions for a LineItem subclass"""

    name = "prod"

    @classmethod
    def build_formset(cls, post=None):
        products = money_models.Product.objects.filter(active=True)
        products = products.order_by('category__order', 'order')
        initial = [
            dict(
                product=product,
                count=0, # if product.price() else 1,
                price_each=product.price(),
            ) for product in products
        ]
        formset_cls = forms.inlineformset_factory(money_models.Transaction,
                                                  money_models.ProductLineItem,
                                                  form=ProductLineItemForm,
                                                  extra=len(initial),
                                                  can_delete=False, )
        return formset_cls(post,
                           prefix='prodform',
                           queryset=money_models.ProductLineItem.objects.none(),
                           initial=initial, )

    @classmethod
    def save_txn(cls, txn, ):
        return True


def _template_list(name):
    return ['money/' + name, 'money_default/' + name]

def pay_start(request, ):
    formsets = {}
    # Handle the form
    if request.method == 'POST':
        pay_form = TransactionForm(request.POST)
        for name, desc in _lineitem_descs.items():
            formsets[name] = desc.build_formset(request.POST)
        all_valid = pay_form.is_valid()
        for formset in formsets.values():
            all_valid = all_valid and formset.is_valid()

        # TODO: Also check if they tried to pay anything, and reject if they
        # didn't. This is somewhat awkward because there's two formsets and
        # ideally we want to figure this out before we save (so we can't use
        # txn.net_amount() either, I think)

        if all_valid:
            # Save
            with reversion.create_revision(atomic=True):
                reversion.set_comment("online payment - save cart")
                if request.user.is_authenticated:
                    reversion.set_user(request.user)
                txn = pay_form.save(commit=False)
                txn.stage = money_models.Transaction.Stage.CART
                txn.save()
                for formset in formsets.values():
                    formset.instance = txn
                    formset.save()
                receipt = request.build_absolute_uri(reverse('pay:post-cybersource',
                                                             args=(txn.pk, txn.nonce, )))
                context = dict(
                    txn=txn, cybersource=settings.CYBERSOURCE_CONFIG,
                    receipt=receipt,
                    pagename='pay'
                )
                return render(request, _template_list('cybersource_pre.html'), context)
    else:
        pay_form = TransactionForm()
        for name, desc in _lineitem_descs.items():
            formsets[name] = desc.build_formset()

    context = dict(
        pay_form=pay_form, formsets=formsets,
        pagename='pay'
    )
    return render(request, _template_list('pay_start.html'), context)


@require_POST
@csrf_exempt
def pay_mock_cybersource(request, ):
    if settings.CYBERSOURCE_CONFIG_NAME != 'mock':
        raise PermissionDenied
    context = dict(
        post=request.POST,
    )
    return render(request, _template_list('cybersource_mock.html'), context)


@require_POST
@csrf_exempt
def pay_post_cybersource(request, pk, nonce, ):
    # TODO(pylint): This is probably true, but I'm not fixing it right now.
    # pylint:disable=too-many-locals,too-many-branches,too-many-statements
    logger.getChild('cybersource.post').info("Received Cybersource POST: pk=%s nonce=%s POST=%s",
                                             pk, nonce, request.POST)
    error = False
    try:
        txn = money_models.Transaction.objects.get(pk=pk, nonce=nonce, )
        expected_amount = txn.net_amount()
    except money_models.Transaction.DoesNotExist:
        logger.warning("Couldn't find transaction %s", pk)
        txn = None
        error = True
        expected_amount = 0

    try:
        amount = decimal.Decimal(request.POST['auth_amount'])
    except (KeyError, ValueError):
        amount = 0

    decision = request.POST.get('decision', '')
    card_number = request.POST.get('req_card_number', '')[-5:]
    card_type = request.POST.get('card_type_name', '')
    cybersource = money_models.CybersourceLineItem(
        transaction=txn,
        amount=-1 * amount,
        account_name='/Assets/Receivable/Cybersource',
        label=f'Paid by {card_type} {card_number}',
        receipt_post=request.POST,
        decision=decision,
        ref_number=request.POST.get('req_reference_number', ''),
        card_number=card_number, card_type=card_type,
    )

    with reversion.create_revision(atomic=True):
        reversion.set_comment("online payment - process payment")
        if request.user.is_authenticated:
            reversion.set_user(request.user)
        cybersource.save()

        if txn:
            if decision == 'ACCEPT':
                if amount != expected_amount:
                    txn.admin_notes += f"Amount mismatch: {amount=} != {expected_amount=}\n"
                    txn.stage = money_models.Transaction.Stage.REVIEW
                else:
                    results = []
                    for desc in _lineitem_descs.values():
                        result = desc.save_txn(txn)
                        results.append(result)
                    if all(results):
                        txn.stage = money_models.Transaction.Stage.PAID
                    else:
                        txn.stage = money_models.Transaction.Stage.REVIEW
            else:
                error = True
                txn.stage = money_models.Transaction.Stage.CANCEL
                txn.admin_notes += f"Decision: {decision}\n"
            txn.save()

    if txn and (txn.stage == money_models.Transaction.Stage.PAID):
        tmpl = select_template(_template_list('cybersource_receipt.txt'))
        context = dict(txn=txn, cybersource=cybersource)
        email_body = tmpl.render(context)
        addrs = set([txn.email, 'tech-squares-payments@mit.edu', ])
        email = mail.EmailMessage(subject="Tech Squares Receipt",
                                  body=email_body,
                                  to=addrs)
        mail.get_connection().send_messages([email])

    if error:
        return redirect('pay:error-cybersource')
    else:
        return redirect('pay:receipt', pk, nonce)


@require_GET
def pay_error_cybersource(request, ):
    context = dict(pagename='pay', )
    return render(request, _template_list('cybersource_error.html'), context)


@require_GET
@csrf_exempt
def pay_receipt(request, pk, nonce, ):
    txn = get_object_or_404(money_models.Transaction, pk=pk, nonce=nonce, )
    paid = (txn.stage == money_models.Transaction.Stage.PAID)
    context = dict(
        txn=txn,
        paid=paid,
        pagename='pay'
    )
    return render(request, _template_list('cybersource_receipt.html'), context)

# TODO:
# [ ] Handle the review flow
#     - allow updating the person on a subscription payment
#     - add a button to re-run the copy process
#     - send an email receipt???
# [ ] add useful __str__ methods
