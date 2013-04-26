from survey.models import SurveyAnswer, SurveyChoice, SurveyQuestion, Survey
from django.contrib import admin

class SurveyChoiceInline(admin.TabularInline):
    """
    A newforms-admin inline option class for the ``SurveyChoice`` model.
    """
    model = SurveyChoice
    extra = 2
    fields = ('text', 'order',)
    template = 'admin/survey/choice/edit_inline_tabular.html'


class SurveyQuestionOptions(admin.ModelAdmin):
    """
    A newforms-admin options class for the ``SurveyQuestion`` model.
    """
    list_select_related = True
    list_filter = ('survey', 'qtype')
    list_display_links = ('text',)
    list_display = ('survey', 'text', 'qtype', 'required')
    search_fields = ('text',)
    inlines = [
        SurveyChoiceInline,
        ]

class SurveyQuestionInline(admin.TabularInline):
    """
    A newforms-admin inline option class for the ``SurveyQuestion`` model.
    """
    model = SurveyQuestion
    extra = 1
    fields = ('text', 'order',)
    template = 'admin/survey/question/edit_inline_tabular.html'

class SurveyOptions(admin.ModelAdmin):
    """
    A newforms-admin options class for the ``Survey`` model.
    """
    prepopulated_fields = {'slug': ('title',)}
    list_display = ('__unicode__', 'visible', 'public',
                        'opens', 'closes', 'open')
    inlines = [SurveyQuestionInline]

class SurveyAnswerOptions(admin.ModelAdmin):
    """
    A newforms-admin options class for the ``SurveyAnswer`` model.
    """
    list_display = ('interview_uuid','question','user', 'submission_date',
                    'session_key', 'text')
    #list_filter = ('question__survey',)
    search_fields = ('text',)
    list_select_related=True

class SurveyChoiceOptions(admin.ModelAdmin):
    list_display = ('question','text',)
    search_fields = ('text',)
    list_filter = ('question',)


# The try/catch blocks are there to supress the ``AlreadyRegistered`` warning.
try:
    admin.site.register(SurveyQuestion, SurveyQuestionOptions)
except:
    pass

try:
    admin.site.register(Survey, SurveyOptions)
except:
    pass

try:
    admin.site.register(SurveyAnswer, SurveyAnswerOptions)
except:
    pass

try:
    admin.site.register(SurveyChoice, SurveyChoiceOptions)
except:
    pass
