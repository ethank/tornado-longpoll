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
from multiprocessing import Pool, Queue
import uuid
import os
from time import time
import time
from tornado.options import define, options

define("port", default=8089, help="run on the given port", type=int)


class QueueMixin(object):
    waiters = []
    cache = []
    
    def waitForMessage(self,callback,token):
        cls = QueueMixin
        waiter = {'callback':callback,'token':token}

        cls.waiters.append(waiter)

    def submitMessage(self,message,token):
        cls = QueueMixin
        for waiter in cls.waiters:
            try:
                
                callback = waiter['callback']
                waiter_token = waiter['token']
                message_to_send = "{'message':'%s : from: %s, to: %s'}" % (message,token,waiter_token)
                print message_to_send
                if waiter_token == token:
                    callback(message_to_send)
                    cls.waiters.remove(waiter)
            except:
                logging.error("error")
        #cls.waiters = []
        
        
class MainHandler(tornado.web.RequestHandler,QueueMixin):
    def get(self):
        # Set cookie

        if not self.get_secure_cookie("_session"):
            cookie = str(uuid.uuid4())
            self.set_secure_cookie("_session",cookie,1)
        self.submitMessage("client connected",self.get_secure_cookie("_session"))
        self.render("maintemplate.html")

# Async handler for the long poller
class UpdateHandler(tornado.web.RequestHandler,QueueMixin):
    @tornado.web.asynchronous
    
    def post(self):
        self.waitForMessage(self.async_callback(self.on_response),self.get_secure_cookie("_session"))
        
        
    def on_response(self,response):
        if self.request.connection.stream.closed():
            return
        self.finish(response)

def demoFunction(message):
    # this is where the rabbitmq stuff would happen. pass in the channel
    message = "<strong>%s</strong>" % message
    time.sleep(1)
    return message
      
# Handler which submits content to get pushed out
class SubmitHandler(tornado.web.RequestHandler,QueueMixin):
    @tornado.web.asynchronous
    
    def post(self):
        #process
        message = self.get_argument("message")
        p = self.application.settings.get('pool')
        p.apply_async(demoFunction,[message],callback=self.async_callback(self.on_done))
        
        
    
    def on_done(self,message):
        self.submitMessage(message,self.get_secure_cookie("_session"))
        
    def get(self):
      
        self.submitMessage("test message",self.get_secure_cookie("_session"))


class Application(tornado.web.Application):
    def __init__(self):
        handlers = [
            (r"/",MainHandler),
            (r"/update",UpdateHandler),
            (r"/submit",SubmitHandler)

        ]
        settings = dict(
            title="Long Poll Framework",
            cookie_secret="43oETzKXQAGaYdkL5gEmGeJJFuYh7EQnp2XdTP1o/Vo=",
            template_path=os.path.join(os.path.dirname(__file__), "templates"),
            static_path=os.path.join(os.path.dirname(__file__), "static"),
            xsrf_cookies=True,
            pool = Pool(4)
        )

        tornado.web.Application.__init__(self, handlers, **settings)



def main():
    tornado.options.parse_command_line()
    http_server = tornado.httpserver.HTTPServer(Application())
    http_server.listen(options.port)
    tornado.ioloop.IOLoop.instance().start()
    

if __name__ == "__main__":
    main()
