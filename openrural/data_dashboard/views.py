import time

from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Max, Q
from django.core.urlresolvers import reverse
from django.http import Http404
from django.views.decorators.http import require_POST

from ebpub.db import breadcrumbs
from ebpub.db.models import Schema

from openrural.data_dashboard import models as dd
from openrural.data_dashboard import tasks as dashboard_tasks
from openrural.data_dashboard.forms import (RunCommentForm,
                                           GeocodeFailuresSearch)

from celery.registry import tasks


def base_crumbs():
    crumbs = breadcrumbs.home({})
    crumbs.append(('Data Dashboard', reverse('dashboard')))
    return crumbs


def dashboard(request):
    scrapers = dd.Scraper.objects.annotate(last_run=Max('runs__end_date'))
    context = {'scrapers': scrapers, 'breadcrumbs': base_crumbs()}
    return render(request, 'data_dashboard/dashboard.html', context)


def view_scraper(request, scraper_slug):
    scraper = get_object_or_404(dd.Scraper, slug=scraper_slug)
    try:
        schema = Schema.objects.get(slug=scraper.schema)
    except Schema.DoesNotExist:
        schema = None
    crumbs = base_crumbs()
    crumbs.append((scraper_slug, reverse('view_scraper', args=[scraper_slug])))
    # Default: Do not return skipped runs.
    show_skipped = (request.GET['show_skipped']
            if 'show_skipped' in request.GET else "0")
    show_skipped = 0 if show_skipped == '0' else 1
    if show_skipped:
        runs = scraper.runs.order_by('-date')
    else:
        runs = scraper.runs.exclude(status='skipped').order_by('-date')
    num_failures = dd.Geocode.objects.filter(scraper=scraper.slug,
            success=False).count()
    context = {'scraper': scraper,
               'runs': runs,
               'breadcrumbs': crumbs,
               'schema': schema,
               'show_skipped': -1*show_skipped+1,
               'num_failures': num_failures}
    return render(request, 'data_dashboard/view_scraper.html', context)


def view_run(request, scraper_slug, run_id):
    run = get_object_or_404(dd.Run, scraper__slug=scraper_slug, pk=run_id)
    if request.POST:
        form = RunCommentForm(request.POST, instance=run)
        if form.is_valid():
            form.save()
    else:
        form = RunCommentForm(instance=run)
    crumbs = base_crumbs()
    crumbs.append((scraper_slug,
                   reverse('view_scraper', args=[scraper_slug])))
    crumbs.append(('Run %d' % run.pk,
                   reverse('view_run', args=[scraper_slug, run_id])))
    num_failures = run.geocodes.filter(success=False).count()
    context = {'run': run,
               'stats': run.stats.order_by('name'),
               'breadcrumbs': crumbs,
               'form': form,
               'num_failures': num_failures}
    return render(request, 'data_dashboard/view_run.html', context)


def list_failures(request, scraper_slug, run_id=None):
    scraper = get_object_or_404(dd.Scraper, slug=scraper_slug)
    run = (get_object_or_404(dd.Run, scraper__slug=scraper_slug, pk=run_id)
            if run_id else None)
    crumbs = base_crumbs()
    crumbs.append((scraper_slug,
                   reverse('view_scraper', args=[scraper_slug])))
    if run:
        crumbs.append(('Run %d' % run.pk,
                       reverse('view_run', args=[scraper_slug, run_id])))
    crumbs.append(('Failures', ''))
    if run:
        geocodes = run.geocodes.filter(success=False).select_related()
    else:
        geocodes = dd.Geocode.objects.filter(scraper=scraper.slug,
                success=False).select_related()
    if request.GET:
        form = GeocodeFailuresSearch(request.GET)
        if form.is_valid():
            search = form.cleaned_data['search']
            geocodes = geocodes.filter(Q(name__icontains=search) |
                                       Q(location__icontains=search) |
                                       Q(description__icontains=search))
    else:
        form = GeocodeFailuresSearch()
    context = {'geocodes': geocodes.order_by('-date'),
               'run': run,
               'scraper': scraper,
               'breadcrumbs': crumbs,
               'form': form}
    return render(request, 'data_dashboard/list_failures.html', context)


@require_POST
def run_scraper(request, scraper_slug):
    scraper = get_object_or_404(dd.Scraper, slug=scraper_slug)
    slug = 'openrural.%s' % scraper.slug
    try:
        Task = tasks[slug]
    except KeyError:
        raise Http404('Task not found!')
    Task.delay()
    time.sleep(1)
    return redirect('view_scraper', scraper_slug=scraper.slug)
