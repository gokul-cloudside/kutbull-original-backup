$(document).ready(function() {
    
    var csrftoken = Cookies.get('csrftoken');
    function csrfSafeMethod(method) {
        // these HTTP methods do not require CSRF protection
        return (/^(GET|HEAD|OPTIONS|TRACE)$/.test(method));
    }
    $.ajaxSetup({
        beforeSend: function(xhr, settings) {
            if (!csrfSafeMethod(settings.type) && !this.crossDomain) {
                xhr.setRequestHeader("X-CSRFToken", csrftoken);
            }
        }
    });

    var url = window.location.href;

    var url_array = url.split('/');

    var ticket_id = url_array[url_array.length - 2];

    $("#breadcrumb_page_path").empty();
    $("#breadcrumb_page_path").append('<li class="text-center text-bold" ><a href="#">Client</a></li><li class="text-center text-bold"><a href="#">Client Dashboard</a></li><li class="text-center text-bold"><a href="#">Plant Dashboard</a></li><li class="text-center text-bold"><a href="#">Ticket ' + ticket_id + '</a></li>')

    ticket_view(ticket_id);

});

function ticket_view(ticket_id) {

	$.ajax({
        type: "GET",
        async: false,
        url: "/api/solar/plants/".concat(plant_slug).concat("/tickets/" + ticket_id + "/followups/"),
        success: function(ticket_info){

            $("#timeline_history").empty();
            $("#timeline_history").append("<div class='timeline-header'><div class='timeline-header-title bg-purple'>Now</div></div>");

            for(var k = ticket_info.followups.length-1; k >= 0; k--) {

                var time = new Date(ticket_info.followups[k].date);
                var title = ticket_info.followups[k].title;

                if(ticket_info.followups[k].title) {
                    $("#timeline_history").append("<div class='timeline-entry'><div class='timeline-stat'><div class='timeline-icon bg-warning'><i class='fa fa-comment fa-lg'></i></div><div class='timeline-time'>" + time + "</div></div><div class='timeline-label'><h4 class='text-info text-lg'>" + title + "</h4><p>" + ticket_info.followups[k].comment + "</p></div></div>");
                }

            }
            
        },
        error: function(data){
            console.log("no data");
        }
    });

    $.ajax({
        type: "GET",
        async:false,
        url: "/api/solar/plants/".concat(plant_slug).concat("/tickets/" + ticket_id + "/"),
        success: function(ticket_details){

            $("#ticket_details").empty();

            var modified_date = new Date(ticket_details.ticket.modified);
            var ticket_type = ticket_details.ticket.ticket_type;
            var modified = new Date(ticket_details.ticket.modified);
            var status = ticket_details.ticket.status;
            var priority = ticket_details.ticket.priority;
            var assigned_to = ticket_details.ticket.assigned_to;
            if (assigned_to) {
                $("#assign_me").attr('disabled', 'disabled');
            }

            $("#ticket_details").append("<span class='text-2x'>Title : " + ticket_details.ticket.title + "</span></br>");
            /*$("#ticket_details").append("<span>Created On : " + created_date + "<span></h4></br>");*/
            $("#ticket_details").append("<span>Modified On : " + modified_date + "</h4></br>");
            $("#ticket_details").append("<span>Assigned To : " + ticket_details.ticket.assigned_to + "</h4></br>");
            $("#ticket_details").append("<span>Status : </span><span class='label' id='status'>" + status + "</span></br>");
            $("#ticket_details").append("<span>Description : " + ticket_details.ticket.description + "</span></h4></br>");
            $("#ticket_details").append("<span>Priority : </span><span class='label' id='priority'>" + priority + "</span></br>");

            if(status == "Open") {
                $("#status").addClass('label-warning');
            } else if(status == "Acknowledged") {
                $("#status").addClass('label-primary');
            } else if(status == "Reopened") {
                $("#status").addClass('label-dark');
            } else if(status == "Resolved") {
                $("#status").addClass('label-success');
            } else if(status == "Closed") {
                $("#status").addClass('label-info');
            } else if(status == "Duplicate") {
                $("#status").addClass('label-primary');
            }

            if(priority == "Critical") {
                $("#priority").addClass('label-danger');
            } else if(priority == "High") {
                $("#priority").addClass('label-warning');
            } else if(priority == "Normal") {
                $("#priority").addClass('label-dark');
            } else if(priority == "Low") {
                $("#priority").addClass('label-purple');
            } else if(priority == "Very Low") {
                $("#priority").addClass('label-primary');
            }

            $("#associations_heading").empty();
            $("#associations_heading").append("<h3>Affected Devices</h3>");

            $("#associations_div").empty();

            if (ticket_type == "GATEWAY_POWER_OFF" || ticket_type == "GATEWAY_DISCONNECTED" || ticket_type == "INVERTERS_DISCONNECTED" || ticket_type == "AJBS_DISCONNECTED") {
                $("#associations_div").append("<div class='table-responsive'><table class='table table-striped'><thead><tr><th class='text-center'>Device Name</th><th>Status</th><th>Created</th><th>Event</th><th>Updated</th></tr></thead><tbody id='associations_devices'></tbody></table></div></div>");

            } else if (ticket_type == "INVERTERS_ALARMS") {
                $("#associations_div").append("<div class='table-responsive'><table class='table table-striped'><thead><tr><th class='text-center'>Device Name</th><th>Status</th><th>Created</th><th>Solar Status</th><th>Error Code</th><th>Created/Updated</th><th>Active</th></tr></thead><tbody id='associations_devices'></tbody></table></div></div>");

            } else if (ticket_type == "PANEL_CLEANING") {
                $("#associations_div").append("<div class='table-responsive'><table class='table table-striped'><thead><tr><th class='text-center'>Device Name</th><th>Status</th><th>Created</th><th>From</th><th>Till</th><th>Residuals</th></tr></thead><tbody id='associations_devices'></tbody></table></div></div>");

            } else if(ticket_type == "INVERTERS_UNDERPERFORMING" || ticket_type == "MPPT_UNDERPERFORMING" || ticket_type == "AJB_UNDERPERFORMING") {
                $("#associations_div").append("<div class='table-responsive'><table class='table table-striped'><thead><tr><th class='text-center'>Device Name</th><th>Status</th><th>Created</th><th>Start Time</th><th>End Time</th><th>Delta</th><th>Mean</th></tr></thead><tbody id='associations_devices'></tbody></table></div></div>");
            }

            for(var i = 0; i < ticket_details.associations.length; i++) {

                var current_status = ticket_details.associations[i].active;
                var time = $.format.date(new Date(ticket_details.associations[i].created), 'yyyy/MM/dd HH:mm')

                /*if (ticket_type == "PANEL_CLEANING") {
                    current_status = "Need Cleaning"
                } else {
                    if(current_status == true) {
                        current_status = "Exists";
                    } else {
                        current_status = "Fixed";
                    }
                }*/

                if (ticket_type == "GATEWAY_POWER_OFF" || ticket_type == "GATEWAY_DISCONNECTED" || ticket_type == "INVERTERS_DISCONNECTED" || ticket_type == "AJBS_DISCONNECTED") {
                    $("#associations_devices").append("<tr><td>" + ticket_details.associations[i].identifier_name + "</td><td><span class='label' id='current_status"+i+"'>" + current_status + "</td><td>" + time + "</td><td>" + ticket_details.associations[i].comment1 + "</td><td>" + $.format.date(new Date(ticket_details.associations[i].comment2), 'yyyy/MM/dd HH:mm') + "</td></tr>")

                } else if (ticket_type == "INVERTERS_ALARMS") {
                    $("#associations_devices").append("<tr><td>" + ticket_details.associations[i].identifier_name + "</td><td><span class='label' id='current_status"+i+"'>" + current_status + "</td><td>" + time + "</td><td>" + parseInt(ticket_details.associations[i].comment1) + "</td><td>" + parseInt(ticket_details.associations[i].comment2) + "</td><td>" + $.format.date(new Date(ticket_details.associations[i].comment3), 'yyyy/MM/dd HH:mm') + "</td><td>" + ticket_details.associations[i].comment4 + "</td></tr>")

                } else if (ticket_type == "PANEL_CLEANING") {
                    if(current_status == true) {
                        current_status = "Exists";
                    } else {
                        current_status = "Fixed";
                    }
                    $("#associations_devices").append("<tr><td>" + ticket_details.associations[i].identifier_name + "</td><td><span class='label' id='current_status"+i+"'>" + current_status + "</td><td>" + time + "</td><td>" + $.format.date(new Date(ticket_details.associations[i].comment1), 'yyyy/MM/dd HH:mm') + "</td><td>" +  $.format.date(new Date(ticket_details.associations[i].comment2), 'yyyy/MM/dd HH:mm') + "</td><td>" + parseFloat(ticket_details.associations[i].comment3).toFixed(2) + "</td></tr>")

                } else if(ticket_type == "INVERTERS_UNDERPERFORMING" || ticket_type == "MPPT_UNDERPERFORMING" || ticket_type == "AJB_UNDERPERFORMING") {
                    current_status = "Underperformed"
                    $("#associations_devices").append("<tr><td>" + ticket_details.associations[i].identifier_name + "</td><td><span class='label' id='current_status"+i+"'>" + current_status + "</td><td>" + time + "</td><td>" + $.format.date(new Date(ticket_details.associations[i].comment1), 'yyyy/MM/dd HH:mm') + "</td><td>" + $.format.date(new Date(ticket_details.associations[i].comment2), 'yyyy/MM/dd HH:mm') + "</td><td>" + parseFloat(ticket_details.associations[i].comment3).toFixed(2) + "</td><td>" + parseFloat(ticket_details.associations[i].comment4).toFixed(2) + "</td></tr>")
                }


                if(current_status == "Exists" || current_status == true) {
                    $("#current_status"+i).addClass('label-danger');
                } else if (current_status == "Fixed" || current_status == false) {
                    $("#current_status"+i).addClass('label-success');
                } else {
                    $("#current_status"+i).addClass('label-info');
                }

            }

        },
        error: function(data){
            console.log("no data");
        }
    });

    /*var comments_history = [];

    $('#comments-container').comments({
        sendText: 'Comment',
        enableAttachments : true,
        enableDeleting: false,
        enableDeletingCommentWithReplies: false,
        enableUpvoting: false,
        getComments: function(success, error) {
            var commentsArray = [{
                id: 1,
                created: '2015-10-01',
                content: 'Lorem ipsum dolort sit amet',
                fullname: 'Simon Powell',
                upvote_count: 2,
                user_has_upvoted: false
            }];
            success(commentsArray);

            console.log(commentsArray);

            $.ajax({
                type: "GET",
                url: "/api/solar/plants/".concat(plant_slug).concat("/tickets/" + ticket_id + "/followups"),
                success: function(commentsArray) {
                    
                    console.log(commentsArray.followups);

                    for(var i = 0; i < commentsArray.followups.length; i++) {

                        var date = new Date(commentsArray.followups[i].date);

                        comments_history[i].push({

                            "content": commentsArray.followups[i].comment,
                            "created": date,
                            "id": commentsArray.followups[i].id

                        });

                        console.log(comments_history);

                    }

                    success(comments_history);

                },
                error: function(data){
                    console.log("no data");
                }
            });
        }*/
        /*postComment: function(commentJSON, success, error) {

            console.log(commentJSON);

            $.ajax({
                type: 'PATCH',
                url: "/api/solar/plants/".concat(plant_slug).concat('/tickets/1/'),
                data: {
                    "comment": commentJSON,
                },
                success: function(comment) {
                    
                    success(comment);

                },
                error: function(data){
                    console.log("no data");
                }
            });
        }*/
    /*});*/

}

function assign_me() {

    var url = window.location.href;
    var url_array = url.split('/');
    var id = url_array[url_array.length - 2];

    $.ajax({
        type: "PATCH",
        async: false,
        url: "/api/solar/plants/".concat(plant_slug).concat("/tickets/" + id + "/"),
        data: {
            "new_status": 6
        },
        success: function(ticket_updated){
            
            ticket_view(id);

        },
        error: function(data){
            console.log("no data");
        }
    });

}

function new_status() {

    var url = window.location.href;
    var url_array = url.split('/');
    var id = url_array[url_array.length - 2];

    var updated_status = $("#status_dropdown").val();

    $.ajax({
        type: "PATCH",
        async: false,
        url: "/api/solar/plants/".concat(plant_slug).concat("/tickets/" + id + "/"),
        data: {
            "new_status": updated_status
        },
        success: function(ticket_updated){
            
            ticket_view(id);

        },
        error: function(data){
            console.log("no data");
        }
    });

}