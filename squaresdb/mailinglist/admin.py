from django.contrib import admin

from reversion.admin import VersionAdmin

from . import models as mail_models

# Admins are easier to copy/paste if they're all Admin_ModelName
# pylint:disable=invalid-name

@admin.register(mail_models.ListCategory)
class Admin_ListCategory(VersionAdmin):
    fields = ['slug', 'name', 'order']
    list_display = fields
    list_display_links = fields
    list_filter = ['slug', 'name']

@admin.register(mail_models.MailingList)
class Admin_MailingList(VersionAdmin):
    fields = ['list_type', 'category', 'name', 'order', 'description']
    list_display = ['pk', 'list_type', 'category', 'name', 'order']
    list_display_links = ['pk', 'name']
    list_filter = ['list_type', 'category']
    ordering = ['category__order', 'order']

# Version list membership. It's possible this will be too much data or
# otherwise undesirable, but it seems maybe nice to be able to see "So when
# did Alice sign up for this list?".
@admin.register(mail_models.ListMember)
class Admin_ListMember(VersionAdmin):
    fields = ['mail_list', 'email', ]
    readonly_fields = fields
    list_display = fields
    list_display_links = ['email']
    list_filter = ['mail_list', 'mail_list__category', 'mail_list__list_type']
    search_fields = ['mail_list__name', 'email']
