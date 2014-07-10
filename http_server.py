"""
 Licensed under the Apache License, Version 2.0 (the "License");
 you may not use this file except in compliance with the License.
 You may obtain a copy of the License at

     http://www.apache.org/licenses/LICENSE-2.0

 Unless required by applicable law or agreed to in writing, software
 distributed under the License is distributed on an "AS IS" BASIS,
 WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 See the License for the specific language governing permissions and
 limitations under the License.
"""

# helper to load url
# runs webserver and loads url with webbrowswer module
import sys

def load_url(path):
    PORT = 8000
    httpd = StoppableHTTPServer(("127.0.0.1",PORT), handler)
    thread.start_new_thread(httpd.serve, ())
    webbrowser.open_new('http://localhost:%s/%s'%(PORT,path))
    input("Press <RETURN> to stop server\n")
    httpd.stop()
    print("To restart server run: \n%s"%server)


if sys.version_info[0] == 2:
    import SimpleHTTPServer, BaseHTTPServer
    import socket
    import thread
    import webbrowser
    handler = SimpleHTTPServer.SimpleHTTPRequestHandler
    input = raw_input
    server = "python -m SimpleHTTPServer 8000"

    class StoppableHTTPServer(BaseHTTPServer.HTTPServer):

        def server_bind(self):
            BaseHTTPServer.HTTPServer.server_bind(self)
            self.socket.settimeout(1)
            self.run = True

        def get_request(self):
            while self.run:
                try:
                    sock, addr = self.socket.accept()
                    sock.settimeout(None)
                    return (sock, addr)
                except socket.timeout:
                    pass

        def stop(self):
            self.run = False

        def serve(self):
            while self.run:
                self.handle_request()


else:
    import http.server, http.server
    import socket
    import _thread as thread
    import webbrowser
    handler = http.server.SimpleHTTPRequestHandler
    server = "python -m http.server 8000"

    class StoppableHTTPServer(http.server.HTTPServer):

        def server_bind(self):
            http.server.HTTPServer.server_bind(self)
            self.socket.settimeout(1)
            self.run = True

        def get_request(self):
            while self.run:
                try:
                    sock, addr = self.socket.accept()
                    sock.settimeout(None)
                    return (sock, addr)
                except socket.timeout:
                    pass

        def stop(self):
            self.run = False

        def serve(self):
            while self.run:
                self.handle_request()





