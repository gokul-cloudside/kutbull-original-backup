var show_cuf = true;
var table_config = null;
var page_load_time = null;
var first_load = true;
function set_config(config_data) {
    console.log(config_data.dd_keyname);
    if (typeof config_data.dd_keyname != 'undefined') {
        console.log("updating");
        $("#dd_keyname").text(config_data.dd_keyname);
        $("#devices_down_details").hide();
    }

    if (typeof config_data.show_cuf != 'undefined' && config_data.show_cuf == "False") {
        show_cuf = false;
    }

    if (typeof config_data.table_order != 'undefined') {
        table_config = config_data.table_order;
    }


};

var debug = true;
var map = null;
var access_level = 0;

function col_update_col (id, from, to) {
    $(id).removeClass(from);
    $(id).addClass(to);
}
function delete_div(id) {
    $(id).empty();
}

function hide_div(id) {
    $(id).hide();
}

function show_div(id) {
    $(id).show();
}


function access_control(data) {
    if (typeof data.prediction_deviation == 'undefined' &&
        typeof data.total_disconnected_inverters == 'undefined' &&
        typeof data.total_disconnected_smbs == 'undefined') {

        // switch off both alerts and analytics
        //hide_div("#alerts_and_analytics");
        show_div("#generation_and_infra");
        col_update_col("#generation_and_infra", "col-lg-6", "col-lg-12")
        col_update_col("#generation_and_infra", "col-md-6", "col-md-12")
        col_update_col("#weekly_generation", "col-lg-12", "col-lg-6")
        col_update_col("#weekly_generation", "col-md-12", "col-md-6")
        col_update_col("#infra_availibility", "col-lg-12", "col-lg-6")
        col_update_col("#infra_availibility", "col-md-12", "col-md-6")
        // extend the table height
        $("#plants_table").css("height", "68vh");
        $("#generation_prediction_div").hide();
        access_level = 1;


    } else if (typeof data.prediction_deviation == 'undefined') {
        show_div("#generation_and_infra");
        $("#generation_prediction_div").children().hide();
        $("#gateways_down_div").children().hide();
        $("#predictive_issues_div").children().hide();
        $("#devices_down_div").removeClass("col-lg-6");
        $("#devices_down_div").removeClass("col-md-6");
        $("#alarms_raised_div").removeClass("col-lg-6");
        $("#alarms_raised_div").removeClass("col-md-6");
        show_div("#alerts_and_analytics");
        show_div("#devices_down_div");
        show_div("#alarms_raised_div");
        $("#generation_prediction_div").hide();
        access_level = 2;

    } else {
        show_div("#generation_and_infra");
        show_div("#alerts_and_analytics");
        show_div("#devices_down_div");
        show_div("#alarms_raised_div");
        $("#predictive_issues_div").show();
        $("#generation_prediction_div").show();
        $("#gateways_down_div").show();
        show_div("#prediction_text");
        access_level = 0;

    }

    console.log(access_level);
};

$(document).ready(function() {
    console.log(window.matchMedia("(min-height: 800px)").matches);
    page_load_time = new Date();
    mixpanel.identify(user_email);

    if (config_data != null) {
        set_config(config_data);
    }

    $(function () {
      $('[data-toggle="tooltip"]').tooltip()
    });

    var client_data = null;
    var bounds_leaflet_map = null;

    $("#leaflet_map").empty();

    var mapboxTiles = L.tileLayer('http://{s}.tiles.wmflabs.org/bw-mapnik/{z}/{x}/{y}.png', {
    });

    // Create the map
    map = L.map('leaflet_map', {
        center: [28.7042,77.1025],
        scrollWheelZoom: false,
        zoomControl: false,
        zoom: 13,
        attributionControl: false
    }).addLayer(mapboxTiles);

    L.control.zoom({
        position: 'bottomleft'
    }).addTo(map);

    var r1 = new Date();
    $("#client_spinner").show();
    console.log("after show: ", new Date() - r1);

    var r2 = new Date();
    dashboard_clients(true);
    console.log("after dashboard_clients: ", new Date() - r2);

    redraw_window();

    var r3 = new Date();
    $("#client_spinner").hide();
    console.log("after hide: ", new Date() - r3);

    setInterval(function () {
        client_data = null;
        bounds_leaflet_map = null;
        map = null;
        dashboard_clients(false);
        redraw_window();
        var flag = 0;
    }, 5000*60);

});

$('.datepicker').datepicker({
    autoclose: true,
    todayHighlight: true,
    startView: "days",
    minViewMode: "days",
    format: "dd-mm-yyyy"
});

function get_dates(){
    // get the start date
    var st = $(".datepicker").val();

    st = st.split("-");
    st = st[2] + "-" + st[1] + "-" + st[0];

    /*var st = new Date();*/
    if (st == '') {
        st = new Date();
    } else {
        st = new Date(st);
    }
    // prepare an end date
    var e = new Date(st.getTime());
    e = new Date(e.setDate(st.getDate() + 1));
    // convert them into strings

    st = dateFormat(st, "yyyy-mm-dd");
    e = dateFormat(e, "yyyy-mm-dd");

    return [st, e];
}

function redraw_window() {
    $('a[data-toggle="tab"]').on('shown.bs.tab', function (e) {
        e.preventDefault();
        window.dispatchEvent(new Event('resize'));
    });
}

function set_variable_value(variable, value) {

    if (typeof value == 'undefined' || value == null || (typeof value == 'string' && value.includes("NaN"))) {
        value = "NA";
    }

    if ((typeof value == 'string' && value.includes("kWh") && (value.includes("m^2") || value.includes("m2")))) {
        value = value.replace("m^2", "m<sup>2</sup>");
        value = value.replace("m2", "m<sup>2</sup>");
    }

    if (typeof value == 'string' && value.includes('MWh')) {
        value = value.replace("MWh", "<span style='font-size: small'>MWh</span>")

    } else if (typeof value == 'string' && value.includes('kWh')) {
        value = value.replace("kWh", "<span style='font-size: small'>kWh</span>")

    } else if (typeof value == 'string' && value.includes('kW')) {
        value = value.replace("kW", "<span style='font-size: small'>kW</span>")

    } else if (typeof value == 'string' && value.includes('%')) {
        value = value.replace("kW", "<span style='font-size: small'>%</span>")
    }

    try {
        variable.empty();
        variable.append(value);
    } catch (err) {
        console.log("error setting a variable value");
    }
}

function small_text(text){
    return '';
}

