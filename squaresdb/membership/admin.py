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

@admin.register(member_models.PersonComment)
class PersonCommentAdmin(admin.ModelAdmin):
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
class PersonAdmin(admin.ModelAdmin):
    list_display = ['name', 'email', 'level', 'status', 'mit_affil']
    list_filter = ['level', 'status', 'mit_affil', 'fee_cat', 'classes']
    search_fields = ['name', 'email']
    inlines = [
        PersonCommentInline,
        TSClassMemberPersonInline, TSClassAssistPersonInline,
    ]

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
class TSClassAdmin(admin.ModelAdmin):
    list_display = ['label', 'coordinator', 'start_date', 'end_date']
    search_fields = ['label', 'coordinator']
    inlines = [
        TSClassAssistClassInline, TSClassMemberClassInline,
    ]

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
