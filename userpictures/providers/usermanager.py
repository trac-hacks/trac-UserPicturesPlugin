from trac.config import *
from trac.core import *

try:
    from tracusermanager.api import UserManager
except ImportError:
    class UserManager(object):
        def __init__(self, env):
            self.env = env
        def get_user(self, username):
            self.env.log.warning("Trying to use UserPicturesUserManagerProvider, but UserManager plugin is not installed!")
            return None

from userpictures import IUserPicturesProvider

class UserPicturesUserManagerProvider(Component):
    implements(IUserPicturesProvider)

    def get_src(self, req, username, size):
        user_manager = UserManager(self.env)
        user = user_manager.get_user(username)
        if not user or not user['picture_href']:
            return req.href.chrome('userpictures/default-portrait.gif')
        return user['picture_href']