function dashboard_clients(first_call) {

    var t = new Date();
    $.ajax({
        type: "GET",
        async: false,
        url : "/api/v1/solar/client/summary/",
        success: function(api_client_info){
            if (first_call == true) {
                access_control(api_client_info);
            }

            console.log("api time",new Date() - t);
            client_info = api_client_info;

            var t0 = new Date();
            // leaflet map
            var leaflet_status = 1;

            if (debug == true) {
                console.log("plants map", new Date() - t0);
            }

            // top left blue blocks parameters
            var t1 = new Date();
            set_variable_value($("#last_updated_time"), "Updated: ".concat((moment(client_info.updated_at).format("HH:mm:ss") || "Not Available")));
            set_variable_value($("#current_power"), (client_info.total_active_power || "0.0") + " kW");
            var generation_today = (client_info.energy_today || "NA kWh").split(" ");
            if (generation_today.length == 2) {
                set_variable_value($("#today_energy"), generation_today[0]);
                set_variable_value($("#today_energy_unit"), '<span> '+ generation_today[1] +'</span>');

                var houses_powered = parseInt((generation_today[0])/3);

                set_variable_value($("#predictive_issues_details"), (houses_powered + " Houses Powered"));
            } else {
                set_variable_value($("#today_energy"), 0);
                set_variable_value($("#today_energy_unit"), '<span> '+ ' kWh' +'</span>');
                set_variable_value($("#predictive_issues_details"), ("0 Houses Powered"));
            }

            if (parseFloat(client_info.total_pr) == 0) {
                set_variable_value($("#average_pr"), parseInt(((client_info.total_co2) || "0 Kg").split(" ")[0]) + "<span style='font-size: small'> " + ((client_info.total_co2) || "0 Kg").split(" ")[1] + "</span>");
                set_variable_value($("#first_green_block"), 'CO<sub>2</sub> Emissions Saved');

            } else {
                set_variable_value($("#average_pr"), (parseFloat(client_info.total_pr * 100) || 0.0).toFixed(1) + '<span style="font-size: small"> % </span>');
                set_variable_value($("#first_green_block"), 'Average PR');
            }

            set_variable_value($("#total_specific_yield"), (parseFloat(client_info.total_specific_yield || 0.0).toFixed(1) + '<span class="pad-no mar-no hidden-xs" style="font-size: small"> kWh/kWp</span>'));
            set_variable_value($("#open_tickets"), (parseInt(client_info.total_open_tickets) || 0) + (parseInt(client_info.total_unacknowledged_tickets) || 0) );
            if (debug == true) {
                console.log("top right blue blocks: ", new Date() - t1);
            }

            // client's logo
            var t2 = new Date();
            var client_image = $("#client_image");
            client_image.empty();
            if (client_name == 'Comfonomics') {
                client_image.append("<img style='width: 17vw !important;' class='mar-btm client-logo-image' src='" + client_info.client_logo + "' alt='DATAGLEN'>");
            } else {
                client_image.append("<img style='' class='mar-btm client-logo-image' src='" + client_info.client_logo + "' alt='DATAGLEN'>");
            }
            if (debug == true) {
                console.log("client's logo: ", new Date() - t2);
            }

            // green blocks - left side (total assets)
            var t3 = new Date();
            var plants_length = ((((client_info || {}).plants || {}).length || 0));
            var total_plants = 0;
            var live_plants = 0;
            for(var each_plant = 0; each_plant < plants_length; each_plant++) {
                if(client_info.plants[each_plant].status == "connected") {
                    live_plants++;
                }
            }
            total_plants = plants_length;
            set_variable_value($("#plants_div"), '<div class="row"><span class="text-2x text-thin text-semibold text-live" id="total_plants"></span></div><div class="row"><span class="text-xs" id="total_plants_text" style="font-size: small">Sites</span></div><div class="row"><p class="text-thin text-blue text-xs text-live">Monitored</p></div>' );
            set_variable_value($("#total_plants"), total_plants || 0);
            if (show_cuf == true) {
                set_variable_value($("#average_cuf"), (parseInt(client_info.total_cuf * 100) || "0") + '<span style="font-size: small"> % </span>');
                set_variable_value($("#second_green_block"), 'Average CUF');
            } else {
                set_variable_value($("#average_cuf"), live_plants);
                set_variable_value($("#second_green_block"), 'Connected Sites');
            }
            var total_energy_generation = (client_info.total_energy || "0 kWh").split(" ");
            if (total_energy_generation.length == 2) {
                set_variable_value($("#total_energy_generation"), total_energy_generation[0]);
                set_variable_value($("#total_energy_generation_unit_div"), '<span style="font-size: small"> '+ total_energy_generation[1] +'</span>');
            } else {
                set_variable_value($("#total_energy_generation"), 0);
                set_variable_value($("#total_energy_generation_unit_div"), '<span style="font-size: small"> '+ ' kWh' +'</span>');
            }
            var net_assets = (client_info.total_capacity || "0 kWp").split(" ");
            if (net_assets.length == 2) {
                set_variable_value($("#net_assets_value"), net_assets[0]);
                set_variable_value($("#net_assets_value_unit"), '<span style="font-size: small"> '+ net_assets[1] +'</span>');
            } else {
                set_variable_value($("#net_assets_value"), 0);
                set_variable_value($("#net_assets_value_unit"), '<span style="font-size: small"> '+ ' kWp' +'</span>');
            }

            set_variable_value($("#prediction_deviation"), (((client_info || {"prediction_deviation": "NA "}).prediction_deviation || "NA ")).split(" ")[0] + '<span style="font-size:small">%</span>' || "NA");
            var value_predicted_today = (client_info.total_today_predicted_energy_value || "NA kWh").split(" ");
            if (value_predicted_today.length == 2) {
                set_variable_value($("#value_predicted_today"), parseInt(value_predicted_today[0]) + '<span style="font-size: small" id="value_predicted_today_unit"> '+ value_predicted_today[1] +'</span>');
            } else {
                set_variable_value($("#value_predicted_today"), "NA" + '<span style="font-size: small" id="value_predicted_today_unit"> '+ ' kWh' +'</span>');
            }
            set_variable_value($("#prediction_accuracy"), 100.0 - parseFloat(client_info.prediction_deviation || 0).toFixed(1) + " % Accuracy");

            set_variable_value($("#strings_performing_low"), (parseInt(client_info.string_errors_smbs) || "NA"));
            if (debug == true) {
                console.log("green blocks and prediction value", new Date() - t3);
            }

            // charts
            var t4 = new Date();
            var total_generation_timestamps = [], total_generation_energy = [];
            var grid_unavailability_timestamps = [], grid_unavailability_values = [];
            var equipment_unavailability_timestamps = [], equipment_unavailability_values = [];
            var past_generations_length = ((((client_info || {}).client_past_generations || {}).length || 0));
            var morris_data = [];

            for(var i = 0; i < past_generations_length; i++) {
                    if (i == 0 ) {
                        var generation_unit = client_info.client_past_generations[i].energy.split(" ")[1];
                    }

                    //collect energy timestamps and values
                    var total_generation_date = new Date(client_info.client_past_generations[i].timestamp);
                    total_generation_date = dateFormat(total_generation_date, "mmm dd");
                    var total_generation_value = parseFloat(client_info.client_past_generations[i].energy);
                    total_generation_timestamps.push(total_generation_date);
                    total_generation_energy.push(total_generation_value);
                    morris_data.push({x: total_generation_date.toString(),
                                      y: total_generation_value});

//                    if(client_info.client_past_grid_unavailability) {
//                        var date_grid_unavailability = new Date(client_info.client_past_grid_unavailability[i].timestamp);
//                        date_grid_unavailability = dateFormat(date_grid_unavailability, "mmm dd");
//                        grid_unavailability_timestamps.push(date_grid_unavailability);
//                        var grid_unavailability_value = parseFloat(client_info.client_past_grid_unavailability[i].unavailability);
//                        grid_unavailability_values.push(100 - grid_unavailability_value);
//                    }
//
//                    if(client_info.client_past_equipment_unavailability) {
//                        var date_equipment_unavailability = new Date(client_info.client_past_equipment_unavailability[i].timestamp);
//                        date_equipment_unavailability = dateFormat(date_equipment_unavailability, "mmm dd");
//                        equipment_unavailability_timestamps.push(date_equipment_unavailability);
//                        var equipment_unavailability_value = parseFloat(client_info.client_past_equipment_unavailability[i].unavailability);
//                        equipment_unavailability_values.push(100 - equipment_unavailability_value);
//                    }
                }

            $("#generation_and_losses").empty();
            //plot the chart now
            var tm = new Date();
            if(past_generations_length > 0) {
                // Use Morris.Bar
                Morris.Bar({
                  element: 'generation_and_losses',
                  data: morris_data,
                  xkey: 'x',
                  ykeys: ['y'],
                  labels: ['Plant Generation'],
                  stacked: true,
                  hideHover: 'auto',
                  postUnits: ' '.concat(generation_unit)
                });

            } else {
                var gal_id = $("#generation_and_losses");
                gal_id.empty();
                gal_id.append("<div class='panel-body'><div class='alert alert-warning' id='alert'>No data for Weekly Energy Generation.</div></div>");
            }
            console.log("Just morris", new Date() - tm);
            if (debug == true) {
                console.log("Morris charts for weekly generation : ", new Date() - t4);
            }

            var t5 = new Date();
            //easy pie charts for grid and equipment availability
            if(typeof client_info.grid_unavailability !== 'undefined') {
                var grid_availability_value = parseFloat(client_info.grid_unavailability);
                grid_availability_value = 100 - grid_availability_value;

                $("#grid_availability_chart").attr('data-percent', grid_availability_value.toString());
            } else {
                $("#grid_availability_chart").attr('data-percent', "0");
            }

            if(typeof client_info.equipment_unavailability !== 'undefined') {
                var equipment_availability_value = parseFloat(client_info.equipment_unavailability);
                equipment_availability_value = 100 - equipment_availability_value;

                $("#equipment_availability_chart").attr('data-percent', equipment_availability_value.toString());
            } else {
                $("#equipment_availability_chart").attr('data-percent', "0");
            }

            var easy_pie_chart_size = "";

            var monitor_height = window.screen.availHeight;
            var monitor_width = window.screen.availWidth;

            console.log("Monitor Height" + monitor_height);
            console.log("Monitor Width" + monitor_width);

            /*if(monitor_width <= 1280 && monitor_width > 1024) {
                easy_pie_chart_size = 80;
            } else */if(monitor_width <= 1370) {
                easy_pie_chart_size = 110;
            } else if(monitor_width <= 1440 && monitor_width > 1370) {
                easy_pie_chart_size = 128;
            } else if(monitor_width <= 1600 && monitor_width > 1440) {
                easy_pie_chart_size = 150;
            } else if(monitor_width <= 1680 && monitor_width > 1600) {
                easy_pie_chart_size = 160;
            } else if(monitor_width <= 1930 && monitor_width > 1680) {
                easy_pie_chart_size = 180;
            } else if(monitor_width <= 2048 && monitor_width > 1930) {
                easy_pie_chart_size = 190;
            }

            console.log(easy_pie_chart_size);

            $('.chart').easyPieChart({
                easing: 'easeOutElastic',
                delay: 3000,
                barColor: '#69c',
                trackColor: '#ace',
                scaleColor: false,
                lineWidth: 30,
                trackWidth: 18,
                lineCap: 'butt',
                size: easy_pie_chart_size,
                onStep: function(from, to, percent) {
                    $(this.el).find('.percent').text(percent);
                }
            });

            if (debug == true) {
                console.log("Easy pie charts for weekly generation : ", new Date() - t5);
            }

            console.log("Easy Pie Chart", easy_pie_chart_size);

            // alerts and alarms boxes
            var t6 = new Date();
            set_variable_value($("#devices_down"), (client_info.total_disconnected_inverters || 0) + (client_info.total_disconnected_smbs || 0));

            if(client_name == "EDP") {
                set_variable_value($("#devices_down_details"), (client_info.total_disconnected_inverters || 0) + " Panels, " + (client_info.total_disconnected_smbs || 0) + " SMBs");    
            } else {
                set_variable_value($("#devices_down_details"), (client_info.total_disconnected_inverters || 0) + " Inverters, " + (client_info.total_disconnected_smbs || 0) + " SMBs");
            }

            set_variable_value($("#alarms_raised"), (client_info.total_inverter_error_numbers || 0) + (client_info.total_inverter_cleaning_numbers || 0));
            if(client_name == "EDP") {
                set_variable_value($("#alarms_raised_details"), (client_info.total_inverter_error_numbers || 0) + " Panels, " + (client_info.total_inverter_cleaning_numbers || 0) + " Cleaning");
            } else {
                set_variable_value($("#alarms_raised_details"), (client_info.total_inverter_error_numbers || 0) + " Inverters, " + (client_info.total_inverter_cleaning_numbers || 0) + " Cleaning");
            }

            if(client_name == "Renew Power") {
                var total_co2 = client_info.total_co2;
                total_co2 = (total_co2 || "0 Ton").split(" ");

                if(total_co2.length == 2) {
                    set_variable_value($("#predictive_issues"), (total_co2[0] + '<span style="font-size: small"> '+ total_co2[1] +'</span>'));
                } else {
                    set_variable_value($("#predictive_issues"), ("0" + '<span style="font-size: small"> '+ total_co2[1] +'</span>'));
                }    
            } else {
                set_variable_value($("#predictive_issues"), ((((client_info || {"total_low_anomaly_smb_numbers": 0}).total_low_anomaly_smb_numbers || 0)) || 0) + ((((client_info || {"total_high_anomaly_smb_numbers": 0}).total_high_anomaly_smb_numbers || 0)) || 0));
                set_variable_value($("#predictive_issues_details"), (((client_info || {"total_low_anomaly_smb_numbers": 0}).total_low_anomaly_smb_numbers || 0) + ((client_info || {"total_high_anomaly_smb_numbers": 0}).total_high_anomaly_smb_numbers || 0)) + " SMBs");
            }

            set_variable_value($("#gateways_disconnected"), (client_info.gateways_disconnected || 0) + (client_info.gateways_powered_off || 0));
            set_variable_value($("#gateways_powered_off"), (client_info.gateways_disconnected || 0) + " Disconnected, " + (client_info.gateways_powered_off || 0) + " Off ");

            // set the table
            foo_tables(client_info.plants || []);
            if (debug == true) {
                console.log("Table and alerts : ", new Date() - t5);
            }

            if(client_info.plants[0].status) {
                all_plants(client_info, leaflet_status);
            }
        },
        error: function(xhr, status, error){
            var err = eval("(" + xhr.responseText + ")");
            console.log(err.Message);
            console.log("error");
        }
    });

}

