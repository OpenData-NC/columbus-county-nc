from django.shortcuts import render, get_object_or_404
from django.db.models import Max
from django.core.urlresolvers import reverse

from ebpub.db import breadcrumbs

from openrural.data_dashboard import models as dd


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
    crumbs = base_crumbs()
    crumbs.append((scraper_slug,
                   reverse('view_scraper', args=[scraper_slug])))
    context = {'scraper': scraper,
               'runs': scraper.runs.order_by('-end_date'),
               'breadcrumbs': crumbs}
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
