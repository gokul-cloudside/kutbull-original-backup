var page_load_time = null
var first_page_load = true;

$(document).ready(function() {
    
    $("#breadcrumb_page_path").empty();
    $("#breadcrumb_page_path").append('<li class="text-center text-bold" ><a href="#">Client</a></li><li class="text-center text-bold"><a href="#">Client Dashboard</a></li><li class="text-center text-bold"><a href="#">Plant Dashboard</a></li><li class="text-center text-bold"><a href="#">Reports</a></li>')

    /*download_options();*/
    devices_dropdown();
});

$('.datepicker_start').datepicker({
    autoclose: true,
    todayHighlight: true,
    startView: "days",
    minViewMode: "days",
    format: "dd-mm-yyyy"
});

function datepicker_start_day() {

    $('.datepicker_start_days').datepicker({
        autoclose: true,
        todayHighlight: true,
        startView: "days",
        minViewMode: "days",
        format: "dd-mm-yyyy"
    });

}

function datepicker_start_month() {

    $('.datepicker_start_months').datepicker({
        autoclose: true,
        todayHighlight: true,
        startView: "months",
        minViewMode: "months",
        format: "mm-yyyy"
    });
    
}

function datepicker_start_year() {

    $('.datepicker_start_years').datepicker({
        autoclose: true,
        todayHighlight: true,
        startView: "years",
        minViewMode: "years",
        format: "yyyy"
    });
    
}

var aggregator_string;

$(".report_period-list>li>a").click(function(){
    $("#dropdown_report_period").html();
    $("#dropdown_report_period").html($(this).text());

    aggregator_string = $(this).text();

    console.log(aggregator_string);

    if(aggregator_string == "Daily") {

        aggregator_string = "daily";
        $("#download_report_date").empty();
        $("#download_report_date").append('<input type="text" class="form-control datepicker_start_days" id="datepicker_selected_picker" placeholder="Pick a Date" style="height: 31px;">');
        $("#device_type_button_div").removeClass("disabled");
        $("#excel_worksheet_button_div").removeClass("disabled");
        datepicker_start_day();

    } else if(aggregator_string == "Monthly") {

        aggregator_string = "monthly";
        $("#download_report_date").empty();
        $("#download_report_date").append('<input type="text" class="form-control datepicker_start_months" id="datepicker_selected_picker" placeholder="Pick a Month" style="height: 31px;">');
        $("#device_type_button_div").addClass("disabled");
        $("#excel_worksheet_button_div").addClass("disabled");
        datepicker_start_month();

    } else if(aggregator_string == "Yearly") {

        aggregator_string = "yearly";
        $("#download_report_date").empty();
        $("#download_report_date").append('<input type="text" class="form-control datepicker_start_years" id="datepicker_selected_picker" placeholder="Pick a Year" style="height: 31px;">');
        $("#device_type_button_div").addClass("disabled");
        $("#excel_worksheet_button_div").addClass("disabled");
        datepicker_start_year();

    }

    console.log(aggregator_string);
});

$("#download_report-download").on('click', function() {

    console.log(aggregator_string);

    if(aggregator_string == undefined) {
        noty_message("Please select a Report Type!", 'error', 5000)
        return;
    }

    var st = $("#datepicker_selected_picker").val();
    console.log(st);
    if(st == "") {
        if(aggregator_string == "daily") {
            noty_message("Please select a Date!", 'error', 5000)
            return;
        } else if(aggregator_string == "monthly") {
            noty_message("Please select a Month!", 'error', 5000)
            return;
        } else if(aggregator_string == "yearly") {
            noty_message("Please select a Year!", 'error', 5000)
            return;
        }
        
    }

    if(aggregator_string == "") {
        noty_message("Please select a aggregator!", 'error', 5000)
        return;
    }

    if(aggregator_string == "daily") {
        download_report_day(aggregator_string, st);
    } else if(aggregator_string == "monthly") {
        download_report_monthly(aggregator_string, st);
    } else if(aggregator_string == "yearly") {
        download_report_yearly(aggregator_string, st);
    }
})