var modal_info = $("#modal_info");

$("#info_button_alarms_raised").click(function() {
    $("#info_modal").modal({
        showClose: false
    });
    modal_info.empty();
    modal_info.append("<div class='row text-center'><span class='text-2x text-bold'>Alarm Tickets</span></div><br/>");

    modal_info.append('<div class="panel-body"><table class="table table-vcenter"><thead><tr><th class="text-center min-width">Plant Name</th><th class="text-center">Devices Impacted</th><th class="text-center">Ticket Link</th></tr></thead><tbody id="table_data"></tbody></table></div>');

    var table_data = $("#table_data");
    table_data.empty();

    for(var i = 0; i < client_info.client_current_inverter_error_details.length; i++) {
        if(client_info.client_current_inverter_error_details[i].plant_name) {
            table_data.append("<tr id='modal_row"+i+"'><td class='text-center'><span class='text-semibold'>" + client_info.client_current_inverter_error_details[i].plant_name + "</span></td><td class='text-center'><span class='text-semibold'>" + client_info.client_current_inverter_error_details[i].affected_inverters_number + "</span></td><td class='text-center'><span class='text-semibold'><a href='" + client_info.client_current_inverter_error_details[i].ticket_url + "'>Check Here</a></span></td></tr>");
        }
    }

    modal_info.append("<div class='row text-center'><span class='text-2x text-bold'>Inverter Cleaning Tickets</span></div><br/>");

    modal_info.append('<div class="panel-body"><table class="table table-vcenter"><thead><tr><th class="text-center min-width">Plant Name</th><th class="text-center">Devices Impacted</th><th class="text-center">Ticket Link</th></tr></thead><tbody id="table_data_cleaning"></tbody></table></div>');

    var table_data_cleaning = $("#table_data_cleaning");
    table_data_cleaning.empty();

    for (i=0; i < client_info.client_inverter_cleaning_details.length; i++) {
        if (typeof client_info.client_inverter_cleaning_details[i].inverters_required_cleaning_numbers !== 'undefined') {
            var td = "<tr id='modal_row"+(i+client_info.client_current_inverter_error_details.length)+"'><td class='text-center'><span class='text-semibold'>" + client_info.client_inverter_cleaning_details[i].plant_name + "</span></td><td class='text-center'><span class='text-semibold'>" + client_info.client_inverter_cleaning_details[i].inverters_required_cleaning_numbers + "</span></td><td class='text-center'><span class='text-semibold'><a href='" + client_info.client_inverter_cleaning_details[i].ticket_url + "'>Check Here</a></span></td></tr>";
            table_data_cleaning.append(td);
        }
    }

});

