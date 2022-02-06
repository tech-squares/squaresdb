from django.contrib import admin

from reversion.admin import VersionAdmin

import squaresdb.gate.models as gate_models

# Register your models here.

# Admins are easier to copy/paste if they're all Admin_ModelName
# pylint:disable=invalid-name

@admin.register(gate_models.SubscriptionPeriod)
class Admin_SubscriptionPeriod(VersionAdmin):
    fields = ['slug', 'name', 'start_date', 'end_date', ]
    readonly_fields = ['slug']
    list_display = fields
    ordering = ['start_date']


@admin.register(gate_models.SubscriptionPeriodPrice)
class Admin_SubscriptionPeriodPrice(VersionAdmin):
    list_display = ['period', 'fee_cat', 'low', 'high']
    list_filter = ['period']
    ordering = ['period', 'low']
    # TODO: admin should create these inline with subscription period


@admin.register(gate_models.DancePriceScheme)
class Admin_DancePriceScheme(VersionAdmin):
    fields = ['name', 'notes', 'active', ]
    list_display = ['name', 'active']
    ordering = ['-active', 'name']


@admin.register(gate_models.DancePrice)
class Admin_DancePrice(VersionAdmin):
    list_display = ['price_scheme', 'fee_cat', 'low', 'high']
    ordering = ['price_scheme', 'low']
    # TODO: admin should create these inline with dance price scheme


@admin.register(gate_models.Dance)
class Admin_Dance(VersionAdmin):
    list_display = ['time', 'period']
    list_filter = ['period']


@admin.register(gate_models.PaymentMethod)
class Admin_PaymentMethod(VersionAdmin):
    fields = ['slug', 'name', 'in_gate', ]
    readonly_fields = fields
    list_display = fields


@admin.register(gate_models.SubscriptionPayment)
class Admin_SubscriptionPayment(VersionAdmin):
    list_display = ['time', 'person', 'at_dance', 'payment_type', ]
    ordering = ['at_dance', 'person']
    list_filter = ['periods']


@admin.register(gate_models.DancePayment)
class Admin_DancePayment(VersionAdmin):
    list_display = ['time', 'for_dance', 'person', 'at_dance', 'payment_type', ]
    ordering = ['for_dance', 'person']


@admin.register(gate_models.Attendee)
class Admin_Attendee(VersionAdmin):
    fields = ['person', 'dance', 'payment']
    list_display = fields
