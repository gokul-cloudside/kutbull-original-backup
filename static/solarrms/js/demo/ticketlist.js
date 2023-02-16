var page_load_time = null
var first_page_load = true;

$(document).ready(function() {
    
    mixpanel.identify(user_email);

    $("#breadcrumb_page_path").empty();
    $("#breadcrumb_page_path").append('<li class="text-center text-bold" ><a href="#">Client</a></li><li class="text-center text-bold"><a href="#">Client Dashboard</a></li><li class="text-center text-bold"><a href="#">Plant Dashboard</a></li><li class="text-center text-bold"><a href="#">Tickets</a></li>')

    ticket_list();

});

var isValid;
var option = {
    container: 'popover',
    message: 'This value is not valid',
    feedbackIcons: {
        valid: 'fa fa-check-circle fa-lg text-success',
        invalid: 'fa fa-times-circle fa-lg',
        validating: 'fa fa-refresh'
    },
    fields: {
        ticket_title: {
            message: 'The value is not valid',
            validators: {
                notEmpty: {
                    message: 'The value is required.'
                }
            }
        },
        ticket_issue: {
            message: 'The value is not valid',
            validators: {
                notEmpty: {
                    message: 'The value is required.'
                }
            }
        },
        date_occurred: {
            message: 'The value is not valid',
            validators: {
                notEmpty: {
                    message: 'The value is required.'
                }
            }
        },
        start_time: {
            message: 'The value is not valid',
            validators: {
                notEmpty: {
                    message: 'The value is required.'
                }
            }
        },
        decription_issue: {
            message: 'The value is not valid',
            validators: {
                notEmpty: {
                    message: 'The value is required.'
                }
            }
        }
    }
};

$("#create_ticket").bootstrapValidator(option).on('success.field.bv', function(e, data) {
    // $(e.target)  --> The field element
    // data.bv      --> The BootstrapValidator instance
    // data.field   --> The field name
    // data.element --> The field element

    var $parent = data.element.parents('.form-group');

    // Remove the has-success class
    $parent.removeClass('has-success');


    // Hide the success icon
    //$parent.find('.form-control-feedback[data-bv-icon-for="' + data.field + '"]').hide();
}).on('error.form.bv', function(e) {
    isValid = false;
});

function ticket_list() {

    $.ajax({
        type: "GET",
        url: "/api/solar/plants/".concat(plant_slug).concat('/tickets/'),
        success: function(tickets){

            $("#ticket_list_table").empty();
            $("#ticket_list_table").append('<table id="tickets_table" class="display" cellspacing="0" width="100%"><thead id="filter_row"><tr><th class="text-center" style="width: 25%;">Title</th><th style="width: 20%;">Modified</th><th style="width: 10%;">Assigned To</th><th style="width: 12%;">Status</th><th style="width: 23%;">Description</th><th style="width: 10%;">Priority</th></tr></thead><tbody id="ticket_list_row"><tbody></table>');

            for(var k = 0; k < tickets.length; k++) {
                /*var created_date = new Date(tickets[k].created);*/
                var modified_date = new Date(tickets[k].modified);
                var due_date = new Date(tickets[k].due_date);
                var status = tickets[k].status;
                var priority = tickets[k].priority;

                $("#ticket_list_row").append("<tr><td id='ticket"+k+"'><a class='btn-link' href='/solar/plant/" + plant_slug + "/ticket_view/" + tickets[k].id + "/'><span>" + tickets[k].title + "</span></a></td><td><span>" + modified_date + "</span></td><td><div id='input_box'>" + tickets[k].assigned_to + "</div></td><td><div id='status"+ k +"' class='label label-table' style='max-width: initial;'>" + status + "</div></td><td>" + tickets[k].description + "</td><td><div id='priority"+ k +"' class='label label-table'>" + priority + "</div></td></tr>");

                if(status == "Open") {
                    $("#status"+k).addClass('label-warning');
                } else if(status == "Acknowledged") {
                    $("#status"+k).addClass('label-primary');
                } else if(status == "Reopened") {
                    $("#status"+k).addClass('label-dark');
                } else if(status == "Resolved") {
                    $("#status"+k).addClass('label-success');
                } else if(status == "Closed") {
                    $("#status"+k).addClass('label-info');
                } else if(status == "Duplicate") {
                    $("#status"+k).addClass('label-primary');
                }

                if(priority == "Critical") {
                    $("#priority"+k).addClass('label-danger');
                } else if(priority == "High") {
                    $("#priority"+k).addClass('label-warning');
                } else if(priority == "Normal") {
                    $("#priority"+k).addClass('label-dark');
                } else if(priority == "Low") {
                    $("#priority"+k).addClass('label-purple');
                } else if(priority == "Very Low") {
                    $("#priority"+k).addClass('label-primary');
                }
            }

            $('#tickets_table #filter_row th').each(function () {
                var title = $(this).text();
                if(title == "Assigned To" || title == "Status" || title == "Priority") {
                    $(this).html('<input type="text" placeholder="Search '+title+'"/>');
                }
            });

            // DataTable
            var table = $('#tickets_table').DataTable({
                "language": {
                    "search": "Search or Filter"
                },
                "order": [[3, "desc"]]
            });
 
            // Apply the search
            table.columns().every( function () {
                var that = this;

                $( 'input', this.header() ).on( 'keyup change', function () {
                    
                    if ( that.search() !== this.value ) {
                        that
                            .search( this.value )
                            .draw();
                    }
                } );
            } );

            /*$('th').on("click", function (event) {
                console.log(event);
                console.log("input box");
                if($(event.target).is("input")) {
                    console.log("do not sort");
                    event.stopImmediatePropagation();
                }
            });*/
          
        },
        error: function(data){
            console.log("no data");
        }
    });

}

function create_user_ticket() {



}

$( document ).ajaxComplete(function( event, request, settings ) {
    console.log("active AJAX calls", $.active);
    if (first_page_load == true && $.active == 1) {
        page_load_time = new Date() - page_load_time;
        console.log("page load time: ", page_load_time.toString().concat(" ms"))
        var load_time = page_load_time.toString().concat(" ms");
        mixpanel.track(
            "Ticket List page loaded",
            {"load_time": load_time,
             "user_email": user_email}
        );
        first_page_load = false;
    } else if (first_page_load == false && $.active == 1) {
        page_load_time = new Date() - page_load_time;
        console.log("page load time: ", page_load_time.toString().concat(" ms"))
        var load_time = page_load_time.toString().concat(" ms");
        mixpanel.track(
            "Ticket List page loaded",
            {"load_time": load_time,
             "user_email": user_email}
        );
        first_page_load = false;
    }
    console.log(first_page_load);
});