$("#info_button_inverters_need_cleaning").click(function() {
    $("#info_modal").modal({
        showClose: false
    });

    modal_info.empty();
    modal_info.append("<div class='row text-center'><span class='text-2x text-bold'>Inverters Require Cleaning</span></div><br/>");

    modal_info.append('<div class="panel-body"><table class="table table-hover table-vcenter"><thead><tr><th class="text-center min-width">Plant Name</th><th class="text-center">Devices Impacted</th></tr></thead><tbody id="table_data"></tbody></table></div>');

    var table_data = $("#table_data");
    table_data.empty();

    for(var i = 0; i < client_info.client_inverter_cleaning_details.length; i++) {
        if(client_info.client_inverter_cleaning_details[i].plant_name) {
            table_data.append("<tr id='modal_row"+i+"'><td class='text-center'><span class='text-semibold'>" + client_info.client_inverter_cleaning_details[i].plant_name + "</span></td><td class='text-center'><span class='text-semibold'>" + client_info.client_inverter_cleaning_details[i].inverters_required_cleaning_numbers + "</span></td></tr>");
        }
    }

});

$("#info_button_smb_high_current_strings").click(function() {
    $("#info_modal").modal({
        showClose: false
    });

    modal_info.empty();
    modal_info.append("<div class='row text-center'><span class='text-2x text-bold'>SMBs With High Current Anomaly</span></div><br/>");

    modal_info.append('<div class="panel-body"><table class="table table-hover table-vcenter"><thead><tr><th class="text-center min-width">Plant Name</th><th class="text-center">Devices Impacted</th></tr></thead><tbody id="table_data"></tbody></table></div>');

    var table_data = $("#table_data");
    table_data.empty();

    for(var i = 0; i < client_info.client_string_anomaly_details.length; i++) {
        if(client_info.client_string_anomaly_details[i].plant_name) {
            table_data.append("<tr id='modal_row"+i+"'><td class='text-center'><span class='text-semibold'>" + client_info.client_string_anomaly_details[i].plant_name + "</span></td><td class='text-center'><span class='text-semibold'>" + client_info.client_string_anomaly_details[i].high_anomaly_affected_ajbs_number + "</span></td></tr>");
        }
    }

});

$("#info_button_gateways_powered_off").click(function() {
    $("#info_modal").modal({
        showClose: false
    });

    modal_info.empty();
    modal_info.append("<div class='row text-center'><span class='text-2x text-bold'>Gateways Disconnected</span></div><br/>");
    modal_info.append('<div class="panel-body"><table class="table table-hover table-vcenter"><thead><tr><th class="text-center min-width">Gateways Disconnected</th></tr></thead><tbody id="table_data_disconnected"></tbody></table></div>');

    var table_data_disconnected = $("#table_data_disconnected");
    table_data_disconnected.empty();

    for(var i = 0; i < client_info.gateways_disconnected_list.length; i++) {
        if(client_info.gateways_disconnected_list[i]) {
            table_data_disconnected.append("<tr id='modal_row"+i+"'><td class='text-center'><span class='text-semibold'>" + client_info.gateways_disconnected_list[i] + "</span></td></tr>");
        }
    }

    modal_info.append("<div class='row text-center'><span class='text-2x text-bold'>Gateways Powered Off</span></div><br/>");
    modal_info.append('<div class="panel-body"><table class="table table-hover table-vcenter"><thead><tr><th class="text-center min-width">Gateways Powered Off</th></tr></thead><tbody id="table_data_powered_off"></tbody></table></div>');

    var table_data = $("#table_data_powered_off");
    table_data.empty();

    for(var i = 0; i < client_info.gateways_powered_off_list.length; i++) {
        if(client_info.gateways_powered_off_list[i]) {
            table_data.append("<tr id='modal_row"+i+"'><td class='text-center'><span class='text-semibold'>" + client_info.gateways_powered_off_list[i] + "</span></td></tr>");
        }
    }

});

$("#info_button_smb_low_current_strings").click(function() {
    $("#info_modal").modal({
        showClose: false
    });

    modal_info.empty();
    modal_info.append("<div class='row text-center'><span class='text-2x text-bold'>SMBs With Low Current Anomaly</span></div><br/>");

    modal_info.append('<div class="panel-body"><table class="table table-hover table-vcenter"><thead><tr><th class="text-center min-width">Plant Name</th><th class="text-center">Devices Impacted</th></tr></thead><tbody id="table_data"></tbody></table></div>');

    var table_data = $("#table_data");
    table_data.empty();

    for(var i = 0; i < client_info.client_string_anomaly_details.length; i++) {
        if(client_info.client_string_anomaly_details[i].plant_name) {
            table_data.append("<tr id='modal_row"+i+"'><td class='text-center'><span class='text-semibold'>" + client_info.client_string_anomaly_details[i].plant_name + "</span></td><td class='text-center'><span class='text-semibold'>" + client_info.client_string_anomaly_details[i].low_anomaly_affected_ajbs_number + "</span></td></tr>");
        }
    }

});

