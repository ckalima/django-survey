from datetime import datetime
import os

from django.db import models
from django.db.models import Q
from django.conf import settings
from django.core.cache import cache
from django.core.urlresolvers import reverse
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.contrib.auth.views import redirect_to_login
from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpResponseRedirect, HttpResponse, Http404, HttpResponseNotFound
from django.template import loader, RequestContext
from django.template.defaultfilters import slugify
from django.template.loader import render_to_string
from django.shortcuts import get_object_or_404, render_to_response
from django.utils.translation import ugettext_lazy as _
from django.views.generic.list import ListView
from django.views.generic.edit import DeleteView
# from django.views.generic.create_update import delete_object

from survey.forms import forms_for_survey, SurveyForm, SurveyQuestionForm, SurveyChoiceForm
from survey.models import Survey, SurveyAnswer, SurveyQuestion, SurveyChoice
from survey.settings import LOGIN_URL


def _survey_redirect(request, survey,
                    group_slug=None, group_slug_field=None, group_qs=None,
                    template_name = 'survey/thankyou.html',
                    extra_context=None,
                    *args, **kw):
    """
    Conditionally redirect to the appropriate page;
    if there is a "next" value in the GET URL parameter,
    go to the URL specified under Next.

    If there is no "next" URL specified, then go to
    the survey results page...but only if it is viewable
    by the user.

    Otherwise, only direct the user to a page showing
    their own survey answers...assuming they have answered
    any questions.

    If all else fails, go to the Thank You page.
    """
    if ('next' in request.REQUEST and
        request.REQUEST['next'].startswith('http:') and
        request.REQUEST['next'] != request.path):
        return HttpResponseRedirect(request.REQUEST['next'])
    if survey.answers_viewable_by(request.user):
        return HttpResponseRedirect(reverse('survey-results', None, (),
                                                {'survey_slug': survey.slug}))

    # For this survey, have they answered any questions?
    if (hasattr(request, 'session') and SurveyAnswer.objects.filter(
            session_key=request.session.session_key.lower(),
            question__survey__visible=True,
            question__survey__slug=survey.slug).count()):
        return HttpResponseRedirect(
            reverse('answers-detail', None, (),
                    {'survey_slug': survey.slug,
                     'key': request.session.session_key.lower()}))

    # go to thank you page
    return render_to_response(template_name,
                              {'survey': survey, 'title': _('Thank You')},
                              context_instance=RequestContext(request))

def survey_detail(request, survey_slug,
               group_slug=None, group_slug_field=None, group_qs=None,
               template_name = 'survey/survey_detail.html',
               extra_context=None,
               allow_edit_existing_answers=False,
               *args, **kw):
    """

    """
    survey = get_object_or_404(Survey.objects.filter(visible=True), slug=survey_slug)
    if survey.closed:
        if survey.answers_viewable_by(request.user):
            return HttpResponseRedirect(reverse('survey-results', None, (),
                                                {'survey_slug': survey_slug}))
        raise Http404 #(_('Page not found.')) # unicode + exceptions = bad
    # if user has a session and have answered some questions
    # and the survey does not accept multiple answers,
    # go ahead and redirect to the answers, or a thank you
    if (hasattr(request, 'session') and
        survey.has_answers_from(request.session.session_key) and
        not survey.allows_multiple_interviews and not allow_edit_existing_answers):
        return _survey_redirect(request, survey,group_slug=group_slug)
    # if the survey is restricted to authentified user redirect
    # annonymous user to the login page
    if survey.restricted and str(request.user) == "AnonymousUser":
        return HttpResponseRedirect(LOGIN_URL+"?next=%s" % request.path)
    if request.POST and not hasattr(request, 'session'):
        return HttpResponse(unicode(_('Cookies must be enabled.')), status=403)
    if hasattr(request, 'session'):
        skey = 'survey_%d' % survey.id
        request.session[skey] = (request.session.get(skey, False) or
                                 request.method == 'POST')
        request.session.modified = True ## enforce the cookie save.
    survey.forms = forms_for_survey(survey, request, allow_edit_existing_answers)
    if (request.POST and all(form.is_valid() for form in survey.forms)):
        for form in survey.forms:
            form.save()
        return _survey_redirect(request, survey,group_slug=group_slug)
    # Redirect either to 'survey.template_name' if this attribute is set or
    # to the default template
    return render_to_response(survey.template_name or template_name,
                              {'survey': survey,
                               'title': survey.title,
                               'group_slug': group_slug},
                              context_instance=RequestContext(request))