function get_date(st) {

    var et = new Date();

    st = st.split("-");
    st = st[2] + "-" + st[1] + "-" + st[0];
    st = new Date(st);

    if(aggregator_string == "monthly") {
        st = new Date(st.getFullYear(), st.getMonth(), 1);
        et = new Date(st.getFullYear(), st.getMonth() + 1, 0);

    } 

    st = dateFormat(st, "yyyy-mm-dd");
    et = dateFormat(et, "yyyy-mm-dd");

    return [st, et];

}

$(".excel_parameter li a").click(function(){
    $("#dropdown_parameter").html();
    $("#dropdown_parameter").html($(this).text());
});

$("#report_summary-before").on('click', function() {
    if($("#report_summary-li").hasClass("disabled") == false) {
        var st = $(".datepicker_start").val();

        if(st == "") {
            st = new Date();
        } else {
            st = st.split("-");
            st = st[2] + "-" + st[1] + "-" +st[0];
            st = new Date(st);    
        }
        st.setDate(st.getDate() - 1);
        st = dateFormat(st, "dd-mm-yyyy");

        $(".datepicker_start").val(st);
    }
})

$("#report_summary-next").on('click', function() {
    if($("#report_summary-li-next").hasClass("disabled") == false) {
        var st = $(".datepicker_start").val();

        if(st == "") {
            st = new Date();
        } else {
            st = st.split("-");
            st = st[2] + "-" + st[1] + "-" +st[0];
            st = new Date(st);
        }
        st.setDate(st.getDate() + 1);
        st = dateFormat(st, "dd-mm-yyyy");

        $(".datepicker_start").val(st);
    }
})

function devices_dropdown() {

    $.ajax({
        type: "GET",
        url: "/api/v1/solar/plants/".concat(plant_slug).concat("/devices/"),
        success: function(data){
            if(data == "") {
                noty_message("No devices are present!", 'success', 5000)
                return;
            } else {
                var device = Object.keys(data);

                for(var devices = 0; devices < device.length; devices++) {
                    if(device[devices] != "group_names" && device[devices] != "plant_meta_source") {
                        $("#devices_present").append("<li><a>" + (device[devices].toUpperCase()).slice(0, -1) + "</a></li>");
                    } else if(device[devices] == "plant_meta_source") {
                        $("#devices_present").append("<li><a>WEATHER_STATION</a></li>");
                    }
                }

                $(".devices_present li a").click(function(){
                    $("#device_type").html();
                    $("#device_type").html($(this).text());
                });
            }

        },
        error: function(data){
            console.log("no data");

            noty_message("No data to download!", 'error', 5000)
            return;
        }
    });

}

function download_report_day(aggregator_string, st) {

    if(st == "") {
        noty_message("Select a start date!", 'error', 5000)
        return;
    }

    st = st.split("-");
    st = st[2] + "-" + st[1] + "-" + st[0];

    var parameter_selected = selected;
    var device_selected = $("#device_type").text();

    if(parameter_selected == null) {
        noty_message("Select a Excel Worksheet parameter!", 'error', 5000)
        return;
    }

    if(device_selected == 'Device Type') {
        noty_message("Select a Device Type!", 'error', 5000)
        return;
    }

    $(".loader").show();

    if(parameter_selected != 'Excel Worksheets' && device_selected != 'Device Type') {

        var download_report_data = "/api/v1/solar/plants/".concat(plant_slug).concat("/report/?date=").concat(st).concat("&sheet=").concat(parameter_selected).concat("&device_type="+device_selected);
        download_multiple("/api/v1/solar/plants/".concat(plant_slug).concat("/report/?date=").concat(st).concat("&sheet=").concat(parameter_selected).concat("&device_type="+device_selected));

        $.ajax({
            type: "GET",
            url: download_report_data,
            success: function(data){
                $("#report_summary-li").removeClass("disabled");
                $("#report_summary-li-next").removeClass("disabled");

                $(".loader").hide();

                noty_message("Your report will be downloaded!", 'success', 5000)
                return;
            },
            error: function(data){
                console.log("no data");

                $("#report_summary-li").addClass("disabled");
                $("#report_summary-li-next").addClass("disabled");

                $(".loader").hide();

                noty_message("No data to download!", 'error', 5000)
                return;
            }
        });
        
    }
}

