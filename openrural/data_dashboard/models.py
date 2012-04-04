from django.db import models

from ebpub.db.models import Schema


class Scraper(models.Model):
    slug = models.SlugField()
    schema = models.ForeignKey(Schema, related_name='scrapers')


class Run(models.Model):
    scraper = models.ForeignKey(Scraper)
    date = models.DateTimeField(auto_now_add=True, db_index=True)
