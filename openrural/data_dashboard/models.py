from django.db import models

from ebpub.db.models import Schema


class Scraper(models.Model):
    slug = models.SlugField(unique=True)
    schema = models.CharField(max_length=255)

    def __unicode__(self):
        return self.slug


class Run(models.Model):
    scraper = models.ForeignKey(Scraper, related_name='runs')
    date = models.DateTimeField(auto_now_add=True, db_index=True)
    end_date = models.DateTimeField(db_index=True, blank=True, null=True)

    def duration(self):
        return self.end_date - self.date

    def __unicode__(self):
        date = self.date.strftime('%m/%d/%Y %I:%M:%S %p')
        return "%s - %s" % (self.scraper_id, date)


class Stat(models.Model):
    run = models.ForeignKey(Run, related_name='stats')
    name = models.CharField(max_length=255)
    value = models.IntegerField(default=0)
