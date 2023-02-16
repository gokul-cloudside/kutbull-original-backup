var show_cuf = true;
var $inverter_grid = null;
var $ajb_grid = null;
var page_load_time = null
var first_page_load = true;

function col_update_col (id, from, to) {
    $(id).removeClass(from);
    $(id).addClass(to);
}

function check_element(value, self_id, neighbours_id) {
    if (typeof(value) == 'undefined' || value == "NA") {
        $("#" + self_id).hide();
        if(neighbours_id != "") {
            $("#" + neighbours_id).removeClass("col-lg-6 col-md-6 col-sm-6 col-xs-6");
            $("#" + neighbours_id).addClass("col-lg-12 col-md-12 col-sm-12 col-xs-12");
        }
    } else {
        $("#" + self_id).show();
    }
}

function set_config(config_data) {
    if (typeof config_data.show_cuf != 'undefined' && config_data.show_cuf == "False") {
        show_cuf = false;
    }

    if (typeof config_data.metadata_border_color != 'undefined') {
        //$("#image_div").css('border-color', config_data.metadata_border_color);
        //$(".left_block_text").removeClass("text-white");
        //$(".left_block_text").css('color', config_data.metadata_text_color);
    }
}
function access_control(data) {
    if (parseFloat(data.performance_ratio) != 0.0 || parseFloat(data.module_temperature) != 0.0) {
        $("#summary_performance_ratio").show();
        $("#module_temperature_div").show();
        $("#insolation_div").show();
    } else {
    //remove the insolation block
        $("#generation_summary_div").removeClass("col-lg-4");
        $("#generation_summary_div").removeClass("col-md-4");
        $("#generation_summary_div").addClass("col-lg-6");
        $("#generation_summary_div").addClass("col-md-6");
        $("#economic_benefits_div").removeClass("col-lg-4");
        $("#economic_benefits_div").removeClass("col-md-4");
        $("#economic_benefits_div").addClass("col-lg-6");
        $("#economic_benefits_div").addClass("col-md-6");
    }
    if (typeof data.total_high_anomaly_smb_numbers != 'undefined' &&
        typeof data.total_low_anomaly_smb_numbers != 'undefined' &&
        typeof data.plant_inverter_cleaning_details != 'undefined') {
        $("#data_analytics_div").show();
    }
    if (typeof data.disconnected_inverters != 'undefined' &&
        typeof data.disconnected_smbs != 'undefined' &&
        typeof data.total_inverter_error_numbers != 'undefined') {
        $("#data_alerts_div").show();
    }
    if (typeof data.gateways_disconnected != 'undefined' &&
        typeof data.gateways_powered_off != 'undefined') {
        $("#gateways_div").show();
    }
};

$(document).ready(function() {
    console.log(config_data);
    page_load_time = new Date();
    mixpanel.identify(user_email);
    if (config_data != null) {
        set_config(config_data);
    } else {
        //$("#image_div").css('border-color', "#2980B9");
        //$("#left_block").addClass("color-e");
    }

    $(function () {
      $('[data-toggle="tooltip"]').tooltip()
    })

    var t1 = new Date();

    $("#client_spinner").show();

    var t2 = new Date();
    console.log("After loading show: ", t2 - t1);

    var summary_info = null;
    var bounds_leaflet_map = null;
    var map = null;
    dashboard_clients(true);

    var t3 = new Date();
    console.log("After dashboard clients: ", t3 - t2);

    var dates = get_dates();
    var st = dates[0];
    var et = dates[1];

    power_irradiation_chart(st, et);

    var t4 = new Date();
    console.log("After power irradiation chart: ", t4 - t3);

    var t5 = new Date();

    var t6 = new Date();
    console.log("After loading hide: ", t6 - t5);

    inverters_ajbs(2);

    setInterval(function () {
        summary_info = null;
        bounds_leaflet_map = null;
        map = null;
        dashboard_clients(false);

        dates = get_dates();
        st = dates[0];
        et = dates[1];
        
        power_irradiation_chart(st, et);

        energy_meters_and_transformers();
        inverters_ajbs(1);
    }, 5000*60);

});

$('.datepicker_start_days').datepicker({
    autoclose: true,
    todayHighlight: true,
    startView: "days",
    minViewMode: "days",
    format: "dd-mm-yyyy"
});

function redraw_window() {
    $('a[data-toggle="tab"]').on('shown.bs.tab', function (e) {
        e.preventDefault();
        window.dispatchEvent(new Event('resize'));
    });
}

var debug = true;

function set_variable_value(variable, value) {

    if (typeof value == 'undefined' || value == null || (typeof value == 'string' && value.includes("NaN"))) {
        value = "NA";
    }

    if ((typeof value == 'string' && value.includes("kWh/m^2"))) {
        value = value.replace("kWh/m^2", "<span style='font-size: small'>kWh/m<sup>2</sup></span>");

    } else if ((typeof value == 'string' && value.includes("kWh") && (value.includes("m^2") || value.includes("m2")))) {
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
        console.log(err);
        console.log(variable);
        console.log(value);
    }
}

