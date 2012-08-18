import hashlib
import re

from trac.config import *
from trac.core import *

from userpictures import IUserPicturesProvider

class UserPicturesGravatarProvider(Component):
    implements(IUserPicturesProvider)

    # from trac source
    _long_author_re = re.compile(r'.*<([^@]+)@([^@]+)>\s*|([^@]+)@([^@]+)')

    @property
    def email_map(self):
        if hasattr(self, '_email_map'):
            return self._email_map
        _email_map = {}
        for username, name, email in self.env.get_known_users():
            _email_map[username] = email
        setattr(self, '_email_map', _email_map)
        return self._email_map

    def get_src(self, req, username, size):
        email = ''
        if '@' not in username:
            if username != 'anonymous':
                email = self.email_map.get(username) or ''
        else:
            author_info = self._long_author_re.match(username)
            if author_info:
                if author_info.group(1):
                    email = '%s@%s' % author_info.group(1, 2)
                elif author_info.group(3):
                    email = '%s@%s' % author_info.group(3, 4)

        email_hash = hashlib.md5(email).hexdigest()
        if req.base_url.startswith("https://"):
            href = "https://gravatar.com/avatar/" + email_hash
        else:
            href = "http://www.gravatar.com/avatar/" + email_hash
        href += "?size=%s" % size
        return href

