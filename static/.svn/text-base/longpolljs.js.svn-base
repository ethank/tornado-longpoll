jQuery.submitMessage = function( message ) {
    // validate and process form here  
    var args = {"message":message};
    args._xsrf = getCookie("_xsrf");
    
    $.ajax({
     url: "/submit",
     data:$.param(args),
     type: "POST",
     dataType:"text",
     success: function(response) {
       $('#flash').fadeIn('slow').html('Submitted message').fadeOut('slow');
       //alert('success');
       }});
}


var updater = $.longPoll('/update');
updater.callbacks.push(
    function(response) {
        
        $('<div class="message">'+response['message']+'</div>').fadeIn('slow')
        .prependTo($('#messages'));        
    }
    
    )


$(document).ready(
    function() {
        $('#messages').show();
        
        updater.poll();
        $.submitMessage('I joined');
    }
);


$(function() {  
  $(".button").click(function() {  
      var message = $("input#message").val();
      $.submitMessage(message);
     });
    });
