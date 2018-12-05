# coding=utf-8
from __future__ import unicode_literals

from django.urls import reverse

from django.views.generic import ListView, CreateView, DetailView, UpdateView

from .base import AbstractAuthedIndigoView, PlaceBasedView

from indigo_api.models import Task


class TaskListView(AbstractAuthedIndigoView, PlaceBasedView, ListView):
    # permissions
    permission_required = ('indigo_api.view_work',)
    check_country_perms = False

    context_object_name = 'tasks'
    paginate_by = 16
    paginate_orphans = 4

    def get_queryset(self):
        return Task.objects.filter(country=self.country, locality=self.locality).order_by('-created_at')


class TaskDetailView(AbstractAuthedIndigoView, PlaceBasedView, DetailView):
    # permissions
    permission_required = ('indigo_api.view_work',)
    check_country_perms = False

    context_object_name = 'task'
    model = Task


class TaskCreateView(AbstractAuthedIndigoView, PlaceBasedView, CreateView):
    # permissions
    permission_required = ('indigo_api.add_work',)
    check_country_perms = False

    context_object_name = 'task'
    fields = ['title', 'work', 'document', 'description', 'assigned_to']
    model = Task

    def get_form_kwargs(self):
        kwargs = super(TaskCreateView, self).get_form_kwargs()

        task = Task()
        task.country = self.country
        task.locality = self.locality
        task.created_by = self.request.user

        kwargs['instance'] = task

        return kwargs

    def get_success_url(self):
        return reverse('tasks', kwargs={'place': self.kwargs['place']})


class TaskEditView(AbstractAuthedIndigoView, PlaceBasedView, UpdateView):
    # permissions
    permission_required = ('indigo_api.add_work',)
    check_country_perms = False

    context_object_name = 'task'
    fields = ['title', 'work', 'document', 'description', 'assigned_to']
    model = Task

    def get_success_url(self):
        return reverse('task_detail', kwargs={'place': self.kwargs['place'], 'pk': self.kwargs['pk']})