function sparkline_bar_chart(id, data_array, date_values, units, parameter) {

    var label;

    if(parameter == "PR") {
        label = "Performance Ratio in %";
    } else {
        label = "Monthly Generation";
    }

    $("#"+id).empty();

    var barEl = $("#"+id);
    var barValues = data_array;
    var barValueCount = data_array.length;
    var barSpacing = 1;

    barEl.sparkline(barValues, {
        type: 'bar',
        width: '100%',
        height: 20,
        barWidth: Math.round((barEl.parent().width() - ( barValueCount - 1 ) * barSpacing ) / barValueCount),
        barSpacing: barSpacing,
        zeroAxis: true,
        chartRangeMin: 0,
        tooltipChartTitle: 'Performance Ratio',
        tooltipSuffix: '',
        barColor: '#0aa699',
        tooltipFormatter: function(sparkline, options, field) {
            var unit = 0;
            if(units[field[0].offset] != undefined) {
                unit = units[field[0].offset];
            } else {
                unit = " ";
            }
            return label + ' for ' + date_values[field[0].offset] + " : " + field[0].value.toFixed(2) + " " + unit;
        }
    });

}

function foo_tables(plants) {

    // access_level - 0 (all)
    // access_level - 1 (no alerts/alarms/devices down or analytics) [default]
    // access_level - 2 (no analytics/predicted/deviation)
    // plant_status (green/red/blue) ["view plant"], ["plant name"], "devices down", "alarms", "energy_sparkline", "pr_sparkline", "predicted", "deviation"

    if (client_name == 'Asun Solar') {
        var append_heading = '<div class="panel-body pad-no table-responsive"><table id="demo-foo-row-toggler" class="table toggle-circle"><thead><tr><th class="text-center" data-toggle="true" style="width: 25%;">Plant Name</th><th class="text-center" id="plant_capacity" style="width: 15%;">Capacity</th><th class="text-center" id="specific_yield" style="width: 18%;">Specific Yield</th><th class="text-center" id="energy_today" style="width: 18%;">Energy Today</th><th class="text-center" id="alarms_up" style="width: 12%;">Alarms</th><th class="text-center" id="inverters_numbers" style="width: 12%;">Inverters</th><th class="text-center" id="table_deviation" data-hide="all">Prediction Deviation</th></tr></thead><tbody id="foo_table_tbody"></tbody></table>';
        $("#plants_table").empty();
        $("#plants_table").append(append_heading);
        for(var i = 0; i < plants.length; i++) {
            if(plants[i].status) {
                $("#foo_table_tbody").append('<tr id="row' + i + '" class="table-row"><tr>');
                var status = plants[i].status;
                var status_icon, status_icon_color;
                if(status == "connected") {
                    status_icon = "badge badge-mint";
                } else if(status == "disconnected") {
                    status_icon = "badge badge-danger";
                } else {
                    status_icon = "badge badge-info";
                }
                var append_row_table = '<td style="width: 25%;"><a href="' + "/solar/plant/" + plants[i].plant_slug + '/">' + '<span class="' + status_icon + '">View Plant</span> ' + plants[i].plant_name + '</a></td><td class="text-center" style="width: 15%;">' + plants[i].plant_capacity + '</td><td class="text-center" style="width: 18%;">' + plants[i].specific_yield + '</td><td class="text-center" style="width: 18%;">' + plants[i].plant_generation_today + '</td><td class="text-center" style="width: 12%;">0</td><td class="text-center" style="width: 12%;">' + (plants[i].connected_inverters +  plants[i].disconnected_inverters + plants[i].invalid_inverters ) + '</td>';
                $("#row"+i).append(append_row_table);
            }
        }
    } else {
        if(access_level == 0) {
            if(client_name == "Renew Power") {
                var append_heading = '<div class="panel-body pad-no table-responsive"><table id="demo-foo-row-toggler" class="table toggle-circle"><thead><tr><th data-toggle="true" style="width: 25%;">Plant Name</th><th data-toggle="true" class="text-center" style="width: 10%;">Power</th><th class="text-center" id="energy_produced" style="width: 16%;">Energy Today</th><th class="text-center" id="specific_yield" style="width: 18%;">Specific Yield</th><th class="text-center" style="width: 15%;">Energy</th><th class="text-center" style="width: 15%;">PR</th><th class="text-center" id="table_prediction" data-hide="all">Predicted</th><th class="text-center" id="table_deviation" data-hide="all">Prediction Deviation</th><th data-hide="all">Network</th><th id="devices_down" data-hide="all">Inv. / SMBs <i class="fa fa-long-arrow-down" aria-hidden="true" style="color: red;"></i></th><th id="alarms_up" data-hide="all">Alarms</th></tr></thead><tbody id="foo_table_tbody"></tbody></table>';
            } else if(client_name == "EDP") {
                var append_heading = '<div class="panel-body pad-no table-responsive"><table id="demo-foo-row-toggler" class="table toggle-circle"><thead><tr><th data-toggle="true" style="width: 25%;">Plant Name</th><th data-toggle="true" style="width: 12%;">Network</th><th class="text-center" id="devices_down" style="width: 15%;">Panels <i class="fa fa-long-arrow-down" aria-hidden="true" style="color: red;"></i></th><th class="text-center" id="alarms_up" style="width: 10%;">Alarms</th><th class="text-center" style="width: 15%;">Energy</th><th class="text-center" style="width: 15%;">PR</th><th class="text-center" id="table_prediction" data-hide="all">Predicted</th><th class="text-center" id="table_deviation" data-hide="all">Prediction Deviation</th><th class="text-center" id="table_specific_yield" data-hide="all">Specific Yield</th></tr></thead><tbody id="foo_table_tbody"></tbody></table>';
            } else {
                var append_heading = '<div class="panel-body pad-no table-responsive"><table id="demo-foo-row-toggler" class="table toggle-circle"><thead><tr><th data-toggle="true" style="width: 25%;">Plant Name</th><th data-toggle="true" style="width: 12%;">Network</th><th class="text-center" id="devices_down" style="width: 15%;">Inv. / SMBs <i class="fa fa-long-arrow-down" aria-hidden="true" style="color: red;"></i></th><th class="text-center" id="alarms_up" style="width: 10%;">Alarms</th><th class="text-center" style="width: 15%;">Energy</th><th class="text-center" style="width: 15%;">PR</th><th class="text-center" id="table_prediction" data-hide="all">Predicted</th><th class="text-center" id="table_deviation" data-hide="all">Prediction Deviation</th><th class="text-center" id="table_specific_yield" data-hide="all">Specific Yield</th></tr></thead><tbody id="foo_table_tbody"></tbody></table>';
            }
        } else if(access_level == 2) {
            if(client_name == "Renew Power") {
                var append_heading = '<div class="panel-body pad-no table-responsive"><table id="demo-foo-row-toggler" class="table toggle-circle"><thead><tr><th data-toggle="true" style="width: 25%;">Plant Name</th><th data-toggle="true" class="text-center" style="width: 10%;">Power</th><th class="text-center" id="energy_produced" style="width: 16%;">Energy Today</th><th class="text-center" id="specific_yield" style="width: 18%;">Specific Yield</th><th class="text-center" style="width: 12%;">Energy</th><th class="text-center" style="width: 12%;">PR</th><th data-toggle="true" data-hide="all">Network</th><th class="text-center" id="devices_down" data-hide="all">Inv. / SMBs <i class="fa fa-long-arrow-down" aria-hidden="true" style="color: red;"></i></th><th class="text-center" id="alarms_up" data-hide="all">Alarms</th></tr></thead><tbody id="foo_table_tbody"></tbody></table>';
            } else if(client_name == "EDP") {
                var append_heading = '<div class="panel-body pad-no table-responsive"><table id="demo-foo-row-toggler" class="table toggle-circle"><thead><tr><th data-toggle="true" style="width: 25%;">Plant Name</th><th data-toggle="true" style="width: 12%;">Network</th><th class="text-center" id="devices_down" style="width: 15%;">Panels <i class="fa fa-long-arrow-down" aria-hidden="true" style="color: red;"></i></th><th class="text-center" id="alarms_up" style="width: 12%;">Alarms</th><th class="text-center" style="width: 12%;">Energy</th><th class="text-center" style="width: 12%;">PR</th></tr></thead><tbody id="foo_table_tbody"></tbody></table>';
            } else {
                var append_heading = '<div class="panel-body pad-no table-responsive"><table id="demo-foo-row-toggler" class="table toggle-circle"><thead><tr><th data-toggle="true" style="width: 25%;">Plant Name</th><th data-toggle="true" style="width: 12%;">Network</th><th class="text-center" id="devices_down" style="width: 15%;">Inv. / SMBs <i class="fa fa-long-arrow-down" aria-hidden="true" style="color: red;"></i></th><th class="text-center" id="alarms_up" style="width: 12%;">Alarms</th><th class="text-center" style="width: 12%;">Energy</th><th class="text-center" style="width: 12%;">PR</th></tr></thead><tbody id="foo_table_tbody"></tbody></table>';
            }
        } else {
            if(client_name == "Renew Power") {
                var append_heading = '<div class="panel-body pad-no table-responsive"><table id="demo-foo-row-toggler" class="table toggle-circle"><thead><tr><th data-toggle="true" style="width: 25%;">Plant Name</th><th data-toggle="true" class="text-center" style="width: 10%;">Power</th><th class="text-center" id="energy_produced" style="width: 16%;">Energy Today</th><th class="text-center" id="specific_yield" style="width: 18%;">Specific Yield</th><th data-toggle="true" style="width: 12%;">Network</th><th class="text-center" style="width: 12%;">Energy</th><th class="text-center" style="width: 12%;">PR</th></tr></thead><tbody id="foo_table_tbody"></tbody></table>';
            } else {
                var append_heading = '<div class="panel-body pad-no table-responsive"><table id="demo-foo-row-toggler" class="table toggle-circle"><thead><tr><th data-toggle="true" style="width: 25%;">Plant Name</th><th data-toggle="true" style="width: 12%;">Network</th><th class="text-center" style="width: 12%;">Energy</th><th class="text-center" style="width: 12%;">PR</th></tr></thead><tbody id="foo_table_tbody"></tbody></table>';
            }
        }

        $("#plants_table").empty();
        $("#plants_table").append(append_heading);

        $("#foo_table_tbody").empty();

        for(var i = 0; i < plants.length; i++) {
            if(plants[i].status) {
                $("#foo_table_tbody").append('<tr id="row' + i + '" class="table-row"><tr>');
                var status = plants[i].status;
                var status_text;
                var network_up = plants[i].network_up;
                var status_icon, status_icon_color;
                if(network_up == "Yes" || network_up == "yes") {
                    status_icon = "badge badge-mint";
                    status_text = "Connected";
                } else if(network_up == "No" || network_up == "no") {
                    status_icon = "badge badge-danger";
                    status_text = "Disconnected";
                } else {
                    status_icon = "badge badge-info";
                    status_text = "Unknown";
                }

                var alarms = null;
                var plant_string_error_smbs = (plants[i].string_errors_smbs || 0);
                alarms = plant_string_error_smbs;

                if(access_level == 0) {
                    if(client_name == "Renew Power") {
                        var append_row_table = '<td style="width: 25%;"><a href="' + "/solar/plant/" + plants[i].plant_slug + '/">' + '<span class="' + status_icon + '">View Plant</span> ' + plants[i].plant_name + " - " + plants[i].plant_capacity + '</a></td><td class="text-center" style="width: 10%;">' + (plants[i].current_power).toFixed(2) + '</td><td class="text-center" style="width: 16%;">' + plants[i].plant_generation_today + '</td><td class="text-center" style="width: 18%;">' + plants[i].specific_yield + '</td><td class="text-center" style="width: 15%;"><span id="energy_chart'+i+'"></span></td><td class="text-center" style="width: 15%;"><span id="pr_chart'+i+'"></span></td><td class="text-center">' + plants[i].total_today_predicted_energy_value + '</td><td class="text-center">' + plants[i].prediction_deviation + '</td><td class="text-center">' + status_text + '</td><td class="text-center">' + (plants[i].disconnected_inverters + plants[i].disconnected_smbs) + '</td><td class="text-center">' + alarms + '</td>';
                    } else {
                        var append_row_table = '<td style="width: 25%;"><a href="' + "/solar/plant/" + plants[i].plant_slug + '/">' + '<span class="' + status_icon + '">View Plant</span> ' + plants[i].plant_name + " - " + plants[i].plant_capacity + '</a></td><td class="text-center" style="width: 12%;">' + status_text + '</td><td class="text-center" style="width: 14%;">' + (plants[i].disconnected_inverters + plants[i].disconnected_smbs) + '</td><td class="text-center" style="width: 10%;">' + alarms + '</td><td class="text-center" style="width: 15%;"><span id="energy_chart'+i+'"></span></td><td class="text-center" style="width: 15%;"><span id="pr_chart'+i+'"></span></td><td class="text-center">' + plants[i].total_today_predicted_energy_value + '</td><td class="text-center">' + plants[i].prediction_deviation + '</td><td class="text-center">' + plants[i].specific_yield + '</td>';
                    }
                } else if(access_level == 2) {
                    if(client_name == "Renew Power") {
                        var append_row_table = '<td style="width: 25%;"><a href="' + "/solar/plant/" + plants[i].plant_slug + '/">' + '<span class="' + status_icon + '">View Plant</span> ' + plants[i].plant_name + " - " + plants[i].plant_capacity + '</a></td><td class="text-center" style="width: 10%;">' + (plants[i].current_power).toFixed(2) + '</td><td class="text-center" style="width: 16%;">' + plants[i].plant_generation_today + '</td><td class="text-center" style="width: 16%;">' + plants[i].specific_yield + '</td><td class="text-center" style="width: 12%;"><span id="energy_chart'+i+'"></span></td><td class="text-center" style="width: 12%;"><span id="pr_chart'+i+'"></span></td><td class="text-center">' + status_text + '</td><td class="text-center">' + (plants[i].disconnected_inverters + plants[i].disconnected_smbs) + '</td><td class="text-center">' + alarms + '</td>';
                    } else {
                        var append_row_table = '<td style="width: 25%;"><a href="' + "/solar/plant/" + plants[i].plant_slug + '/">' + '<span class="' + status_icon + '">View Plant</span> ' + plants[i].plant_name + " - " + plants[i].plant_capacity + '</a></td><td class="text-center" style="width: 12%;">' + status_text + '</td><td class="text-center" style="width: 15%;">' + (plants[i].disconnected_inverters + plants[i].disconnected_smbs) + '</td><td class="text-center" style="width: 18%;">' + alarms + '</td><td class="text-center" style="width: 12%;"><span id="energy_chart'+i+'"></span></td><td class="text-center" style="width: 12%;"><span id="pr_chart'+i+'"></span></td>';
                    }
                } else {
                    if(client_name == "Renew Power") {
                        var append_row_table = '<td style="width: 25%;"><a href="' + "/solar/plant/" + plants[i].plant_slug + '/">' + '<span class="' + status_icon + '">View Plant</span> ' + plants[i].plant_name + " - " + plants[i].plant_capacity + '</a></td><td class="text-center" style="width: 10%;">' + (plants[i].current_power).toFixed(2) + '</td><td class="text-center" style="width: 16%;">' + plants[i].plant_generation_today + '</td><td class="text-center" style="width: 16%;">' + plants[i].specific_yield + '</td><td class="text-center" style="width: 12%;">' + status_text + '</td><td class="text-center" style="width: 12%;"><span id="energy_chart'+i+'"></span></td><td class="text-center" style="width: 12%;"><span id="pr_chart'+i+'"></span></td>';
                    } else {
                        var append_row_table = '<td style="width: 25%;"><a href="' + "/solar/plant/" + plants[i].plant_slug + '/">' + '<span class="' + status_icon + '">View Plant</span> ' + plants[i].plant_name + " - " + plants[i].plant_capacity + '</a></td><td class="text-center" style="width: 12%;">' + status_text + '</td><td class="text-center" style="width: 12%;"><span id="energy_chart'+i+'"></span></td><td class="text-center" style="width: 12%;"><span id="pr_chart'+i+'"></span></td>';
                    }
                }
                $("#row"+i).append(append_row_table);
                var energy_id = "energy_chart"+i;
                var pr_id = "energy_chart"+i;
                var energy_date = [], energy_values = [];
                var pr_date = [], pr_values_array = [];

                if(plants[i].past_pr) {
                    for(var individual_plant = 0; individual_plant < plants[i].past_pr.length; individual_plant++) {
                        var date = plants[i].past_pr[individual_plant].timestamp;
                        date = dateFormat(date, "mmm dd, yyyy");
                        pr_date.push(date);
                        var pr_value = (plants[i].past_pr[individual_plant].pr * 100);
                        pr_values_array.push(pr_value);
                    }
                } else {
                    $("#pr_chart"+i).empty();
                    $("#pr_chart"+i).append("No PR values.")
                }

                sparkline_bar_chart("pr_chart"+i, pr_values_array, pr_date, "", "PR");

                var energy_value_units = [];

                if(plants[i].past_monthly_generation) {
                    for(var individual_plant = 0; individual_plant < plants[i].past_monthly_generation.length; individual_plant++) {
                        var date = plants[i].past_monthly_generation[individual_plant].timestamp;
                        date = dateFormat(date, "mmm dd, yyyy");
                        energy_date.push(date);
                        var energy_value = plants[i].past_monthly_generation[individual_plant].energy;
                        energy_value = energy_value.split(" ");
                        energy_values.push(energy_value[0]);
                        energy_value_units.push(energy_value[1]);
                    }
                } else {
                    $("#energy_chart"+i).empty();
                    $("#energy_chart"+i).append("No Energy values.")
                }
                sparkline_bar_chart("energy_chart"+i, energy_values, energy_date, energy_value_units, "Energy");
            } else {
                $("#plants_table").empty();
                $("#plants_table").append("<div class='panel-body'><div class='alert alert-warning' id='alert'>No data for the plants in the table.</div></div>");
            }
        }
    }

    $(function() {
        $('.table').footable({
            "paging": {
                enabled: true
            }
        });
    });

}

