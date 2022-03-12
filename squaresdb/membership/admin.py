from django.contrib import admin
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils.html import format_html

from reversion.admin import VersionAdmin

import squaresdb.membership.models as member_models

@admin.register(member_models.SquareLevel)
class SquareLevelAdmin(VersionAdmin):
    fields = ['slug', 'name', 'order']
    readonly_fields = fields
    list_display = fields
    ordering = ['order', 'slug']

@admin.register(member_models.PersonStatus)
class PersonStatusAdmin(VersionAdmin):
    fields = ['slug', 'name', 'member']
    readonly_fields = fields
    list_display = fields

@admin.register(member_models.MITAffil)
class MITAffilAdmin(VersionAdmin):
    fields = ['slug', 'name', 'student']
    readonly_fields = fields
    list_display = fields

@admin.register(member_models.FeeCategory)
class FeeCategoryAdmin(VersionAdmin):
    fields = ['slug', 'name']
    readonly_fields = fields
    list_display = fields

@admin.register(member_models.PersonFrequency)
class PersonFrequencyAdmin(VersionAdmin):
    fields = ['slug', 'name', 'order']
    readonly_fields = fields
    list_display = fields
    ordering = ['order', 'slug']

@admin.register(member_models.PersonComment)
class PersonCommentAdmin(VersionAdmin):
    fields = ['person', 'body', 'author']
    list_display = ['person', 'author', 'timestamp', 'body']
    list_display_links = list_display
    list_filter = ['timestamp']
    search_fields = ['person__name', 'person__email']

class PersonCommentInline(admin.TabularInline):
    model = member_models.PersonComment
    fk_name = 'person'
    extra = 1

class TSClassMemberPersonInline(admin.TabularInline):
    model = member_models.TSClassMember
    fk_name = 'student'
    verbose_name_plural = 'classes taken'
    extra = 1

class TSClassAssistPersonInline(admin.TabularInline):
    model = member_models.TSClassAssist
    fk_name = 'assistant'
    verbose_name_plural = 'classes helped with (not including as class coordinator)'
    extra = 1

@admin.register(member_models.Person)
class PersonAdmin(VersionAdmin):
    actions = ['make_auth_link']
    list_display = ['view_link', 'name', 'email', 'level', 'status', 'mit_affil', 'frequency', ]
    list_display_links = ['name']
    list_filter = [
        'level', 'status', 'mit_affil', 'fee_cat', 'frequency',
        'classes', 'last_marked_correct'
    ]
    search_fields = ['name', 'email']
    inlines = [
        PersonCommentInline,
        TSClassMemberPersonInline, TSClassAssistPersonInline,
    ]

    @admin.action(description="Create and send login (auth) link",
                  permissions=['bulkcreate_authlink'])
    def make_auth_link(self, request, queryset):
        #pylint:disable=no-self-use,unused-argument
        selected = queryset.values_list('pk', flat=True)
        base_url = reverse('membership:personauthlink-bulkcreate')
        people = ",".join([str(sel) for sel in selected])
        return HttpResponseRedirect("%s/?link=1&people=%s" % (base_url, people))

    def has_bulkcreate_authlink_permission(self, request): # pylint:disable = no-self-use
        """Does the user have bulk create PersonAuthLink permission"""
        return request.user.has_perm('membership.bulk_create_personauthlink')

    def view_link(self, obj): #pylint:disable=no-self-use
        url = reverse('membership:person', args=[str(obj.id)])
        return format_html("<a href='{}'>View</a>", url)

@admin.register(member_models.PersonAuthLink)
class PersonAuthLinkAdmin(VersionAdmin):
    list_display = [
        'person',
        'allowed_ip', 'expire_time',
        'create_user', 'create_time',
        'create_reason_basic', 'create_reason_detail'
    ]
    fields = list_display + ['create_ip', ]
    readonly_fields = fields

class TSClassAssistClassInline(admin.TabularInline):
    model = member_models.TSClassAssist
    fk_name = 'clas'
    verbose_name_plural = 'Assistants'
    extra = 1

class TSClassMemberClassInline(admin.TabularInline):
    model = member_models.TSClassMember
    fk_name = 'clas'
    verbose_name_plural = 'Students'
    extra = 1

@admin.register(member_models.TSClass)
class TSClassAdmin(VersionAdmin):
    list_display = ['label', 'coordinator', 'start_date', 'end_date']
    search_fields = ['label', 'coordinator']
    inlines = [
        TSClassAssistClassInline, TSClassMemberClassInline,
    ]

@admin.register(member_models.TSClassAssist)
class TSClassAssistAdmin(VersionAdmin):
    list_display = ['assistant', 'clas', 'role']
    list_display_links = ['assistant', 'clas']
    list_filter = ['clas']
    search_fields = ['assistant']

@admin.register(member_models.TSClassMember)
class TSClassMemberAdmin(VersionAdmin):
    list_display = ['student', 'clas', 'pe']
    list_display_links = ['student', 'clas']
    list_filter = ['pe', 'clas']
    search_fields = ['student']
