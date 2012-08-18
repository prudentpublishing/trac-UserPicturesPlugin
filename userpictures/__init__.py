from genshi.filters.transform import Transformer
from genshi.builder import tag
import hashlib
import itertools
from pkg_resources import resource_filename
import re

from trac.config import *
from trac.core import *
from trac.web.api import ITemplateStreamFilter

class UserPicturesModule(Component):
    implements(ITemplateStreamFilter)

    ticket_comment_diff_size = Option("userpictures", "ticket_comment_diff_size", default="40")
    ticket_reporter_size = Option("userpictures", "ticket_reporter_size", default="60")
    ticket_comment_size = Option("userpictures", "ticket_comment_size", default="40")
    timeline_size = Option("userpictures", "timeline_size", default="30")
    browser_changeset_size = Option("userpictures", "browser_changeset_size", default="40")
    browser_lineitem_size = Option("userpictures", "browser_lineitem_size", default="20")

    def filter_stream(self, req, method, filename, stream, data):
        filter_ = []
        if req.path_info.startswith("/ticket"):
            filter_.extend(self._ticket_filter(req, data))
        elif req.path_info.startswith("/timeline"):
            filter_.extend(self._timeline_filter(req, data))
        elif req.path_info.startswith("/browser"):
            filter_.extend(self._browser_filter(req, data))
        elif req.path_info.startswith("/log"):
            filter_.extend(self._log_filter(req, data))

        for f in filter_:
            if f is not None:
                stream |= f

        #add_stylesheet(req, 'tracvatar/tracvatar.css')
        return stream

    def _generate_avatar(self, req, data, author, class_, size):
        email_hash = hashlib.md5("ethan.jucovy@gmail.com").hexdigest()
        if req.base_url.startswith("https://"):
            href = "https://gravatar.com/avatar/" + email_hash
        else:
            href = "http://www.gravatar.com/avatar/" + email_hash
        href += "?size=%s" % size
        return tag.img(src=href, class_='tracvatar %s' % class_,
                       width=size, height=size).generate()

    def _ticket_filter(self, req, data):
        filter_ = []
        if "action=comment-diff" in req.query_string:
            filter_.extend(self._ticket_comment_diff_filter(req, data))
        else:
            filter_.extend(self._ticket_reporter_filter(req, data))
            filter_.extend(self._ticket_comment_filter(req, data))
        return filter_

    def _ticket_comment_diff_filter(self, req, data):
        author = data['change']['author']

        return [lambda stream: Transformer('//dd[@class="author"]'
                                           ).prepend(self._generate_avatar(
                    req, data, author, 
                    "ticket-comment-diff", self.ticket_comment_diff_size)
                                                     )(stream)]

    def _ticket_reporter_filter(self, req, data):
        if 'ticket' not in data:
            return []
        author = data['ticket'].values['reporter']

        return [lambda stream: Transformer('//div[@id="ticket"]'
                                           ).prepend(self._generate_avatar(
                    req, data, author,
                    'ticket-reporter', self.ticket_reporter_size)
                                                     )(stream)]

    def _ticket_comment_filter(self, req, data):
        if 'changes' not in data:
            return []

        apply_authors = []
        for change in data['changes']:
            author = change['author']
            apply_authors.insert(0, author)

        def find_change(stream):
            stream = iter(stream)
            author = apply_authors.pop()
            tag = self._generate_avatar(req, data, author,
                                        'ticket-comment', self.ticket_comment_size)
            return itertools.chain([next(stream)], tag, stream)

        return [Transformer('//div[@id="changelog"]/div[@class="change"]/h3[@class="change"]'
                            ).filter(find_change)]

    def _timeline_filter(self, req, data):
        if 'events' not in data:
            return []

        apply_authors = []
        for event in reversed(data['events']):
            author = event['author']
            apply_authors.append(author)

        def find_change(stream):
            stream = iter(stream)
            author = apply_authors.pop()
            tag = self._generate_avatar(req, data, author,
                                        'timeline', self.timeline_size)
            return itertools.chain(tag, stream)

        return [Transformer('//div[@id="content"]/dl/dt/a/span[@class="time"]'
                            ).filter(find_change)]

    def _browser_filter(self, req, data):
        if 'dir' not in data:
            return self._browser_changeset_filter(req, data)
        else:
            return self._browser_lineitem_filter(req, data)

    def _browser_changeset_filter(self, req, data):
        if 'file' not in data or not data['file'] or 'changeset' not in data['file']:
            return []
        author = data['file']['changeset'].author

        return [lambda stream: Transformer('//table[@id="info"]//th'
                                           ).prepend(self._generate_avatar(
                    req, data, author,
                    "browser-changeset", self.browser_changeset_size)
                                                     )(stream)]

    def _browser_lineitem_filter(self, req, data):
        if not data.get('dir') or 'changes' not in data['dir']:
            return []
        return self._browser_lineitem_render_filter(req, data)
    
    def _browser_lineitem_render_filter(self, req, data):
        def find_change(stream):
            author = stream[1][1]
            tag = self._generate_avatar(req, data, author,
                                        'browser-lineitem', self.browser_lineitem_size)
            return itertools.chain([stream[0]], tag, stream[1:])

        return [Transformer('//td[@class="author"]').filter(find_change)]

    def _log_filter(self, req, data):
        if 'changes' not in data:
            return []

        return self._browser_lineitem_render_filter(req, data)
