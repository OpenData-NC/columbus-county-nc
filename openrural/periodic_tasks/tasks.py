from datetime import timedelta

from celery.task import Task, PeriodicTask
from celery.registry import tasks
from celery.schedules import crontab

from ebpub.alerts.sending import main as send_alerts
from ebpub.db.bin.update_aggregates import update_all_aggregates


class AggregatesTask(PeriodicTask):

    name = 'openrural.aggregates'
    run_every = timedelta(hours=12)

    def run(self, dry_run=False, reset=False):
        logger = self.get_logger()
        logger.info("Starting aggregates task")
        update_all_aggregates(dry_run, reset)
        logger.info("Stopping aggregates task")


class DailyAlertsTask(PeriodicTask):
    alert_frequency = 'daily'

    name = 'openrural.dailyalerts'
    run_every = crontab(hour=0, minute=1)

    def run(self):
        logger = self.get_logger()
        logger.info('Starting %s alerts task' % self.alert_frequency)
        send_alerts(['-f', self.alert_frequency])
        logger.info('Stopping %s alerts task' % self.alert_frequency)


class WeeklyAlertsTask(DailyAlertsTask):
    alert_frequency = 'weekly'

    name = 'openrural.weeklyalerts'
    run_every = crontab(hour=1, minute=1, day_of_week='wednesday')


tasks.register(AggregatesTask)
tasks.register(DailyAlertsTask)
tasks.register(WeeklyAlertsTask)
