#include "SetHtml.h"
#include "WebPage.h"
#include <QUrl>

SetHtml::SetHtml(WebPageManager *manager, QStringList &arguments, QObject *parent)
  : SocketCommand(manager, arguments, parent)
{ }

void SetHtml::start() {
  // setHtml has no network reply to refresh the frame metadata used by Body.
  // Mark this document as HTML even after a prior non-HTML navigation.
  page()->currentFrame()->setProperty("contentType", "text/html; charset=utf-8");
  page()->currentFrame()->setProperty("body", QByteArray());
  if (arguments().size() > 1)
    page()->currentFrame()->setHtml(arguments()[0], QUrl(arguments()[1]));
  else
    page()->currentFrame()->setHtml(arguments()[0]);
  finish(true);
}
