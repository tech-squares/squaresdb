from django import forms
from django.core.exceptions import ValidationError

import squaresdb.gate.models as gate_models
import squaresdb.membership.models as member_models

### Add new period (with dances)

class NewPeriodForm(forms.ModelForm):
    time = forms.TimeField(help_text='Start time for each dance', initial="20:00")
    seasons = ['fall', 'winter', 'spring', 'summer']
    season = forms.ChoiceField(choices=zip(seasons, seasons),
                               help_text="Only used for default name+slug")
    price_qset = gate_models.DancePriceScheme.objects.all().order_by('-active', 'name')
    default_price_scheme = forms.ModelChoiceField(queryset=price_qset, empty_label=None)
    confirm_help = "Recommend leaving unchecked until you see the list of dates"
    confirm = forms.BooleanField(help_text=confirm_help, required=False)

    def clean(self):
        data = super().clean()
        start = data.get('start_date')
        end = data.get('end_date')
        if start and end and not (start < end):
            msg = 'Start date must be before end date'
            self.add_error('start_date', msg)
            self.add_error('end_date', msg)
        if not data.get('confirm'):
            self.add_error('confirm', "Check box to create period")

    class Meta:
        model = gate_models.SubscriptionPeriod
        fields = ['start_date', 'end_date', 'time', 'season', 'name', 'slug',
                  'default_price_scheme', 'confirm']
        help_texts = dict(
            start_date="Date of first dance and start of period (eg, 2022-02-08)"
        )

class NewPeriodPriceForm(forms.ModelForm):
    class Meta:
        model = gate_models.SubscriptionPeriodPrice
        fields = ('fee_cat', 'low', 'high')

def new_period_prices_formset(submit=None):
    fee_cats = list(member_models.FeeCategory.objects.all())
    SubPriceFormset = forms.inlineformset_factory( # pylint:disable=invalid-name
            gate_models.SubscriptionPeriod,
            gate_models.SubscriptionPeriodPrice,
            form=NewPeriodPriceForm, extra=len(fee_cats))
    initial = [{'fee_cat': fee_cat} for fee_cat in fee_cats]
    formset = SubPriceFormset(submit, initial=initial)
    for form in formset:
        form.fields['fee_cat'].disabled = True
    return formset

### squares-pay subscription upload

def file_size(max_size):
    def file_size_validator(value):
        if value.size > max_size:
            raise ValidationError('File too large. Size should not exceed %d bytes.'
                                  % (max_size, ))
    return file_size_validator

class SubUploadForm(forms.Form):
    # At the time of this writing, a semester or so is 9KB, so use 100KB
    file = forms.FileField(validators=[file_size(10**5)])
    sub_periods_qs = gate_models.SubscriptionPeriod.objects.all()
    sub_periods_help = "Allowed sub periods in upload. (Note: error handling " \
                       "if others appear is bad.)"
    sub_periods = forms.ModelMultipleChoiceField(queryset=sub_periods_qs,
                                                 initial=sub_periods_qs,
                                                 help_text=sub_periods_help)

class SubPayAddForm(forms.ModelForm):
    class Meta:
        model = gate_models.SubscriptionPayment
        fields = ['person', 'time', 'payment_type', 'amount', 'fee_cat',
                  'notes', 'periods']
        widgets = dict(person=forms.HiddenInput(), )


### Squares-Pay in SquaresDB

class SubscriptionLineItemForm(forms.ModelForm):
    ignore_warnings = forms.BooleanField(required=False)

    class Meta:
        model = gate_models.SubscriptionLineItem
        fields = ['sub_period', 'subscriber_name', 'amount']


### Bulk add subscriptions

class BulkSubForm(forms.Form):
    payment_qs = gate_models.PaymentMethod.objects.all()
    payment_type = forms.ModelChoiceField(queryset=payment_qs, initial='cash')
    amount = forms.DecimalField(max_digits=5, decimal_places=2, initial=0)
    notes = forms.CharField()

    # People multi-select
    people_qs = member_models.Person.objects.order_by('frequency__order', 'name')
    people_qs = people_qs.exclude(status__slug='system')
    people_qs = people_qs.select_related('fee_cat', 'frequency')
    people = forms.ModelMultipleChoiceField(queryset=people_qs,
                                            widget=forms.CheckboxSelectMultiple)
