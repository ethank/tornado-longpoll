#!/usr/bin/env python
#
# Copyright 2009 Facebook
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import logging
import tornado.auth
import tornado.escape
import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.web
import os.path
import Queue
import uuid
from time import time
from tornado.options import define, options

define("port", default=8089, help="run on the given port", type=int)


class QueueMixin(object):
    waiters = []
    cache = []
    
    def waitForMessage(self,callback):
        cls = QueueMixin
        cls.waiters.append(callback)
        
    def submitMessage(self,message):
        cls = QueueMixin
        message = "{'message':'%s'}" % message
        for callback in cls.waiters:
            try:
                callback(message)
            except:
                loggin.error("error")
        cls.waiters = []
        
        
class MainHandler(tornado.web.RequestHandler,QueueMixin):
    def get(self):
        self.submitMessage("client connected")
        self.render("maintemplate.html")

class UpdateHandler(tornado.web.RequestHandler,QueueMixin):
    @tornado.web.asynchronous
    
    def post(self):
        self.waitForMessage(self.async_callback(self.on_response))
        
        
    def on_response(self,response):
        if self.request.connection.stream.closed():
            return
        self.finish(response)
      

class SubmitHandler(tornado.web.RequestHandler,QueueMixin):
    def post(self):
        self.submitMessage(self.get_argument("message"))
        
    def get(self):
        self.submitMessage("test message")


class Application(tornado.web.Application):
    def __init__(self):
        handlers = [
            (r"/",MainHandler),
            (r"/update",UpdateHandler),
            (r"/submit",SubmitHandler)

        ]
        settings = dict(
            title="Long Poll Test",
            cookie_secret="43oETzKXQAGaYdkL5gEmGeJJFuYh7EQnp2XdTP1o/Vo=",
            template_path=os.path.join(os.path.dirname(__file__), "templates"),
            static_path=os.path.join(os.path.dirname(__file__), "static"),
            xsrf_cookies=True,
        )

        tornado.web.Application.__init__(self, handlers, **settings)



def main():
    tornado.options.parse_command_line()
    http_server = tornado.httpserver.HTTPServer(Application())
    http_server.listen(options.port)
    tornado.ioloop.IOLoop.instance().start()
    

if __name__ == "__main__":
    main()
