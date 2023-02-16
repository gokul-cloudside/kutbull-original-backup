$(document).ready(function() {
    
    $("#breadcrumb_page_path").empty();
    $("#breadcrumb_page_path").append('<li class="text-center text-bold" ><a href="#">Client</a></li><li class="text-center text-bold"><a href="#">Client Dashboard</a></li><li class="text-center text-bold"><a href="#">Plant Dashboard</a></li><li class="text-center text-bold"><a href="#">Report Summary</a></li>')
    
});

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

/*$(function() {
    $(".datetimepicker_start_compare_inverter_table_day").datetimepicker({
        timepicker: false,
        format: 'Y/m/d',
        scrollMonth:false,
        scrollTime:false,
        scrollInput:false
    });
    $(".datetimepicker_start_compare_inverter_table_day").on('change', function(ev) {
        $(this).datetimepicker('hide');
    });
});

$(function() {
    $(".datetimepicker_end_compare_inverter_table_day").datetimepicker({
        timepicker: false,
        format: 'Y/m/d',
        scrollMonth:false,
        scrollTime:false,
        scrollInput:false
    });
    $(".datetimepicker_end_compare_inverter_table_day").on('change', function(ev) {
        $(this).datetimepicker('hide');
    });
});

function limit_compare_inverters_start_date() {
    $(function(){
        $('#start_compare_parameters_day').datetimepicker({
            onShow:function( ct ){
                this.setOptions({
                    maxDate: new Date()
                })
            },
        });
    });
}

function limit_compare_inverters_end_date() {

    var max_date = new Date();
    var e = new Date(max_date.getTime());
    e = new Date(e.setDate(max_date.getDate() + 1));

    $(function(){
        $('#end_compare_parameters_day').datetimepicker({
            onShow:function( ct ){
                this.setOptions({
                    minDate: new Date($('#start_compare_parameters_day').val()),
                    maxDate: e
                })
            },
        });
    });
}*/

function report() {

    $("#client_spinner").show();

    var st = $(".datepicker_start").val();
    var et = $(".datepicker_end").val();

    if(st == "") {
        $("#client_spinner").hide();

        noty_message("Select a start date!", 'error', 5000)
        return;
    } else {
        st = st.split("-");
        st = st[2] + "-" + st[1] + "-" + st[0];
    }

    if(et == "") {
        $("#client_spinner").hide();
        
        noty_message("Select an end date!", 'error', 5000)
        return;
    } else {
        et = et.split("-");
        et = et[2] + "-" + et[1] + "-" + et[0];
    }

    /*st = dateFormat(st, "yyyy-mm-dd");
    et = dateFormat(et, "yyyy-mm-dd");*/

    var inverter_data = "/api/solar/plants/".concat(plant_slug).concat("/energy/?startTime=").concat(st).concat("&endTime=").concat(et).concat("&aggregator=DAY&split=1");

    $.ajax({
        type: "GET",
        url: inverter_data,
        success: function(data){
            if(data.csvdata == "") {

                $("#client_spinner").hide();

                noty_message("No data for the selected dates!", 'error', 5000)
                return;
            } else { 
                $("#report_empty").empty();

                var parsed_data = Papa.parse(data.csvdata);

                console.log(parsed_data);

                $('#report_table').html('');
                $('<div class="ibox-content" id="data_table"> ' +
                '</div>').appendTo('#report_table');

                $('#report_table').append("<table class='table table-striped table-bordered table-hover dataScroll dataTables-example'> <thead> <tr id='heading_table'> </tr></thread> <tbody id='table_body'> </tbody></table>");

                $('#heading_table').append("<th></th>");
                for(var heading = 1; heading < parsed_data.data.length-1; heading++) {
                    $('#heading_table').append("<th>"+ parsed_data.data[heading][0] +"</th>");
                }

                for(var invidual_array = 1; invidual_array < parsed_data.data[0].length; invidual_array++) {
                    $('#table_body').append("<tr id='row"+invidual_array+"'> </tr>");
                    for(var invidual_data = 0; invidual_data < parsed_data.data.length-1; invidual_data++) {
                        var table_div = "";
                        if(invidual_data == 0) {
                            table_div = "<b>" + parsed_data.data[invidual_data][invidual_array] + "</b>";
                        } else {
                            table_div = parsed_data.data[invidual_data][invidual_array];
                        }
                        $('#row'+invidual_array).append("<td>" + table_div + "</td>");
                    }
                }

                var report_title = $("title");

                report_title.empty();
                report_title.append("Dataglen Report For ", plant_name);

                $('.dataTables-example').DataTable({
                    responsive: true,
                    "sScrollX": "100%",
                    "sScrollXInner": "120%",
                    "bScrollCollapse": true,
                    "dom": 'Bfrtip',
                    "columnDefs": [
                        { type: 'natural', targets: 0 }
                    ],
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
                        'pdfHtml5'
                    ]
                });
            }

            $("#client_spinner").hide();

        },
        error: function(data){
            console.log("no data");

            $("#client_spinner").hide();

            noty_message("No data for the selected date!", 'error', 5000)
            return;
        }
    });

}