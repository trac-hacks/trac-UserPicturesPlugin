from genshi.filters.transform import Transformer
from genshi.builder import tag
import hashlib
import itertools
from pkg_resources import resource_filename
import re

from trac.config import *
from trac.core import *
from trac.web.chrome import ITemplateProvider, add_stylesheet
from trac.web.api import ITemplateStreamFilter

class _render_event(object):
    def __init__(self, event, base_render, generate_avatar):
        self.event = event
        self.base_render = base_render
        self.generate_avatar = generate_avatar

    def __call__(self, field, context):
        orig = self.base_render(field, context)
        if field != 'description':
            return orig
        if not self.event.get('author'):
            return orig
        author = self.event['author']

        return tag.div(self.generate_avatar(author), orig)
    ## style="padding-top: 0.2em; padding-right: 1em; margin-left: -5.8em; vertical-align: text-top"),

class UserPicturesModule(Component):
    implements(ITemplateStreamFilter, ITemplateProvider)

    ticket_comment_diff_size = Option("userpictures", "ticket_comment_diff_size", default="40")
    ticket_reporter_size = Option("userpictures", "ticket_reporter_size", default="60")
    ticket_owner_size = Option("userpictures", "ticket_owner_size", default="30")
    ticket_comment_size = Option("userpictures", "ticket_comment_size", default="40")
    timeline_size = Option("userpictures", "timeline_size", default="30")
    browser_changeset_size = Option("userpictures", "browser_changeset_size", default="30")
    browser_filesource_size = Option("userpictures", "browser_filesource_size", default="40")
    browser_lineitem_size = Option("userpictures", "browser_lineitem_size", default="20")

    ## ITemplateProvider methods

    def get_htdocs_dirs(self):
        yield 'userpictures', resource_filename(__name__, 'htdocs')

    def get_templates_dirs(self):
        return []    

    ## ITemplateStreamFilter methods

    def filter_stream(self, req, method, filename, stream, data):
        filter_ = []
        if req.path_info.startswith("/ticket"):
            filter_.extend(self._ticket_filter(req, data))
        elif req.path_info.startswith("/timeline"):
            filter_.extend(self._timeline_filter(req, data))
        elif req.path_info.startswith("/browser") or req.path_info.startswith("/changeset"):
            filter_.extend(self._browser_filter(req, data))
        elif req.path_info.startswith("/log"):
            filter_.extend(self._log_filter(req, data))

        for f in filter_:
            if f is not None:
                stream |= f

        add_stylesheet(req, 'userpictures/userpictures.css')
        return stream

    def _generate_avatar(self, req, author, class_, size):
        email_hash = hashlib.md5("ethan.jucovy@gmail.com").hexdigest()
        if req.base_url.startswith("https://"):
            href = "https://gravatar.com/avatar/" + email_hash
        else:
            href = "http://www.gravatar.com/avatar/" + email_hash
        href += "?size=%s" % size
        return tag.img(src=href, class_='userpictures_avatar %s' % class_,
                       width=size, height=size).generate()

    def _ticket_filter(self, req, data):
        filter_ = []
        if "action=comment-diff" in req.query_string:
            filter_.extend(self._ticket_comment_diff_filter(req, data))
        else:
            filter_.extend(self._ticket_reporter_filter(req, data))
            filter_.extend(self._ticket_owner_filter(req, data))
            filter_.extend(self._ticket_comment_filter(req, data))
        return filter_

    def _ticket_comment_diff_filter(self, req, data):
        author = data['change']['author']

        return [lambda stream: Transformer('//dd[@class="author"]'
                                           ).prepend(self._generate_avatar(
                    req, author, 
                    "ticket-comment-diff", self.ticket_comment_diff_size)
                                                     )(stream)]

    def _ticket_reporter_filter(self, req, data):
        if 'ticket' not in data:
            return []
        author = data['ticket'].values['reporter']

        return [lambda stream: Transformer('//div[@id="ticket"]'
                                           ).prepend(self._generate_avatar(
                    req, author,
                    'ticket-reporter', self.ticket_reporter_size)
                                                     )(stream)]
    def _ticket_owner_filter(self, req, data):
        if 'ticket' not in data:
            return []
        author = data['ticket'].values['owner']

        return [lambda stream: Transformer('//td[@headers="h_owner"]'
                                           ).prepend(self._generate_avatar(
                    req, author,
                    'ticket-owner', self.ticket_owner_size)
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
            tag = self._generate_avatar(req, author,
                                        'ticket-comment', self.ticket_comment_size)
            return itertools.chain([next(stream)], tag, stream)

        return [Transformer('//div[@id="changelog"]/div[@class="change"]/h3[@class="change"]'
                            ).filter(find_change)]

    def _timeline_filter(self, req, data):
        if 'events' not in data:
            return []

        # Instead of using a Genshi filter here,
        # we'll reach into the guts of the context
        # and manipulate the `render` function provided in there.
        # This is likely to break one day since this is not a public API!
        for event in data['events']:
            base_render = event['render']
            event['render'] = _render_event(
                event, base_render, 
                lambda author: self._generate_avatar(req, author, 
                                                     'timeline',
                                                     self.timeline_size))
            
        return []

    def _browser_filter(self, req, data):
        if not data.get('dir'):
            return self._browser_changeset_filter(req, data)
        else:
            return self._browser_lineitem_filter(req, data)

    def _browser_changeset_filter(self, req, data):
        author = None
        if data.get('file', {}).get('changeset'):
            author = data['file']['changeset'].author
        elif 'changeset' in data:
            author = data['changeset'].author
        if author is None:
            return []

        return [lambda stream: Transformer('//table[@id="info"]//th'
                                           ).prepend(self._generate_avatar(
                    req, author,
                    "browser-filesource", self.browser_filesource_size)
                                                     )(stream),
                lambda stream: Transformer('//dd[@class="author"]'
                                           ).prepend(self._generate_avatar(
                    req, author,
                    "browser-changeset", self.browser_changeset_size)
                                                     )(stream),
                ]

    def _browser_lineitem_filter(self, req, data):
        if not data.get('dir') or 'changes' not in data['dir']:
            return []
        return self._browser_lineitem_render_filter(req, data)
    
    def _browser_lineitem_render_filter(self, req, data):
        def find_change(stream):
            author = stream[1][1]
            tag = self._generate_avatar(req, author,
                                        'browser-lineitem', self.browser_lineitem_size)
            return itertools.chain([stream[0]], tag, stream[1:])

        return [Transformer('//td[@class="author"]').filter(find_change)]

    def _log_filter(self, req, data):
        if 'changes' not in data:
            return []

        return self._browser_lineitem_render_filter(req, data)
