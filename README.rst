=====
ausis
=====

.. image:: https://travis-ci.org/naglis/plugin.audio.ausis.svg?branch=master
    :target: https://travis-ci.org/naglis/plugin.audio.ausis
    :alt: Build status

.. image:: https://codecov.io/gh/naglis/plugin.audio.ausis/branch/master/graph/badge.svg
    :target: https://codecov.io/gh/naglis/plugin.audio.ausis
    :alt: Code coverage

.. image:: https://img.shields.io/badge/Say%20Thanks-!-1EAEDB.svg
   :target: https://saythanks.io/to/naglis
   :alt: Say Thanks

ausis is an audiobook support plugin for `Kodi`_.

.. note:: Currently only Kodi 17 (Krypton) on GNU/Linux is supported.
   It might work on other platforms/Kodi versions, but it is not tested.

How it works?
#############

*ausis* assumes that your audiobooks are regular albums in your Kodi music
library. It then tracks playback events and stores bookmarks with playback
position for each album. Playback of an audiobook album can then be resumed
from a selected bookmark.

If the audiobook directory is set in *ausis* settings, bookmarks will only
be saved for files from within that directory. Currently, only one audiobook
directory is supported.

Known issues
############

* No bookmark is saved when switching to another file or exiting Kodi while an
  audiobook is playing (see `issue #8`_).

* Can't seek back to the beginning of a file when resuming a bookmark with
  non-zero position (see `issue #9`_).

Credits
#######

The plugin's fanart image: `Bookshelves`_ by `Germán Poo-Caamaño`_.

.. _Kodi: https://kodi.tv/
.. _`issue #8`: https://github.com/naglis/plugin.audio.ausis/issues/8
.. _`issue #9`: https://github.com/naglis/plugin.audio.ausis/issues/9
.. _Bookshelves: https://flic.kr/p/eHJWM3
.. _`Germán Poo-Caamaño`: https://www.flickr.com/photos/gpoo/
