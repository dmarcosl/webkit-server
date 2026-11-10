"""Run under Xvfb. Only a loopback fixture server is contacted."""
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import webkit_server as wk

HTML = '<!doctype html><html><body><p id="v">before</p></body></html>'
XML = '<?xml version="1.0"?><rss><channel><title>á 日本 😀</title></channel></rss>'
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.server.hits.append(self.path)
        if self.path == '/slow': time.sleep(2)
        changed = self.path == '/changing' and self.server.hits.count(self.path) > 1
        xml = self.path == '/xml' or changed
        body = (XML if xml else HTML).encode('utf-8')
        self.send_response(503 if changed else 200)
        self.send_header('Content-Type', ('application/xml' if xml else 'text/html')+'; charset=utf-8')
        self.end_headers()
        try: self.wfile.write(body)
        except BrokenPipeError: pass
    def log_message(self, *args): pass

class FramingTests(unittest.TestCase):
    def test_utf8_byte_length(self):
        class Socket:
            data = b''
            def sendall(self, data): self.data += data
        conn = object.__new__(wk.ServerConnection)
        conn._sock = Socket()
        conn._read_response = lambda: 'ok'
        value = 'á 日本 😀\nsecond line'
        conn.issue_command('SetHtml', value)
        encoded = value.encode('utf-8')
        self.assertEqual(conn._sock.data, b'SetHtml\n1\n'+str(len(encoded)).encode()+b'\n'+encoded)

class DOMTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.http = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        cls.http.hits = []
        threading.Thread(target=cls.http.serve_forever, daemon=True).start()
        cls.url = 'http://127.0.0.1:' + str(cls.http.server_port)
    @classmethod
    def tearDownClass(cls):
        cls.http.shutdown(); cls.http.server_close()
    def setUp(self):
        self.engine = wk.Server()
        self.client = wk.Client(wk.ServerConnection(self.engine))
        self.client.set_timeout(1)
    def tearDown(self):
        self.client.conn._sock.close()
        self.engine.kill()
        self.assertIsNotNone(self.engine._server.poll())
    def test_fresh_set_html_and_unicode_followed_by_commands(self):
        self.client.set_html(HTML.replace('before','á 日本 😀\nsecond line'))
        self.assertIn('á 日本 😀', self.client.body())
        self.assertIn('second line', self.client.body())
        self.assertEqual(self.client.eval_script('2+2'), 4)
    def test_immediate_and_delayed_mutation(self):
        for delay in (0, 100):
            self.client.set_html(HTML + '<script>setTimeout(function(){document.getElementById("v").textContent="after";},%s);</script>' % delay)
            deadline = time.monotonic() + 3
            while self.client.xpath('//*[@id="v"]')[0].text() != 'after':
                self.assertLess(time.monotonic(), deadline)
                time.sleep(.02)
            self.assertIn('>after<', self.client.body())
    def test_source_still_fetches_url_and_body_is_dom(self):
        self.client.visit(self.url+'/html')
        self.client.set_html(HTML.replace('before','changed'), self.url+'/html')
        count = len(self.http.hits)
        self.assertEqual(self.client.source(), HTML)
        self.assertEqual(len(self.http.hits), count+1)
        self.assertIn('changed', self.client.body())
    def test_source_on_about_blank_preserves_body(self):
        self.client.set_html(HTML)
        before = self.client.body()
        for _ in range(2):
            self.assertEqual(self.client.source(), '')
            self.assertEqual(self.client.body(), before)

    def test_source_xml_does_not_replace_set_html_document(self):
        self.client.set_html(HTML, self.url+'/xml')
        before = self.client.body()
        self.assertEqual(self.client.source(), XML)
        self.assertEqual(self.client.body(), before)
        self.client.visit(self.url+'/xml')
        self.assertEqual(self.client.body(), XML)

    def test_source_changed_response_preserves_document_metadata(self):
        self.client.visit(self.url+'/changing')
        before = (self.client.body(), self.client.status_code(), self.client.headers())
        self.assertEqual(self.client.source(), XML)
        self.assertEqual((self.client.body(), self.client.status_code(), self.client.headers()), before)

    def test_empty_html_is_a_valid_empty_dom(self):
        self.client.set_html('')
        self.assertIn('<body></body>', self.client.body())
    def test_xml_html_xml_navigation(self):
        self.client.visit(self.url+'/xml')
        self.assertEqual(self.client.body(), XML)
        self.client.set_html(HTML)
        self.assertIn('before', self.client.body())
        self.client.visit(self.url+'/xml')
        self.assertEqual(self.client.body(), XML)
        self.client.visit(self.url+'/html')
        self.assertIn('before', self.client.body())
    def test_command_error_does_not_corrupt_next_command(self):
        with self.assertRaises(wk.InvalidResponseError):
            self.client.conn.issue_command('NotACommand')
        self.client.set_html(HTML)
        self.assertIn('before', self.client.body())
    def test_navigation_timeout_remains_bounded(self):
        start = time.monotonic()
        with self.assertRaises(wk.InvalidResponseError):
            self.client.visit(self.url+'/slow')
        self.assertLess(time.monotonic()-start, 4)

if __name__ == '__main__': unittest.main(verbosity=2)
