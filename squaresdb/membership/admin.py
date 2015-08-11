from django.contrib import admin

import squaresdb.membership.models as member_models

@admin.register(member_models.SquareLevel)
class SquareLevelAdmin(admin.ModelAdmin):
    fields = ['slug', 'name', 'order']
    readonly_fields = fields
    list_display = fields
    ordering = ['order', 'slug']

@admin.register(member_models.PersonStatus)
class PersonStatusAdmin(admin.ModelAdmin):
    fields = ['slug', 'name', 'member']
    readonly_fields = fields
    list_display = fields

@admin.register(member_models.MITAffil)
class MITAffilAdmin(admin.ModelAdmin):
    fields = ['slug', 'name', 'student']
    readonly_fields = fields
    list_display = fields

@admin.register(member_models.FeeCategory)
class FeeCategoryAdmin(admin.ModelAdmin):
    fields = ['slug', 'name']
    readonly_fields = fields
    list_display = fields

class PersonCommentInline(admin.TabularInline):
    model = member_models.PersonComment
    fk_name = 'person'
    extra = 1

@admin.register(member_models.Person)
class PersonAdmin(admin.ModelAdmin):
    list_display = ['name', 'email', 'level', 'status', 'mit_affil']
    list_filter = ['level', 'status', 'mit_affil', 'fee_cat', 'classes']
    search_fields = ['name', 'email']
    inlines = [PersonCommentInline]

@admin.register(member_models.TSClass)
class TSClassAdmin(admin.ModelAdmin):
    list_display = ['label', 'coordinator', 'start_date', 'end_date']
    search_fields = ['label', 'coordinator']

@admin.register(member_models.TSClassAssist)
class TSClassAssistAdmin(admin.ModelAdmin):
    list_display = ['assistant', 'clas', 'role']
    list_display_links = ['assistant', 'clas']
    list_filter = ['clas']
    search_fields = ['assistant']

@admin.register(member_models.TSClassMember)
class TSClassMemberAdmin(admin.ModelAdmin):
    list_display = ['student', 'clas', 'pe']
    list_display_links = ['student', 'clas']
    list_filter = ['pe', 'clas']
    search_fields = ['student']
