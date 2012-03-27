from graypy import GELFHandler


class CustomGELFHandler(GELFHandler):
    """
    GELF Handler that accepts an ``extra_fields`` dictionary which is added to
    logged messages
    """

    def __init__(self, *args, **kwargs):
        self.extra_fields = kwargs.pop('extra_fields', {})
        GELFHandler.__init__(self, *args, **kwargs)

    def make_message_dict(self, record):
        msg_dict = dict(('_' + k, v) for k, v in self.extra_fields.items())
        msg_dict.update(GELFHandler.make_message_dict(self, record))
        # the request object, if added by Django's exception handler, is
        # not picklable (which prevents graypy from sending this log record)
        # and may contain sensitive information, so just remove it here. repr()
        # may be used to obtain a string version of the request if needed
        msg_dict.pop('_request', None)
        # force full_message to be a full stack trace, if available
        if record.exc_info:
            import traceback
            exception = traceback.format_exception_only(*record.exc_info[:2])
            exception = '; '.join([part.strip() for part in exception])
            stack_trace = '\n'.join(traceback.format_exception(*record.exc_info))
            msg_dict['short_message'] += ' (%s)' % exception
            msg_dict['full_message'] = stack_trace
        return msg_dict
