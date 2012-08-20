Adds user picture icons (avatars) to Trac.

Screenshots of the plugin in action can be found at https://github.com/boldprogressives/trac-UserPicturesPlugin/wiki/Screenshots

Credit goes to Michael Bayer for the idea -- and most of the code -- in https://bitbucket.org/zzzeek/tracvatar

A mirror is also available on Bitbucket: https://bitbucket.org/boldprogressives/trac-userpictures-plugin

The avatar engine is configurable, and two are provided in this
package: a GravatarProvider that looks up the user's email address at
Gravatar, and a UserManagerProvider that uses internally hosted images
provided by the Trac UserManager Plugin if it is installed: http://trac-hacks.org/wiki/UserManagerPlugin

The approach of the plugin is to filter specific Trac views, gather
all the authors found in the "data" hash being passed to Genshi, then
using Genshi filters to insert additional avatar nodes with the proper
img tags. 

Currently supported views are:

 * Timeline
 * Ticket details: reporter, owner, comments, comment diffs
 * Attachment views (on tickets, wiki pages, etc)
 * Source control views (directory listings, file contents, changesets)
 * Report and custom query views
 * Wiki history, diffs and individual versions
 * Search results

This is, more or less, all the places where users show up in a
standard Trac instance.  If you find any other places where icons
should also be inserted, whether in a standard Trac installation or in
a view provided by your favorite plugin, please submit an issue or a
patch.

Patches implementing additional avatar engines are also welcome.

Installation
============

Install the plugin in your favorite way (python setup.py develop,
uploading an egg, etc) and then enable its components in trac.ini like
so::

  [components]
  userpictures.* = enabled

You should then choose your preferred avatar engine.  For Gravatar::

  [userpictures]
  pictures_provider = UserPicturesGravatarProvider

For UserManager, ensure that the UserManager plugin is installed, and
then::

  [userpictures]
  pictures_provider = UserPicturesUserManagerProvider

If you do not explicitly select either engine, a default provider is
used which displays a blank silhouette for every user.

There are a number of optional "size" settings for each view; these
are set to sensible defaults that are designed to look good with a
standard Trac install and the stylesheet provided by this plugin, but
look at the source in userpictures/__init__.py (and the CSS in
userpictures/htdocs/userpictures.css) if you really want to change the
way the icons are displayed. 
