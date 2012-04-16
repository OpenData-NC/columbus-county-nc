from django.shortcuts import render, get_object_or_404
from django.db.models import Max

from openrural.data_dashboard import models as dd


def dashboard(request):
    scrapers = dd.Scraper.objects.annotate(last_run=Max('runs__end_date'))
    context = {'scrapers': scrapers}
    return render(request, 'data_dashboard/dashboard.html', context)


def view_scraper(request, scraper_slug):
    scraper = get_object_or_404(dd.Scraper, slug=scraper_slug)
    context = {'scraper': scraper,
               'runs': scraper.runs.order_by('-end_date')}
    return render(request, 'data_dashboard/view_scraper.html', context)


def view_run(request, scraper_slug, run_id):
    run = get_object_or_404(dd.Run, scraper__slug=scraper_slug, pk=run_id)
    context = {'run': run}
    return render(request, 'data_dashboard/view_run.html', context)
