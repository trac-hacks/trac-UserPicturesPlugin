from genshi.filters.transform import Transformer
from genshi.builder import tag
import itertools
from pkg_resources import resource_filename

from trac.config import *
from trac.core import *
from trac.web.api import ITemplateStreamFilter
from trac.web.chrome import ITemplateProvider, add_stylesheet

class IUserPicturesProvider(Interface):
    def get_src(req, username, size):
        """
        Return the path to an image for this user, either locally or on the web
        """

class DefaultUserPicturesProvider(Component):
    implements(IUserPicturesProvider)

    def get_src(self, req, username, size):
        return req.href.chrome('userpictures/default-portrait.gif')

from userpictures.providers import *

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

    pictures_provider = ExtensionOption('userpictures', 'pictures_provider',
                                        IUserPicturesProvider,
                                        'DefaultUserPicturesProvider')

    ticket_comment_diff_size = Option("userpictures", "ticket_comment_diff_size", default="30")
    ticket_reporter_size = Option("userpictures", "ticket_reporter_size", default="60")
    ticket_owner_size = Option("userpictures", "ticket_owner_size", default="30")
    ticket_comment_size = Option("userpictures", "ticket_comment_size", default="40")
    timeline_size = Option("userpictures", "timeline_size", default="30")
    report_size = Option("userpictures", "report_size", default="20")
    browser_changeset_size = Option("userpictures", "browser_changeset_size", default="30")
    browser_filesource_size = Option("userpictures", "browser_filesource_size", default="40")
    browser_lineitem_size = Option("userpictures", "browser_lineitem_size", default="20")
    search_results_size = Option("userpictures", "search_results_size", default="20")
    wiki_diff_size = Option("userpictures", "wiki_diff_size", default="30")
    wiki_history_lineitem_size = Option("userpictures", "wiki_history_lineitem_size", default="20")
    wiki_view_size = Option("userpictures", "wiki_view_size", default="40")
    attachment_view_size = Option("userpictures", "attachment_view_size", default="40")
    attachment_lineitem_size = Option("userpictures", "attachment_lineitem_size", default="20")

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
        elif req.path_info.startswith("/search"):
            filter_.extend(self._search_filter(req, data))
        elif req.path_info.startswith("/report") or req.path_info.startswith("/query"):
            filter_.extend(self._report_filter(req, data))
        elif req.path_info.startswith("/wiki"):
            filter_.extend(self._wiki_filter(req, data))
        elif req.path_info.startswith("/attachment"):
            filter_.extend(self._attachment_filter(req, data))
        
        if 'attachments' in data and data.get('attachments', {}).get('attachments'):
            filter_.extend(self._page_attachments_filter(req, data))

        for f in filter_:
            if f is not None:
                stream |= f

        add_stylesheet(req, 'userpictures/userpictures.css')
        return stream

    def _generate_avatar(self, req, author, class_, size):
        href = self.pictures_provider.get_src(req, author, size)
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
        filter_ = []
        filter_.extend(self._browser_changeset_filter(req, data))
        filter_.extend(self._browser_lineitem_filter(req, data))
        return filter_

    def _browser_changeset_filter(self, req, data):
        author = None
        if (data.get('file') or {}).get('changeset'):
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
        def find_change(stream):
            author = ''.join(stream_part[1] for stream_part in stream if stream_part[0] == 'TEXT').strip()
            tag = self._generate_avatar(req, author,
                                        'browser-lineitem', self.browser_lineitem_size)
            return itertools.chain([stream[0]], tag, stream[1:])

        return [Transformer('//td[@class="author"]').filter(find_change)]

    def _log_filter(self, req, data):
        if 'changes' not in data:
            return []

        return self._browser_lineitem_filter(req, data)

    def _search_filter(self, req, data):
        if 'results' not in data:
            return []

        ## The stream contains this stupid "By ethan" instead of just "ethan"
        ## so we'll rely on the ordering of the data instead, 
        ## and file a ticket with Trac core eventually
        results_iter = iter(data['results'])
        def find_change(stream):
            try:
                author = results_iter.next()['author']
            except StopIteration:
                author = ''.join(stream_part[1] for stream_part in stream if stream_part[0] == 'TEXT').strip() ## As a fallback, we may as well, but this should never happen...
            tag = self._generate_avatar(req, author,
                                        'search-results', 
                                        self.search_results_size)
            return itertools.chain([stream[0]], tag, stream[1:])

        return [Transformer('//span[@class="author"]').filter(find_change)]

    def _report_filter(self, req, data):
        if 'tickets' not in data and 'row_groups' not in data:
            return []

        if 'tickets' in data:
            class_ = 'query'
        elif 'row_groups' in data:
            class_ = 'report'

        def find_change(stream):
            author = ''.join(stream_part[1] for stream_part in stream if stream_part[0] == 'TEXT').strip()
            tag = self._generate_avatar(req, author,
                                        class_, self.report_size)
            return itertools.chain([stream[0]], tag, stream[1:])

        return [Transformer('//table[@class="listing tickets"]/tbody/tr/td[@class="owner"]|//table[@class="listing tickets"]/tbody/tr/td[@class="reporter"]').filter(find_change)]

    def _wiki_filter(self, req, data):
        if "action=diff" in req.query_string:
            return self._wiki_diff_filter(req, data)
        elif "action=history" in req.query_string:
            return self._wiki_history_lineitem_filter(req, data)
        elif "version" in req.query_string:
            if 'page' not in data:
                return []
            author = data['page'].author
            return [lambda stream: Transformer('//table[@id="info"]//th'
                                               ).prepend(
                    self._generate_avatar(
                        req, author,
                        "wiki-view", self.wiki_view_size)
                    )(stream)]
        return []

    def _wiki_diff_filter(self, req, data):
        author = data['change']['author']

        return [lambda stream: Transformer('//dd[@class="author"]'
                                           ).prepend(self._generate_avatar(
                    req, author, 
                    "wiki-diff", self.wiki_diff_size)
                                                     )(stream)]
    
    def _wiki_history_lineitem_filter(self, req, data):
        def find_change(stream):
            author = ''.join(stream_part[1] for stream_part in stream if stream_part[0] == 'TEXT').strip()
            tag = self._generate_avatar(req, author,
                                        'wiki-history-lineitem', self.wiki_history_lineitem_size)
            return itertools.chain([stream[0]], tag, stream[1:])

        return [Transformer('//td[@class="author"]').filter(find_change)]

    def _attachment_filter(self, req, data):
        if not data.get('attachment'):
            return []
        author = data['attachment'].author
        if not author:
            return []
        return [Transformer('//table[@id="info"]//th'
                            ).prepend(
                self._generate_avatar(
                    req, author,
                    "attachment-view", self.attachment_view_size)
                )]

    def _page_attachments_filter(self, req, data):
        def find_change(stream):
            author = ''.join(stream_part[1] for stream_part in stream if stream_part[0] == 'TEXT').strip()
            tag = self._generate_avatar(req, author,
                                        'attachment-lineitem', self.attachment_lineitem_size)
            return itertools.chain([stream[0]], tag, stream[1:])

        return [Transformer('//div[@id="attachments"]/div/ul/li/em|//div[@id="attachments"]/div[@class="attachments"]/dl[@class="attachments"]/dt/em').filter(find_change)]
        