# TODO: ajaxify this page (jquery) : add a date picker, ...
# TODO: Fix the bug that make the questions and the choices unordered

@login_required()
def survey_edit(request,survey_slug,
               group_slug=None, group_slug_field=None, group_qs=None,
               template_name = "survey/survey_edit.html",
               extra_context=None,
               *args, **kw):
    survey = get_object_or_404(Survey, slug=survey_slug)
    return render_to_response(template_name,
                              {'survey': survey,
                               'group_slug': group_slug},
                              context_instance=RequestContext(request))

# TODO: Refactor the object add to avoid the code duplication.
# def object_add(request, object, form, template_name,
# post_create_redirect, extra_context):

@login_required()
def survey_add(request,
               group_slug=None, group_slug_field=None, group_qs=None,
               template_name = 'survey/survey_add.html',
               extra_context=None,
               *args, **kw):

    if request.method == "POST":
        request_post = request.POST.copy()
        survey_form = SurveyForm(request_post)
        if survey_form.is_valid():
            new_survey = survey_form.save(commit=False)
            new_survey.created_by =  request.user
            new_survey.editable_by = request.user
            new_survey.slug = slugify(new_survey.title)
            if group_slug:
                group = get_object_or_404(group_qs,slug=group_slug)
                new_survey.recipient = group
            new_survey.save()
            return HttpResponseRedirect(reverse("surveys-editable",kwargs={}))


    else:
        survey_form = SurveyForm()
    return render_to_response(template_name,
                              {'title': _("Add a survey"),
                               'form' : survey_form},
                              context_instance=RequestContext(request))

@login_required()
def survey_update(request, survey_slug,
               group_slug=None, group_slug_field=None, group_qs=None,
               template_name = 'survey/survey_add.html',
               extra_context=None,
               *args, **kw):
    if request.method == "POST":
        request_post = request.POST.copy()
        survey = get_object_or_404(Survey, slug=survey_slug)
        survey_form = SurveyForm(instance=survey,data=request_post)
        if survey_form.is_valid():
            new_survey = survey_form.save(commit=False)
            new_survey.created_by =  request.user
            new_survey.editable_by = request.user
            new_survey.slug = slugify(new_survey.title)
            new_survey.save()
            return HttpResponseRedirect(reverse("survey-edit",None,(),{"survey_slug":survey_slug}))


    else:
        survey = get_object_or_404(Survey, slug=survey_slug)
        survey_form = SurveyForm(instance=survey)
    return render_to_response(template_name,
                              {'title': _("Update '%s'") % survey.title,
                               'survey' : survey,
                               'form' : survey_form},
                              context_instance=RequestContext(request))

@login_required()
def survey_delete(request,survey_slug=None,
               group_slug=None, group_slug_field=None,
               group_qs=None,
               template_name = "survey/editable_survey_list.html",
               extra_context=None,
               *args, **kw):
    # TRICK: The following line does not have any logical explination
    # except than working around a bug in FF. It has been suggested there
    # http://groups.google.com/group/django-users/browse_thread/thread/e6c96ab0538a544e/0e01cdda3668dfce#0e01cdda3668dfce
    request_post = request.POST.copy()
    return delete_object(request, slug=survey_slug,
        **{"model":Survey,
         "post_delete_redirect": reverse("surveys-editable",kwargs={}),
         "template_object_name":"survey",
         "login_required": True,
         'extra_context': {'title': _('Delete survey')}
        })

@login_required()
def question_add(request,survey_slug,
               group_slug=None, group_slug_field=None,
               group_qs=None,
               template_name = 'survey/question_add.html',
               extra_context=None,
               *args, **kw):
    survey = get_object_or_404(Survey, slug=survey_slug)
    if request.method == "POST":
        request_post = request.POST.copy()
        question_form = SurveyQuestionForm(data=request_post,files=request.FILES)
        if question_form.is_valid():
            new_question = question_form.save(commit=False)
            new_question.survey = survey
            new_question.save()
            return HttpResponseRedirect(reverse("survey-edit",None,(),
                                                {"survey_slug":survey_slug}))

    else:
        question_form = SurveyQuestionForm()
    return render_to_response(template_name,
                              {'title': _("Add a question"),
                               'form' : question_form},
                              context_instance=RequestContext(request))

