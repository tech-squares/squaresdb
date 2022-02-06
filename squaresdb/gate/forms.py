import datetime

from django import forms

import squaresdb.gate.models as gate_models
import squaresdb.membership.models as member_models

class NewPeriodForm(forms.ModelForm):
    # TODO: Add SubscriptionPeriodPrice for every fee cat
    # TODO: Need to create dance objects
    # TODO: Choose default price scheme
    # Form is:
    # - Basic period info (name, slug, dates)
    # - default price scheme just one)
    # - prices for every fee cat
    # Then we create dance objects
    # So I think this is a overall form + SubscriptionPeriodPrice formset
    # https://docs.djangoproject.com/en/4.0/topics/forms/formsets/#using-more-than-one-formset-in-a-view
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
    SubPriceFormset = forms.inlineformset_factory(gate_models.SubscriptionPeriod,
            gate_models.SubscriptionPeriodPrice,
            form=NewPeriodPriceForm, extra=len(fee_cats))
    initial = [{'fee_cat': fee_cat} for fee_cat in fee_cats]
    formset = SubPriceFormset(submit, initial=initial)
    for form in formset:
        form.fields['fee_cat'].disabled = True
    return formset
