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
from amqplib import client_0_8 as amqp
from amqplib.client_0_8 import Message

import tamqp


define("port", default=8089, help="run on the given port", type=int)

#static methods


#demos a async multiproc function
def demoFunction(message):
    # this is where the rabbitmq stuff would happen. pass in the channel
    message = "<strong>%s</strong>" % message
    time.sleep(1)
    return message
    
# setup the amqp library    
def amqp_setup():
    conn = amqp.Connection(host="localhost:5672",userid="guest",password="guest",virtual_host="/",insist=False)
    chan = conn.channel()
    
    chan.exchange_declare(exchange="router",type="topic",durable=True,auto_delete=False)
    chan.queue_declare(queue="beacon_server",durable=True,exclusive=False,auto_delete=False)
    
    chan.queue_bind(queue="beacon_server",exchange="router",routing_key="beacon.#")
    
# simple channel factory    
def channel_factory():
    conn = amqp.Connection(host="localhost:5672",userid="guest",password="guest",virtual_host="/",insist=False)
    return conn.channel()

# method to notify listeners to the queue. could use some routing here?
listeners= []
def notify_listeners(msg):
    for l in list(listeners):

        l(msg)


class QueueMixin(object):
    waiters = []
    cache = []
    
    def waitForMessage(self,callback,token):
        cls = QueueMixin
        # create method for identifying
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
                # if the waiter is the same as the sender, send back response
                if waiter_token == token:
                    callback(message_to_send)
                    # waiter is now over, it'll rehook in
                    cls.waiters.remove(waiter)
            except:
                logging.error("error")
        #cls.waiters = []
        

# Main handler for the non-rabbitmq async long-poll        
class MainHandler(tornado.web.RequestHandler,QueueMixin):
    def get(self):
        # Set cookie
        
        if not self.get_secure_cookie("_session"):
            cookie = str(uuid.uuid4())
            self.set_secure_cookie("_session",cookie,1)
        self.submitMessage("client connected",self.get_secure_cookie("_session"))
        self.render("maintemplate.html")

# Main handler for the Queue based long poll
class QueueMainHandler(tornado.web.RequestHandler):
    def get(self):
        if not self.get_secure_cookie("_session"):
            cookie = str(uuid.uuid4())
            self.set_secure_cookie("_session",cookie,1)
        self.render("queue.html")


# Async handler for the queue, bound to by the long poll javascript
class UpdateQueueHandler(tornado.web.RequestHandler):
    @tornado.web.asynchronous
    def post(self):
        listeners.append(self.on_response)
        
    def on_response(self,msg):
        listeners.remove(self.on_response)
        if self.request.connection.stream.closed():
            return
        self.finish(msg.body)

# Handler for publishing to rabbitMQ
class PubHandler(tornado.web.RequestHandler):
    
    def send(self,message):
        message_to_send = "{'message':'%s'}" % message
        msg = Message(message_to_send)
        producer.publish(msg, exchange="router",routing_key="beacon.test")
        
    def get(self):
        self.send(self.get_argument("message"))
    
    def post(self):
        self.send(self.get_argument("message"))

# Async handler for the long poller, non rabbitmq
class UpdateHandler(tornado.web.RequestHandler,QueueMixin):
    @tornado.web.asynchronous
    
    def post(self):
        # wait for the message, sending in the session ID
        self.waitForMessage(self.async_callback(self.on_response),self.get_secure_cookie("_session"))
        
        
    def on_response(self,response):
        if self.request.connection.stream.closed():
            return
        self.finish(response)


      
# Handler which submits content to get pushed out
class SubmitHandler(tornado.web.RequestHandler,QueueMixin):
    #@tornado.web.asynchronous
    
    def post(self):
        #process asynchronously
        message = self.get_argument("message")
        p = self.application.settings.get('pool')
        # spawn a new thread from the main poll to execute demo function, argument message, with callback
        p.apply_async(demoFunction,[message],callback=self.async_callback(self.on_done))
        
        
    # callback from async multiproc
    def on_done(self,message):
        # after processing, send back to the client the processed response
        self.submitMessage(message,self.get_secure_cookie("_session"))
        
    def get(self):
      
        self.submitMessage("test message",self.get_secure_cookie("_session"))


class Application(tornado.web.Application):
    def __init__(self):
        handlers = [
            (r"/",MainHandler),
            (r"/update",UpdateHandler),
            (r"/submit",SubmitHandler),
            (r"/monitor",UpdateQueueHandler),
            (r"/pub",PubHandler),
            (r"/queue",QueueMainHandler)

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
    global listeners, consumer, producer
    amqp_setup()
    consumer = tamqp.AmqpConsumer(channel_factory,"beacon_server",notify_listeners)
    producer = tamqp.AmqpProducer(channel_factory)
    
    tornado.options.parse_command_line()
    http_server = tornado.httpserver.HTTPServer(Application())
    http_server.listen(options.port)
    tornado.ioloop.IOLoop.instance().start()
    

if __name__ == "__main__":
    main()