function get_dates() {
    // get the start date

    var st = $(".datepicker_start_days").val();

    if(st == "") {
        st = new Date();
    } else {
        console.log(st);

        /*var st = new Date();*/
        st = st.split("-");
        st = st[2] + "-" + st[1] + "-" + st[0];
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

function dashboard_clients(first_call) {

    $.ajax({
        type: "GET",
        url : "/api/v1/solar/plants/".concat(plant_slug).concat("/summary/"),
        success: function(api_summary_info){
            summary_info = api_summary_info;
            if (first_call) {
                access_control(summary_info);
            }

            $("#breadcrumb_page_path").empty();
            var slug_name = ((summary_info || {'plant_slug': 'No Plant'}).plant_slug || "No Plant").charAt(0).toUpperCase() + ((summary_info || {'plant_slug': 'No Plant'}).plant_slug || "No Plant").slice(1).toLowerCase();
            $("#breadcrumb_page_path").append("<ol class='breadcrumb mar-ver-5'> <li class='text-center text-bold'> <a href='/solar/client/'>All Plants</a> </li> <li class='text-center text-bold'><a href='#'>" + slug_name + "</a> </li> </ol>")

            //blue widget left side
            var t1 = new Date();
            var client_image = $("#client_logo").empty();
            client_image.append("<img class='mar-btm client-logo-image' src='" + summary_info.plant_logo + "' alt='DATAGLEN'>");
            set_variable_value($("#client_name"), (summary_info.plant_name || "Plant Name Not Specified"));
            set_variable_value($("#plant_location"), (summary_info.plant_location || "Unknown Location"));
            if(summary_info.status) {
                weather_status_response = weather_current(summary_info.latitude.toString(), summary_info.longitude.toString(), summary_info, "39217aee72de46088c4145902170302");
            }
            //open_weather(summary_info.latitude.toString(), summary_info.longitude.toString(), summary_info, "c126206e0336923caee2b677b0e373cb");

            var dc_capacity = (summary_info.plant_capacity || "0 MWh").split(" ");
            if (dc_capacity.length == 2) {
                set_variable_value($("#dc_capacity"), dc_capacity[0] + '<span style="font-size: small" id="dc_capacity_unit"> '+ dc_capacity[1] +'</span>');
            } else {
                set_variable_value($("#dc_capacity"), 0 + '<span style="font-size: small" id="dc_capacity_unit"> '+ ' MW' +'</span>');
            }

            //grey widget left side
            set_variable_value($("#last_updated_time"), "Updated: ".concat((moment(summary_info.updated_at).format("HH:mm:ss") || "Not Available")));
            set_variable_value($("#module_temperature"), (summary_info.module_temperature || 0).toFixed(2) + " &#8451;" );

            set_variable_value($("#panel_numbers"), (((((summary_info || {"panel_details": {"numbers": 0}}).panel_details || 0))).numbers || 0));
            set_variable_value($("#panel_make"), (((((summary_info || {"panel_details": {"make": "Manufacturer: NA"}}).panel_details || "Manufacturer: NA"))).make || "Manufacturer: NA"));
            set_variable_value($("#panel_capacity"), (((((summary_info || {"panel_details": {"capacity": "0"}}).panel_details || "0"))).capacity || "0") + " Wp");

            if (debug == true) {
                console.log("left side blocks blue and grey: ", new Date() - t1);
            }

            //First grey box in the center
            var t2 = new Date();
            var plant_generation_today = (summary_info.plant_generation_today || "0 MWh").split(" ");
            if (plant_generation_today.length == 2) {
                set_variable_value($("#plant_today_generation"), plant_generation_today[0] + '<span style="font-size: small" id="plant_today_generation_unit"> '+ plant_generation_today[1] +'</span>');
                if(client_name == "Renew Power") {
                    var houses_powered = parseInt((plant_generation_today[0])/3);
                    set_variable_value($("#houses_powered"), houses_powered);
                } else{
                    set_variable_value($("#houses_powered"), "NA");    
                }
            } else {
                set_variable_value($("#houses_powered"), "NA");
                set_variable_value($("#plant_today_generation"), 0 + '<span style="font-size: small" id="plant_today_generation_unit"> '+ ' kWp' +'</span>');
            }
            var plant_current_power = (summary_info.current_power);
            if (plant_current_power) {
                set_variable_value($("#current_power"), plant_current_power.toFixed(1) + '<span style="font-size: small" id="plant_today_generation_unit"> kW</span>');
            } else {
                set_variable_value($("#current_power"), 0 + '<span style="font-size: small" id="plant_today_generation_unit"> '+ ' kW' +'</span>');
            }
            set_variable_value($("#plant_total_energy"), (summary_info.plant_total_energy || "NA"));
            set_variable_value($("#pvsyst_generation"), (summary_info.pvsyst_generation || "NA"));
            check_element((summary_info.pvsyst_generation || "NA"), 'pvsyst_generation_today_div', "");

            if (client_name != "Asun Solar") {
                set_variable_value($("#predicted_plant_generation_today"), (summary_info.total_today_predicted_energy_value || "NA"));
                set_variable_value($("#predicted_plant_generation_text"), "Predicted");
            } else {
                set_variable_value($("#predicted_plant_generation_today"), (summary_info.predicted_generation || "NA"));
                if ((summary_info.plant_total_energy || "0 kWh").split(" ")[1] == 'kWh') {
                    set_variable_value($("#predicted_plant_generation_today"), parseFloat((summary_info.plant_total_energy || "0 kWh").split(" ")[0])*8);
                    set_variable_value($("#predicted_plant_generation_text"), "Savings");
                } else if ((summary_info.plant_total_energy || "0 kWh").split(" ")[1] == 'MWh') {
                    set_variable_value($("#predicted_plant_generation_today"), "<i class='fa fa-inr'></i> " + parseFloat((summary_info.plant_total_energy || "0 kWh").split(" ")[0])*8*1000);
                    set_variable_value($("#predicted_plant_generation_text"), "Savings");
                }
            }

            //Second grey box in the center
            if (((((summary_info || {"past_kwh_per_meter_square": []}). past_kwh_per_meter_square || []))).length > 0) {
                var insolation = (summary_info.past_kwh_per_meter_square[(summary_info.past_kwh_per_meter_square.length)-1].kwh_value).split(" ");
            } else {
                var insolation = []
            }
            if (insolation.length == 2) {
                set_variable_value($("#insolation"), insolation[0] + '<span style="font-size: small" id="insolation_unit"> '+ insolation[1] +'</span>');
            } else {
                set_variable_value($("#insolation"), 0 + '<span style="font-size: small" id="insolation_unit"> '+ ' kWh/m^2' +'</span>');
            }
            var pvsyst_ghi = (summary_info.pvsyst_ghi || "NA").split(" ");
            if (pvsyst_ghi.length == 2) {
                set_variable_value($("#pvsyst_ghi"), pvsyst_ghi[0] + '<span style="font-size: small" id="pvsyst_ghi_unit"> '+ pvsyst_ghi[1] +'</span>');
                check_element((summary_info.pvsyst_ghi || "NA"), 'pvsyst_ghi_div', "");
            } else {
                /*set_variable_value($("#pvsyst_ghi"), 0 + '<span style="font-size: small" id="pvsyst_ghi_unit"> '+ ' kWh/m^2' +'</span>');*/
                $("#pvsyst_ghi_div").show();

                $("#pvsyst_ghi_div").empty();
                $("#pvsyst_ghi_div").append("Solar<br/>Radiation");
            }
            var pvsyst_in_plane = (summary_info.pvsyst_in_plane || "NA kWh/m^2").split(" ");
            if (pvsyst_in_plane.length == 2) {
                set_variable_value($("#pvsyst_in-plane"), pvsyst_in_plane[0] + '<span style="font-size: small" id="pvsyst_in_plane_unit"> '+ pvsyst_in_plane[1] +'</span>');
                check_element((summary_info.pvsyst_in_plane || "NA"), 'pvsyst_in_plane_div', "");
            } else {
                set_variable_value($("#pvsyst_in-plane"), 0 + '<span style="font-size: small" id="pvsyst_in_plane_unit"> '+ ' kWh/m^2' +'</span>');
            }

            //Third grey box in the center
            var co2_savings = (summary_info.plant_co2 || "0 Ton").split(" ");
            if (co2_savings.length == 2) {
                set_variable_value($("#co2_value"), co2_savings[0] + '<span style="font-size: small" id="co2_value_unit"> '+ co2_savings[1] +'</span>');
            } else {
                set_variable_value($("#co2_value"), 0 + '<span style="font-size: small" id="co2_value_unit"> '+ ' Ton' +'</span>');
            }

            /*var houses_powered = (summary_info.households_powered || "NA ").split(" ");
            if (houses_powered.length == 2) {
                set_variable_value($("#diesel_saved"), houses_powered[0] + '<span style="font-size: small" id="diesel_saved_unit"> '+ houses_powered[1] +'</span>');
            } else {
                set_variable_value($("#diesel_saved"), 0 + '<span style="font-size: small" id="diesel_saved_unit"> '+ ' Households' +'</span>');
            }*/
            var distance_travelled = (summary_info.seeds_planted || "NA ").split(" ");
            if (distance_travelled.length == 2) {
                set_variable_value($("#distance_travelled"), distance_travelled[0] + '<span style="font-size: small" id="distance_travelled_unit"> '+ distance_travelled[1] +'</span>');
            } else {
                set_variable_value($("#distance_travelled"), 0 + '<span style="font-size: small" id="distance_travelled_unit"> '+ ' Trees' +'</span>');
            }

            if (debug == true) {
                console.log("3 mini-blocks in the center: ", new Date() - t2);
            }

            //mint widget right side
            var t3 = new Date();
            set_variable_value($("#performance_ratio_today"), (parseFloat(summary_info.performance_ratio*100).toFixed(1).toString()) + "%" || "0 %");
            set_variable_value($("#pvsyst_pr"), (parseFloat(summary_info.pvsyst_pr*100).toFixed(1).toString()) + "%" || "NA");
            check_element((summary_info.pvsyst_pr || "NA"), 'pvsyst_pr_div', "pr_div");
            if (show_cuf == true){
                set_variable_value($("#cuf_text"), "CUF");
                set_variable_value($("#cuf_todays"), (parseFloat(summary_info.cuf*100).toFixed(1).toString()) + "%" || "0 %");
                set_variable_value($("#cuf_unit"), "Today's");
                set_variable_value($("#pvsyst_cuf"), (parseFloat(summary_info.pvsyst_cuf).toFixed(1).toString()) + "kW" || "0 kW");
                check_element((summary_info.pvsyst_cuf || "NA"), 'pvsyst_cuf_div', "cuf_div");
                set_variable_value($("#pvsyst_cuf_unit"), "PVsyst");
            } else {
                //show power
                set_variable_value($("#cuf_text"), "Power");
                set_variable_value($("#cuf_todays"), (parseFloat(summary_info.current_power).toFixed(1).toString()) + " kW" || "NA kW");
                set_variable_value($("#cuf_unit"), "Current");
                set_variable_value($("#pvsyst_cuf"), (parseFloat(summary_info.max_power).toFixed(1).toString()) + " kW" || "NA kW");
                check_element((summary_info.max_power || "NA"), 'pvsyst_cuf_div', "cuf_div");
                set_variable_value($("#pvsyst_cuf_unit"), "Peak Today");
            }
            set_variable_value($("#specific_yield_todays"), summary_info.specific_yield || '0');
            if (typeof summary_info.specific_yield_pvsyst == 'undefined') {
                $("#sy_pvsyst").remove();
                col_update_col("#sy_today", "col-lg-6", "col-lg-12");
                col_update_col("#sy_today", "col-md-6", "col-md-12");
                col_update_col("#sy_today", "col-xs-6", "col-xs-12");
                col_update_col("#sy_today", "col-sm-6", "col-sm-12");
            } else {
                set_variable_value($("#pvsyst_specific_yield"), summary_info.specific_yield_pvsyst || "NA");
            }

            //grey widget right side

            set_variable_value($("#inverters_number"), (((((summary_info || {"inverter_details": {"numbers": 0}}).inverter_details || 0))).numbers || 0));
            set_variable_value($("#inverters_make"), (((((summary_info || {"inverter_details": {"make": "Manufacturer: NA"}}).inverter_details || "Manufacturer: NA"))).make || "Manufacturer: NA"));
            set_variable_value($("#inverters_capacity"), (((((summary_info || {"inverter_details": {"capacity": "0"}}).inverter_details || "0"))).capacity || "0"));

            if (debug == true) {
                console.log("right side widget mint and grey: ", new Date() - t3);
            }

            //operation and maintenance bottom widget
            var t4 = new Date();
            var device_down;

            if(typeof summary_info.disconnected_inverters !== 'undefined' && typeof summary_info.disconnected_smbs !== 'undefined') {
                device_down = summary_info.disconnected_inverters + summary_info.disconnected_smbs;
                if(device_down > 0) {
                    console.log(device_down);
                    $("#devices_down").removeClass("black_color_font");
                    $("#devices_down").addClass("red_color_font");
                    $("#devices_down_details").empty();
                    $("#devices_down_details").append('<a class="btn btn-danger btn-xs" id="devices_down_button" onClick="redraw_window();" data-toggle="tab" href="#dc_devices">View Details</a>')
                } else {
                    $("#devices_down").removeClass("red_color_font");
                    $("#devices_down").addClass("black_color_font");
                    $("#devices_down_details").empty();
                }
            } else {
                device_down = "N/A";
                $("#devices_down").removeClass("red_color_font");
                $("#devices_down").addClass("black_color_font");
                $("#devices_down_details").empty();
            }

            $("#devices_down").empty();
            $("#devices_down").append(device_down);

            $("#devices_down_button").click(function (e) {
                $("#dc_devices_li").addClass("active")
                $("#plant_section_li").removeClass("active")

                hide_date(e);
            });

            var alarms_raised;

            if(typeof summary_info.total_inverter_error_numbers !== 'undefined') {
                alarms_raised = summary_info.total_inverter_error_numbers;
                if(alarms_raised > 0) {
                    $("#alarms_raised").removeClass("black_color_font");
                    $("#alarms_raised").addClass("red_color_font");
                    $("#alarms_raised_details").empty();
                    $("#alarms_raised_details").append('<a class="btn btn-danger btn-xs" id="alarms_raised_button" onClick="redraw_window();" data-toggle="tab" href="#dc_devices">View Details</a>')
                } else {
                    $("#alarms_raised").removeClass("red_color_font");
                    $("#alarms_raised").addClass("black_color_font");
                    $("#alarms_raised_details").empty();
                }
            } else {
                alarms_raised = "N/A";
                $("#alarms_raised").removeClass("red_color_font");
                $("#alarms_raised").addClass("black_color_font");
                $("#alarms_raised_details").empty();
            }

            $("#alarms_raised_button").click(function (e) {
                $("#dc_devices_li").addClass("active")
                $("#plant_section_li").removeClass("active")

                hide_date(e);
            });

            $("#alarms_raised").empty();
            $("#alarms_raised").append(alarms_raised);

            var gateways_disconnected;

            if(typeof summary_info.gateways_disconnected !== 'undefined') {
                gateways_disconnected = summary_info.gateways_disconnected;
                $("#gateways_disconnected_details").empty();
                if(gateways_disconnected > 0) {
                    $("#gateways_disconnected").removeClass("black_color_font");
                    $("#gateways_disconnected").addClass("red_color_font");
                    $("#gateways_disconnected_details").empty();
                    $("#gateways_disconnected_details").append('<a class="btn btn-danger btn-xs" href="' + summary_info.gateways_disconnected_ticket + '" role="button">View Details</a>');
                } else {
                    $("#gateways_disconnected").removeClass("red_color_font");
                    $("#gateways_disconnected").addClass("black_color_font");
                    $("#gateways_disconnected_details").hide();
                }
            } else {
                gateways_disconnected = "N/A";
                $("#gateways_disconnected").removeClass("red_color_font");
                $("#gateways_disconnected").addClass("black_color_font");
                $("#gateways_disconnected_details").empty();
                $("#gateways_disconnected_details").hide();
            }

            $("#gateways_disconnected").empty();
            $("#gateways_disconnected").append(gateways_disconnected);

            var gateways_powered_off;

            if(typeof summary_info.gateways_powered_off !== 'undefined') {
                gateways_powered_off = summary_info.gateways_powered_off;
                $("#gateways_powered_off_details").empty();
                if(gateways_powered_off > 0) {
                    $("#gateways_powered_off").removeClass("black_color_font");
                    $("#gateways_powered_off").addClass("red_color_font");
                    $("#gateways_powered_off_details").empty();
                    $("#gateways_powered_off_details").append('<a class="btn btn-danger btn-xs" href="' + summary_info.gateways_powered_off_ticket + '" role="button">View Details</a>');
                } else {
                    $("#gateways_powered_off").removeClass("red_color_font");
                    $("#gateways_powered_off").addClass("black_color_font");
                    $("#gateways_powered_off_details").hide();
                }
            } else {
                gateways_powered_off = "N/A";
                $("#gateways_powered_off").removeClass("red_color_font");
                $("#gateways_powered_off").addClass("black_color_font");
                $("#gateways_powered_off_details").empty();
                $("#gateways_powered_off_details").hide();
            }

            $("#gateways_powered_off").empty();
            $("#gateways_powered_off").append(gateways_powered_off);

            var inverters_panel_need_cleaning;

            if(summary_info.plant_inverter_cleaning_details && summary_info.plant_inverter_cleaning_details.length > 0) {
                inverters_panel_need_cleaning = summary_info.plant_inverter_cleaning_details[0].inverters_required_cleaning_numbers;
                if(inverters_panel_need_cleaning > 0) {
                    $("#inverters_panel_need_cleaning").removeClass("black_color_font");
                    $("#inverters_panel_need_cleaning").addClass("red_color_font");
                    $("#inverters_panels_need_cleaning_details").empty();
                    $("#inverters_panels_need_cleaning_details").append('<a class="btn btn-danger btn-xs" href="' + summary_info.plant_inverter_cleaning_details[0].ticket_url + '" role="button">View Details</a>')
                } else {
                    $("#inverters_panel_need_cleaning").removeClass("red_color_font");
                    $("#inverters_panel_need_cleaning").addClass("black_color_font");
                }
            } else if (summary_info.plant_inverter_cleaning_details && summary_info.plant_inverter_cleaning_details.length == 0) {
                inverters_panel_need_cleaning = 0;
                $("#inverters_panel_need_cleaning").removeClass("red_color_font");
                $("#inverters_panel_need_cleaning").addClass("black_color_font");
                $("#inverters_panels_need_cleaning_details").empty();
            } else {
                inverters_panel_need_cleaning = "N/A";
                $("#inverters_panel_need_cleaning").removeClass("red_color_font");
                $("#inverters_panel_need_cleaning").addClass("black_color_font");
                $("#inverters_panels_need_cleaning_details").empty();
            }

            $("#inverters_panel_need_cleaning").empty();
            $("#inverters_panel_need_cleaning").append(inverters_panel_need_cleaning);

            var predictive_issues;

            if(typeof summary_info.total_high_anomaly_smb_numbers != 'undefined' && typeof summary_info.total_low_anomaly_smb_numbers != 'undefined') {
                predictive_issues = parseInt(summary_info.total_low_anomaly_smb_numbers) + parseInt(summary_info.total_high_anomaly_smb_numbers);
                if(predictive_issues > 0) {
                    $("#predictive_issues").removeClass("black_color_font");
                    $("#predictive_issues").addClass("red_color_font");
                    $("#predictive_issues_details").empty();
                    $("#predictive_issues_details").append('<a class="btn btn-danger btn-xs" href="/solar/plant/' + plant_slug + '/ticket_list/" role="button">View Details</a>');
                } else {
                    $("#predictive_issues").removeClass("red_color_font");
                    $("#predictive_issues").addClass("black_color_font");
                    $("#predictive_issues_details").empty();
                }
            } else {
                predictive_issues = "N/A";
                $("#predictive_issues").removeClass("red_color_font");
                $("#predictive_issues").addClass("black_color_font");
                $("#predictive_issues_details").empty();
            }

            $("#predictive_issues").empty();
            $("#predictive_issues").append(predictive_issues);

            if(typeof summary_info.grid_unavailability !== 'undefined') {
                var grid_availability_value = parseFloat(summary_info.grid_unavailability);
                grid_availability_value = 100 - grid_availability_value;

                $("#grid_availability_chart").attr('data-percent', grid_availability_value.toString());
            } else {
                $("#grid_availability_chart").attr('data-percent', "0");
            }

            if(typeof summary_info.equipment_unavailability !== 'undefined') {
                var equipment_availability_value = parseFloat(summary_info.equipment_unavailability)
                equipment_availability_value = 100 - equipment_availability_value;

                $("#equipment_availability_chart").attr('data-percent', equipment_availability_value.toString());
            } else {
                $("#equipment_availability_chart").attr('data-percent', "0");
            }

            var easy_pie_chart_size = "";

            var monitor_height = window.screen.availHeight;
            var monitor_width = window.screen.availWidth;

            if(monitor_width <= 1366) {
                easy_pie_chart_size = 110;
            } else if(monitor_width <= 1440 && monitor_width > 1366) {
                easy_pie_chart_size = 120;
            } else if(monitor_width <= 1600 && monitor_width > 1440) {
                easy_pie_chart_size = 150;
            } else if(monitor_width <= 1680 && monitor_width > 1600) {
                easy_pie_chart_size = 140;
            } else if(monitor_width <= 1920 && monitor_width > 1680) {
                easy_pie_chart_size = 180;
            } else if(monitor_width <= 2048 && monitor_width > 1930) {
                easy_pie_chart_size = 190;
            }

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
                console.log("bottom widget values and easy pie chart: ", new Date() - t4);
            }

            $("#client_spinner").hide();
        },
        error: function(data){
            console.log("no data");

            $("#client_spinner").hide();

            noty_message("No data for today!", 'error', 5000)
            return;
        }
    });

}

$('a[data-toggle="tab"]').on('shown.bs.tab', function (e) {
    
    hide_date(e);    

});

function hide_date(e) {

    var active_tab = $(e.target).attr("href"); // activated tab

    console.log(active_tab);

    if(active_tab != "#plant") {

        $("#datepicker_selected_picker").hide();
        $("#power_irradiation-before").hide();
        $("#power_irradiation-next").hide();

    } else {

        $("#datepicker_selected_picker").show();
        $("#power_irradiation-before").show();
        $("#power_irradiation-next").show();

    }

}

function power_irradiation_chart(st, et) {

    $.ajax({
        type: "GET",
        url: "/api/solar/plants/".concat(plant_slug).concat('/irradiation-power/'),
        data: {startTime: (st), endTime: (et)},
        success: function(power_irradiation) {
            var power_data = [], irradiation_data = [], timestamps = [], inverters_down = [], modbus_error = [], annotation_array = [];

            if(power_irradiation != "") {
                for(var j = 0; j < power_irradiation.length; j++) {
                    power_data.push(power_irradiation[j].power);
                    irradiation_data.push(power_irradiation[j].irradiation);
                    timestamps.push(new Date(power_irradiation[j].timestamp).valueOf());
                }

                var power_max_value = Math.max.apply(null, power_data);
                console.log(power_max_value);

                for(var m = 0; m < power_irradiation.length; m++) {
                    if(m < power_irradiation.length-1) {
                        if(power_irradiation[m].Inverters_down > 0) {
                            annotation_array.push({
                                type: 'box',
                                xScaleID: 'x-axis-0',
                                yScaleID: 'y-axis-1',
                                // Left edge of the box. in units along the x axis
                                xMin: new Date(power_irradiation[m].timestamp).valueOf(),
                                xMax: new Date(power_irradiation[m+1].timestamp).valueOf(),
                                // Right edge of the box
                                // Top edge of the box in units along the y axis
                                yMax: power_max_value * 1.11,

                                // Bottom edge of the box
                                yMin: power_max_value * 1.10,

                                label: "Inverters Down",
                                backgroundColor: 'rgba(101, 33, 171, 0.5)',
                                borderColor: 'rgb(101, 33, 171)',
                                borderWidth: 1,
                                onMouseover: function(e) {
                                    console.log(e);
                                    console.log('Box', e.type, this);

                                    $("#annotation_tooltip").show();

                                    var time = new Date(this._model.ranges["x-axis-0"].min);
                                    time = dateFormat(time, "HH:MM:ss");
                                    $("#annotation_tooltip").empty();
                                    $("#annotation_tooltip").append("Inverters Down at " + time);
                                },
                                onMouseleave: function(e) {
                                    $("#annotation_tooltip").hide();
                                }
                            })
                        }
                        if(power_irradiation[m].modbus_read_error == true) {
                            annotation_array.push({
                                type: 'box',
                                xScaleID: 'x-axis-0',
                                yScaleID: 'y-axis-1',
                                // Left edge of the box. in units along the x axis
                                xMin: new Date(power_irradiation[m].timestamp).valueOf(),
                                xMax: new Date(power_irradiation[m+1].timestamp).valueOf(),
                                // Right edge of the box
                                // Top edge of the box in units along the y axis
                                yMax: power_max_value * 1.13,

                                // Bottom edge of the box
                                yMin: power_max_value * 1.12,

                                backgroundColor: 'red',
                                borderColor: 'green',
                                borderWidth: 1,
                                label: "Read Error",
                                onMouseover: function(e) {
                                    console.log(e);
                                    console.log('Box', e.type, this);

                                    $("#annotation_tooltip").show();
                                    
                                    var time = new Date(this._model.ranges["x-axis-0"].min);
                                    time = dateFormat(time, "HH:MM:ss");
                                    $("#annotation_tooltip").empty();
                                    $("#annotation_tooltip").append("Read Error at " + time);
                                },
                                onMouseleave: function(e) {
                                    $("#annotation_tooltip").hide();
                                }
                            })
                        }
                    }
                }

                power_irradiation_data(power_data, irradiation_data, timestamps, []);
            } else {
                /*$("#no_power_and_irradiation").empty();
                $("#no_power_and_irradiation").append("<div class='alert alert-warning' id='alert'>No data for power and irradiation on this date.</div>");*/

                power_irradiation_data(power_data, irradiation_data, timestamps, []);

                noty_message("No chart data for today!", 'error', 5000)
                return;
            }

        },
        error: function(data) {
            console.log("error_streams_data");
            data = null;

            noty_message("No chart data for today!", 'error', 5000)
            return;
        }
    });

}

function weather_current(latitude, longitude, summary_info, key) {

    var success_code = null;
    if(typeof latitude !== 'undefined' && typeof longitude !== 'undefined') {
        $.ajax({
            type: "GET",
            url: "https://api.worldweatheronline.com/premium/v1/weather.ashx".concat("?key=" + key + "&q=").concat(latitude.concat(",").concat(longitude)).concat("&num_of_day=1").concat("&format=json"),
            success: function(weather_data) {
                $(".canvas_icon").show();
                $("#windspeed_unit").show();
                $("#precipitation_unit").show();
                var temp;
                if(summary_info.ambient_temperature) {
                    temp = parseInt(summary_info.ambient_temperature) + '<span style="font-size: small" id="ac_capacity_unit"> ' + String.fromCharCode(176) + 'C</span>';
                } else {
                    temp = weather_data.data.current_condition[0].FeelsLikeC;
                    temp = Math.round(temp) + '<span style="font-size: small" id="ac_capacity_unit"> ' + String.fromCharCode(176) + 'C</span>';
                }
                $('#temperature').empty();
                $('#temperature').append(temp);
                var wind = "";
                if(plant_slug == "unipatch") {
                    wind = 1;
                } else {
                    if(summary_info.windspeed) {
                        wind = parseInt(summary_info.windspeed)
                    } else {
                        wind = weather_data.data.current_condition[0].windspeedKmph;
                    }
                }
                $('#windspeed').empty();
                $('#windspeed').append(Math.round(wind));
                var clouds_description = weather_data.data.current_condition[0].weatherDesc[0].value;
                $('#weather_status').empty();
                $('#weather_status').text(clouds_description);
                var weather_description_icon = null;
                var time_of_day = new Date(summary_info.updated_at);
                time_of_day = new Date(time_of_day.toString());
                time_of_day = time_of_day.getHours();
                if(clouds_description == "Sunny") {
                    weather_description_icon = "clear_day_status_icon";
                } else if(clouds_description == "Haze") {
                    weather_description_icon = "mist_or_fog_icon";
                } else if(clouds_description == "Mist") {
                    weather_description_icon = "mist_or_fog_icon";
                } else if(clouds_description == "Rain") {
                    weather_description_icon = "rain_icon";
                } else if(clouds_description == "Thunderstorm") {
                    weather_description_icon = "thuderstorm_icon";
                } else if(clouds_description == "Snow") {
                    weather_description_icon = "snow_icon";
                } else if(clouds_description == "Wind") {
                    weather_description_icon = "wind_status_icon";
                } else if(clouds_description == "Clear" && (time_of_day >= 5 && time_of_day < 19)) {
                    weather_description_icon = "clear_day_status_icon";
                } else if(clouds_description == "Clear" && (time_of_day < 5 || time_of_day > 19)) {
                    weather_description_icon = "clear_night_status_icon";
                } else if((clouds_description == "Cloudy" || clouds_description == "Partly cloudy") && (time_of_day >= 5 && time_of_day < 19)) {
                    weather_description_icon = "partly_cloudy_sunny_day_icon";
                } else if((clouds_description == "Cloudy" || clouds_description == "Partly cloudy") && (time_of_day < 5 || time_of_day > 19)) {
                    weather_description_icon = "partly_cloudy_night_icon";
                } else {
                    weather_description_icon = "partly_cloudy_sunny_day_icon";
                }
                console.log("id addition: ", new Date());
                $('#weather_icon').empty();
                $('<canvas/>').attr({id:weather_description_icon, width: '65', height: '65'}).appendTo("#weather_icon");
                var precipitation = weather_data.data.current_condition[0].precipMM;
                $('#precipitation').empty();
                $('#precipitation').append(precipitation);
                set_weather_icon();
                success_code = 200;
            },
            error: function(weather_data){
                console.log("no data");
                success_code = 429;
            }
        });
        return success_code;
    } else {
        $('#no_weather').empty();
        $('#no_weather').append("No weather report.");

        $(".canvas_icon").hide();
        $("#windspeed_unit").hide();
        $("#precipitation_unit").hide();
    }

}

function open_weather(latitude, longitude, summary_info, key) {

    if(typeof latitude !== 'undefined' && typeof longitude !== 'undefined') {
        $.ajax({
            type: "GET",
            url: "https://api.openweathermap.org/data/2.5/weather?lat=".concat(latitude).concat("&lon="+longitude).concat("&APPID="+key),
            success: function(weather_data) {
                console.log(weather_data);
                $(".canvas_icon").show();
                $("#windspeed_unit").show();
                $("#precipitation_unit").show();
                var temp;
                if(summary_info.ambient_temperature) {
                    temp = parseInt(summary_info.ambient_temperature) + '<span style="font-size: small" id="ac_capacity_unit"> ' + String.fromCharCode(176) + 'C</span>';
                } else {
                    temp = weather_data.main.temp-273;
                    temp = Math.round(temp) + '<span style="font-size: small" id="ac_capacity_unit"> ' + String.fromCharCode(176) + 'C</span>';
                }
                $('#temperature').empty();
                $('#temperature').append(temp);
                var wind = "";
                if(plant_slug == "unipatch") {
                    wind = 1;
                } else {
                    if(summary_info.windspeed) {
                        wind = parseInt(summary_info.windspeed)
                    } else {
                        wind = weather_data.wind.speed;
                    }
                }
                $('#windspeed').empty();
                $('#windspeed').append(Math.round(wind));
                var clouds_description = weather_data.weather[0].main;
                $('#weather_status').empty();
                $('#weather_status').text(clouds_description);
                var weather_description_icon = null;
                var time_of_day = new Date(summary_info.updated_at);
                time_of_day = new Date(time_of_day.toString());
                time_of_day = time_of_day.getHours();
                if(clouds_description == "Sunny") {
                    weather_description_icon = "clear_day_status_icon";
                } else if(clouds_description == "Haze") {
                    weather_description_icon = "mist_or_fog_icon";
                } else if(clouds_description == "Mist") {
                    weather_description_icon = "mist_or_fog_icon";
                } else if(clouds_description == "Rain") {
                    weather_description_icon = "rain_icon";
                } else if(clouds_description == "Thunderstorm" || clouds_description == "Rain with thunderstorm" || clouds_description == "Light rain with thunderstorm") {
                    weather_description_icon = "thuderstorm_icon";
                } else if(clouds_description == "Snow") {
                    weather_description_icon = "snow_icon";
                } else if(clouds_description == "Wind") {
                    weather_description_icon = "wind_status_icon";
                } else if(clouds_description == "Clear" && (time_of_day >= 5 && time_of_day < 19)) {
                    weather_description_icon = "clear_day_status_icon";
                } else if(clouds_description == "Clear" && (time_of_day < 5 || time_of_day > 19)) {
                    weather_description_icon = "clear_night_status_icon";
                } else if((clouds_description == "Cloudy" || clouds_description == "Partly classloudy") && (time_of_day >= 5 && time_of_day < 19)) {
                    weather_description_icon = "partly_cloudy_sunny_day_icon";
                } else if((clouds_description == "Cloudy" || clouds_description == "Partly cloudy") && (time_of_day < 5 || time_of_day > 19)) {
                    weather_description_icon = "partly_cloudy_night_icon";
                } else {
                    weather_description_icon = "partly_cloudy_sunny_day_icon";
                }
                console.log("id addition: ", new Date());
                $('#weather_icon').empty();
                $('<canvas/>').attr({id:weather_description_icon, width: '65', height: '65'}).appendTo("#weather_icon");
                var humidity = weather_data.main.humidity
                $("#humidity").empty();
                $("#humidity").append(humidity);
                /*var precipitation = weather_data.rain.3h;
                $('#precipitation').empty();
                $('#precipitation').append(precipitation);*/
                set_weather_icon();
                return 200;
            },
            error: function(weather_data){
                console.log("no data");
                return 400;
            }
        });
    } else {
        $('#no_weather').empty();
        $('#no_weather').append("No weather report.");

        $(".canvas_icon").hide();
        $("#windspeed_unit").hide();
        $("#precipitation_unit").hide();
    }

}

function set_weather_icon(){
    var skycons = new Skycons(
    {
        color : 'white',
        resizeClear : true
    });
    console.log("skycon: ", new Date());
    /* Small Icons*/
    skycons.set("cloudy_status_icon", Skycons.CLOUDY);
    skycons.set("rain_icon", Skycons.RAIN);
    skycons.set("partly_cloudy_sunny_day_icon", Skycons.PARTLY_CLOUDY_DAY);
    skycons.set("mist_or_fog_icon", Skycons.FOG);
    skycons.set("snow_icon", Skycons.SNOW);
    skycons.set("thuderstorm_icon", Skycons.SLEET);
    skycons.set("clear_day_status_icon", Skycons.CLEAR_DAY);
    skycons.set("partly_cloudy_night_icon", Skycons.PARTLY_CLOUDY_NIGHT);
    skycons.set("clear_night_status_icon", Skycons.CLEAR_NIGHT);

    skycons.play();
    var skycons_wind = new Skycons(
    {
        color : 'white',
        resizeClear : true
    });

    skycons_wind.set("wind_status_icon", Skycons.WIND);
    skycons_wind.set("rain_icon", Skycons.RAIN);
    skycons_wind.play();
}
function inverters_status_chart() {

    $.ajax({
        type: "GET",
        url: "/api/solar/plants/".concat(plant_slug).concat('/status/'),
        success: function(data) {

            if(plant_slug == "palladam" || plant_slug == "thuraiyur") {
                return plot_labels_orientation_seven(data, 7);
            } else {
                return plot_labels_orientation(data, 5);
            }
            
        },
        error: function(data) {
            console.log("error_streams_data");
            data = null;
        }
    });
}

function plot_labels_orientation(data, inverter_blocks){
    var list = $('#inverter_status');
    var north_elements = 0, south_elements = 0, east_elements = 0, west_elements = 0, south_west_elements = 0, east_west_elements = 0, row_count = -1, d = 0;
    var north_row_count = 0, south_row_count = 0, east_row_count = 0, west_row_count = 0, south_west_row_count = 0, east_west_row_count = 0;
    var d_north = 0, d_south = 0, d_east = 0, d_west = 0, d_south_west = 0, d_east_west = 0;
    list.innerHTML = "";
    list.empty();
    var north = $("<div class='row' id='north' style='margin-top: 20px;' disabled><div class='row' style='text-align: center;'><strong style='font-size:20px;font-weight:900;'>NORTH</strong></div></div>");
    var south = $("<div class='row' id='south' style='margin-top: 20px;' disabled><div class='row' style='text-align: center;'><strong style='font-size:20px;font-weight:900;'>SOUTH</strong></div></div>");
    var east = $("<div class='row' id='east' style='margin-top: 20px;' disabled><div class='row' style='text-align: center;'><strong style='font-size:20px;font-weight:900;'>EAST</strong></div></div>");
    var west = $("<div class='row' id='west' style='margin-top: 20px;' disabled><div class='row' style='text-align: center;'><strong style='font-size:20px;font-weight:900;'>WEST</strong></div></div>");
    var south_west = $("<div class='row' id='south_west' style='margin-top: 20px;' disabled><div class='row' style='text-align: center;'><strong style='font-size:20px;font-weight:900;'>SOUTH WEST</strong></div></div>");
    var east_west = $("<div class='row' id='east_west' style='margin-top: 20px;' disabled><div class='row' style='text-align: center;'><strong style='font-size:20px;font-weight:900;'>EAST WEST</strong></div></div>");
    list.append(north);
    list.append(south);
    list.append(east);
    list.append(west);
    list.append(south_west);
    list.append(east_west);
    for(var i = 0; i < data.inverters.length; i++) {
        if(data.inverters[i].orientation == 'NORTH') {
            if(north_elements % inverter_blocks == 0) {
                north_row_count++;
                $("#north").append('<div class="row" id="north-row'+north_row_count+'"></div>');
                d_north = 0;
            }
            var generation = data.inverters[i].generation;
            var current_power = data.inverters[i].power;
            if (data.inverters[i].connected == "connected") {
                if(current_power == 0) {
                    var success = $('<div class="col-lg-2 pad-all" id="div'+d_north+'" style="text-align:center;"> ' +
                    '<div class="row"> ' + '<div class="col-lg-1"></div>' + '<strong>' + data.inverters[i].name + '</strong>' + ' </div> ' +
                    '<button class="btn btn-lg mar-lft" inverter_name="'+data.inverters[i].name+'" inverter_connected="'+data.inverters[i].connected+'" inverter_orientation="'+data.inverters[i].orientation+'" inverter_capacity="'+data.inverters[i].capacity+'" inverter_power="'+data.inverters[i].power+'" inverter_generation="'+data.inverters[i].generation+'" id="inverter_button_value_'+i+'" style="width: 150px; background-color:#f3f307;">' + generation.toFixed(2) +
                    ' kWh </button>' + '<div class="row"> ' + '<div class="col-lg-1"></div>' + '<strong>' + current_power.toFixed(2) + ' kW</strong>' + ' </div> ' + '</div>');
                } else {
                    var success = $('<div class="col-lg-2 pad-all" id="div'+d_north+'" style="text-align:center;"> ' +
                    '<div class="row"> ' + '<div class="col-lg-1"></div>' + '<strong>' + data.inverters[i].name + '</strong>' + ' </div> ' +
                    '<button class="btn btn-lg btn-success mar-lft" inverter_name="'+data.inverters[i].name+'" inverter_connected="'+data.inverters[i].connected+'" inverter_orientation="'+data.inverters[i].orientation+'" inverter_capacity="'+data.inverters[i].capacity+'" inverter_power="'+data.inverters[i].power+'" inverter_generation="'+data.inverters[i].generation+'" id="inverter_button_value_'+i+'" style="width: 150px;">' + generation.toFixed(2) +
                    ' kWh </button>' + '<div class="row"> ' + '<div class="col-lg-1"></div>' + '<strong>' + current_power.toFixed(2) + ' kW</strong>' + ' </div> ' + '</div>');
                }
                $("#north-row"+north_row_count).append(success);
            } else if (data.inverters[i].connected == "disconnected") {
                var success = $('<div class="col-lg-2 pad-all" id="div'+d_north+'" style="text-align:center;"> ' +
                    '<div class="row"> ' + '<div class="col-lg-1"></div>' + '<strong>' + data.inverters[i].name + '</strong>' + ' </div> ' +
                    '<button class="btn btn-lg btn-danger mar-lft" inverter_name="'+data.inverters[i].name+'" inverter_connected="'+data.inverters[i].connected+'" inverter_orientation="'+data.inverters[i].orientation+'" inverter_capacity="'+data.inverters[i].capacity+'" inverter_power="'+data.inverters[i].power+'" inverter_generation="'+data.inverters[i].generation+'" id="inverter_button_value_'+i+'" style="width: 150px;">' + generation.toFixed(2) +
                    ' kWh </button>' + '<div class="row"> ' + '<div class="col-lg-1"></div>' + '<strong>' + current_power.toFixed(2) + ' kW</strong>' + ' </div> ' + '</div>');
                $("#north-row"+north_row_count).append(success);
            }
            else {
                var label = $('<div class="col-lg-2 pad-all" id="div'+d_north+'" style="text-align:center;"> ' +
                    '<div class="row"> ' + '<div class="col-lg-1"></div>' + '<strong>' + data.inverters[i].name + '</strong>' + ' </div> ' +
                    '<button class="btn btn-lg btn-info mar-lft" inverter_name="'+data.inverters[i].name+'" inverter_connected="'+data.inverters[i].connected+'" inverter_orientation="'+data.inverters[i].orientation+'" inverter_capacity="'+data.inverters[i].capacity+'" inverter_power="'+data.inverters[i].power+'" inverter_generation="'+data.inverters[i].generation+'"  id="inverter_button_value_'+i+'" style="width: 150px;">' + generation.toFixed(2) +
                    ' kWh </button>' + '<div class="row"> ' + '<div class="col-lg-1"></div>' + '<strong>' + current_power.toFixed(2) + ' kW</strong>' + ' </div> ' + ' </div>');
                $("#north-row"+north_row_count).append(label);
            }
            north_elements++;
            d_north++;
        } else if(data.inverters[i].orientation == 'SOUTH') {
            if(south_elements % inverter_blocks == 0) {
                south_row_count++;
                $("#south").append('<div class="row" id="south-row'+south_row_count+'"></div>');
                d_south = 0;
            }
            var generation = data.inverters[i].generation;
            var current_power = data.inverters[i].power;
            if (data.inverters[i].connected == "connected") {
                if(current_power == 0) {
                    var success = $('<div class="col-lg-2 pad-all" id="div'+d_south+'" style="text-align:center;"> ' +
                    '<div class="row"> ' + '<div class="col-lg-1"></div>' + '<strong>' + data.inverters[i].name + '</strong>' + ' </div> ' +
                    '<button class="btn btn-lg mar-lft" inverter_name="'+data.inverters[i].name+'" inverter_connected="'+data.inverters[i].connected+'" inverter_orientation="'+data.inverters[i].orientation+'" inverter_capacity="'+data.inverters[i].capacity+'" inverter_power="'+data.inverters[i].power+'" inverter_generation="'+data.inverters[i].generation+'" id="inverter_button_value_'+i+'" style="width: 150px; background-color:#f3f307;">' + generation.toFixed(2) +
                    ' kWh </button>' + '<div class="row"> ' + '<div class="col-lg-1"></div>' + '<strong>' + current_power.toFixed(2) + ' kW</strong>' + ' </div> ' + '</div>');
                } else {
                    var success = $('<div class="col-lg-2 pad-all" id="div'+d_south+'" style="text-align:center;"> ' +
                    '<div class="row"> ' + '<div class="col-lg-1"></div>' + '<strong>' + data.inverters[i].name + '</strong>' + ' </div> ' +
                    '<button class="btn btn-lg btn-success mar-lft" inverter_name="'+data.inverters[i].name+'" inverter_connected="'+data.inverters[i].connected+'" inverter_orientation="'+data.inverters[i].orientation+'" inverter_capacity="'+data.inverters[i].capacity+'" inverter_power="'+data.inverters[i].power+'" inverter_generation="'+data.inverters[i].generation+'" id="inverter_button_value_'+i+'" style="width: 150px;">'+ generation.toFixed(2) +
                    ' kWh </button>' + '<div class="row"> ' + '<div class="col-lg-1"></div>' + '<strong>' + current_power.toFixed(2) + ' kW</strong>' + ' </div> ' + '</div>');
                }
                $("#south-row"+south_row_count).append(success);
            } else if (data.inverters[i].connected == "disconnected") {
                var success = $('<div class="col-lg-2 pad-all" id="div'+d_south+'" style="text-align:center;"> ' +
                    '<div class="row"> ' + '<div class="col-lg-1"></div>' + '<strong>' + data.inverters[i].name + '</strong>' + ' </div> ' +
                    '<button class="btn btn-lg btn-danger mar-lft" inverter_name="'+data.inverters[i].name+'" inverter_connected="'+data.inverters[i].connected+'" inverter_orientation="'+data.inverters[i].orientation+'" inverter_capacity="'+data.inverters[i].capacity+'" inverter_power="'+data.inverters[i].power+'" inverter_generation="'+data.inverters[i].generation+'" id="inverter_button_value_'+i+'" style="width: 150px;">'+ generation.toFixed(2) +
                    ' kWh </button>' + '<div class="row"> ' + '<div class="col-lg-1"></div>' + '<strong>' + current_power.toFixed(2) + ' kW</strong>' + ' </div> ' + '</div>');
                $("#south-row"+south_row_count).append(success);
            }
            else {
                var label = $('<div class="col-lg-2 pad-all" id="div'+d_south+'" style="text-align:center;"> ' +
                    '<div class="row"> ' + '<div class="col-lg-1"></div>' + '<strong>' + data.inverters[i].name + '</strong>' + ' </div> ' +
                    '<button class="btn btn-lg btn-info mar-lft" inverter_name="'+data.inverters[i].name+'" inverter_connected="'+data.inverters[i].connected+'" inverter_orientation="'+data.inverters[i].orientation+'" inverter_capacity="'+data.inverters[i].capacity+'" inverter_power="'+data.inverters[i].power+'" inverter_generation="'+data.inverters[i].generation+'" id="inverter_button_value_'+i+'" style="width: 150px;">' + generation.toFixed(2) +
                    ' kWh </button>' + '<div class="row"> ' + '<div class="col-lg-1"></div>' + '<strong> ' + current_power.toFixed(2) + ' kW</strong>' + ' </div> ' + '</div>');
                $("#south-row"+south_row_count).append(label);
            }
            south_elements++;
            d_south++;
        } else if(data.inverters[i].orientation == 'EAST') {
            if(east_elements % inverter_blocks == 0) {
                east_row_count++;
                $("#east").append('<div class="row" id="east_row'+east_row_count+'"></div>');
                d_east = 0;
            }
            var generation = data.inverters[i].generation;
            var current_power = data.inverters[i].power;
            if (data.inverters[i].connected == "connected") {
                if(current_power == 0) {
                    var success = $('<div class="col-lg-2 pad-all" id="div'+d_east+'" style="text-align:center;"> ' +
                    '<div class="row"> ' + '<div class="col-lg-1"></div>' + '<strong>' + data.inverters[i].name + '</strong>' + ' </div> ' +
                    '<button class="btn btn-lg mar-lft" inverter_name="'+data.inverters[i].name+'" inverter_connected="'+data.inverters[i].connected+'" inverter_orientation="'+data.inverters[i].orientation+'" inverter_capacity="'+data.inverters[i].capacity+'" inverter_power="'+data.inverters[i].power+'" inverter_generation="'+data.inverters[i].generation+'" id="inverter_button_value_'+i+'" style="width: 150px; background-color:#f3f307;">'+ generation.toFixed(2) +
                    ' kWh </button>' + '<div class="row"> ' + '<div class="col-lg-1"></div>' + '<strong>' + current_power.toFixed(2) + ' kW</strong>' + ' </div> ' + '</div>');
                } else {
                    var success = $('<div class="col-lg-2 pad-all" id="div'+d_east+'" style="text-align:center;"> ' +
                    '<div class="row"> ' + '<div class="col-lg-1"></div>' + '<strong>' + data.inverters[i].name + '</strong>' + ' </div> ' +
                    '<button class="btn btn-lg btn-success mar-lft" inverter_name="'+data.inverters[i].name+'" inverter_connected="'+data.inverters[i].connected+'" inverter_orientation="'+data.inverters[i].orientation+'" inverter_capacity="'+data.inverters[i].capacity+'" inverter_power="'+data.inverters[i].power+'" inverter_generation="'+data.inverters[i].generation+'" id="inverter_button_value_'+i+'" style="width: 150px;">'+ generation.toFixed(2) +
                    ' kWh </button>' + '<div class="row"> ' + '<div class="col-lg-1"></div>' + '<strong>' + current_power.toFixed(2) + ' kW</strong>' + ' </div> ' + '</div>');
                }
                $("#east_row"+east_row_count).append(success);
            } else if (data.inverters[i].connected == "disconnected") {
                var success = $('<div class="col-lg-2 pad-all" id="div'+d_east+'" style="text-align:center;"> ' +
                    '<div class="row"> ' + '<div class="col-lg-1"></div>' + '<strong>' + data.inverters[i].name + '</strong>' + ' </div> ' +
                    '<button class="btn btn-lg btn-danger mar-lft" inverter_name="'+data.inverters[i].name+'" inverter_connected="'+data.inverters[i].connected+'" inverter_orientation="'+data.inverters[i].orientation+'" inverter_capacity="'+data.inverters[i].capacity+'" inverter_power="'+data.inverters[i].power+'" inverter_generation="'+data.inverters[i].generation+'" id="inverter_button_value_'+i+'" style="width: 150px;">'+ generation.toFixed(2) +
                    ' kWh </button>' + '<div class="row"> ' + '<div class="col-lg-1"></div>' + '<strong>' + current_power.toFixed(2) + ' kW</strong>' + ' </div> ' + '</div>');
                $("#east_row"+east_row_count).append(success);
            }
            else {
                var label = $('<div class="col-lg-2 pad-all" id="div'+d_east+'" style="text-align:center;"> ' +
                    '<div class="row"> ' + '<div class="col-lg-1"></div>' + '<strong>' + data.inverters[i].name + '</strong>' + ' </div> ' +
                    '<button class="btn btn-lg btn-info mar-lft" inverter_name="'+data.inverters[i].name+'" inverter_connected="'+data.inverters[i].connected+'" inverter_orientation="'+data.inverters[i].orientation+'" inverter_capacity="'+data.inverters[i].capacity+'" inverter_power="'+data.inverters[i].power+'" inverter_generation="'+data.inverters[i].generation+'" id="inverter_button_value_'+i+'" style="width: 150px;">' + generation.toFixed(2) +
                    ' kWh </button>' + '<div class="row"> ' + '<div class="col-lg-1"></div>' + '<strong>' + current_power.toFixed(2) + ' kW</strong>' + ' </div> ' + '</div>');
                $("#east_row"+east_row_count).append(label);
            }
            east_elements++;
            d_east++;
        } else if(data.inverters[i].orientation == 'WEST') {
            if(west_elements % inverter_blocks == 0) {
                west_row_count++;
                $("#west").append('<div class="row" id="west_row'+west_row_count+'"></div>');
                d_west = 0;
            }
            var generation = data.inverters[i].generation;
            var current_power = data.inverters[i].power;
            if (data.inverters[i].connected == "connected") {
                if(current_power == 0) {
                    var success = $('<div class="col-lg-2 pad-all" id="div'+d_west+'" style="text-align:center;"> ' +
                    '<div class="row"> ' + '<div class="col-lg-1"></div>' + '<strong>' + data.inverters[i].name + '</strong>' + ' </div> ' +
                    '<button class="btn btn-lg mar-lft" inverter_name="'+data.inverters[i].name+'" inverter_connected="'+data.inverters[i].connected+'" inverter_orientation="'+data.inverters[i].orientation+'" inverter_capacity="'+data.inverters[i].capacity+'" inverter_power="'+data.inverters[i].power+'" inverter_generation="'+data.inverters[i].generation+'" id="inverter_button_value_'+i+'" style="width: 150px; background-color:#f3f307;">'+ generation.toFixed(2) +
                    ' kWh </button>' + '<div class="row"> ' + '<div class="col-lg-1"></div>' + '<strong>' + current_power.toFixed(2) + ' kW</strong>' + ' </div> ' + '</div>');
                } else {
                    var success = $('<div class="col-lg-2 pad-all" id="div'+d_west+'" style="text-align:center;"> ' +
                    '<div class="row"> ' + '<div class="col-lg-1"></div>' + '<strong>' + data.inverters[i].name + '</strong>' + ' </div> ' +
                    '<button class="btn btn-lg btn-success mar-lft" inverter_name="'+data.inverters[i].name+'" inverter_connected="'+data.inverters[i].connected+'" inverter_orientation="'+data.inverters[i].orientation+'" inverter_capacity="'+data.inverters[i].capacity+'" inverter_power="'+data.inverters[i].power+'" inverter_generation="'+data.inverters[i].generation+'" id="inverter_button_value_'+i+'" style="width: 150px;">'+ generation.toFixed(2) +
                    ' kWh </button>' + '<div class="row"> ' + '<div class="col-lg-1"></div>' + '<strong>' + current_power.toFixed(2) + ' kW</strong>' + ' </div> ' + '</div>');
                }
                $("#west_row"+west_row_count).append(success);
            } else if (data.inverters[i].connected == "disconnected") {
                var success = $('<div class="col-lg-2 pad-all" id="div'+d_west+'" style="text-align:center;"> ' +
                    '<div class="row"> ' + '<div class="col-lg-1"></div>' + '<strong>' + data.inverters[i].name + '</strong>' + ' </div> ' +
                    '<button class="btn btn-lg btn-danger mar-lft" inverter_name="'+data.inverters[i].name+'" inverter_connected="'+data.inverters[i].connected+'" inverter_orientation="'+data.inverters[i].orientation+'" inverter_capacity="'+data.inverters[i].capacity+'" inverter_power="'+data.inverters[i].power+'" inverter_generation="'+data.inverters[i].generation+'" id="inverter_button_value_'+i+'" style="width: 150px;">'+ generation.toFixed(2) +
                    ' kWh </button>' + '<div class="row"> ' + '<div class="col-lg-1"></div>' + '<strong> ' + current_power.toFixed(2) + ' kW</strong>' + ' </div> ' + '</div>');
                $("#west_row"+west_row_count).append(success);
            }
            else {
                var label = $('<div class="col-lg-2 pad-all" id="div'+d_west+'" style="text-align:center;"> ' +
                    '<div class="row"> ' + '<div class="col-lg-1"></div>' + '<strong>' + data.inverters[i].name + '</strong>' + ' </div> ' +
                    '<button class="btn btn-lg btn-info mar-lft" inverter_name="'+data.inverters[i].name+'" inverter_connected="'+data.inverters[i].connected+'" inverter_orientation="'+data.inverters[i].orientation+'" inverter_capacity="'+data.inverters[i].capacity+'" inverter_power="'+data.inverters[i].power+'" inverter_generation="'+data.inverters[i].generation+'" id="inverter_button_value_'+i+'" style="width: 150px;">' + generation.toFixed(2) +
                    ' kWh </button>' + '<div class="row"> ' + '<div class="col-lg-1"></div>' + '<strong>' + current_power.toFixed(2) + ' kW</strong>' + ' </div> ' + '</div>');
                $("#west_row"+west_row_count).append(label);
            }
            west_elements++;
            d_west++;
        } else if(data.inverters[i].orientation == 'SOUTH-WEST') {
            if(south_west_elements % inverter_blocks == 0) {
                south_west_row_count++;
                $("#south_west").append('<div class="row" id="south_west_row'+south_west_row_count+'"></div>');
                d_south_west = 0;
            }
            var generation = data.inverters[i].generation;
            var current_power = data.inverters[i].power;
            if (data.inverters[i].connected == "connected") {
                if(current_power == 0) {
                    var success = $('<div class="col-lg-2 pad-all" id="div'+d_south_west+'" style="text-align:center;"> ' +
                    '<div class="row"> ' + '<div class="col-lg-1"></div>' + '<strong>' + data.inverters[i].name + '</strong>' + ' </div> ' +
                    '<button class="btn btn-lg mar-lft" inverter_name="'+data.inverters[i].name+'" inverter_connected="'+data.inverters[i].connected+'" inverter_orientation="'+data.inverters[i].orientation+'" inverter_capacity="'+data.inverters[i].capacity+'" inverter_power="'+data.inverters[i].power+'" inverter_generation="'+data.inverters[i].generation+'" id="inverter_button_value_'+i+'" style="width: 150px; background-color:#f3f307;">'+ generation.toFixed(2) +
                    ' kWh </button>' + '<div class="row"> ' + '<div class="col-lg-1"></div>' + '<strong>' + current_power.toFixed(2) + ' kW</strong>' + ' </div> ' + '</div>');
                } else {
                    var success = $('<div class="col-lg-2 pad-all" id="div'+d_south_west+'" style="text-align:center;"> ' +
                    '<div class="row"> ' + '<div class="col-lg-1"></div>' + '<strong>' + data.inverters[i].name + '</strong>' + ' </div> ' +
                    '<button class="btn btn-lg btn-success mar-lft" inverter_name="'+data.inverters[i].name+'" inverter_connected="'+data.inverters[i].connected+'" inverter_orientation="'+data.inverters[i].orientation+'" inverter_capacity="'+data.inverters[i].capacity+'" inverter_power="'+data.inverters[i].power+'" inverter_generation="'+data.inverters[i].generation+'" id="inverter_button_value_'+i+'" style="width: 150px;">'+ generation.toFixed(2) +
                    ' kWh </button>' + '<div class="row"> ' + '<div class="col-lg-1"></div>' + '<strong>' + current_power.toFixed(2) + ' kW</strong>' + ' </div> ' + '</div>');
                }
                $("#south_west_row"+south_west_row_count).append(success);
            } else if (data.inverters[i].connected == "disconnected") {
                var success = $('<div class="col-lg-2 pad-all" id="div'+d_south_west+'" style="text-align:center;"> ' +
                    '<div class="row"> ' + '<div class="col-lg-1"></div>' + '<strong>' + data.inverters[i].name + '</strong>' + ' </div> ' +
                    '<button class="btn btn-lg btn-danger mar-lft" inverter_name="'+data.inverters[i].name+'" inverter_connected="'+data.inverters[i].connected+'" inverter_orientation="'+data.inverters[i].orientation+'" inverter_capacity="'+data.inverters[i].capacity+'" inverter_power="'+data.inverters[i].power+'" inverter_generation="'+data.inverters[i].generation+'" id="inverter_button_value_'+i+'" style="width: 150px;">'+ generation.toFixed(2) +
                    ' kWh </button>' + '<div class="row"> ' + '<div class="col-lg-1"></div>' + '<strong> ' + current_power.toFixed(2) + ' kW</strong>' + ' </div> ' + '</div>');
                $("#south_west_row"+south_west_row_count).append(success);
            }
            else {
                var label = $('<div class="col-lg-2 pad-all" id="div'+d_south_west+'" style="text-align:center;"> ' +
                    '<div class="row"> ' + '<div class="col-lg-1"></div>' + '<strong>' + data.inverters[i].name + '</strong>' + ' </div> ' +
                    '<button class="btn btn-lg btn-info mar-lft" inverter_name="'+data.inverters[i].name+'" inverter_connected="'+data.inverters[i].connected+'" inverter_orientation="'+data.inverters[i].orientation+'" inverter_capacity="'+data.inverters[i].capacity+'" inverter_power="'+data.inverters[i].power+'" inverter_generation="'+data.inverters[i].generation+'" id="inverter_button_value_'+i+'" style="width: 150px;">' + generation.toFixed(2) +
                    ' kWh </button>' + '<div class="row"> ' + '<div class="col-lg-1"></div>' + '<strong>' + current_power.toFixed(2) + ' kW</strong>' + ' </div> ' + '</div>');
                $("#south_west_row"+south_west_row_count).append(label);
            }
            south_west_elements++;
            d_south_west++;
        } else if(data.inverters[i].orientation == 'EAST-WEST') {
            if(east_west_elements % inverter_blocks == 0) {
                east_west_row_count++;
                $("#east_west").append('<div class="row" id="east_west_row'+east_west_row_count+'"></div>');
                d_east_west = 0;
            }
            var generation = data.inverters[i].generation;
            var current_power = data.inverters[i].power;
            if (data.inverters[i].connected == "connected") {
                if(current_power == 0) {
                    var success = $('<div class="col-lg-2 pad-all" id="div'+d_east_west+'" style="text-align:center;"> ' +
                    '<div class="row"> ' + '<div class="col-lg-1"></div>' + '<strong>' + data.inverters[i].name + '</strong>' + ' </div> ' +
                    '<button class="btn btn-lg mar-lft" inverter_name="'+data.inverters[i].name+'" inverter_connected="'+data.inverters[i].connected+'" inverter_orientation="'+data.inverters[i].orientation+'" inverter_capacity="'+data.inverters[i].capacity+'" inverter_power="'+data.inverters[i].power+'" inverter_generation="'+data.inverters[i].generation+'" id="inverter_button_value_'+i+'" style="width: 150px; background-color:#f3f307;">'+ generation.toFixed(2) +
                    ' kWh </button>' + '<div class="row"> ' + '<div class="col-lg-1"></div>' + '<strong>' + current_power.toFixed(2) + ' kW</strong>' + ' </div> ' + '</div>');
                } else {
                    var success = $('<div class="col-lg-2 pad-all" id="div'+d_east_west+'" style="text-align:center;"> ' +
                    '<div class="row"> ' + '<div class="col-lg-1"></div>' + '<strong>' + data.inverters[i].name + '</strong>' + ' </div> ' +
                    '<button class="btn btn-lg btn-success mar-lft" inverter_name="'+data.inverters[i].name+'" inverter_connected="'+data.inverters[i].connected+'" inverter_orientation="'+data.inverters[i].orientation+'" inverter_capacity="'+data.inverters[i].capacity+'" inverter_power="'+data.inverters[i].power+'" inverter_generation="'+data.inverters[i].generation+'" id="inverter_button_value_'+i+'" style="width: 150px;">'+ generation.toFixed(2) +
                    ' kWh </button>' + '<div class="row"> ' + '<div class="col-lg-1"></div>' + '<strong>' + current_power.toFixed(2) + ' kW</strong>' + ' </div> ' + '</div>');
                }
                $("#east_west_row"+east_west_row_count).append(success);
            } else if (data.inverters[i].connected == "disconnected") {
                var success = $('<div class="col-lg-2 pad-all" id="div'+d_east_west+'" style="text-align:center;"> ' +
                    '<div class="row"> ' + '<div class="col-lg-1"></div>' + '<strong>' + data.inverters[i].name + '</strong>' + ' </div> ' +
                    '<button class="btn btn-lg btn-danger mar-lft" inverter_name="'+data.inverters[i].name+'" inverter_connected="'+data.inverters[i].connected+'" inverter_orientation="'+data.inverters[i].orientation+'" inverter_capacity="'+data.inverters[i].capacity+'" inverter_power="'+data.inverters[i].power+'" inverter_generation="'+data.inverters[i].generation+'" id="inverter_button_value_'+i+'" style="width: 150px;">'+ generation.toFixed(2) +
                    ' kWh </button>' + '<div class="row"> ' + '<div class="col-lg-1"></div>' + '<strong> ' + current_power.toFixed(2) + ' kW</strong>' + ' </div> ' + '</div>');
                $("#east_west_row"+east_west_row_count).append(success);
            }
            else {
                var label = $('<div class="col-lg-2 pad-all" id="div'+d_east_west+'" style="text-align:center;"> ' +
                    '<div class="row"> ' + '<div class="col-lg-1"></div>' + '<strong>' + data.inverters[i].name + '</strong>' + ' </div> ' +
                    '<button class="btn btn-lg btn-info mar-lft" inverter_name="'+data.inverters[i].name+'" inverter_connected="'+data.inverters[i].connected+'" inverter_orientation="'+data.inverters[i].orientation+'" inverter_capacity="'+data.inverters[i].capacity+'" inverter_power="'+data.inverters[i].power+'" inverter_generation="'+data.inverters[i].generation+'" id="inverter_button_value_'+i+'" style="width: 150px;">' + generation.toFixed(2) +
                    ' kWh </button>' + '<div class="row"> ' + '<div class="col-lg-1"></div>' + '<strong>' + current_power.toFixed(2) + ' kW</strong>' + ' </div> ' + '</div>');
                $("#east_west_row"+east_west_row_count).append(label);
            }
            east_west_elements++;
            d_east_west++;
        }
        $("#inverter_button_value_"+i).click(function() {

            var inverter_name = $(this).attr('inverter_name');
            var inverter_connected = $(this).attr('inverter_connected');
            var inverter_orientation = $(this).attr('inverter_orientation');
            var inverter_capacity = $(this).attr('inverter_capacity');
            var inverter_power = $(this).attr('inverter_power');
            var inverter_generation = $(this).attr('inverter_generation');

            $("#inverter_name").empty();
            $("#inverter_name").append(inverter_name);

            $("#status_name").empty();
            $("#status_name").append("<div class='text-semibold'>Inverter Name : " + inverter_name + "</div>");
            $("#status_connected").empty();
            $("#status_connected").append("<div class='text-semibold'>Connection Status : " + inverter_connected + "</div>");
            $("#status_orientation").empty();
            $("#status_orientation").append("<div class='text-semibold'>Inverter Orientation : " + inverter_orientation + "</div>");
            $("#status_capacity").empty();
            $("#status_capacity").append("<div class='text-semibold'>Inverter Capacity : " + inverter_capacity + " kW</div>");
            $("#status_power").empty();
            $("#status_power").append("<div class='text-semibold'>Current Power : " + inverter_power + " kW</div>");
            $("#status_generation").empty();
            $("#status_generation").append("<div class='text-semibold'>Current Generation : " + inverter_generation + " kWh</div>");

            $(".inverter_modal").modal('show');

        });
    }
    /*for (var datapoint in data.inverters) {
        var inverter_name = datapoint.name;
        if (data.inverters.hasOwnProperty(inverter_name)) {

        }
    }*/
    if(north_row_count == 0) {
        $("#north").remove();
    } else {
        for(var j = 0; j <=north_row_count; j++) {
            $("#north-row"+j+" div:first").addClass("col-lg-offset-1");
        }
    }
    if(south_row_count == 0) {
        $("#south").remove();
    } else {
        for(var j = 0; j <=south_row_count; j++) {
            $("#south-row"+j+" div:first").addClass("col-lg-offset-1");
        }
    }
    if(east_row_count == 0) {
        $("#east").remove();
    } else {
        for(var j = 0; j <=east_row_count; j++) {
            $("#east_row"+j+" div:first").addClass("col-lg-offset-1");
        }
    }
    if(west_row_count == 0) {
        $("#west").remove();
    } else {
        for(var j = 0; j <=west_row_count; j++) {
            $("#west_row"+j+" div:first").addClass("col-lg-offset-1");
        }
    }
    if(south_west_row_count == 0) {
        $("#south_west").remove();
    } else {
        for(var j = 0; j <=south_west_row_count; j++) {
            $("#south_west_row"+j+" div:first").addClass("col-lg-offset-1");
        }
    }
    if(east_west_row_count == 0) {
        $("#east_west").remove();
    } else {
        for(var j = 0; j <=east_west_row_count; j++) {
            $("#east_west_row"+j+" div:first").addClass("col-lg-offset-1");
        }
    }

    return plot_labels_groups(data);

}

function plot_labels_orientation_seven(data, inverter_blocks){
    var list = $('#inverter_status');
    var north_elements = 0, south_elements = 0, east_elements = 0, west_elements = 0, south_west_elements = 0, east_west_elements = 0, row_count = -1, d = 0;
    var north_row_count = 0, south_row_count = 0, east_row_count = 0, west_row_count = 0, south_west_row_count = 0, east_west_row_count = 0;
    var d_north = 0, d_south = 0, d_east = 0, d_west = 0, d_south_west = 0, d_east_west = 0;
    list.innerHTML = "";
    list.empty();
    var north = $("<div class='row' id='north' style='margin-top: 20px;' disabled><div class='row' style='text-align: center;'><strong style='font-size:20px;font-weight:900;'>NORTH</strong></div></div>");
    var south = $("<div class='row' id='south' style='margin-top: 20px;' disabled><div class='row' style='text-align: center;'><strong style='font-size:20px;font-weight:900;'>SOUTH</strong></div></div>");
    var east = $("<div class='row' id='east' style='margin-top: 20px;' disabled><div class='row' style='text-align: center;'><strong style='font-size:20px;font-weight:900;'>EAST</strong></div></div>");
    var west = $("<div class='row' id='west' style='margin-top: 20px;' disabled><div class='row' style='text-align: center;'><strong style='font-size:20px;font-weight:900;'>WEST</strong></div></div>");
    var south_west = $("<div class='row' id='south_west' style='margin-top: 20px;' disabled><div class='row' style='text-align: center;'><strong style='font-size:20px;font-weight:900;'>SOUTH WEST</strong></div></div>");
    var east_west = $("<div class='row' id='east_west' style='margin-top: 20px;' disabled><div class='row' style='text-align: center;'><strong style='font-size:20px;font-weight:900;'>EAST WEST</strong></div></div>");
    list.append(north);
    list.append(south);
    list.append(east);
    list.append(west);
    list.append(south_west);
    list.append(east_west);
    for(var i = 0; i < data.inverters.length; i++) {
        if(data.inverters[i].orientation == 'NORTH') {
            if(north_elements % inverter_blocks == 0) {
                north_row_count++;
                $("#north").append('<div class="row seven-cols" id="north-row'+north_row_count+'"></div>');
                d_north = 0;
            }
            var generation = data.inverters[i].generation;
            var current_power = data.inverters[i].power;
            if (data.inverters[i].connected == "connected") {
                if(current_power == 0) {
                    var success = $('<div class="col-lg-1 mar-top mar-btm" id="div'+d_north+'" style="text-align:center; padding-left:0px; padding-right:0px;"> ' +
                    '<div class="row"> ' + '<div class="col-lg-1"></div>' + '<strong>' + data.inverters[i].name + '</strong>' + ' </div> ' +
                    '<button class="btn btn-lg mar-lft" inverter_name="'+data.inverters[i].name+'" inverter_connected="'+data.inverters[i].connected+'" inverter_orientation="'+data.inverters[i].orientation+'" inverter_capacity="'+data.inverters[i].capacity+'" inverter_power="'+data.inverters[i].power+'" inverter_generation="'+data.inverters[i].generation+'" id="inverter_button_value_'+i+'" style="background-color:#f3f307;">' + generation.toFixed(2) +
                    ' kWh </button>' + '<div class="row"> ' + '<div class="col-lg-1"></div>' + '<strong>' + current_power.toFixed(2) + ' kW</strong>' + ' </div> ' + '</div>');
                } else {
                    var success = $('<div class="col-lg-1 mar-top mar-btm" id="div'+d_north+'" style="text-align:center; padding-left:0px; padding-right:0px;"> ' +
                    '<div class="row"> ' + '<div class="col-lg-1"></div>' + '<strong>' + data.inverters[i].name + '</strong>' + ' </div> ' +
                    '<button class="btn btn-lg btn-success mar-lft" inverter_name="'+data.inverters[i].name+'" inverter_connected="'+data.inverters[i].connected+'" inverter_orientation="'+data.inverters[i].orientation+'" inverter_capacity="'+data.inverters[i].capacity+'" inverter_power="'+data.inverters[i].power+'" inverter_generation="'+data.inverters[i].generation+'" id="inverter_button_value_'+i+'">' + generation.toFixed(2) +
                    ' kWh </button>' + '<div class="row"> ' + '<div class="col-lg-1"></div>' + '<strong>' + current_power.toFixed(2) + ' kW</strong>' + ' </div> ' + '</div>');
                }
                $("#north-row"+north_row_count).append(success);
            } else if (data.inverters[i].connected == "disconnected") {
                var success = $('<div class="col-lg-1 mar-top mar-btm" id="div'+d_north+'" style="text-align:center; padding-left:0px; padding-right:0px;"> ' +
                    '<div class="row"> ' + '<div class="col-lg-1"></div>' + '<strong>' + data.inverters[i].name + '</strong>' + ' </div> ' +
                    '<button class="btn btn-lg btn-danger mar-lft" inverter_name="'+data.inverters[i].name+'" inverter_connected="'+data.inverters[i].connected+'" inverter_orientation="'+data.inverters[i].orientation+'" inverter_capacity="'+data.inverters[i].capacity+'" inverter_power="'+data.inverters[i].power+'" inverter_generation="'+data.inverters[i].generation+'" id="inverter_button_value_'+i+'">' + generation.toFixed(2) +
                    ' kWh </button>' + '<div class="row"> ' + '<div class="col-lg-1"></div>' + '<strong>' + current_power.toFixed(2) + ' kW</strong>' + ' </div> ' + '</div>');
                $("#north-row"+north_row_count).append(success);
            }
            else {
                var label = $('<div class="col-lg-1 mar-top mar-btm" id="div'+d_north+'" style="text-align:center; padding-left:0px; padding-right:0px;"> ' +
                    '<div class="row"> ' + '<div class="col-lg-1"></div>' + '<strong>' + data.inverters[i].name + '</strong>' + ' </div> ' +
                    '<button class="btn btn-lg btn-info mar-lft" inverter_name="'+data.inverters[i].name+'" inverter_connected="'+data.inverters[i].connected+'" inverter_orientation="'+data.inverters[i].orientation+'" inverter_capacity="'+data.inverters[i].capacity+'" inverter_power="'+data.inverters[i].power+'" inverter_generation="'+data.inverters[i].generation+'"  id="inverter_button_value_'+i+'">' + generation.toFixed(2) +
                    ' kWh </button>' + '<div class="row"> ' + '<div class="col-lg-1"></div>' + '<strong>' + current_power.toFixed(2) + ' kW</strong>' + ' </div> ' + ' </div>');
                $("#north-row"+north_row_count).append(label);
            }
            north_elements++;
            d_north++;
        } else if(data.inverters[i].orientation == 'SOUTH') {
            if(south_elements % inverter_blocks == 0) {
                south_row_count++;
                $("#south").append('<div class="row seven-cols" id="south-row'+south_row_count+'"></div>');
                d_south = 0;
            }
            var generation = data.inverters[i].generation;
            var current_power = data.inverters[i].power;
            if (data.inverters[i].connected == "connected") {
                if(current_power == 0) {
                    var success = $('<div class="col-lg-1 mar-top mar-btm" id="div'+d_south+'" style="text-align:center; padding-left:0px; padding-right:0px;"> ' +
                    '<div class="row"> ' + '<div class="col-lg-1"></div>' + '<strong>' + data.inverters[i].name + '</strong>' + ' </div> ' +
                    '<button class="btn btn-lg mar-lft" inverter_name="'+data.inverters[i].name+'" inverter_connected="'+data.inverters[i].connected+'" inverter_orientation="'+data.inverters[i].orientation+'" inverter_capacity="'+data.inverters[i].capacity+'" inverter_power="'+data.inverters[i].power+'" inverter_generation="'+data.inverters[i].generation+'" id="inverter_button_value_'+i+'" style="background-color:#f3f307;">' + generation.toFixed(2) +
                    ' kWh </button>' + '<div class="row"> ' + '<div class="col-lg-1"></div>' + '<strong>' + current_power.toFixed(2) + ' kW</strong>' + ' </div> ' + '</div>');
                } else {
                    var success = $('<div class="col-lg-1 mar-top mar-btm" id="div'+d_south+'" style="text-align:center; padding-left:0px; padding-right:0px;"> ' +
                    '<div class="row"> ' + '<div class="col-lg-1"></div>' + '<strong>' + data.inverters[i].name + '</strong>' + ' </div> ' +
                    '<button class="btn btn-lg btn-success mar-lft" inverter_name="'+data.inverters[i].name+'" inverter_connected="'+data.inverters[i].connected+'" inverter_orientation="'+data.inverters[i].orientation+'" inverter_capacity="'+data.inverters[i].capacity+'" inverter_power="'+data.inverters[i].power+'" inverter_generation="'+data.inverters[i].generation+'" id="inverter_button_value_'+i+'">'+ generation.toFixed(2) +
                    ' kWh </button>' + '<div class="row"> ' + '<div class="col-lg-1"></div>' + '<strong>' + current_power.toFixed(2) + ' kW</strong>' + ' </div> ' + '</div>');
                }
                $("#south-row"+south_row_count).append(success);
            } else if (data.inverters[i].connected == "disconnected") {
                var success = $('<div class="col-lg-1 mar-top mar-btm" id="div'+d_south+'" style="text-align:center; padding-left:0px; padding-right:0px;"> ' +
                    '<div class="row"> ' + '<div class="col-lg-1"></div>' + '<strong>' + data.inverters[i].name + '</strong>' + ' </div> ' +
                    '<button class="btn btn-lg btn-danger mar-lft" inverter_name="'+data.inverters[i].name+'" inverter_connected="'+data.inverters[i].connected+'" inverter_orientation="'+data.inverters[i].orientation+'" inverter_capacity="'+data.inverters[i].capacity+'" inverter_power="'+data.inverters[i].power+'" inverter_generation="'+data.inverters[i].generation+'" id="inverter_button_value_'+i+'">'+ generation.toFixed(2) +
                    ' kWh </button>' + '<div class="row"> ' + '<div class="col-lg-1"></div>' + '<strong>' + current_power.toFixed(2) + ' kW</strong>' + ' </div> ' + '</div>');
                $("#south-row"+south_row_count).append(success);
            }
            else {
                var label = $('<div class="col-lg-1 mar-top mar-btm" id="div'+d_south+'" style="text-align:center; padding-left:0px; padding-right:0px;"> ' +
                    '<div class="row"> ' + '<div class="col-lg-1"></div>' + '<strong>' + data.inverters[i].name + '</strong>' + ' </div> ' +
                    '<button class="btn btn-lg btn-info mar-lft" inverter_name="'+data.inverters[i].name+'" inverter_connected="'+data.inverters[i].connected+'" inverter_orientation="'+data.inverters[i].orientation+'" inverter_capacity="'+data.inverters[i].capacity+'" inverter_power="'+data.inverters[i].power+'" inverter_generation="'+data.inverters[i].generation+'" id="inverter_button_value_'+i+'">' + generation.toFixed(2) +
                    ' kWh </button>' + '<div class="row"> ' + '<div class="col-lg-1"></div>' + '<strong> ' + current_power.toFixed(2) + ' kW</strong>' + ' </div> ' + '</div>');
                $("#south-row"+south_row_count).append(label);
            }
            south_elements++;
            d_south++;
        } else if(data.inverters[i].orientation == 'EAST') {
            if(east_elements % inverter_blocks == 0) {
                east_row_count++;
                $("#east").append('<div class="row seven-cols" id="east_row'+east_row_count+'"></div>');
                d_east = 0;
            }
            var generation = data.inverters[i].generation;
            var current_power = data.inverters[i].power;
            if (data.inverters[i].connected == "connected") {
                if(current_power == 0) {
                    var success = $('<div class="col-lg-1 mar-top mar-btm" id="div'+d_east+'" style="text-align:center; padding-left:0px; padding-right:0px;"> ' +
                    '<div class="row"> ' + '<div class="col-lg-1"></div>' + '<strong>' + data.inverters[i].name + '</strong>' + ' </div> ' +
                    '<button class="btn btn-lg mar-lft" inverter_name="'+data.inverters[i].name+'" inverter_connected="'+data.inverters[i].connected+'" inverter_orientation="'+data.inverters[i].orientation+'" inverter_capacity="'+data.inverters[i].capacity+'" inverter_power="'+data.inverters[i].power+'" inverter_generation="'+data.inverters[i].generation+'" id="inverter_button_value_'+i+'" style="background-color:#f3f307;">'+ generation.toFixed(2) +
                    ' kWh </button>' + '<div class="row"> ' + '<div class="col-lg-1"></div>' + '<strong>' + current_power.toFixed(2) + ' kW</strong>' + ' </div> ' + '</div>');
                } else {
                    var success = $('<div class="col-lg-1 mar-top mar-btm" id="div'+d_east+'" style="text-align:center; padding-left:0px; padding-right:0px;"> ' +
                    '<div class="row"> ' + '<div class="col-lg-1"></div>' + '<strong>' + data.inverters[i].name + '</strong>' + ' </div> ' +
                    '<button class="btn btn-lg btn-success mar-lft" inverter_name="'+data.inverters[i].name+'" inverter_connected="'+data.inverters[i].connected+'" inverter_orientation="'+data.inverters[i].orientation+'" inverter_capacity="'+data.inverters[i].capacity+'" inverter_power="'+data.inverters[i].power+'" inverter_generation="'+data.inverters[i].generation+'" id="inverter_button_value_'+i+'">'+ generation.toFixed(2) +
                    ' kWh </button>' + '<div class="row"> ' + '<div class="col-lg-1"></div>' + '<strong>' + current_power.toFixed(2) + ' kW</strong>' + ' </div> ' + '</div>');
                }
                $("#east_row"+east_row_count).append(success);
            } else if (data.inverters[i].connected == "disconnected") {
                var success = $('<div class="col-lg-1 mar-top mar-btm" id="div'+d_east+'" style="text-align:center; padding-left:0px; padding-right:0px;"> ' +
                    '<div class="row"> ' + '<div class="col-lg-1"></div>' + '<strong>' + data.inverters[i].name + '</strong>' + ' </div> ' +
                    '<button class="btn btn-lg btn-danger mar-lft" inverter_name="'+data.inverters[i].name+'" inverter_connected="'+data.inverters[i].connected+'" inverter_orientation="'+data.inverters[i].orientation+'" inverter_capacity="'+data.inverters[i].capacity+'" inverter_power="'+data.inverters[i].power+'" inverter_generation="'+data.inverters[i].generation+'" id="inverter_button_value_'+i+'">'+ generation.toFixed(2) +
                    ' kWh </button>' + '<div class="row"> ' + '<div class="col-lg-1"></div>' + '<strong>' + current_power.toFixed(2) + ' kW</strong>' + ' </div> ' + '</div>');
                $("#east_row"+east_row_count).append(success);
            }
            else {
                var label = $('<div class="col-lg-1 mar-top mar-btm" id="div'+d_east+'" style="text-align:center; padding-left:0px; padding-right:0px;"> ' +
                    '<div class="row"> ' + '<div class="col-lg-1"></div>' + '<strong>' + data.inverters[i].name + '</strong>' + ' </div> ' +
                    '<button class="btn btn-lg btn-info mar-lft" inverter_name="'+data.inverters[i].name+'" inverter_connected="'+data.inverters[i].connected+'" inverter_orientation="'+data.inverters[i].orientation+'" inverter_capacity="'+data.inverters[i].capacity+'" inverter_power="'+data.inverters[i].power+'" inverter_generation="'+data.inverters[i].generation+'" id="inverter_button_value_'+i+'">' + generation.toFixed(2) +
                    ' kWh </button>' + '<div class="row"> ' + '<div class="col-lg-1"></div>' + '<strong>' + current_power.toFixed(2) + ' kW</strong>' + ' </div> ' + '</div>');
                $("#east_row"+east_row_count).append(label);
            }
            east_elements++;
            d_east++;
        } else if(data.inverters[i].orientation == 'WEST') {
            if(west_elements % inverter_blocks == 0) {
                west_row_count++;
                $("#west").append('<div class="row seven-cols" id="west_row'+west_row_count+'"></div>');
                d_west = 0;
            }
            var generation = data.inverters[i].generation;
            var current_power = data.inverters[i].power;
            if (data.inverters[i].connected == "connected") {
                if(current_power == 0) {
                    var success = $('<div class="col-lg-1 mar-top mar-btm" id="div'+d_west+'" style="text-align:center; padding-left:0px; padding-right:0px;"> ' +
                    '<div class="row"> ' + '<div class="col-lg-1"></div>' + '<strong>' + data.inverters[i].name + '</strong>' + ' </div> ' +
                    '<button class="btn btn-lg mar-lft" inverter_name="'+data.inverters[i].name+'" inverter_connected="'+data.inverters[i].connected+'" inverter_orientation="'+data.inverters[i].orientation+'" inverter_capacity="'+data.inverters[i].capacity+'" inverter_power="'+data.inverters[i].power+'" inverter_generation="'+data.inverters[i].generation+'" id="inverter_button_value_'+i+'" style="background-color:#f3f307;">'+ generation.toFixed(2) +
                    ' kWh </button>' + '<div class="row"> ' + '<div class="col-lg-1"></div>' + '<strong>' + current_power.toFixed(2) + ' kW</strong>' + ' </div> ' + '</div>');
                } else {
                    var success = $('<div class="col-lg-1 mar-top mar-btm" id="div'+d_west+'" style="text-align:center; padding-left:0px; padding-right:0px;"> ' +
                    '<div class="row"> ' + '<div class="col-lg-1"></div>' + '<strong>' + data.inverters[i].name + '</strong>' + ' </div> ' +
                    '<button class="btn btn-lg btn-success mar-lft" inverter_name="'+data.inverters[i].name+'" inverter_connected="'+data.inverters[i].connected+'" inverter_orientation="'+data.inverters[i].orientation+'" inverter_capacity="'+data.inverters[i].capacity+'" inverter_power="'+data.inverters[i].power+'" inverter_generation="'+data.inverters[i].generation+'" id="inverter_button_value_'+i+'">'+ generation.toFixed(2) +
                    ' kWh </button>' + '<div class="row"> ' + '<div class="col-lg-1"></div>' + '<strong>' + current_power.toFixed(2) + ' kW</strong>' + ' </div> ' + '</div>');
                }
                $("#west_row"+west_row_count).append(success);
            } else if (data.inverters[i].connected == "disconnected") {
                var success = $('<div class="col-lg-1 mar-top mar-btm" id="div'+d_west+'" style="text-align:center; padding-left:0px; padding-right:0px;"> ' +
                    '<div class="row"> ' + '<div class="col-lg-1"></div>' + '<strong>' + data.inverters[i].name + '</strong>' + ' </div> ' +
                    '<button class="btn btn-lg btn-danger mar-lft" inverter_name="'+data.inverters[i].name+'" inverter_connected="'+data.inverters[i].connected+'" inverter_orientation="'+data.inverters[i].orientation+'" inverter_capacity="'+data.inverters[i].capacity+'" inverter_power="'+data.inverters[i].power+'" inverter_generation="'+data.inverters[i].generation+'" id="inverter_button_value_'+i+'">'+ generation.toFixed(2) +
                    ' kWh </button>' + '<div class="row"> ' + '<div class="col-lg-1"></div>' + '<strong> ' + current_power.toFixed(2) + ' kW</strong>' + ' </div> ' + '</div>');
                $("#west_row"+west_row_count).append(success);
            }
            else {
                var label = $('<div class="col-lg-1 mar-top mar-btm" id="div'+d_west+'" style="text-align:center; padding-left:0px; padding-right:0px;"> ' +
                    '<div class="row"> ' + '<div class="col-lg-1"></div>' + '<strong>' + data.inverters[i].name + '</strong>' + ' </div> ' +
                    '<button class="btn btn-lg btn-info mar-lft" inverter_name="'+data.inverters[i].name+'" inverter_connected="'+data.inverters[i].connected+'" inverter_orientation="'+data.inverters[i].orientation+'" inverter_capacity="'+data.inverters[i].capacity+'" inverter_power="'+data.inverters[i].power+'" inverter_generation="'+data.inverters[i].generation+'" id="inverter_button_value_'+i+'">' + generation.toFixed(2) +
                    ' kWh </button>' + '<div class="row"> ' + '<div class="col-lg-1"></div>' + '<strong>' + current_power.toFixed(2) + ' kW</strong>' + ' </div> ' + '</div>');
                $("#west_row"+west_row_count).append(label);
            }
            west_elements++;
            d_west++;
        } else if(data.inverters[i].orientation == 'SOUTH-WEST') {
            if(south_west_elements % inverter_blocks == 0) {
                south_west_row_count++;
                $("#south_west").append('<div class="row seven-cols" id="south_west_row'+south_west_row_count+'"></div>');
                d_south_west = 0;
            }
            var generation = data.inverters[i].generation;
            var current_power = data.inverters[i].power;
            if (data.inverters[i].connected == "connected") {
                if(current_power == 0) {
                    var success = $('<div class="col-lg-1 mar-top mar-btm" id="div'+d_south_west+'" style="text-align:center; padding-left:0px; padding-right:0px;"> ' +
                    '<div class="row"> ' + '<div class="col-lg-1"></div>' + '<strong>' + data.inverters[i].name + '</strong>' + ' </div> ' +
                    '<button class="btn btn-lg mar-lft" inverter_name="'+data.inverters[i].name+'" inverter_connected="'+data.inverters[i].connected+'" inverter_orientation="'+data.inverters[i].orientation+'" inverter_capacity="'+data.inverters[i].capacity+'" inverter_power="'+data.inverters[i].power+'" inverter_generation="'+data.inverters[i].generation+'" id="inverter_button_value_'+i+'" style="background-color:#f3f307;">'+ generation.toFixed(2) +
                    ' kWh </button>' + '<div class="row"> ' + '<div class="col-lg-1"></div>' + '<strong>' + current_power.toFixed(2) + ' kW</strong>' + ' </div> ' + '</div>');
                } else {
                    var success = $('<div class="col-lg-1 mar-top mar-btm" id="div'+d_south_west+'" style="text-align:center; padding-left:0px; padding-right:0px;"> ' +
                    '<div class="row"> ' + '<div class="col-lg-1"></div>' + '<strong>' + data.inverters[i].name + '</strong>' + ' </div> ' +
                    '<button class="btn btn-lg btn-success mar-lft" inverter_name="'+data.inverters[i].name+'" inverter_connected="'+data.inverters[i].connected+'" inverter_orientation="'+data.inverters[i].orientation+'" inverter_capacity="'+data.inverters[i].capacity+'" inverter_power="'+data.inverters[i].power+'" inverter_generation="'+data.inverters[i].generation+'" id="inverter_button_value_'+i+'">'+ generation.toFixed(2) +
                    ' kWh </button>' + '<div class="row"> ' + '<div class="col-lg-1"></div>' + '<strong>' + current_power.toFixed(2) + ' kW</strong>' + ' </div> ' + '</div>');
                }
                $("#south_west_row"+south_west_row_count).append(success);
            } else if (data.inverters[i].connected == "disconnected") {
                var success = $('<div class="col-lg-1 mar-top mar-btm" id="div'+d_south_west+'" style="text-align:center; padding-left:0px; padding-right:0px;"> ' +
                    '<div class="row"> ' + '<div class="col-lg-1"></div>' + '<strong>' + data.inverters[i].name + '</strong>' + ' </div> ' +
                    '<button class="btn btn-lg btn-danger mar-lft" inverter_name="'+data.inverters[i].name+'" inverter_connected="'+data.inverters[i].connected+'" inverter_orientation="'+data.inverters[i].orientation+'" inverter_capacity="'+data.inverters[i].capacity+'" inverter_power="'+data.inverters[i].power+'" inverter_generation="'+data.inverters[i].generation+'" id="inverter_button_value_'+i+'">'+ generation.toFixed(2) +
                    ' kWh </button>' + '<div class="row"> ' + '<div class="col-lg-1"></div>' + '<strong> ' + current_power.toFixed(2) + ' kW</strong>' + ' </div> ' + '</div>');
                $("#south_west_row"+south_west_row_count).append(success);
            }
            else {
                var label = $('<div class="col-lg-1 mar-top mar-btm" id="div'+d_south_west+'" style="text-align:center; padding-left:0px; padding-right:0px;"> ' +
                    '<div class="row"> ' + '<div class="col-lg-1"></div>' + '<strong>' + data.inverters[i].name + '</strong>' + ' </div> ' +
                    '<button class="btn btn-lg btn-info mar-lft" inverter_name="'+data.inverters[i].name+'" inverter_connected="'+data.inverters[i].connected+'" inverter_orientation="'+data.inverters[i].orientation+'" inverter_capacity="'+data.inverters[i].capacity+'" inverter_power="'+data.inverters[i].power+'" inverter_generation="'+data.inverters[i].generation+'" id="inverter_button_value_'+i+'">' + generation.toFixed(2) +
                    ' kWh </button>' + '<div class="row"> ' + '<div class="col-lg-1"></div>' + '<strong>' + current_power.toFixed(2) + ' kW</strong>' + ' </div> ' + '</div>');
                $("#south_west_row"+south_west_row_count).append(label);
            }
            south_west_elements++;
            d_south_west++;
        } else if(data.inverters[i].orientation == 'EAST-WEST') {
            if(east_west_elements % inverter_blocks == 0) {
                east_west_row_count++;
                $("#east_west").append('<div class="row seven-cols" id="east_west_row'+east_west_row_count+'"></div>');
                d_east_west = 0;
            }
            var generation = data.inverters[i].generation;
            var current_power = data.inverters[i].power;
            if (data.inverters[i].connected == "connected") {
                if(current_power == 0) {
                    var success = $('<div class="col-lg-1 mar-top mar-btm" id="div'+d_east_west+'" style="text-align:center; padding-left:0px; padding-right:0px;"> ' +
                    '<div class="row"> ' + '<div class="col-lg-1"></div>' + '<strong>' + data.inverters[i].name + '</strong>' + ' </div> ' +
                    '<button class="btn btn-lg mar-lft" inverter_name="'+data.inverters[i].name+'" inverter_connected="'+data.inverters[i].connected+'" inverter_orientation="'+data.inverters[i].orientation+'" inverter_capacity="'+data.inverters[i].capacity+'" inverter_power="'+data.inverters[i].power+'" inverter_generation="'+data.inverters[i].generation+'" id="inverter_button_value_'+i+'" style="background-color:#f3f307;">'+ generation.toFixed(2) +
                    ' kWh </button>' + '<div class="row"> ' + '<div class="col-lg-1"></div>' + '<strong>' + current_power.toFixed(2) + ' kW</strong>' + ' </div> ' + '</div>');
                } else {
                    var success = $('<div class="col-lg-1 mar-top mar-btm" id="div'+d_east_west+'" style="text-align:center; padding-left:0px; padding-right:0px;"> ' +
                    '<div class="row"> ' + '<div class="col-lg-1"></div>' + '<strong>' + data.inverters[i].name + '</strong>' + ' </div> ' +
                    '<button class="btn btn-lg btn-success mar-lft" inverter_name="'+data.inverters[i].name+'" inverter_connected="'+data.inverters[i].connected+'" inverter_orientation="'+data.inverters[i].orientation+'" inverter_capacity="'+data.inverters[i].capacity+'" inverter_power="'+data.inverters[i].power+'" inverter_generation="'+data.inverters[i].generation+'" id="inverter_button_value_'+i+'">'+ generation.toFixed(2) +
                    ' kWh </button>' + '<div class="row"> ' + '<div class="col-lg-1"></div>' + '<strong>' + current_power.toFixed(2) + ' kW</strong>' + ' </div> ' + '</div>');
                }
                $("#east_west_row"+east_west_row_count).append(success);
            } else if (data.inverters[i].connected == "disconnected") {
                var success = $('<div class="col-lg-1 mar-top mar-btm" id="div'+d_east_west+'" style="text-align:center; padding-left:0px; padding-right:0px;"> ' +
                    '<div class="row"> ' + '<div class="col-lg-1"></div>' + '<strong>' + data.inverters[i].name + '</strong>' + ' </div> ' +
                    '<button class="btn btn-lg btn-danger mar-lft" inverter_name="'+data.inverters[i].name+'" inverter_connected="'+data.inverters[i].connected+'" inverter_orientation="'+data.inverters[i].orientation+'" inverter_capacity="'+data.inverters[i].capacity+'" inverter_power="'+data.inverters[i].power+'" inverter_generation="'+data.inverters[i].generation+'" id="inverter_button_value_'+i+'">'+ generation.toFixed(2) +
                    ' kWh </button>' + '<div class="row"> ' + '<div class="col-lg-1"></div>' + '<strong> ' + current_power.toFixed(2) + ' kW</strong>' + ' </div> ' + '</div>');
                $("#east_west_row"+east_west_row_count).append(success);
            }
            else {
                var label = $('<div class="col-lg-1 mar-top mar-btm" id="div'+d_east_west+'" style="text-align:center; padding-left:0px; padding-right:0px;"> ' +
                    '<div class="row"> ' + '<div class="col-lg-1"></div>' + '<strong>' + data.inverters[i].name + '</strong>' + ' </div> ' +
                    '<button class="btn btn-lg btn-info mar-lft" inverter_name="'+data.inverters[i].name+'" inverter_connected="'+data.inverters[i].connected+'" inverter_orientation="'+data.inverters[i].orientation+'" inverter_capacity="'+data.inverters[i].capacity+'" inverter_power="'+data.inverters[i].power+'" inverter_generation="'+data.inverters[i].generation+'" id="inverter_button_value_'+i+'">' + generation.toFixed(2) +
                    ' kWh </button>' + '<div class="row"> ' + '<div class="col-lg-1"></div>' + '<strong>' + current_power.toFixed(2) + ' kW</strong>' + ' </div> ' + '</div>');
                $("#east_west_row"+east_west_row_count).append(label);
            }
            east_west_elements++;
            d_east_west++;
        }
        $("#inverter_button_value_"+i).click(function() {

            var inverter_name = $(this).attr('inverter_name');
            var inverter_connected = $(this).attr('inverter_connected');
            var inverter_orientation = $(this).attr('inverter_orientation');
            var inverter_capacity = $(this).attr('inverter_capacity');
            var inverter_power = $(this).attr('inverter_power');
            var inverter_generation = $(this).attr('inverter_generation');

            $("#inverter_name").empty();
            $("#inverter_name").append(inverter_name);

            $("#status_name").empty();
            $("#status_name").append("<div class='text-semibold'>Inverter Name : " + inverter_name + "</div>");
            $("#status_connected").empty();
            $("#status_connected").append("<div class='text-semibold'>Connection Status : " + inverter_connected + "</div>");
            $("#status_orientation").empty();
            $("#status_orientation").append("<div class='text-semibold'>Inverter Orientation : " + inverter_orientation + "</div>");
            $("#status_capacity").empty();
            $("#status_capacity").append("<div class='text-semibold'>Inverter Capacity : " + inverter_capacity + " kW</div>");
            $("#status_power").empty();
            $("#status_power").append("<div class='text-semibold'>Current Power : " + inverter_power + " kW</div>");
            $("#status_generation").empty();
            $("#status_generation").append("<div class='text-semibold'>Current Generation : " + inverter_generation + " kWh</div>");

            $(".inverter_modal").modal('show');

        });
    }
    
    if(north_row_count == 0) {
        $("#north").remove();
    } 
    if(south_row_count == 0) {
        $("#south").remove();
    } 
    if(east_row_count == 0) {
        $("#east").remove();
    } 
    if(west_row_count == 0) {
        $("#west").remove();
    } 
    if(south_west_row_count == 0) {
        $("#south_west").remove();
    } 
    if(east_west_row_count == 0) {
        $("#east_west").remove();
    } 

    return plot_labels_groups(data);

}

function plot_labels_groups(data) {

    if(data.total_group_number == 0) {

        $("#groupstab").hide();
        $("#groups-lft").hide();

    }

    var all_groups = data.solar_groups;

    var list = $('#inverter_status_groups');
    list.innerHTML = "";
    list.empty();

    for(var i = 0; i < all_groups.length; i++) {

        var solar_group = $("<div class='row' id='"+all_groups[i]+"' style='margin-top: 20px;' disabled><div class='row' style='text-align: center;'><strong style='font-size:20px;font-weight:900;'>"+all_groups[i]+"</strong></div></div>");
        list.append(solar_group);

        var solar_group_element = 0;
        var solar_group_row = 0;
        var d_solar_group = 0;

        for(var j = 0; j < data.inverters.length; j++) {

            if(all_groups[i] === data.inverters[j].solar_group) {

                if(solar_group_element % 5 == 0) {
                    solar_group_row++;
                    $("#"+all_groups[i]).append('<div class="row" id="'+all_groups[i] + '-' + solar_group_row+'"></div>');
                    d_solar_group = 0;
                }

                var generation = data.inverters[j].generation;
                var current_power = data.inverters[j].power;
                if (data.inverters[j].connected == "connected") {
                    if(current_power == 0) {
                        var success = $('<div class="col-lg-2 pad-all" id="div'+d_solar_group+'" style="text-align:center;"> ' +
                        '<div class="row"> ' + '<div class="col-lg-1"></div>' + '<strong>' + data.inverters[j].name + '</strong>' + ' </div> ' +
                        '<button class="btn btn-lg mar-lft" inverter_name="'+data.inverters[j].name+'" inverter_connected="'+data.inverters[j].connected+'" inverter_orientation="'+data.inverters[j].orientation+'" inverter_capacity="'+data.inverters[j].capacity+'" inverter_power="'+data.inverters[j].power+'" inverter_generation="'+data.inverters[j].generation+'" id="inverter_button_group_value_'+j+'" style="width: 150px; background-color:#f3f307;">' + generation.toFixed(2) +
                        ' kWh </button>' + '<div class="row"> ' + '<div class="col-lg-1"></div>' + '<strong>' + current_power.toFixed(2) + ' kW</strong>' + ' </div> ' + '</div>');
                    } else {
                        var success = $('<div class="col-lg-2 pad-all" id="div'+d_solar_group+'" style="text-align:center;"> ' +
                        '<div class="row"> ' + '<div class="col-lg-1"></div>' + '<strong>' + data.inverters[j].name + '</strong>' + ' </div> ' +
                        '<button class="btn btn-lg btn-success mar-lft" inverter_name="'+data.inverters[j].name+'" inverter_connected="'+data.inverters[j].connected+'" inverter_orientation="'+data.inverters[j].orientation+'" inverter_capacity="'+data.inverters[j].capacity+'" inverter_power="'+data.inverters[j].power+'" inverter_generation="'+data.inverters[j].generation+'" id="inverter_button_group_value_'+j+'" style="width: 150px;">' + generation.toFixed(2) +
                        ' kWh </button>' + '<div class="row"> ' + '<div class="col-lg-1"></div>' + '<strong>' + current_power.toFixed(2) + ' kW</strong>' + ' </div> ' + '</div>');
                    }
                    $("#"+all_groups[i] + "-" + solar_group_row).append(success);
                } else if (data.inverters[j].connected == "disconnected") {
                    var success = $('<div class="col-lg-2 pad-all" id="div'+d_solar_group+'" style="text-align:center;"> ' +
                        '<div class="row"> ' + '<div class="col-lg-1"></div>' + '<strong>' + data.inverters[j].name + '</strong>' + ' </div> ' +
                        '<button class="btn btn-lg btn-danger mar-lft" inverter_name="'+data.inverters[j].name+'" inverter_connected="'+data.inverters[j].connected+'" inverter_orientation="'+data.inverters[j].orientation+'" inverter_capacity="'+data.inverters[j].capacity+'" inverter_power="'+data.inverters[j].power+'" inverter_generation="'+data.inverters[j].generation+'" id="inverter_button_group_value_'+j+'" style="width: 150px;">' + generation.toFixed(2) +
                        ' kWh </button>' + '<div class="row"> ' + '<div class="col-lg-1"></div>' + '<strong>' + current_power.toFixed(2) + ' kW</strong>' + ' </div> ' + '</div>');
                    $("#"+all_groups[i] + "-" + solar_group_row).append(success);
                }
                else {
                    var label = $('<div class="col-lg-2 pad-all" id="div'+d_solar_group+'" style="text-align:center;"> ' +
                        '<div class="row"> ' + '<div class="col-lg-1"></div>' + '<strong>' + data.inverters[j].name + '</strong>' + ' </div> ' +
                        '<button class="btn btn-lg btn-info mar-lft" inverter_name="'+data.inverters[j].name+'" inverter_connected="'+data.inverters[j].connected+'" inverter_orientation="'+data.inverters[j].orientation+'" inverter_capacity="'+data.inverters[j].capacity+'" inverter_power="'+data.inverters[j].power+'" inverter_generation="'+data.inverters[j].generation+'"  id="inverter_button_group_value_'+j+'" style="width: 150px;">' + generation.toFixed(2) +
                        ' kWh </button>' + '<div class="row"> ' + '<div class="col-lg-1"></div>' + '<strong>' + current_power.toFixed(2) + ' kW</strong>' + ' </div> ' + ' </div>');
                    $("#"+all_groups[i] + "-" + solar_group_row).append(label);
                }
                solar_group_element++;
                d_solar_group++;

                $("#inverter_button_group_value_"+j).click(function() {

                    var inverter_name = $(this).attr('inverter_name');
                    var inverter_connected = $(this).attr('inverter_connected');
                    var inverter_orientation = $(this).attr('inverter_orientation');
                    var inverter_capacity = $(this).attr('inverter_capacity');
                    var inverter_power = $(this).attr('inverter_power');
                    var inverter_generation = $(this).attr('inverter_generation');

                    $("#inverter_name").empty();
                    $("#inverter_name").append(inverter_name);

                    $("#status_name").empty();
                    $("#status_name").append("<div class='text-semibold'>Inverter Name : " + inverter_name + "</div>");
                    $("#status_connected").empty();
                    $("#status_connected").append("<div class='text-semibold'>Connection Status : " + inverter_connected + "</div>");
                    $("#status_orientation").empty();
                    $("#status_orientation").append("<div class='text-semibold'>Inverter Orientation : " + inverter_orientation + "</div>");
                    $("#status_capacity").empty();
                    $("#status_capacity").append("<div class='text-semibold'>Inverter Capacity : " + inverter_capacity + " kW</div>");
                    $("#status_power").empty();
                    $("#status_power").append("<div class='text-semibold'>Current Power : " + inverter_power + " kW</div>");
                    $("#status_generation").empty();
                    $("#status_generation").append("<div class='text-semibold'>Current Generation : " + inverter_generation + " kWh</div>");

                    $(".inverter_modal").modal('show');

                });

            }

        }

        if(solar_group_row == 0) {
            $("#"+all_groups[i]).remove();
        } else {
            for(var j = 0; j <=solar_group_row; j++) {
                $("#"+all_groups[i] + "-" + j +" div:first").addClass("col-lg-offset-1");
            }
        }

    }

    var not_group = $("<div class='row' id='not_grouped' style='margin-top: 20px;' disabled><div class='row' style='text-align: center;'><strong style='font-size:20px;font-weight:900;'>Not Grouped</strong></div></div>");
    list.append(not_group);

    var not_group_element = 0;
    var not_group_row = 0;
    var d_not_group = 0;

    for(var j = 0; j < data.inverters.length; j++) {

        if(data.inverters[j].solar_group == "NA") {

            if(not_group_element % 5 == 0) {
                not_group_row++;
                $("#not_grouped").append('<div class="row" id="not_grouped'+not_group_row+'"></div>');
                d_not_group = 0;
            }

            var generation = data.inverters[j].generation;
            var current_power = data.inverters[j].power;
            if (data.inverters[j].connected == "connected") {
                if(current_power == 0) {
                    var success = $('<div class="col-lg-2 pad-all" id="div'+d_not_group+'" style="text-align:center;"> ' +
                    '<div class="row"> ' + '<div class="col-lg-1"></div>' + '<strong>' + data.inverters[j].name + '</strong>' + ' </div> ' +
                    '<button class="btn btn-lg mar-lft" inverter_name="'+data.inverters[j].name+'" inverter_connected="'+data.inverters[j].connected+'" inverter_orientation="'+data.inverters[j].orientation+'" inverter_capacity="'+data.inverters[j].capacity+'" inverter_power="'+data.inverters[j].power+'" inverter_generation="'+data.inverters[j].generation+'" id="inverter_button_not_group_value_'+j+'" style="width: 150px; background-color:#f3f307;">' + generation.toFixed(2) +
                    ' kWh </button>' + '<div class="row"> ' + '<div class="col-lg-1"></div>' + '<strong>' + current_power.toFixed(2) + ' kW</strong>' + ' </div> ' + '</div>');
                } else {
                    var success = $('<div class="col-lg-2 pad-all" id="div'+d_not_group+'" style="text-align:center;"> ' +
                    '<div class="row"> ' + '<div class="col-lg-1"></div>' + '<strong>' + data.inverters[j].name + '</strong>' + ' </div> ' +
                    '<button class="btn btn-lg btn-success mar-lft" inverter_name="'+data.inverters[j].name+'" inverter_connected="'+data.inverters[j].connected+'" inverter_orientation="'+data.inverters[j].orientation+'" inverter_capacity="'+data.inverters[j].capacity+'" inverter_power="'+data.inverters[j].power+'" inverter_generation="'+data.inverters[j].generation+'" id="inverter_button_not_group_value_'+j+'" style="width: 150px;">' + generation.toFixed(2) +
                    ' kWh </button>' + '<div class="row"> ' + '<div class="col-lg-1"></div>' + '<strong>' + current_power.toFixed(2) + ' kW</strong>' + ' </div> ' + '</div>');
                }
                $("#not_grouped"+not_group_row).append(success);
            } else if (data.inverters[j].connected == "disconnected") {
                var success = $('<div class="col-lg-2 pad-all" id="div'+d_not_group+'" style="text-align:center;"> ' +
                    '<div class="row"> ' + '<div class="col-lg-1"></div>' + '<strong>' + data.inverters[j].name + '</strong>' + ' </div> ' +
                    '<button class="btn btn-lg btn-danger mar-lft" inverter_name="'+data.inverters[j].name+'" inverter_connected="'+data.inverters[j].connected+'" inverter_orientation="'+data.inverters[j].orientation+'" inverter_capacity="'+data.inverters[j].capacity+'" inverter_power="'+data.inverters[j].power+'" inverter_generation="'+data.inverters[j].generation+'" id="inverter_button_not_group_value_'+j+'" style="width: 150px;">' + generation.toFixed(2) +
                    ' kWh </button>' + '<div class="row"> ' + '<div class="col-lg-1"></div>' + '<strong>' + current_power.toFixed(2) + ' kW</strong>' + ' </div> ' + '</div>');
                $("#not_grouped"+not_group_row).append(success);
            }
            else {
                var label = $('<div class="col-lg-2 pad-all" id="div'+d_not_group+'" style="text-align:center;"> ' +
                    '<div class="row"> ' + '<div class="col-lg-1"></div>' + '<strong>' + data.inverters[j].name + '</strong>' + ' </div> ' +
                    '<button class="btn btn-lg btn-info mar-lft" inverter_name="'+data.inverters[j].name+'" inverter_connected="'+data.inverters[j].connected+'" inverter_orientation="'+data.inverters[j].orientation+'" inverter_capacity="'+data.inverters[j].capacity+'" inverter_power="'+data.inverters[j].power+'" inverter_generation="'+data.inverters[j].generation+'"  id="inverter_button_not_group_value_'+j+'" style="width: 150px;">' + generation.toFixed(2) +
                    ' kWh </button>' + '<div class="row"> ' + '<div class="col-lg-1"></div>' + '<strong>' + current_power.toFixed(2) + ' kW</strong>' + ' </div> ' + ' </div>');
                $("#not_grouped"+not_group_row).append(label);
            }
            not_group_element++;
            d_not_group++;

            $("#inverter_button_not_group_value_"+j).click(function() {

                var inverter_name = $(this).attr('inverter_name');
                var inverter_connected = $(this).attr('inverter_connected');
                var inverter_orientation = $(this).attr('inverter_orientation');
                var inverter_capacity = $(this).attr('inverter_capacity');
                var inverter_power = $(this).attr('inverter_power');
                var inverter_generation = $(this).attr('inverter_generation');

                $("#inverter_name").empty();
                $("#inverter_name").append(inverter_name);

                $("#status_name").empty();
                $("#status_name").append("<div class='text-semibold'>Inverter Name : " + inverter_name + "</div>");
                $("#status_connected").empty();
                $("#status_connected").append("<div class='text-semibold'>Connection Status : " + inverter_connected + "</div>");
                $("#status_orientation").empty();
                $("#status_orientation").append("<div class='text-semibold'>Inverter Orientation : " + inverter_orientation + "</div>");
                $("#status_capacity").empty();
                $("#status_capacity").append("<div class='text-semibold'>Inverter Capacity : " + inverter_capacity + " kW</div>");
                $("#status_power").empty();
                $("#status_power").append("<div class='text-semibold'>Current Power : " + inverter_power + " kW</div>");
                $("#status_generation").empty();
                $("#status_generation").append("<div class='text-semibold'>Current Generation : " + inverter_generation + " kWh</div>");

                $(".inverter_modal").modal('show');
            
            });

        }

    }

    if(not_group_row == 0) {
        $("#not_grouped").remove();
    } else {
        for(var j = 0; j <= not_group_row; j++) {
            $("#not_grouped"+j+" div:first").addClass("col-lg-offset-1");
        }
    }

    /*if(data.solar_groups.length > 0) {
        groups_inverter_power(data);    
    } else {
        $("#group_powertab").hide();
    }*/

}

function inverters_ajbs(first_call) {

    console.log("first call - ",first_call);

    var device_name = "";

    if(client_slug == "edp") {
        device_name = '<button class="btn btn-default is-checked" data-sort-by="original-order">Panel Name</button>';
    } else {
        device_name = '<button class="btn btn-default is-checked" data-sort-by="original-order">Inverter Name</button>';
    }

    $(".loader").show();
    $("#inverters_filters_and_sorts").empty();
    $("#inverters_filters_and_sorts").append('<div class="row">' + 
                                            '<div class="col-lg-6 col-md-6 col-sm-6">' + 
                                              '<h3 class="text-info">Filter</h3>' +
                                              '<div id="filters" class="btn-group">' + 
                                                '<button class="btn btn-default is-checked" data-filter="*">Show All</button>' + 
                                                '<button class="btn btn-default" data-filter=".connected_no_alarms_no_ajbs_down">Generating</button>' + 
                                                '<button class="btn btn-default" data-filter=".connected_alarms_ajbs_down">Alarms</button>' + 
                                                '<button class="btn btn-default" data-filter=".disconnected">Disconnected</button>' + 
                                                '<button class="btn btn-default" data-filter=".unknown">Invalid</button>' + 
                                              '</div>' + 
                                            '</div>' + 
                                            '<div class="col-lg-3 col-md-3 col-sm-3"><h3 class="text-info">Sort</h3>' + 
                                              '<div id="sorts" class="btn-group">' + device_name + 
                                                '<button class="btn btn-default" data-sort-by="energy">Energy</button>' + 
                                                '<button class="btn btn-default" data-sort-by="power">Power</button>' + 
                                              '</div>' + 
                                            '</div>' + 
                                          '</div>');
  
    $.ajax({
        type: "GET",
        url: "/api/v1/solar/plants/".concat(plant_slug).concat('/live/'),
        success: function(data) {
            $("#inverters_grid").empty();

            var connection, button_color, connection_status, connection_text_color_status, group_name, group_name_class, solar_status, total_ajbs_down, ajbs_down_number, total_ajbs_down_class, errors, errors_div, errors_hide, errors_table, errors_present = 0, dc_sld_length_number;

            for(var i = 0; i < data.inverters.length; i++) {
                if(data.inverters[i].solar_group != "NA") {
                    group_name = data.inverters[i].solar_group;
                    group_name_class = "shows";
                } else {
                    group_name_class = "hidden";
                }

                if(data.inverters[i].last_three_errors.length) {
                    if(data.inverters[i].last_three_errors.length > 0) {

                        errors = "";
                        for(var error_row = 0; error_row < data.inverters[i].last_three_errors.length; error_row++) {
                            errors_present = 1;
                            errors = errors + dateFormat(data.inverters[i].last_three_errors[error_row].timestamp, "mmm dd yyyy HH:MM:ss") + "-" + data.inverters[i].last_three_errors[error_row].error_code + ",";
                        }
                        errors_hide = "show";
                        errors = errors.slice(0, -1);

                    } else {
                        errors_hide = "hidden";
                    } 
                } else {
                    errors_hide = "hidden";
                }

              if(data.inverters[i].total_ajbs != 0) {
                ajbs_down_number = data.inverters[i].disconnected_ajbs;
                total_ajbs = data.inverters[i].total_ajbs + " AJBs" ;
                total_ajbs_down_class = "show";
              } else {
                  ajbs_down_number = 0;
                  total_ajbs = 0;
                  total_ajbs_down_class = "hidden";
              }

              if(data.inverters[i].connected == "connected") {
                  connection_status = "connected";
                  connection = "connected_no_alarms_no_ajbs_down";
                  connection_text_color_status = "badge-success";
                  button_color = "btn-info";
              } else if(data.inverters[i].connected == "alarms") {
                  connection_status = "connected";
                  connection = "connected_alarms_ajbs_down";
                  connection_text_color_status = "badge-danger";
                  button_color = "btn-danger";
              } else if(data.inverters[i].connected == "disconnected") {
                  connection_status = "disconnected";
                  connection = "disconnected";
                  connection_text_color_status = "badge-warning";
                  button_color = "btn-warning";
              } else {
                  connection_status = "communictaion error";
                  connection = "unknown";
                  connection_text_color_status = "badge-info";
                  button_color = "btn-info";
              }

              if(data.inverters[i].last_inverter_status && data.inverters[i].last_inverter_status["0"] && data.inverters[i].last_inverter_status["0"].status) {
                  solar_status = data.inverters[i].last_inverter_status["0"].status;
              } else {
                  solar_status = "NA";
              }

              $("#inverters_grid").append('<div class="element-item col-lg-3 col-md-3 col-sm-12 col-xs-12 panel" data-category="' + connection + '" id="inverter_'+i+'" style="background-color: white;padding-bottom: 5px;">' +
    '<div class="row pad-lft">' +  
          '<div class="row">' + 
              '<div class="pull-left"><span class="power text-2x text-dark text-bold">' + parseFloat(data.inverters[i].power).toFixed(1) + '</span><span class="power_unit text-dark text-bold" style="font-size: small" id="power_unit"> kW</span></div>' +
          '</div>' +
          '<div class="row">' + 
              '<div class="pull-left"><p class="power_text text-dark text-sm text-bold">Current Power</p></div>' + 
          '</div>' +
        /*'<div class="col-lg-6 col-md-6 col-sm-6 col-xs-6">' + 
            '<div class="row">' + 
                '<div class="pull-right"><span class="energy text-dark">' +  + '</span><span class="text-dark" style="font-size: small" id="energy_unit"> kW</span></div>' + 
            '</div>' +
            '<div class="row">' + 
                '<div class="pull-right"><p class="energy_text text-dark text-sm">Capacity</p></div>' + 
            '</div>' + 
        '</div>' +*/
      '</div>' +
      '<div class="row pad-lft">' + 
        '<div class="row">' + 
            '<span class="energy text-dark text-bold text-2x">' + (parseFloat(data.inverters[i].generation)).toFixed(1) + '</span><span class="text-dark text-bold" style="font-size: small" id="energy_unit"> kWh</span>' +
        '</div>' +
        '<div class="row">' + 
            '<p class="energy_text text-bold text-dark text-sm">Generation Today</p>' + 
        '</div>' + 
        '<div class="row">' +
            '<span class="name badge text-lg '+ connection_text_color_status +'" style="border-radius: 0px;">' + data.inverters[i].name + ", " + parseFloat(data.inverters[i].capacity) + ' kW</span> <span class="group_name badge text-lg '+ connection_text_color_status +' ' + group_name_class + '" style="border-radius: 0px;">' + data.inverters[i].solar_group + '</span>' +
        '</div>' +
        '<div class="row" style="padding-top: 1vh;">' +
            '<button total_ajbs="' + data.inverters[i].total_ajbs + '" id="inverter_know_' + i + '" name="' + data.inverters[i].name + '" status="' + solar_status + '" inside_temperature="' + data.inverters[i].inside_temperature + '" ajbs_down="' + data.inverters[i].disconnected_ajbs + '" errors="' + errors + '"  class="btn btn-xs text-bold ' + button_color + '">Know More</button> <button id="inverter_parameters_reading_' + i + '" name="' + data.inverters[i].name + '" class="btn btn-xs text-bold ' + button_color + '">Parameter Readings</button>' +
        '</div>' +
        /*'<div class="row text-center pad-top">' +
            '<button total_ajbs="' + data.inverters[i].total_ajbs + '" id="inverter_know_' + i + '" name="' + data.inverters[i].name + '" class="btn btn-xs btn-info text-bold">Know More</button>' +
        '</div>' +*/
      '</div>' +
      /*'<div class="row">' + 
          '<div class="col-lg-4 col-md-4 col-sm-4 col-xs-4 pad-top" style="padding-left: 0px;padding-right: 0px;">' + 
              '<span class="solar_status_value pull-left text-info">Status: ' + solar_status + '</span>' +
          '</div>' +
          '<div class="col-lg-4 col-md-4 col-sm-4 col-xs-4">' +
              '<div class=" ajbs_down">' +
                  '<div class="row pad-top">' + 
                        '<span class="ajbs_down text-sm text-danger pad-rgt' + total_ajbs_down_class + '">' + total_ajbs_down + '</span>' + 
                  '</div>' +
              '</div>' +
              '<div class="pull-right inside_temperature" hidden>' +
                  '<div class="row pad-top">' + 
                        '<span class="inside_temperature_value text-primary">' + data.inverters[i].inside_temperature + '&#8451;</span> <i class="fa fa-thermometer-three-quarters" aria-hidden="true"></i>' +
                  '</div>' +
              '</div>' +
              '<div class="pull-right solar_status pad-top" hidden>' +
                  '<div class="row">' + 
                        '<span class="solar_status_value text-info">Status: ' + solar_status + '</span>' +
                  '</div>' +
              '</div>' +
          '</div>' +
          '<div class="col-lg-6 col-md-6 col-sm-6 col-xs-6 ' + errors_hide + ' pad-top text-center">' +
              '<span class="solar_status_value text-info">Errors: ' + errors + '</span>' +
          '</div>' +
          '<div class="col-lg-2 col-md-2 col-sm-2 col-xs-2 pull-right">' +
              '<div class="ajbs_down pull-right">' +
                  '<div class="row pad-top">' + 
                        '<span class="ajbs_down text-sm text-danger pad-rgt' + total_ajbs_down_class + '">' + total_ajbs_down + '</span>' + 
                  '</div>' +
              '</div>' +
              '<div class="pull-right inside_temperature" hidden>' +
                  '<div class="row pad-top">' + 
                        '<span class="inside_temperature_value text-primary">' + data.inverters[i].inside_temperature + '&#8451;</span> <i class="fa fa-thermometer-three-quarters" aria-hidden="true"></i>' +
                  '</div>' +
              '</div>' +
          '</div>' +
      '</div>' +
  '</div>*/'</div>');

            $("#inverter_"+i).removeClass("connected_no_alarms_no_ajbs_down");
            $("#inverter_"+i).removeClass("connected_alarms_ajbs_down");
            $("#inverter_"+i).removeClass("disconnected");
            $("#inverter_"+i).removeClass("unknown");
            $("#inverter_"+i).addClass(connection);

            $("#inverter_know_"+i).click(function() {
                var inverter_name = $(this).attr("name");

                var status = $(this).attr("status");
                var inside_temperature = $(this).attr("inside_temperature");
                var errors = $(this).attr("errors");
                var ajbs_down = $(this).attr("ajbs_down");
                var total_ajbs = $(this).attr("total_ajbs");

                $("#info_modal").modal({
                    showClose: false,
                    spinnerHtml: '<div class="loading" id="client_spinner"></div>',
                    showSpinner: true
                });

                var modal_info = $("#modal_info");
                modal_info.empty();

                if(status != "NA") {
                    modal_info.append("<div class='row text-center'><span class='text-bold'>Inverter Status: " + status + "</span></div>");
                }
                
                if(inside_temperature) {
                    modal_info.append("<div class='row text-center'><span class='text-bold'>Temp: " + inside_temperature + " &#8451;</span></div>");
                }

                if(ajbs_down > 0) {
                    modal_info.append("<div class='row text-center'><span class='text-bold'>AJBs Down: " + ajbs_down + "</span></div>");
                }

                if(errors != "undefined") {
                    modal_info.append("<br/><div class='row' id='errors_rows'></div>");

                    var errors_rows = $("#errors_rows");
                    errors_rows.empty();
                    errors_rows.append("<div class='row text-center'><span class='text-bold'>Errors in " + inverter_name + "</span></div><br/>");
                    errors_rows.append('<div"><table class="table table-vcenter"><thead><tr><th class="text-center min-width">Time</th><th class="text-center">Error Code</th></tr></thead><tbody id="table_errors"></tbody></table></div>');

                    var table_errors = $("#table_errors");
                    table_errors.empty();

                    var errors_array = errors.split(",");

                    for(var errors_row = 0; errors_row < errors_array.length; errors_row++) {
                        var present_error = errors_array[errors_row].split("-");
                        table_errors.append("<tr id='error_row"+errors_row+"'><td class='text-center'><span class='text-semibold'>" + present_error[0] + "</span></td><td class='text-center'><span class='text-semibold'>" + present_error[1] + "</span></td></tr>");
                    }
                }

                $("#modal_spinner").show();

                if(total_ajbs > 0) {
                    $.ajax({
                        type: "GET",
                        url: "/api/v1/solar/plants/".concat(plant_slug).concat('/live/'),
                        data: {device_type: "ajb", inverter: inverter_name},
                        success: function(inverter_ajb_data) {
                            var spd_status, dc_isolator_status;

                            if(inverter_ajb_data.ajbs.length) {

                                $("#info_modal").addClass("modal-width");

                                modal_info.append("<br/><div class='row text-center'><span class='text-2x text-bold'>All AJBs in " + inverter_name + "</span></div><br/>");
                                modal_info.append('<table class="table table-vcenter"><thead><tr><th class="text-center min-width">AJB Name</th><th class="text-center">Power (kW)</th><th class="text-center">Current (A)</th><th class="text-center">Voltage (V)</th><th class="text-center">Connection</th><th class="text-center">SPD Status</th><th class="text-center">DC Insolator Status</th></tr></thead><tbody id="table_data"></tbody></table>');

                                var table_data = $("#table_data");
                                table_data.empty();

                                for(var ajb_table_row = 0; ajb_table_row < inverter_ajb_data.ajbs.length; ajb_table_row++) {
                                    if(inverter_ajb_data.ajbs[ajb_table_row].last_spd_status) {
                                        if(inverter_ajb_data.ajbs[ajb_table_row].last_spd_status.length > 0) {
                                            spd_status = inverter_ajb_data.ajbs[ajb_table_row].last_spd_status[0].spd_status;
                                        } else {
                                            spd_status = "NA";
                                        }
                                    } else {
                                        spd_status = "NA";
                                    }

                                    if(inverter_ajb_data.ajbs[ajb_table_row].last_dc_isolator_status) {
                                        if(inverter_ajb_data.ajbs[ajb_table_row].last_dc_isolator_status.length > 0) {
                                            dc_isolator_status = inverter_ajb_data.ajbs[ajb_table_row].last_dc_isolator_status[0].dc_isolator_status;
                                        } else {
                                            dc_isolator_status = "NA";
                                        }
                                    } else {
                                        dc_isolator_status = "NA";
                                    }

                                    table_data.append("<tr id='modal_row"+ajb_table_row+"'><td class='text-center'><span class='text-semibold'>" + inverter_ajb_data.ajbs[ajb_table_row].name + "</span></td><td class='text-center'><span class='text-semibold'>" + (parseFloat(inverter_ajb_data.ajbs[ajb_table_row].power)).toFixed(1) + "</span></td><td class='text-center'><span class='text-semibold'>" + (parseFloat(inverter_ajb_data.ajbs[ajb_table_row].current)).toFixed(1) + "</span></td><td class='text-center'><span class='text-semibold'>" + (parseFloat(inverter_ajb_data.ajbs[ajb_table_row].voltage)).toFixed(1) + "</span></td><td class='text-center'><span class='text-semibold'>" + inverter_ajb_data.ajbs[ajb_table_row].connected + "</span></td><td class='text-center'><span class='text-semibold'>" + spd_status + "</span></td><td class='text-center'><span class='text-semibold'>" + dc_isolator_status + "</span></td></tr>");
                                }

                            } else {

                                /*noty_message("No Ajbs for " +  inverter_name + "!", "information", 4000);
                                return;*/

                            }

                            $("#modal_spinner").hide();
                        },
                        error: function(data) {
                            console.log("error_streams_data");

                            $("#modal_spinner").hide();

                            /*noty_message("No Ajbs for " +  inverter_name + "!", "information", 4000);
                            return;*/
                        }
                    });
                } else {
                    $("#modal_spinner").hide();
                }
            });
            
            $("#inverter_parameters_reading_"+i).click(function() {
                var inverter_name = $(this).attr("name");
                console.log(inverter_name);

                var modal_info = $("#modal_info");
                modal_info.empty();

                $.ajax({
                    type: "GET",
                    url: "/api/v1/solar/plants/".concat(plant_slug).concat('/live/'),
                    data: {device_type: "inverter", inverter: inverter_name},
                    success: function(dc_sld_data) {

                        if(dc_sld_data.dc_sld) {

                            if(dc_sld_data.dc_sld.length) {

                                $("#info_modal").modal({
                                    showClose: false,
                                    spinnerHtml: '<div class="loading" id="client_spinner"></div>',
                                    showSpinner: true
                                });

                                $("#info_modal").addClass("modal-width");

                                modal_info.empty();
                                modal_info.append("<div class='row text-center'><span class='text-2x text-bold'>All DC SLD in " + inverter_name + "</span></div><br/>");
                                modal_info.append('<table class="table table-vcenter"><thead><tr><th class="text-center">Parameters</th><th class="text-center">Values</th></tr></thead><tbody id="table_data"></tbody></table>');

                                var table_data = $("#table_data");
                                table_data.empty();

                                for(var sld = 0; sld < dc_sld_data.dc_sld.length; sld++) {
                                    table_data.append("<tr id='" + dc_sld_data.dc_sld[sld].name + "'><td class='text-center'><span class='text-semibold'>" + dc_sld_data.dc_sld[sld].name + "</span></td><td class='text-center'><span class='text-semibold'>" + dc_sld_data.dc_sld[sld].value + "</span></td></tr>");
                                }
                            }
                            
                        } else {

                            noty_message("No DC SLDs for " +  inverter_name + "!", "information", 4000);
                            return;

                        }

                        $("#modal_spinner").hide();
                    },
                    error: function(data) {
                        console.log("error_streams_data");

                        $("#modal_spinner").hide();

                        /*noty_message("No Ajbs for " +  inverter_name + "!", "information", 4000);
                        return;*/
                    }
                });
            });

        }
    
            if(first_call != 2) {
                $('#inverters_grid').isotope('destroy');
            }

          $inverter_grid = $('#inverters_grid').isotope({
              itemSelector: '.element-item',
              layoutMode: 'fitRows',
              getSortData: {
                  name: '.name',
                  energy: '.energy',
                  power: '.power',
                  connection: '[data-category]'
                  /*power: function( itemElem ) {
                      var power = $( itemElem ).find('.power').text();
                      return parseFloat( power );
                  }*/
              }
          });

          /*$(".ajbs_down").click(function(){
              $("#filter_click").empty();
              $("#filter_click").append('<div class="row">' + 
                      '<span class="total_ajbs_down text-danger pad-lft ' + total_ajbs_down_class + '">' + total_ajbs_down + '</span>' +
                  '</div>' +
                  '<div class="row">' + 
                      '<span class="total_ajbs_down_text text-danger pad-rgt ' + total_ajbs_down_class + '">AJBs <i class="fa fa-long-arrow-down" aria-hidden="true"></i></p>' + 
                  '</div>');
          });*/

          // filter functions
          var filterFns = {

            // show if number is greater than 50
            /*numberGreaterThan50: function() {
              var number = $(this).find('.number').text();
              return parseInt( number, 10 ) > 50;
            },
            // show if name ends with -ium
            ium: function() {
              var name = $(this).find('.name').text();
              return name.match( /ium$/ );
            }*/
          };

            // bind filter button click
            filters("#filters", $inverter_grid);

            // bind sort button click
            sorts("#sorts", $inverter_grid);

            // change is-checked class on buttons
            button_in_check();

          $(".selection_button").click(function() {
              var selection_checked = $(this).text();

              if(selection_checked == "Ajbs Down") {
                $(".inside_temperature").hide();
                $(".solar_status").hide();
                $(".ajbs_down").show();
              } else if(selection_checked == "Inside Temp.") {
                $(".ajbs_down").hide();
                $(".solar_status").hide();
                $(".inside_temperature").show();
              } else if(selection_checked == "Status") {
                $(".ajbs_down").hide();
                $(".inside_temperature").hide();
                $(".solar_status").show();
              }

              filters("#filters", $grid);
          })

          $(".loader").hide();

          ajbs(first_call);

        },
        error: function(data) {
            console.log("error_streams_data");
            data = null;

            $(".loader").hide();
        }
    });

}

function ajbs(first_call) {

    $("#ajbs_filters_and_sorts").empty();
    $("#ajbs_filters_and_sorts").append('<div class="row">' + 
                                        '<div class="col-lg-6 col-md-6 col-sm-6">  <h3 class="text-info">Filter</h3>' + 
                                          '<div id="ajbs_filters" class="btn-group">' + 
                                            '<button class="btn btn-default is-checked" data-filter="*">Show All</button>' + 
                                            '<button class="btn btn-default" data-filter=".connected">Generating</button>' + 
                                            '<button class="btn btn-default" data-filter=".unknown">Alarms</button>' + 
                                            '<button class="btn btn-default" data-filter=".disconnected">Invalid</button>' + 
                                          '</div>' + 
                                        '</div>' + 
                                        '<div class="col-lg-6 col-md-6 col-sm-6">' + 
                                          '<h3 class="text-info">Sort</h3>' + 
                                          '<div id="ajbs_sorts" class="btn-group">' + 
                                            '<button class="btn btn-default is-checked" data-sort-by="original-order">Original Order</button>' + 
                                            '<button class="btn btn-default" data-sort-by="current">Current</button>' + 
                                            '<button class="btn btn-default" data-sort-by="ajb_power">Ajb Power</button>' + 
                                          '</div>' + 
                                        '</div>' + 
                                      '</div>');

  $.ajax({
        type: "GET",
        url: "/api/v1/solar/plants/".concat(plant_slug).concat('/live/'),
        data: {device_type: "ajb"},
        success: function(data) {
            if(data.ajbs.length) {

                var devices = "", devices_subtitle = "";

                if(client_slug == "edp") {
                    devices = "Panels";
                    devices_subtitle = "Grid View of Panels.";
                } else {
                    devices = 'Inverters and Ajbs';
                    devices_subtitle = "Grid View of Inverters and Ajbs.";
                }

                $("#device_list").show();
                $("#inverters_title").empty();
                $("#inverters_title").append(devices);
                $("#inverters_subtitle").empty();
                $("#inverters_subtitle").append(devices_subtitle);
                $("#ajbs_grid").empty();

                var connection, connection_status, group_name, group_name_class, spd_status, spd_status_class, spd_status_text;

                for(var i = 0; i < data.ajbs.length; i++) {
                    if(data.ajbs[i].solar_group != "NA") {
                        group_name = data.ajbs[i].solar_group;
                        group_name_class = "shows";
                    } else {
                        group_name_class = "hidden";
                    }

                    if(data.ajbs[i].connected == "connected") {
                        connection_status = "connected";
                        connection = "connected";
                        connection_text_color_status = "badge-success";
                    } else if(data.ajbs[i].connected == "disconnected") {
                        connection_status = "disconnected";
                        connection = "disconnected";
                        connection_text_color_status = "badge-warning";
                    } else {
                        connection_status = "communictaion error";
                        connection = "unknown";
                        connection_text_color_status = "badge-info";
                    }

                    /*if(data.ajbs[i].last_spd_status) {
                        if(data.ajbs[i].last_spd_status["0"]) {
                            if(data.inverters[i].ajbs[i].last_spd_status[0].spd_status) {
                                spd_status = data.inverters[i].last_inverter_status["0"].status;
                                spd_status_class = "show";
                            } else {
                                spd_status_class = "hidden";
                            }
                        } else {
                            spd_status_class = "hidden";
                        }
                    } else {
                        spd_status_class = "hidden";
                    }*/

                  $("#ajbs_grid").append('<div class="element-item col-lg-3 col-md-3 col-sm-12 col-xs-12 panel" data-category="' + connection + '" id="ajb_'+i+'" style="background-color: white;padding-bottom: 5px;">' +
        '<div class="row pad-lft">' +  
              '<div class="row">' + 
                  '<div class="pull-left"><span class="current text-2x text-dark text-bold">' + parseFloat(data.ajbs[i].current).toFixed(1) + '</span><span class="power_unit text-dark text-bold" style="font-size: small" id="current_unit"> A</span></div>' +
              '</div>' +
              '<div class="row">' + 
                  '<div class="pull-left"><p class="power_text text-dark text-sm text-bold">Current</p></div>' + 
              '</div>' +
          '</div>' +
          '<div class="row pad-lft">' + 
            '<div class="row">' + 
                '<span class="ajb_power text-dark text-bold text-2x">' + (parseFloat(data.ajbs[i].power)).toFixed(1) + '</span><span class="text-dark text-bold" style="font-size: small" id="power_unit"> kW</span>' +
            '</div>' +
            '<div class="row">' + 
                '<p class="energy_text text-bold text-dark text-sm">Power</p>' + 
            '</div>' + 
            '<div class="row">' +
                '<span class="ajb_name badge text-lg '+ connection_text_color_status +'" style="border-radius: 0px;">' + data.ajbs[i].name + '</span> <span class="group_name badge text-lg '+ connection_text_color_status +' ' + group_name_class + '" style="border-radius: 0px;">' + data.ajbs[i].solar_group + '</span>' +
            '</div>' +
          '</div>' +
        '</div>');

                  $("#ajb_"+i).removeClass("connected");
                  $("#ajb_"+i).removeClass("disconnected");
                  $("#ajb_"+i).removeClass("unknown");
                  $("#ajb_"+i).addClass(connection);
                }

                if(first_call != 2) {
                    $('#ajbs_grid').isotope('destroy');
                }

                $ajb_grid = $('#ajbs_grid').isotope({
                    itemSelector: '.element-item',
                    layoutMode: 'fitRows',
                    getSortData: {
                        ajb_name: '.ajb_name',
                        current: '.current',
                        ajb_power: '.ajb_power',
                        connection: '[data-category]',
                        /*power: function( itemElem ) {
                            var power = $( itemElem ).find('.power').text();
                            return parseFloat( power );
                        }*/
                    }
                });

                // filter functions
                var filterFns = {
                // show if number is greater than 50
                /*numberGreaterThan50: function() {
                  var number = $(this).find('.number').text();
                  return parseInt( number, 10 ) > 50;
                },
                // show if name ends with -ium
                ium: function() {
                  var name = $(this).find('.name').text();
                  return name.match( /ium$/ );
                }*/
                };

                // bind filter button click
                filters("#ajbs_filters", $ajb_grid);

                // bind sort button click
                sorts("#ajbs_sorts", $ajb_grid);

                // change is-checked class on buttons
                button_in_check();
            }
        },
        error: function(data) {
            console.log("error_streams_data");
            data = null;

            $(".loader").hide();
        }
    });

}

function filters(id, grid) {

    $(id).on( 'click', 'button', function() {
        var filterValue = $( this ).attr('data-filter');
        grid.isotope({ filter: filterValue });
    });
}

function sorts(id, grid) {

    $(id).on( 'click', 'button', function() {
        var sortByValue = $(this).attr('data-sort-by');
        console.log($(this).attr('data-sort-by'));
        grid.isotope({ sortBy: sortByValue });
    });

}

function button_in_check() {

    $('.btn-group').each( function( i, buttonGroup ) {
        var $buttonGroup = $( buttonGroup );
        $buttonGroup.on( 'click', 'button', function() {
            $buttonGroup.find('.is-checked').removeClass('is-checked');
            $( this ).addClass('is-checked');
        });
    });
}

function energy_meters_and_transformers() {

    $.ajax({
        type: "GET",
        url: "/api/v1/solar/plants/".concat(plant_slug).concat('/live/ac/?device_type=meter'),
        success: function(data) {
            console.log(data);

            $("#energy_meters_grid").empty();

            if(data.meters.length > 0) {

                var energy_meter_power, energy_meter_energy_generation;

                for(var i = 0; i < data.meters.length; i++) {
                    if(data.meters[i].solar_group != "NA") {
                        group_name = data.meters[i].solar_group;
                        group_name_class = "shows";
                    } else {
                        group_name_class = "hidden";
                    }

                    if(data.meters[i].connected == "connected") {
                        connection_status = "connected";
                        connection = "connected";
                        connection_text_color_status = "badge-success";
                        button_color = "btn-success";
                    } else if(data.meters[i].connected == "disconnected") {
                        connection_status = "disconnected";
                        connection = "disconnected";
                        connection_text_color_status = "badge-warning";
                        button_color = "btn-warning";
                    } else {
                        connection_status = "communictaion error";
                        connection = "unknown";
                        connection_text_color_status = "badge-info";
                        button_color = "btn-info";
                    }

                    energy_meter_power = (data.meters[i].power).split(" ");
                    energy_meter_energy_generation = (data.meters[i].generation).split(" ");

                  $("#energy_meters_grid").append('<div class="element-item col-lg-3 col-md-3 col-sm-12 col-xs-12 panel" data-category="' + connection + '" id="energy_meter_'+i+'" style="background-color: white;padding-bottom: 5px;">' +
    '<div class="row pad-lft">' +  
          '<div class="row">' + 

              '<div class="pull-left"><span class="power text-2x text-dark text-bold">' + energy_meter_power[0] + '</span><span class="power_unit text-dark text-bold" style="font-size: small" id="power_unit"> ' + energy_meter_power[1] + '</span></div>' +

          '</div>' +
          '<div class="row">' + 
              '<div class="pull-left"><p class="power_text text-dark text-sm text-bold">Current Power</p></div>' + 
          '</div>' +
      '</div>' +
      '<div class="row pad-lft">' + 
        '<div class="row">' + 

            '<span class="energy text-dark text-bold text-2x">' + energy_meter_energy_generation[0] + '</span><span class="text-dark text-bold" style="font-size: small" id="energy_unit"> ' + energy_meter_energy_generation[1] + '</span>' + 

        '</div>' +
        '<div class="row">' + 
            '<p class="energy_text text-bold text-dark text-sm">Generation Today</p>' + 
        '</div>' + 
        '<div class="row">' +
            '<span class="name badge text-lg '+ connection_text_color_status +'" style="border-radius: 0px;">' + data.meters[i].name + '</span> <span class="group_name badge text-lg '+ connection_text_color_status +' ' + group_name_class + '" style="border-radius: 0px;">' + data.meters[i].solar_group + '</span>' +
        '</div>' +
        '<div class="row" style="padding-top: 1vh;">' +
            '<button id="energy_meters_parameters_reading_' + i + '" name="' + data.meters[i].name + '" class="btn btn-xs text-bold ' + button_color + '">Parameter Readings</button>' +
        '</div>' +
      '</div>' +
    '</div>');

                  $("#energy_meter_"+i).removeClass("connected");
                  $("#energy_meter_"+i).removeClass("disconnected");
                  $("#energy_meter_"+i).removeClass("unknown");
                  $("#energy_meter_"+i).addClass(connection);

                    $("#energy_meters_parameters_reading_"+i).click(function() {
                        var energy_meter_name = $(this).attr("name");
                        console.log(energy_meter_name);

                        var modal_info = $("#modal_info");
                        modal_info.empty();

                        $.ajax({
                            type: "GET",
                            url: "/api/v1/solar/plants/".concat(plant_slug).concat('/live/ac/'),
                            data: {device_type: "meter", meter: energy_meter_name},
                            success: function(ac_sld_data) {

                                if(ac_sld_data.ac_sld) {

                                    if(ac_sld_data.ac_sld.length) {

                                        $("#info_modal").modal({
                                            showClose: false,
                                            spinnerHtml: '<div class="loading" id="client_spinner"></div>',
                                            showSpinner: true
                                        });

                                        $("#info_modal").addClass("modal-width");

                                        modal_info.empty();
                                        modal_info.append("<div class='row text-center'><span class='text-2x text-bold'>All AC SLD in " + energy_meter_name + "</span></div><br/>");
                                        modal_info.append('<table class="table table-vcenter"><thead><tr><th class="text-center">Parameters</th><th class="text-center">Values</th></tr></thead><tbody id="table_data"></tbody></table>');

                                        var table_data = $("#table_data");
                                        table_data.empty();

                                        for(var sld = 0; sld < ac_sld_data.ac_sld.length; sld++) {
                                            table_data.append("<tr id='" + ac_sld_data.ac_sld[sld].name + "'><td class='text-center'><span class='text-semibold'>" + ac_sld_data.ac_sld[sld].name + "</span></td><td class='text-center'><span class='text-semibold'>" + ac_sld_data.ac_sld[sld].value + "</span></td></tr>");
                                        }
                                    }
                                    
                                } else {

                                    noty_message("No AC SLDs for " +  energy_meter_name + "!", "information", 4000);
                                    return;

                                }

                                $("#modal_spinner").hide();
                            },
                            error: function(data) {
                                console.log("error_streams_data");

                                $("#modal_spinner").hide();

                                noty_message("No AC SLDs for " +  energy_meter_name + "!", "information", 4000);
                                return;
                            }
                        });
                    });
                }
            } else {

                $("#energy_meters_grid").append("<div class='row text-center'><div class='text-bold'>No Energy Meters Present!</div></div>");

            }
        },
        error: function(data) {
            console.log("error_streams_data");
            data = null;

            $("#energy_meters_grid").empty();
            $("#energy_meters_grid").append("<div class='row text-center'><div class='text-bold'>No Energy Meters Present!</div></div>");
        }
    });

    $.ajax({
        type: "GET",
        url: "/api/v1/solar/plants/".concat(plant_slug).concat('/live/ac/?device_type=transformer'),
        success: function(data) {
            console.log(data);

            $("#transformers_grid").empty();

            if(data.transformers.length > 0) {

                for(var i = 0; i < data.transformers.length; i++) {
                    if(data.transformers[i].connected == "connected") {
                        connection_status = "connected";
                        connection = "connected";
                        connection_text_color_status = "badge-success";
                    } else if(data.transformers[i].connected == "disconnected") {
                        connection_status = "disconnected";
                        connection = "disconnected";
                        connection_text_color_status = "badge-warning";
                    } else {
                        connection_status = "communictaion error";
                        connection = "unknown";
                        connection_text_color_status = "badge-info";
                    }

                  $("#transformers_grid").append('<div class="element-item col-lg-3 col-md-3 col-sm-12 col-xs-12 panel" data-category="' + connection + '" id="transformer_'+i+'" style="background-color: white;padding-bottom: 5px;">' +
    '<div class="row pad-lft">' +  
          '<div class="row">' + 
              '<span class="oti text-2x text-dark text-bold">' + data.transformers[i].OTI + '</span>' +
          '</div>' +
          '<div class="row">' + 
              '<p class="oti_text text-dark text-sm text-bold">OTI</p>' + 
          '</div>' +
      '</div>' +
      '<div class="row pad-lft">' + 
        '<div class="row">' + 
            '<span class="wti text-dark text-bold text-2x">' + data.transformers[i].WTI + '</span>' + 
        '</div>' +
        '<div class="row">' + 
            '<p class="wti_text text-bold text-dark text-sm">WTI</p>' + 
        '</div>' + 
        '<div class="row">' +
            '<span class="name badge text-lg '+ connection_text_color_status +'" style="border-radius: 0px;">' + data.transformers[i].name + '</span>' +
        '</div>' +
      '</div>' +
    '</div>');

                  $("#transformer_"+i).removeClass("connected");
                  $("#transformer_"+i).removeClass("disconnected");
                  $("#transformer_"+i).removeClass("unknown");
                  $("#transformer_"+i).addClass(connection);

                }
            } else {

                $("#transformers_grid").append("<div class='row text-center'><div class='text-bold'>No Transformers Present!</div></div>");

            }
        },
        error: function(data) {
            console.log("error_streams_data");
            data = null;

            $("#transformers_grid").empty();
            $("#transformers_grid").append("<div class='row text-center'><div class='text-bold'>No Transformers Present!</div></div>");
        }
    });

}

$(document).ajaxComplete(function(event, request, settings) {
    console.log("active AJAX calls", $.active);
    if (first_page_load == true && $.active == 1) {
        console.log("calling mixpanel");
        page_load_time = new Date() - page_load_time;
        console.log("page load time: ", page_load_time.toString().concat(" ms"))
        var load_time = page_load_time.toString().concat(" ms");
        mixpanel.track(
        "Plant summary page loaded",
        {"load_time": load_time,
         "plant_slug": plant_slug,
         "user_email": user_email}
        );
        first_page_load = false;
    }
    console.log("first load: ", first_page_load);
});

$("#datepicker_selected_picker").change(function() {

    $("#client_spinner").show();

    st = $(".datepicker_start_days").val();

    console.log(st);

    if(st == "") {
        $("#power_irradiation-before").addClass("disabled");
        $("#power_irradiation-next").addClass("disabled");
    } else {
        $("#power_irradiation-before").removeClass("disabled");
        $("#power_irradiation-next").removeClass("disabled");
    }

    date_changes();

})

function date_changes() {

    var new_dates = get_dates();

    st = new_dates[0];
    et = new_dates[1];

    power_irradiation_chart(st, et);
    plant_summary_date(st);

}

$("#power_irradiation-before").on('click', function() {
    if($("#power_irradiation-before").hasClass("disabled") == false) {
        st = $(".datepicker_start_days").val();

        if(st == "") {
            st = new Date();
        } else {
            st = st.split("-");
            st = st[2] + "-" + st[1] + "-" +st[0];
            st = new Date(st);    
        }
        st.setDate(st.getDate() - 1);
        st = dateFormat(st, "dd-mm-yyyy");

        $(".datepicker_start_days").val(st);
        date_changes();
    }
})

$("#power_irradiation-next").on('click', function() {
    if($("#power_irradiation-next").hasClass("disabled") == false) {
        st = $(".datepicker_start_days").val();

        if(st == "") {
            st = new Date();
        } else {
            st = st.split("-");
            st = st[2] + "-" + st[1] + "-" +st[0];
            st = new Date(st);
        }
        st.setDate(st.getDate() + 1);
        st = dateFormat(st, "dd-mm-yyyy");

        $(".datepicker_start_days").val(st);
        date_changes();
    }
})

function plant_summary_date(st) {

    $.ajax({
        type: "GET",
        url: "/api/v1/solar/plants/".concat(plant_slug).concat("/summary/"),
        data: {date: (st)},
        success: function(summary_data_change){
            
            var objectData = jQuery.isEmptyObject(summary_data_change);

            if(objectData == false) {
                
                set_variable_value($("#specific_yield_todays"), summary_data_change.specific_yield || '0');
                
                set_variable_value($("#pvsyst_generation"), (summary_data_change.pvsyst_generation || "NA"));
                check_element((summary_data_change.pvsyst_generation || "NA"), 'pvsyst_generation_today_div', "");

                var plant_generation_today = (summary_data_change.generation || "0 MWh").split(" ");
                if (plant_generation_today.length == 2) {
                    set_variable_value($("#plant_today_generation"), plant_generation_today[0] + '<span style="font-size: small" id="plant_today_generation_unit"> '+ plant_generation_today[1] +'</span>');
                } else {
                    set_variable_value($("#plant_today_generation"), 0 + '<span style="font-size: small" id="plant_today_generation_unit"> '+ ' kWp' +'</span>');
                }

                set_variable_value($("#pvsyst_generation"), (summary_data_change.pvsyst_generation || "NA"));
                check_element((summary_data_change.pvsyst_generation || "NA"), 'pvsyst_generation_today_div', "");

                set_variable_value($("#last_updated_time"), "Updated: ".concat((moment(summary_data_change.timestamp).format("HH:mm:ss") || "Not Available")));

                set_variable_value($("#performance_ratio_today"), (parseFloat(summary_data_change.performance_ratio*100).toFixed(1).toString()) + "%" || "0 %");

                if (summary_data_change.performance_ratio != 0.0) {
                    $("#summary_performance_ratio").show();
                } else {
                    $("#summary_performance_ratio").hide();
                }

                set_variable_value($("#pvsyst_pr"), (parseFloat(summary_data_change.pvsyst_pr*100).toFixed(1).toString()) + "%" || "NA");
                check_element((summary_data_change.pvsyst_pr || "NA"), 'pvsyst_pr_div', "pr_div");

                if (show_cuf == true){
                    set_variable_value($("#cuf_text"), "CUF");
                    set_variable_value($("#cuf_todays"), (parseFloat(summary_data_change.cuf*100).toFixed(1).toString()) + "%" || "0 %");
                    set_variable_value($("#cuf_unit"), "Today's");
                    set_variable_value($("#pvsyst_cuf"), (parseFloat(summary_data_change.pvsyst_cuf).toFixed(1).toString()) + "kW" || "0 kW");
                    check_element((summary_data_change.pvsyst_cuf || "NA"), 'pvsyst_cuf_div', "cuf_div");
                    set_variable_value($("#pvsyst_cuf_unit"), "PVsyst");
                }

                var co2_savings = (summary_data_change.plant_co2 || "0 Ton").split(" ");
                if (co2_savings.length == 2) {
                    set_variable_value($("#co2_value"), co2_savings[0] + '<span style="font-size: small" id="co2_value_unit"> '+ co2_savings[1] +'</span>');
                } else {
                    set_variable_value($("#co2_value"), 0 + '<span style="font-size: small" id="co2_value_unit"> '+ ' Ton' +'</span>');
                }

                if (client_name != "Asun Solar") {
                    set_variable_value($("#predicted_plant_generation_today"), (summary_data_change.predicted_energy || "NA"));
                    set_variable_value($("#predicted_plant_generation_text"), "Predicted");
                }

                var insolation = (summary_data_change.insolation + " kWh/m^2" || "NA");
                set_variable_value($("#insolation"), insolation);

            } else {

                $("#client_spinner").hide();

                noty_message("No summary data for the chosen date!", 'error', 5000)
                return;

            }

            $("#client_spinner").hide();

        },
        error: function(data){
            console.log("no data");

            $("#client_spinner").hide();

            noty_message("No summary data for the chosen date!", 'error', 5000)
            return;
        }
    });

}
