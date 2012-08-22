from django.db import models

from ebpub.db.models import Schema, NewsItem


class Scraper(models.Model):
    slug = models.SlugField(unique=True)
    schema = models.CharField(max_length=255)

    @models.permalink
    def get_absolute_url(self):
        return ('openrural.data_dashboard.views.view_scraper', [self.slug])

    def __unicode__(self):
        return self.slug


class Run(models.Model):
    STATUS_CHOICES = (('initialized', 'Initialized'),
                      ('running', 'Running'),
                      ('updated', 'Updated'),
                      ('skipped', 'Skipped'),
                      ('failed', 'Failed'))

    scraper = models.ForeignKey(Scraper, related_name='runs')
    date = models.DateTimeField(auto_now_add=True, db_index=True)
    end_date = models.DateTimeField(db_index=True, blank=True, null=True)
    status = models.CharField(max_length=32, choices=STATUS_CHOICES,
                              default='initialized')
    status_description = models.TextField(blank=True)
    comment = models.TextField(blank=True, default="")

    def duration(self):
        return self.end_date - self.date

    @models.permalink
    def get_absolute_url(self):
        return ('openrural.data_dashboard.views.view_run',
                [self.scraper.slug, str(self.id)])

    def __unicode__(self):
        date = self.date.strftime('%m/%d/%Y %I:%M:%S %p')
        return "%s - %s" % (self.scraper_id, date)


class Stat(models.Model):
    run = models.ForeignKey(Run, related_name='stats')
    name = models.CharField(max_length=255)
    value = models.CharField(default='', max_length=255)


class Geocode(models.Model):
    STATUS_CHOICES = (('unneeded', 'Unneeded'),
                      ('success', 'Success'),
                      ('failure', 'Failure'))
    run = models.ForeignKey(Run, related_name='geocodes')
    news_item = models.ForeignKey(NewsItem, related_name='geocodes', null=True,
                                  blank=True)
    date = models.DateTimeField(auto_now_add=True, db_index=True)
    scraper = models.CharField(max_length=255, db_index=True)
    location = models.CharField(max_length=1024)
    city = models.CharField(max_length=255, blank=True, default='')
    zipcode = models.CharField(max_length=16, blank=True, default='')
    name = models.CharField(max_length=255, blank=True, db_index=True)
    description = models.TextField(blank=True)
    status = models.CharField(choices=STATUS_CHOICES, max_length=32, default='unneeded')

    def __unicode__(self):
        if self.name:
            return u"{0}: {1}".format(self.name, self.location)
        else:
            return unicode(self.location)
