from django.shortcuts import render

from ebpub.db.models import Schema


def dashboard(request):
    context = {'schemas': Schema.objects.all()}
    return render(request, 'data_dashboard/dashboard.html', context)
