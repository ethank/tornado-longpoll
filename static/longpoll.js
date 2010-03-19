// Copyright 2009 FriendFeed
//
// Licensed under the Apache License, Version 2.0 (the "License"); you may
// not use this file except in compliance with the License. You may obtain
// a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
// WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
// License for the specific language governing permissions and limitations
// under the License.

// This is the Tornado Long-Polling client-side code and support stuff
// broken out into a separate file and made slightly more reuse-friendly
// than the original chat demo.

function getCookie(name) {
    var r = document.cookie.match("\\b" + name + "=([^;]*)\\b");
    return r ? r[1] : undefined;
}

jQuery.longPoll = function( url, callbacks ) {
    /* Create a new long-polling object to interact with a Tornado web-server

    returns a longPoll object

    The longPoll object has these attributes:

        callbacks -- an array to which you can append code which needs to be called
                          on each successful load.  function( json_result ) {} is called for each
                          successful poll

        baseArguments -- an object (dictionary) of parameters which will be passed to the
                                    polling query.  This can be updated e.g. to restrict the query to
                                    a subset of values (via a "cursor" or similar value).

        poll() -- function which starts polling the server

        stop() -- function which causes the polling to stop (eventually), cancels timeouts and
                     sets a flag to prevent the next poll from happening.  TODO: store the ajax
                     request object and cancel that too.

        restart() -- function which resets the poll-suppression flag and calls poll()

        failureCallbacks -- an array to which to append code which needs to be called
                                     on every failed post.  Note: this is not edge-triggering, that is,
                                     it is called every time we try-and-fail, not just when "going offline"

        errorSleepTime -- in internal value telling us how long to wait after a failure to
                                    attempt a reconnect

        live -- flag controlled by stop/restart

    */
    if (callbacks == null) {
        callbacks = [];
    }
    var updater = {
        callbacks: [],
        failureCallbacks: [],
        /* baseArguments can be modified by outside code to e.g. add cursors or other metadata */
        baseArguments: {"_xsrf": getCookie("_xsrf")},
        errorSleepTime: 500,
        live: true
    };
    updater.onSuccess = function( result ) {
        updater.errorSleepTime = 500; /* reset as we're back to working */
        updater.timer = null;
        for (var i=0;i<updater.callbacks.length;i++) {
            try {
                updater.callbacks[i]( result );
            } catch (e) {
                console.log( "Failure during callback "+updater.callbacks[i] );
            }
        }
        /* Immediately request any new updates... */
        updater.poll();
    };
    updater.onError = function( response ) {
        /*alert(response.status);*/
        updater.errorSleepTime *= 2;
        console.log("Poll error; sleeping for", updater.errorSleepTime, "ms");
        updater.timer = window.setTimeout(updater.poll, updater.errorSleepTime);
        for (var i=0;i<updater.failureCallbacks.length;i++) {
            try {
                updater.failureCallbacks[i]( response );
            } catch( e ) {
                console.log( "Failure during failure callback "+updater.failureCallbacks[i]);
            }
        }
    };
    updater.stop = function() {
        if (updater.timer) {
            window.clearTimeout( updater.timer );
            updater.timer = null;
        }
        updater.live = false;
    };
    updater.restart = function() {
        updater.live = true;
        return updater.poll();
    };
    updater.poll = function() {
        if (updater.live) {
            var args = updater.baseArguments;
            $.ajax({
                url: url,
                type: "POST",
                dataType: "json",
                data: $.param(args),
                success: updater.onSuccess,
                error: updater.onError
            });
        } else {
            console.log( 'Exiting longPoll '+updater );
        }
        updater.timer = null;
    };
    return updater;
}

jQuery.postJSON = function(url, args, callback) {
    $.ajax({
        url: url,
        data: $.param(args),
        dataType: "text",
        type: "POST",
	    success: function(response) {
            if (callback) callback(eval("(" + response + ")"));
        },
        error: function(response) {
            console.log("ERROR:", response)
        }
    });
};

jQuery.fn.formToDict = function() {
    var fields = this.serializeArray();
    var json = {}
    for (var i = 0; i < fields.length; i++) {
	json[fields[i].name] = fields[i].value;
    }
    if (json.next) delete json.next;
    return json;
};

jQuery.fn.disable = function() {
    this.enable(false);
    return this;
};

jQuery.fn.enable = function(opt_enable) {
    if (arguments.length && !opt_enable) {
        this.attr("disabled", "disabled");
    } else {
        this.removeAttr("disabled");
    }
    return this;
};

