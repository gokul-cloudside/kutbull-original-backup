$(document).ready(function() {
    
    $("#breadcrumb_page_path").empty();
    $("#breadcrumb_page_path").append('<li class="text-center text-bold" ><a href="#">Client</a></li><li class="text-center text-bold"><a href="#">Client Dashboard</a></li><li class="text-center text-bold"><a href="#">Plant Dashboard</a></li><li class="text-center text-bold"><a href="#">Alarms List</a></li>')

});

function redraw_window() {
    $('a[data-toggle="tab"]').on('shown.bs.tab', function (e) {
        e.preventDefault();
        window.dispatchEvent(new Event('resize'));
    });
}

$('.datepicker_start').datepicker({
    autoclose: true,
    todayHighlight: true,
    startView: "days",
    minViewMode: "days",
    format: "dd-mm-yyyy"
});

$('.datepicker_end').datepicker({
    autoclose: true,
    todayHighlight: true,
    startView: "days",
    minViewMode: "days",
    format: "dd-mm-yyyy"
});

function get_dates(){
    // get the start date
    var st = $(".datepicker").val();
    var et = $(".datepicker_end_date").val();

    st = st.split("-");
    st = st[2] + "-" + st[1] + "-" + st[0];

    et = et.split("-");
    et = et[2] + "-" + et[1] + "-" + et[0];

    /*var st = new Date();*/
    if (st == '') {
        st = new Date();
    } else {
        st = new Date(st);
    }
    // prepare an end date
    var e = new Date(et);
    // convert them into strings

    st = dateFormat(st, "yyyy-mm-dd");
    e = dateFormat(e, "yyyy-mm-dd");

    return [st, e];
}

$("#devices_type").change(function() {

    var device_type = $("#devices_type").val();
    $("#event_type").empty();

    $("#event_type").prop('disabled', false);

    var inverter_events = ["INVERTERS_DISCONNECTED", "INVERTERS_ALARMS", "PANEL_CLEANING", "INVERTERS_UNDERPERFORMING"];
    var ajb_events = ["AJBS_DISCONNECTED", "AJB_UNDERPERFORMING"];
    var gateway_events = ["GATEWAY_DISCONNECTED_And_POWERED_OFF"];
    var virtual_gateway_events = ["GATEWAY_POWER_OFF"];
    var mppt_events = ["MPPT_UNDERPERFORMING"];

    if(device_type == "INVERTERS") {
        for(var inverter = 0; inverter < inverter_events.length; inverter++) {
            $("#event_type").append("<option value='" + inverter_events[inverter] + "'>" + inverter_events[inverter] + "</option>");
        }
    }

    if(device_type == "AJBS") {
        for(var ajb = 0; ajb < ajb_events.length; ajb++) {
            $("#event_type").append("<option value='" + ajb_events[ajb] + "'>" + ajb_events[ajb] + "</option>");
        }
    }

    if(device_type == "GATEWAYS") {
        for(var gateway = 0; gateway < gateway_events.length; gateway++) {
            $("#event_type").append("<option value='GATEWAY_DISCONNECTED'>" + gateway_events[gateway] + "</option>");
        }
    }

    /*if(device_type == "VIRTUAL_GATEWAYS") {
        for(var virtual_gateway = 0; virtual_gateway < virtual_gateway_events.length; virtual_gateway++) {
            $("#event_type").append("<option value='" + virtual_gateway_events[virtual_gateway] + "'>" + virtual_gateway_events[virtual_gateway] + "</option>");
        }
    }*/

    if(device_type == "MPPTS") {
        for(var mppt = 0; mppt < mppt_events.length; mppt++) {
            $("#event_type").append("<option value='" + mppt_events[mppt] + "'>" + mppt_events[mppt] + "</option>");
        }
    }
});