function all_plants(summary_info, status) {

    var geoJson_summary = {
        "type": "FeatureCollection",
        "features": []
    };

    if(summary_info.plants.length > 0) {
        for(var i = 0; i < summary_info.plants.length; i++) {
            geoJson_summary.features.push({
                "type": "Feature",
                "properties": {
                    "Name": summary_info.plants[i].plant_name,
                    "slug": summary_info.plants[i].plant_slug,
                    "BusType": summary_info.plants[i].status,
                    "Description": "Marker " + i,
                    "id": i
                },
                "geometry": {
                    "type": "Point",
                    "coordinates": [summary_info.plants[i].longitude, summary_info.plants[i].latitude]
                }
            });
        }
    }

    var blueIcon = L.icon({
        iconUrl: '/static/solarrms/plugins/leafletjs/images/marker-icon.png',
        shadowUrl: '/static/solarrms/plugins/leafletjs/images/marker-shadow.png',

        iconSize:     [25, 41], // size of the icon
        shadowSize:   [41, 41], // size of the shadow
        iconAnchor:   [12, 41], // point of the icon which will correspond to marker's location
        shadowAnchor: [12, 41],  // the same for the shadow
        popupAnchor:  [-3, -76] // point from which the popup should open relative to the iconAnchor
    });

    var redIcon = L.icon({
        iconUrl: '/static/solarrms/plugins/leafletjs/images/marker-icon-red.png',
        shadowUrl: '/static/solarrms/plugins/leafletjs/images/marker-shadow.png',

        iconSize:     [25, 41], // size of the icon
        shadowSize:   [41, 41], // size of the shadow
        iconAnchor:   [12, 41], // point of the icon which will correspond to marker's location
        shadowAnchor: [12, 41],  // the same for the shadow
        popupAnchor:  [-3, -76] // point from which the popup should open relative to the iconAnchor
    });

    var greenIcon = L.icon({
        iconUrl: '/static/solarrms/plugins/leafletjs/images/marker-icon-green.png',
        shadowUrl: '/static/solarrms/plugins/leafletjs/images/marker-shadow.png',

        iconSize:     [25, 41], // size of the icon
        shadowSize:   [41, 41], // size of the shadow
        iconAnchor:   [12, 41], // point of the icon which will correspond to marker's location
        shadowAnchor: [12, 41],  // the same for the shadow
        popupAnchor:  [-3, -76] // point from which the popup should open relative to the iconAnchor
    });

    var allplants = L.geoJson(geoJson_summary);
    var connected_plants = L.geoJson(geoJson_summary, {
        filter: function(feature, layer) {
            return feature.properties.BusType == "connected";
        },
        pointToLayer: function(feature, latlng) {
            return L.marker(latlng, {
                icon: greenIcon
            }).on('mouseover', function() {
                this.bindPopup(feature.properties.Name).openPopup();
                hover_marker(feature.properties.id);

                if(summary_info.plants[feature.properties.id]) {
                    foo_tables([summary_info.plants[feature.properties.id]]);
                } else {

                }

                var fooColExp = $('#demo-foo-row-toggler');
                fooColExp.footable().trigger('footable_expand_first_row');

            }).on('mouseout', function() {
                this.bindPopup().closePopup();

                var effect = 'slide';

                // Set the options for the effect type chosen
                var options = { direction: 'left' };

                var duration = 500;
                $('#slider').hide(effect, options, duration);

                foo_tables(summary_info.plants);

                var fooColExp = $('#demo-foo-row-toggler');
                fooColExp.footable().trigger('footable_collapse_first_row');

            }).on('click', marker_on_click);
        }
    });
    var disconnected_plants = L.geoJson(geoJson_summary, {
        filter: function(feature, layer) {
            return feature.properties.BusType == "disconnected";
        },
        pointToLayer: function(feature, latlng) {
            return L.marker(latlng, {
                icon: redIcon
            }).on('mouseover', function() {
                this.bindPopup(feature.properties.Name).openPopup();
                hover_marker(feature.properties.id);
                foo_tables([summary_info.plants[feature.properties.id]]);

                var fooColExp = $('#demo-foo-row-toggler');
                fooColExp.footable().trigger('footable_expand_first_row');

            }).on('mouseout', function() {

                this.bindPopup().closePopup();

                var effect = 'slide';

                // Set the options for the effect type chosen
                var options = { direction: 'left' };

                var duration = 500;
                $('#slider').hide(effect, options, duration);

                foo_tables(summary_info.plants);

                var fooColExp = $('#demo-foo-row-toggler');
                fooColExp.footable().trigger('footable_collapse_first_row');

            }).on('click', marker_on_click);
        }
    });
    var unknown_plants = L.geoJson(geoJson_summary, {
        filter: function(feature, layer) {
            return feature.properties.BusType == "unmonitored";
        },
        pointToLayer: function(feature, latlng) {
            return L.marker(latlng, {
                icon: blueIcon
            }).on('mouseover', function() {
                this.bindPopup(feature.properties.Name).openPopup();
                hover_marker(feature.properties.id);
                foo_tables([summary_info.plants[feature.properties.id]]);

                var fooColExp = $('#demo-foo-row-toggler');
                fooColExp.footable().trigger('footable_expand_first_row');

            }).on('mouseout', function() {

                this.bindPopup().closePopup();

                var effect = 'slide';

                // Set the options for the effect type chosen
                var options = { direction: 'left' };

                var duration = 500;
                $('#slider').hide(effect, options, duration);

                foo_tables(summary_info.plants);

                var fooColExp = $('#demo-foo-row-toggler');
                fooColExp.footable().trigger('footable_collapse_first_row');

            }).on('click', marker_on_click);
        }
    });
    if(summary_info.plants.length > 1) {
        map.fitBounds(allplants.getBounds(), {
            padding: [50, 50]
        });
    } else {
        map.fitBounds(allplants.getBounds(), {
            padding: [50, 50],
            maxZoom: 8
        });
    }

    connected_plants.addTo(map)
    disconnected_plants.addTo(map)
    unknown_plants.addTo(map)

    /*$(".leaflet-top leaflet-right").empty();
    $(".leaflet-top leaflet-right").append();*/

    // The JavaScript below is new
    $("#down_status_button").click(function() {
        map.addLayer(disconnected_plants)
        map.removeLayer(connected_plants)
        map.removeLayer(unknown_plants)
    });
    $("#unknown_status_button").click(function() {
        map.addLayer(unknown_plants)
        map.removeLayer(connected_plants)
        map.removeLayer(disconnected_plants)
    });
    $("#live_status_button").click(function() {
        map.addLayer(connected_plants)
        map.removeLayer(disconnected_plants)
        map.removeLayer(unknown_plants)
    });
    $("#all_status_button").click(function() {
        map.addLayer(connected_plants)
        map.addLayer(disconnected_plants)
        map.addLayer(unknown_plants)
    });

    function hover_marker(id) {
        var effect = 'slide';

        // Set the options for the effect type chosen
        var options = { direction: 'left' };

        var plant_name;

        if(typeof client_info.plants[id].plant_name !== 'undefined') {
            plant_name = client_info.plants[id].plant_name
        } else {
            plant_name = "N/A";
        }

        $("#plant_name").empty();
        $("#plant_name").append(plant_name);

        var plant_current_power;

        if(typeof client_info.plants[id].current_power !== 'undefined') {
            plant_current_power = (client_info.plants[id].current_power).toFixed(2);
        } else {
            plant_current_power = "N/A";
        }

        $("#current_power_plant").empty();
        $("#current_power_plant").append(plant_current_power);

        var todays_plant_generation, todays_plant_generation_value, todays_plant_generation_unit;

        if(typeof client_info.plants[id].plant_generation_today !== 'undefined') {
            todays_plant_generation = client_info.plants[id].plant_generation_today;
            todays_plant_generation = todays_plant_generation.split(" ");
            todays_plant_generation_value = todays_plant_generation[0];
            todays_plant_generation_unit = todays_plant_generation[1];
        } else {
            todays_plant_generation_value = "N/A";
            todays_plant_generation_unit = "N/A";
        }

        $("#todays_generation_plant").empty();
        $("#todays_generation_plant").append(todays_plant_generation_value);

        $("#todays_generation_plant_unit").empty();
        $("#todays_generation_plant_unit").append(todays_plant_generation_unit);

        var pr;
        var cuf;
        var pr_cuf_value;

        if(typeof client_info.plants[id].performance_ratio !== 'undefined' && typeof client_info.plants[id].cuf !== 'undefined') {
            pr = parseInt(client_info.plants[id].performance_ratio * 100);
            cuf = parseInt(client_info.plants[id].cuf * 100);
            pr_cuf_value = pr + "<span class='font-size: small'>%</span>" + "/" + cuf + "<span class='font-size: small'>%</span>";
        } else {
            pr_cuf_value = "NA / NA";
        }

        $("#pr_cuf_plant").empty();
        $("#pr_cuf_plant").append(pr_cuf_value);

        var status = client_info.plants[id].status;
        var icon = null;
        var style = null;

        if(client_info.plants[id].status) {
            status = client_info.plants[id].status
            if(status == "connected") {
                status = "Live";
                icon = 'fa fa-spin fa-circle-o-notch';
            } else if(status == "disconnected") {
                status = "Down";
                icon = 'fa fa-blink fa fa-ban';
                style = 'color: red;'
            } else {
                status = "Unknown";
            }
            $("#status_plant").empty();
            $("#status_plant").append('<i class="' + icon + ' fa-3x network-connected" style="'+style+'"></i> ' + status);
        } else {

        }

        var last_updated;

        if(client_info.plants[id].updated_at) {
            last_updated = client_info.plants[id].updated_at;
            last_updated = dateFormat(last_updated, "HH:MM:ss");
        } else {
            last_updated = "No Last Update";
        }

        $("#last_updated_plant").empty();
        $("#last_updated_plant").append("Last Updated: " + last_updated);

        // Set the duration (default: 400 milliseconds)
        var duration = 500;
        $('#slider').show(effect, options, duration);

    }

    function marker_on_click(e) {

        window.location.href = "/solar/plant/" + this.feature.properties.slug;

    }

}

$( document ).ajaxComplete(function( event, request, settings ) {
    console.log("active AJAX calls", $.active);
    if (first_load == true && $.active == 1) {
        page_load_time = new Date() - page_load_time;
        console.log("page load time: ", page_load_time.toString().concat(" ms"))
        var load_time = page_load_time.toString().concat(" ms");
        mixpanel.track(
        "Client page loaded",
        {"load_time": load_time,
         "user_email": user_email}
        );
        first_load = false;
    }
    console.log(first_load);
});