function download_multiple(url) {
  document.getElementById('my_iframe_download_report').src = url;
};

function download_report_monthly(aggregator_string, st) {

    if(st == "") {
        noty_message("Select a start date!", 'error', 5000)
        return;
    }

    $(".loader").show();

    var dates = get_date(st);
    st = dates[0];
    var et = dates[1];

    var download_report_data = "/api/v1/solar/plants/".concat(plant_slug).concat("/report/?report_type=").concat(aggregator_string).concat("&startTime=").concat(st).concat("&endTime="+et);
    download_multiple("/api/v1/solar/plants/".concat(plant_slug).concat("/report/?report_type=").concat(aggregator_string).concat("&startTime=").concat(st).concat("&endTime="+et));

    console.log(download_report_data);
    debugger;

    $.ajax({
        type: "GET",
        url: download_report_data,
        success: function(data){
            $("#report_summary-li").removeClass("disabled");
            $("#report_summary-li-next").removeClass("disabled");

            $(".loader").hide();

            noty_message("Your report will be downloaded!", 'success', 5000)
            return;
        },
        error: function(data){
            console.log("no data");

            $("#report_summary-li").addClass("disabled");
            $("#report_summary-li-next").addClass("disabled");

            $(".loader").hide();

            noty_message("No data to download!", 'error', 5000)
            return;
        }
    });
}

function download_report_yearly(aggregator_string, st) {

    if(st == "") {
        noty_message("Select a start date!", 'error', 5000)
        return;
    }

    $(".loader").show();

    var download_report_data = "/api/v1/solar/plants/".concat(plant_slug).concat("/report/?report_type=").concat(aggregator_string).concat("&year=").concat(st);
    download_multiple("/api/v1/solar/plants/".concat(plant_slug).concat("/report/?report_type=").concat(aggregator_string).concat("&year=").concat(st));

    $.ajax({
        type: "GET",
        url: download_report_data,
        success: function(data){
            $("#report_summary-li").removeClass("disabled");
            $("#report_summary-li-next").removeClass("disabled");

            $(".loader").hide();

            noty_message("Your report will be downloaded!", 'success', 5000)
            return;
        },
        error: function(data){
            console.log("no data");

            $("#report_summary-li").addClass("disabled");
            $("#report_summary-li-next").addClass("disabled");

            $(".loader").hide();

            noty_message("No data to download!", 'error', 5000)
            return;
        }
    });
}

$( document ).ajaxComplete(function( event, request, settings ) {
    console.log("active AJAX calls", $.active);
    if (first_page_load == true && $.active == 1) {
        page_load_time = new Date() - page_load_time;
        console.log("page load time: ", page_load_time.toString().concat(" ms"))
        var load_time = page_load_time.toString().concat(" ms");
        mixpanel.track(
            "Report Details page loaded",
            {"load_time": load_time,
             "user_email": user_email}
        );
        first_page_load = false;
    } else if (first_page_load == false && $.active == 1) {
        page_load_time = new Date() - page_load_time;
        console.log("page load time: ", page_load_time.toString().concat(" ms"))
        var load_time = page_load_time.toString().concat(" ms");
        mixpanel.track(
            "Report Details page loaded",
            {"load_time": load_time,
             "user_email": user_email}
        );
        first_page_load = false;
    }
    console.log(first_page_load);
});