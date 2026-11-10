**NOTE: This package is not actively maintained. It uses QtWebkit, which is end-of-life and probably doesn't get security fixes backported. Consider using a similar package like Spynner instead.**

# Overview

**Author:** Niklas Baumstark

A standalone version of the Webkit server included in [capybara-webkit][1].
It includes a slim Python wrapper and the following improvements over the
original version from thoughtbot:

* `Wait` command to wait for the current page to load
* `SetAttribute` command to [configure certain `QWebkit` settings][2]
* `SetHtml` command to [load custom HTML][3] into the browser (e.g. to
  execute scripts on web pages scraped by a static scraper)
* `SetViewportSize` command to set the viewport size of the in-memory browser

If you are interested in web scraping using this server, have a look at [dryscrape][4].

# Building and Installing

To install the Python binding (this also builds the server and places it into
Python's `site-package` directory):

    sudo python setup.py install

If you don't need the Python bindings, you can also use the supplied `build.sh`
shellscript to build the server only.

### A word about Qt 5.6

The 5.6 version of Qt removes the Qt WebKit module in favor of the new module Qt WebEngine. So far webkit-server has not been ported to WebEngine (and likely won't be in the near future), so Qt <= 5.5 is a requirement.

# Contact, Bugs, Contributions

If you have any problems with this software, don't hesitate to open an 
issue on [Github](https://github.com/niklasb/webkit-server) or open a pull 
request or write a mail to **niklas 
baumstark at Gmail**.

# License

This software is based on [capybara-webkit][1].
capybara-webkit is Copyright (c) 2011 thoughtbot, inc. It is free software, and
may be redistributed under the terms specified in the LICENSE file.

 [1]: https://github.com/thoughtbot/capybara-webkit
 [2]: https://github.com/thoughtbot/capybara-webkit/pull/171
 [3]: https://github.com/thoughtbot/capybara-webkit/pull/170
 [4]: https://github.com/niklasb/dryscrape
## DOM and UTF-8 regressions

`SetHtml` now marks the frame as HTML and clears its previous raw response body,
so `Body` serializes the current DOM in fresh sessions and after XML navigation.
HTTP non-HTML bodies retain their existing raw-response behavior. `Source` is
unchanged: it fetches the current URL again; it is not a cached original source
or an alias for the DOM. An empty HTML input still produces an empty HTML DOM.

Command arguments are now UTF-8 encoded before their byte length is written to
the socket. This fixes multi-byte input leaving trailing bytes in the protocol.
The server response framing remains unchanged.

Run `tests/test_dom_regressions.py` under Xvfb with the local Python module and
compiled executable (named `webkit_server` beside `webkit_server.py`) on
PYTHONPATH. The tests contact only their own loopback HTTP fixture and start/kill
a fresh WebKit per integration test. Qt5 WebKit is required. The Python framing
test itself does not require a browser. No production dependency updates or
package publication are part of this change.


### Source does not replace document metadata

Source GETs are tagged with an internal QNetworkRequest attribute (not an HTTP
header). Their replies no longer emit the navigation metadata update signal or
modify navigation redirect mappings. They still use the shared network manager,
including its headers, cookies, authentication and proxy configuration; Source
still performs a fresh request and is not a cached original document.

Regression coverage includes repeated Source on about:blank after SetHtml,
Source fetching XML for an in-memory HTML document, and a URL whose second
response changes status/content type. Body and document response metadata must
remain unchanged; ordinary subsequent navigation must still update them.