@login_required()
def question_update(request,survey_slug,question_id,
                    group_slug=None, group_slug_field=None,
                    group_qs=None,
                    template_name = 'survey/question_add.html',
                    extra_context=None,
                    *args, **kw):
    survey = get_object_or_404(Survey, slug=survey_slug)
    question =  get_object_or_404(SurveyQuestion,id=question_id)
    if question not in survey.questions.iterator():
        raise Http404()

    if request.method == "POST":
        request_post = request.POST.copy()
        question_form = SurveyQuestionForm(instance=question,data=request_post,
                                     files=request.FILES)

        if question_form.is_valid():
            new_question = question_form.save(commit=False)
            new_question.survey = survey
            new_question.save()
            return HttpResponseRedirect(reverse("survey-edit",None,(),
                                                {"survey_slug":survey_slug}))
    else:
        question_form = SurveyQuestionForm(instance=question)

    return render_to_response(template_name,
                              {'title': _("Update question"),
                               'question' : question,
                               'model_string' : "SurveyQuestion",
                               'form' : question_form},
                              context_instance=RequestContext(request))

@login_required()
def question_delete(request,survey_slug,question_id,
                    group_slug=None, group_slug_field=None,
                    group_qs=None,
                    template_name = None,
                    extra_context=None,
                    *args, **kw):
    # TRICK: The following line does not have any logical explination
    # except than working around a bug in FF. It has been suggested there
    # http://groups.google.com/group/django-users/browse_thread/thread/e6c96ab0538a544e/0e01cdda3668dfce#0e01cdda3668dfce
    request_post = request.POST.copy()
    return delete_object(request, object_id=question_id,
        **{"model":SurveyQuestion,
         "post_delete_redirect": reverse("survey-edit",None,(),
                                         {"survey_slug":survey_slug,
                                          "group_slug":group_slug}),
         "template_object_name":"question",
         "login_required": True,
         'extra_context': {'title': _('Delete question')}
        })

@login_required()
def choice_add(request,question_id,
                group_slug=None, group_slug_field=None,
                group_qs=None,
                template_name = 'survey/choice_add.html',
                extra_context=None,
                *args, **kw):
    question = get_object_or_404(SurveyQuestion, id=question_id)

    if request.method == "POST":
        request_post = request.POST.copy()
        choice_form = SurveyChoiceForm(data=request_post,files=request.FILES)
        if choice_form.is_valid():
            new_choice = choice_form.save(commit=False)
            new_choice.question = question
            new_choice.save()
            return HttpResponseRedirect(reverse("survey-edit",None,(),
                                                {"survey_slug":question.survey.slug}))
    else:
        choice_form = SurveyChoiceForm()

    return render_to_response(template_name,
                              {'title': _("Add a choice"),
                               'form' : choice_form},
                              context_instance=RequestContext(request))

@login_required()
def choice_update(request,question_id, choice_id,
                group_slug=None, group_slug_field=None,
                group_qs=None,
                template_name = 'survey/choice_add.html',
                extra_context=None,
                *args, **kw):
    question = get_object_or_404(SurveyQuestion, id=question_id)
    choice = get_object_or_404(SurveyChoice, id=choice_id)
    if choice not in question.choices.iterator():
        raise Http404()
    if request.method == "POST":
        request_post = request.POST.copy()
        choice_form = SurveyChoiceForm(instance=choice,data=request_post,
                                 files=request.FILES)
        if choice_form.is_valid():
            new_choice = choice_form.save(commit=False)
            new_choice.question = question
            new_choice.save()
            return HttpResponseRedirect(reverse("survey-edit",None,(),
                                                {"survey_slug":question.survey.slug}))
    else:
        choice_form = SurveyChoiceForm(instance=choice)
    return render_to_response(template_name,
                              {'title': _("Update choice"),
                               'choice' : choice,
                               'model_string' : "Choice",
                               'form' : choice_form},
                              context_instance=RequestContext(request))

