import time

from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Max
from django.core.urlresolvers import reverse
from django.http import Http404
from django.views.decorators.http import require_POST

from ebpub.db import breadcrumbs
from ebpub.db.models import Schema

from openrural.data_dashboard import models as dd
from openrural.data_dashboard import tasks as dashboard_tasks

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
    crumbs.append((scraper_slug,
                   reverse('view_scraper', args=[scraper_slug])))
    context = {'scraper': scraper,
               'runs': scraper.runs.order_by('-date'),
               'breadcrumbs': crumbs,
               'schema': schema}
    return render(request, 'data_dashboard/view_scraper.html', context)


def view_run(request, scraper_slug, run_id):
    run = get_object_or_404(dd.Run, scraper__slug=scraper_slug, pk=run_id)
    crumbs = base_crumbs()
    crumbs.append((scraper_slug,
                   reverse('view_scraper', args=[scraper_slug])))
    crumbs.append(('Run %d' % run.pk,
                   reverse('view_run', args=[scraper_slug, run_id])))
    context = {'run': run,
               'stats': run.stats.order_by('name'),
               'breadcrumbs': crumbs}
    return render(request, 'data_dashboard/view_run.html', context)


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