function alarms_list() {

    $("#client_spinner").show();

    var st = $(".datepicker_start").val();

    if(st == "") {
        $("#client_spinner").hide();

        noty_message("Select a Start Date!", 'error', 5000)
        return;
    } else {
        st = st.split("-");
        st = st[2] + "-" + st[1] + "-" + st[0];
    }

    var et = $(".datepicker_end").val();

    if(et == "") {
        $("#client_spinner").hide();

        noty_message("Select an End Date!", 'error', 5000)
        return;
    } else {
        et = et.split("-");
        et = et[2] + "-" + et[1] + "-" + et[0];
    }

    var device_type = $("#devices_type").val();

    if(device_type == "--Select a Device Type--") {
        $("#client_spinner").hide();

        noty_message("Select a Device!", 'error', 5000)
        return;
    }

    var event_type = $("#event_type").val();

    $.ajax({
        type: "GET",
        url: "/api/v1/solar/plants/".concat(plant_slug).concat('/association_details/'),
        data: {startTime: st, endTime: et, device_type: device_type, event_type: event_type},
        success: function(alarms){

            if(alarms == "") {
                $("#client_spinner").hide();

                noty_message("No data for the selected dates!", 'error', 5000)
                return;
            } else { 

                $('#report_table').html('');
                $('<div class="ibox-content" id="data_table"> ' +
                '</div>').appendTo('#report_table');

                $('#report_table').append("<table class='table table-striped table-bordered table-hover dataScroll dataTables-alarms'> <thead> <tr id='heading_table'> </tr></thread> <tbody id='table_body'> </tbody></table>");

                var headings = Object.keys(alarms[0]);

                for(var heading = 0; heading < headings.length; heading++) {
                    $('#heading_table').append("<th>"+ headings[heading] +"</th>");
                }

                for(var alarm = 0; alarm < alarms.length; alarm++) {
                    $('#table_body').append("<tr id='row"+alarm+"'> </tr>");
                    for(var alarm_heading_value in alarms[alarm]) {
                        $('#row'+alarm).append("<td>" + alarms[alarm][alarm_heading_value] + "</td>");
                    }
                }

                var report_title = $("title");

                report_title.empty();
                report_title.append("Dataglen Alarms For ", plant_name);

                $('.dataTables-alarms').DataTable({
                    /*responsive: true,
                    "sScrollX": "100%",
                    "sScrollXInner": "120%",
                    "bScrollCollapse": true,*/
                    "dom": 'Bfrtip',
                    "tableTools": {
                        "sSwfPath": "/static/dataglen/js/copy_csv_xls_pdf.swf"
                    },
                    buttons: [
                        {
                            extend: 'copyHtml5',
                            exportOptions: {
                                columns: ':contains("Office")'
                            }
                        },
                        'excelHtml5',
                        'csvHtml5',
                        'pdfHtml5',
                        'print'
                    ]
                });

                $("#columns_filtering").empty();

                /*$("#columns_filtering").append('<h3 class="row text-center pad-btm">Column Filters</h3>');*/

                var columns_filtered = [];

                for(var column = 1; column <= headings.length; column++) {
                    if(headings[column-1] != "Start Time" && headings[column-1] != "End Time") {
                        columns_filtered.push({column_number: (column-1), filter_match_mode: 'exact', filter_reset_button_text: "Clear", filter_default_label: 'None Selected'});
                        /*if(headings[column-1] == "Operating Status") {
                            heading_name = "Status";
                        } else {
                            heading_name = headings[column-1];
                        }
                        $("#columns_filtering").append('<div class="col-lg-1 col-md-1 col-sm-1 col-xs-3">' +
                            '<span>' + heading_name + '</span><span><select class="form-control colfiltering" data-colnumber="' + (column - 1) + '">' +
                                '<option value="">No</option>' +
                                '<option value="1">Yes</option>' +
                            '</select></span></div>');*/
                    }
                }

                /*$("#columns_filtering").append('<div class="col-lg-2 col-md-2 col-sm-2 pad-all"><button class="btn btn-default btn-white_color" id="inityadcf">Apply Filters To Table <i class="fa fa-filter" aria-hidden="true"></i></button></div>');*/

                var alarms_table = $('.dataTables-alarms');

                alarms_table.DataTable().destroy();
                yadcf.init(alarms_table.DataTable({
                    /*responsive: true,
                    "sScrollX": "100%",
                    "sScrollXInner": "120%",
                    "bScrollCollapse": true,*/
                    "dom": 'Bfrtip',
                    "tableTools": {
                        "sSwfPath": "/static/dataglen/js/copy_csv_xls_pdf.swf"
                    },
                    buttons: [
                        {
                            extend: 'copyHtml5',
                            exportOptions: {
                                columns: ':contains("Office")'
                            }
                        },
                        {
                            extend: 'excelHtml5',
                            action: function(e, dt, button, config) {
                                 
                                // Add code to make changes to table here
                 
                                // Call the original action function afterwards to
                                // continue the action.
                                // Otherwise you're just overriding it completely.

                                /*noty_message("The page will be reloaded after the pdf is downloaded!", 'information', 4000);
                                return;*/
                                $(".yadcf-filter-wrapper").remove();

                                if ($.fn.dataTable.ext.buttons.excelHtml5.available( dt, config )) {

                                    $.fn.dataTable.ext.buttons.excelHtml5.action.call(this, e, dt, button, config);
                                    location.reload();

                                } else {
                                    
                                    /*noty_message("The page will be reloaded after the pdf is downloaded!", 'information', 4000)
                                    return;*/

                                    $.fn.dataTable.ext.buttons.excelFlash.action.call(this, e, dt, button, config);
                                    location.reload();

                                }

                            }
                        },
                        {
                            extend: 'csvHtml5',
                            action: function(e, dt, button, config) {
                                 
                                // Add code to make changes to table here
                 
                                // Call the original action function afterwards to
                                // continue the action.
                                // Otherwise you're just overriding it completely.

                                /*noty_message("The page will be reloaded after the pdf is downloaded!", 'information', 4000);
                                return;*/
                                $(".yadcf-filter-wrapper").remove();

                                if ($.fn.dataTable.ext.buttons.csvHtml5.available( dt, config )) {

                                    $.fn.dataTable.ext.buttons.csvHtml5.action.call(this, e, dt, button, config);
                                    location.reload();

                                } else {

                                    /*noty_message("The page will be reloaded after the pdf is downloaded!", 'information', 4000)
                                    return;*/

                                    $.fn.dataTable.ext.buttons.csvFlash.action.call(this, e, dt, button, config);
                                    location.reload();

                                }

                            }
                        },
                        {
                            extend: 'pdfHtml5',
                            action: function(e, dt, button, config) {
                                 
                                // Add code to make changes to table here
                 
                                // Call the original action function afterwards to
                                // continue the action.
                                // Otherwise you're just overriding it completely.

                                /*noty_message("The page will be reloaded after the pdf is downloaded!", 'information', 4000);
                                return;*/
                                $(".yadcf-filter-wrapper").remove();

                                if ($.fn.dataTable.ext.buttons.pdfHtml5.available( dt, config )) {

                                    $.fn.dataTable.ext.buttons.pdfHtml5.action.call(this, e, dt, button, config);
                                    location.reload();

                                } else {

                                    /*noty_message("The page will be reloaded after the pdf is downloaded!", 'information', 4000)
                                    return;*/

                                    $.fn.dataTable.ext.buttons.pdfFlash.action.call(this, e, dt, button, config);
                                    location.reload();

                                }

                            }
                        }
                    ]
                }), columns_filtered);

                $(".yadcf-filter").addClass("form-control");
                $(".yadcf-filter").addClass("datatable_dynamic_filter");

                $("#inityadcf").click(function() {
                    /*var colfiltering = [];
                    $(".colfiltering").each(function() {
                        var $that = $(this);
                        if ($that.val()) {
                            console.log($that.val());
                            colfiltering.push({
                                column_number: $that.data("colnumber")
                            });
                        }
                    });*/

                    
                });

                $("#client_spinner").hide();
            }
          
        },
        error: function(data){
            console.log("no data");

            $("#client_spinner").hide();

            noty_message("No data for the selected dates!", 'error', 5000)
            return;
        }
    });

}