@login_required()
def choice_delete(request,survey_slug,choice_id,
                group_slug=None, group_slug_field=None,
                group_qs=None,
                template_name = 'survey/choice_add.html',
                extra_context=None,
                *args, **kw):
    # TRICK: The following line does not have any logical explination
    # except than working around a bug in FF. It has been suggested there
    # http://groups.google.com/group/django-users/browse_thread/thread/e6c96ab0538a544e/0e01cdda3668dfce#0e01cdda3668dfce
    request_post = request.POST.copy()
    return delete_object(request, object_id=choice_id,
        **{"model":SurveyChoice,
         "post_delete_redirect": reverse("survey-edit",None,(),
                                         {"survey_slug":survey_slug}),
         "template_object_name":"choice",
         "login_required": True,
         'extra_context': {'title': _('Delete choice')}
        })


class SurveyList(ListView):
    """
    """
    model = Survey
    template_name = 'survey/survey_list.html'

    def get_context_data(self, **kwargs):
        context = super(SurveyList, self).get_context_data(**kwargs)
        context['title'] = _('Surveys')
        return context


class VisibleSurveyList(SurveyList):
    def get_queryset(self, **kwargs):
        qs = super(VisibleSurveyList, self).get_queryset(**kwargs)
        return qs.filter(visible=True)


class EditableSurveyList(SurveyList):
    template_name = "survey/editable_survey_list.html"

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super(SurveyList, self).dispatch(*args, **kwargs)

    def get_queryset(self, **kwargs):
        qs = super(EditableSurveyList, self).get_queryset(**kwargs)
        u = self.request.user
        return qs.filter(Q(created_by=u) | Q(editable_by=u))


def answers_list(request, survey_slug,
                 group_slug=None, group_slug_field=None, group_qs=None,
                 template_name = 'survey/answers_list.html',
                 extra_context=None,
                 *args, **kw):
    """
    Shows a page showing survey results for an entire survey.
    """
    survey = get_object_or_404(Survey.objects.filter(visible=True), slug=survey_slug)
    # if the user lacks permissions, show an "Insufficient Permissions page"
    if not survey.answers_viewable_by(request.user):
        if (hasattr(request, 'session') and
            survey.has_answers_from(request.session.session_key)):
            return HttpResponseRedirect(
                reverse('answers-detail', None, (),
                        {'survey_slug': survey.slug,
                         'key': request.session.session_key.lower()}))
        return render_to_response('survey/no_privileges.html', {}, context_instance=RequestContext(request))
    return render_to_response(template_name,
        { 'survey': survey,
          'view_submissions': request.user.has_perm('survey.view_submissions'),
          'title': survey.title },
        context_instance=RequestContext(request))

def answers_detail(request, survey_slug, key,
                   group_slug=None, group_slug_field=None, group_qs=None,
                   template_name = 'survey/answers_detail.html',
                   extra_context=None,
                   *args, **kw):
    """
    Shows a page with survey results for a single person.

    If the user lacks permissions, show an "Insufficient Permissions page".
    """
    answers = SurveyAnswer.objects.filter(session_key=key.lower(),
        question__survey__visible=True, question__survey__slug=survey_slug)
    if not answers.count(): raise Http404
    survey = answers[0].question.survey
    try:
      user = answers[0].user
    except:
      user = None

    submission_date = answers[0].submission_date

    mysubmission = (hasattr(request, 'session') and
         request.session.session_key.lower() == key.lower())

    # if owner, has_perm, viewable_by, or is_staff... display answer details
    if (mysubmission or
        (request.user.has_perm('survey.view_submissions') or
         survey.answers_viewable_by(request.user) or
         request.user.is_staff)):
      return render_to_response(template_name,
          {'survey': survey, 'submission': answers, 'user': user, 'submission_date': submission_date, },
          context_instance=RequestContext(request))
    else:
      return render_to_response('survey/no_privileges.html', {}, context_instance=RequestContext(request))

def delete_image(request, model_string,object_id):
    model = models.get_model("survey", model_string)
    object = get_object_or_404(model, id=object_id)
    if object.image == None:
        raise Http404('No image for the given object : %s ' %object)
    if request.method == "POST":
        request_post = request.POST.copy()
        if os.path.isfile(object.get_image_filename()):
            os.remove(object.get_image_filename())
            object.image = None
            object.save()
            return HttpResponseRedirect(object.get_update_url())

    return render_to_response('survey/image_confirm_delete.html',
        {"object" : object},
        context_instance=RequestContext(request))
