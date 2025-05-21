from django.contrib import admin

from reversion.admin import VersionAdmin

import squaresdb.money.models as money_models

# Admins are easier to copy/paste if they're all Admin_ModelName
# pylint:disable=invalid-name

class Admin_Inline_LineItem(admin.TabularInline):
    model = money_models.LineItem
    show_change_link = True
    extra = 0

@admin.register(money_models.Transaction)
class Admin_Transaction(VersionAdmin):
    fields = ['time', 'stage', 'person_name', 'notes', 'admin_notes', ]
    list_display = ['time', 'person_name', 'stage', ]
    list_filter = ['stage', ]
    search_fields = ['person_name', ]
    date_hierarchy = 'time'
    inlines = [ Admin_Inline_LineItem ]


@admin.display(description="Transaction stage")
def format_txn_stage(lineitem):
    return money_models.Transaction.Stage(lineitem.transaction.stage).label


@admin.register(money_models.LineItem)
class Admin_LineItem(VersionAdmin):
    fields = ['transaction', 'amount', 'account_name', 'label', 'notes', ]
    readonly_fields = ['transaction', 'amount', 'account_name', ]
    list_display = ['pk', 'transaction__time', 'amount', 'account_name', 'label',
                    'transaction__person_name', ]
    list_filter = ['transaction__stage', ]
    search_fields = ['transaction__person_name', ]
    date_hierarchy = 'transaction__time'


@admin.register(money_models.CybersourceLineItem)
class Admin_CybersourceLineItem(VersionAdmin):
    fields = ['transaction', 'amount', 'receipt_post', 'decision', 'ref_number',
              'card_number', 'card_type', ]
    readonly_fields = ['transaction', 'receipt_post', 'decision', 'ref_number', ]
    list_display = ['pk', 'transaction__time', 'transaction__person_name', format_txn_stage,
                    'decision', 'amount', 'ref_number', 'card_number', 'card_type', ]
    list_filter = Admin_LineItem.list_filter + ['decision', ]
    date_hierarchy = 'transaction__time'

@admin.register(money_models.Product)
class Admin_Product(VersionAdmin):
    fields = ['pk', 'label', 'account_name', 'low', 'high',
              'description', 'admin_notes', 'active', ]
    readonly_fields = ['pk', ]
    list_display = ['pk', 'active', 'account_name', 'label', 'low', 'high', ]
    list_filter = ['active', ]
    search_fields = ['account_name', 'label', ]

@admin.register(money_models.ProductLineItem)
class Admin_ProductLineItem(VersionAdmin):
    fields = ['transaction', 'product', 'count', 'price_each', 'amount',
              'account_name', 'label', 'notes', ]
    readonly_fields = ['transaction', 'amount', 'account_name', ]
    list_display = ['pk', 'transaction__time', 'count', 'price_each', 'amount',
                    'account_name', 'label', 'transaction__person_name', ]
    list_filter = ['transaction__stage', 'product', ]
    search_fields = ['transaction__person_name', 'label', ]
    date_hierarchy = 'transaction__time'
