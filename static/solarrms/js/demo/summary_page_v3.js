$(document).ready(function() {

    $("#breadcrumb_page_path").empty();
    $("#breadcrumb_page_path").append('<li class="text-center text-bold" ><a href="#">Client</a></li><li class="text-center text-bold"><a href="#">Client Dashboard</a></li><li class="text-center text-bold"><a href="#">Plant Dashboard</a></li>')

    $(function () {
      $('[data-toggle="tooltip"]').tooltip()
    })

    var client_data = null;
    var bounds_leaflet_map = null;
    var map = null;
    dashboard_clients();

    var dates = get_dates();
    var st = dates[0];
    var et = dates[1];

    power_irradiation_chart(st, et);

    $("#loading_row").hide();

    setInterval(function () {
        $("#loading_row").show();

        client_data = null;
        bounds_leaflet_map = null;
        map = null;
        dashboard_clients();

        dates = get_dates();
        st = dates[0];
        et = dates[1];

        power_irradiation_chart(st, et);        

        $("#loading_row").hide();
    }, 5000*60);

});

function get_dates(){
    // get the start date
    /*var st = $(id).val();*/
    var st = new Date();
    /*if (st == '')
        st = new Date();
    else
        st = new Date(st);*/
    // prepare an end date
    var e = new Date(st.getTime());
    e = new Date(e.setDate(st.getDate() + 1));
    // convert them into strings

    st = dateFormat(st, "yyyy-mm-dd");
    e = dateFormat(e, "yyyy-mm-dd");

    return [st, e];
}

function dashboard_clients() {

    $.ajax({
        type: "GET",
        async: false,
        url : "/api/v1/solar/plants/".concat(plant_slug).concat("/summary/"),
        success: function(summary_info){            
            client_data = summary_info;

            weather_current(summary_info.plant_location, summary_info);

            $("#client_logo").empty();
            $("#client_logo").append("<img class='mar-btm' src='" + summary_info.plant_logo + "' alt='Client Logo' style='width: 8vw;'>");

            if(summary_info.plant_name) {
                $("#client_name").empty();
                $("#client_name").append(summary_info.plant_name);
            } else {
                $("#client_name").empty();
                $("#client_name").append("N/A");
            }

            /*$("#current_power").empty();
            $("#current_power").append(summary_info.current_power + " kW");*/

            var plant_energy_today;

            if(summary_info.plant_generation_today) {
                plant_energy_today = summary_info.plant_generation_today;
                plant_energy_today = plant_energy_today.split(" ");
                plant_energy_today = plant_energy_today[0] + '<span style="font-size: small" id="plant_generation_today_unit"> '+ plant_energy_today[1] +'</span>';
            } else {
                plant_energy_today = "N/A";
            }

            $("#plant_today_generation").empty();
            $("#plant_today_generation").append(plant_energy_today);

            var plant_total_energy;

            if(summary_info.plant_total_energy) {
                plant_total_energy = summary_info.plant_total_energy;
            } else {
                plant_total_energy = "N/A";
            }

            $("#plant_total_energy").empty();
            $("#plant_total_energy").append(plant_total_energy);

            var pvsyst_generation;

            if(summary_info.pvsyst_generation) {
                pvsyst_generation = summary_info.pvsyst_generation;
            } else {
                pvsyst_generation = "N/A";
            }

            $("#pvsyst_generation").empty();
            $("#pvsyst_generation").append(pvsyst_generation);

            var predicted_generation;

            if(summary_info.predicted_generation) {
                predicted_generation = summary_info.predicted_generation;
            } else {
                predicted_generation = "N/A";
            }

            $("#predicted_plant_generation_today").empty();
            $("#predicted_plant_generation_today").append(predicted_generation);

            if(summary_info.plant_name) {
                $("#plant_name").empty();
                $("#plant_name").append(summary_info.plant_name);
            } else {
                $("#plant_name").empty();
                $("#plant_name").append("N/A");
            }

            if(summary_info.plant_location) {
                $("#plant_location").empty();
                $("#plant_location").append(summary_info.plant_location);
            } else {
                $("#plant_location").empty();
                $("#plant_location").append("N/A");
            }

            if(summary_info.plant_capacity) {
                var dc_capacity = summary_info.plant_capacity;
                dc_capacity = dc_capacity.split(" ");

                $("#dc_capacity").empty();
                $("#dc_capacity").append(dc_capacity[0] + '<span style="font-size: small" id="dc_capacity_unit"> '+ dc_capacity[1] +'</span>');
            } else {
                $("#dc_capacity").empty();
                $("#dc_capacity").append("N/A");
            }

            if(typeof summary_info.module_temperature !== 'undefined') {
                var module_temperature = summary_info.module_temperature;

                $("#module_temperature").empty();
                $("#module_temperature").append(module_temperature + " &#8451;");
            } else {
                $("#module_temperature").empty();
                $("#module_temperature").append("N/A");
            }

            if(typeof summary_info.panel_details.numbers !== 'undefined') {
                var panel_numbers = summary_info.panel_details.numbers;

                $("#panel_numbers").empty();
                $("#panel_numbers").append(panel_numbers);
            } else {
                $("#panel_numbers").empty();
                $("#panel_numbers").append("N/A");
            }

            if(typeof summary_info.panel_details.make !== 'undefined') {
                var panel_make = summary_info.panel_details.make;

                $("#panel_make").empty();
                $("#panel_make").append(panel_make);
            } else {
                $("#panel_make").empty();
                $("#panel_make").append("N/A");
            }

            if(typeof summary_info.panel_details.capacity !== 'undefined') {
                var panel_capacity = summary_info.panel_details.capacity;

                $("#panel_capacity").empty();
                $("#panel_capacity").append(panel_capacity.toString() + ' kWp');
            } else {
                $("#panel_capacity").empty();
                $("#panel_capacity").append("N/A");
            }


            //inverters details
            if(typeof summary_info.inverter_details.numbers !== 'undefined') {
                var inverters_number = summary_info.inverter_details.numbers;

                $("#inverters_number").empty();
                $("#inverters_number").append(inverters_number);
            } else {
                $("#inverters_number").empty();
                $("#inverters_number").append("N/A");
            }

            if(typeof summary_info.inverter_details.make !== 'undefined') {
                var inverters_make = summary_info.inverter_details.make;
                var inverters_model = null;
                var text = null;

                if(typeof summary_info.inverter_details.model !== 'undefined') {
                    inverters_model = summary_info.inverter_details.model;
                    text = inverters_make + ", " + inverters_model;
                } else {
                    text = inverters_make;
                }
                $("#inverters_make").empty();
                $("#inverters_make").append(text);
            } else {
                $("#inverters_make").empty();
                $("#inverters_make").append("N/A");
            }

            if(typeof summary_info.inverter_details.capacity !== 'undefined') {
                var inverters_capacity = summary_info.inverter_details.capacity;

                $("#inverters_capacity").empty();
                $("#inverters_capacity").append(inverters_capacity.toString() + ' kW');
            } else {
                $("#inverters_capacity").empty();
                $("#inverters_capacity").append("N/A");
            }

            var insolation;

            if(summary_info.past_kwh_per_meter_square) {
                insolation = summary_info.past_kwh_per_meter_square[(summary_info.past_kwh_per_meter_square.length)-1].kwh_value;
                insolation = insolation.split(" ");
                insolation = insolation[0] + '<span style="font-size: small" id="insolation_unit"> '+ insolation[1] +'</span>'
            } else {
                insolation = "N/A";
            }

            $("#insolation").empty();
            $("#insolation").append(insolation);

            var pvsyst_ghi;

            if(summary_info.pvsyst_ghi) {
                pvsyst_ghi = summary_info.pvsyst_ghi;
                pvsyst_ghi = pvsyst_in_plane.split(" ");
                pvsyst_ghi = pvsyst_in_plane[0] + '<span style="font-size: small" id="pvsyst_ghi_unit"> '+ pvsyst_in_plane[1] +'</span>'
            } else {
                pvsyst_ghi = "N/A";
            }

            $("#pvsyst_ghi").empty();
            $("#pvsyst_ghi").append(pvsyst_ghi);

            var pvsyst_in_plane;

            if(summary_info.pvsyst_in_plane) {
                pvsyst_in_plane = summary_info.pvsyst_in_plane;
                pvsyst_in_plane = pvsyst_in_plane.split(" ");
                pvsyst_in_plane = pvsyst_in_plane[0] + '<span style="font-size: small" id="pvsyst_in_plane_unit"> '+ pvsyst_in_plane[1] +'</span>'
            } else {
                pvsyst_in_plane = "N/A";
            }

            $("#pvsyst_in-plane").empty();
            $("#pvsyst_in-plane").append(pvsyst_in_plane);

            var diesel_saved;

            if(summary_info.diesel_saved) {
                diesel_saved = summary_info.diesel_saved;
                diesel_saved = diesel_saved.split(" ");
                diesel_saved = diesel_saved[0] + '<span style="font-size: small" id="diesel_saved_unit"> '+ diesel_saved[1] +'</span>'
            } else {
                diesel_saved = "N/A";
            }

            $("#diesel_saved").empty();
            $("#diesel_saved").append(diesel_saved);

            var distance_travelled;

            if(summary_info.distance_travelled) {
                distance_travelled = summary_info.distance_travelled;
                distance_travelled = diesel_saved.split(" ");
                distance_travelled = diesel_saved[0] + '<span style="font-size: small" id="distance_travelled_unit"> '+ distance_travelled[1] +'</span>'
            } else {
                distance_travelled = "N/A";
            }

            $("#distance_travelled").empty();
            $("#distance_travelled").append(distance_travelled);

            var smbs;

            if(typeof summary_info.connected_smbs !== 'undefined' && typeof summary_info.disconnected_smbs !== 'undefined' && typeof summary_info.invalid_smbs !== 'undefined') {
                smbs = summary_info.connected_smbs + summary_info.disconnected_smbs + summary_info.invalid_smbs;
            } else {
                smbs = "N/A";
            }

            $("#smbs").empty();
            $("#smbs").append(smbs);

            var plant_total_generation;
            
            if(summary_info.plant_total_energy) {
                plant_total_generation = summary_info.plant_total_energy;
                plant_total_generation = plant_total_generation.split(" ");
                plant_total_generation = plant_total_generation[0] + '<span style="font-size: small" id="plant_total_generation_unit"> '+ plant_total_generation[1] +'</span>';
            } else {
                plant_total_generation = "N/A";
            }

            $("#plant_total_generation").empty();
            $("#plant_total_generation").append(plant_total_generation);

            var co2_savings;

            if(summary_info.plant_co2) {
                co2_savings = summary_info.plant_co2;
                co2_savings = co2_savings.split(" ");
                co2_savings = co2_savings[0] + '<span style="font-size: small" id="insolation_unit"> '+ co2_savings[1] +'</span>';
            } else {
                co2_savings = "N/A";
            }

            $("#co2_value").empty();
            $("#co2_value").append(co2_savings);

            var performance_ratio;

            if(summary_info.performance_ratio) {
                performance_ratio = summary_info.performance_ratio;
                performance_ratio = (parseFloat(performance_ratio* 100).toFixed(1).toString() ) + "%";
            } else {
                performance_ratio = "N/A";
            }

            $('#performance_ratio_today').append(performance_ratio);

            var pvsyst_pr;

            if(summary_info.pvsyst_pr) {
                pvsyst_pr = summary_info.pvsyst_pr;
                pvsyst_pr = (parseFloat(pvsyst_pr* 100).toFixed(1).toString() ) + "%";
            } else {
                pvsyst_pr = "N/A";
            }

            $('#pvsyst_pr').append(pvsyst_pr);

            var cuf_percentage;

            if(summary_info.cuf) {
                cuf_percentage = summary_info.cuf;
                cuf_percentage = (parseFloat(cuf_percentage* 100).toFixed(1).toString() ) + "%";
            } else {
                cuf_percentage = "N/A";
            }

            $("#cuf_todays").empty();
            $("#cuf_todays").append(cuf_percentage);

            var pvsyst_cuf;

            if(summary_info.pvsyst_cuf) {
                pvsyst_cuf = summary_info.pvsyst_cuf;
                pvsyst_cuf = (parseFloat(pvsyst_cuf* 100).toFixed(1).toString() ) + "%";
            } else {
                pvsyst_cuf = "N/A";
            }

            $("#pvsyst_cuf").empty();
            $("#pvsyst_cuf").append(pvsyst_cuf);

            var specific_yield;

            if(summary_info.specific_yield) {
                specific_yield = summary_info.specific_yield;
            } else {
                specific_yield = "N/A";
            }

            $("#specific_field_todays").empty();
            $("#specific_field_todays").append(specific_yield);

            var specific_yield_pvsyst;

            if(summary_info.pvsyst_specific_yield) {
                specific_yield_pvsyst = summary_info.pvsyst_specific_yield;
            } else {
                specific_yield_pvsyst = "N/A";
            }

            $("#pvsyst_specific_yield").empty();
            $("#pvsyst_specific_yield").append(specific_yield_pvsyst);

            var device_down;

            if(typeof summary_info.disconnected_inverters !== 'undefined' && typeof summary_info.disconnected_smbs !== 'undefined') {
                device_down = summary_info.disconnected_inverters + summary_info.disconnected_smbs;
            } else {
                device_down = "N/A";
            }

            $("#devices_down").empty();
            $("#devices_down").append(device_down);

            var alarms_raised;

            if(typeof summary_info.total_inverter_error_numbers !== 'undefined') {
                alarms_raised = summary_info.total_inverter_error_numbers;
            } else {
                alarms_raised = "N/A";
            }

            $("#alarms_raised").empty();
            $("#alarms_raised").append(alarms_raised);

            var inverters_panel_need_cleaning;

            if(summary_info.plant_inverter_cleaning_details && summary_info.plant_inverter_cleaning_details.length > 0) {
                inverters_panel_need_cleaning = summary_info.plant_inverter_cleaning_details[0].inverters_required_cleaning_numbers;
            } else {
                inverters_panel_need_cleaning = "N/A";
            }

            $("#inverters_panel_need_cleaning").empty();
            $("#inverters_panel_need_cleaning").append(inverters_panel_need_cleaning);

            var predictive_issues;

            if(typeof summary_info.total_high_anomaly_smb_numbers != 'undefined' && typeof summary_info.total_low_anomaly_smb_numbers != 'undefined') {
                predictive_issues = parseInt(summary_info.total_low_anomaly_smb_numbers) + parseInt(summary_info.total_high_anomaly_smb_numbers);
            } else {
                predictive_issues = "N/A";
            }

            $("#predictive_issues").empty();
            $("#predictive_issues").append(predictive_issues);

            /*var total_plants = summary_info.plants.length;

            $("#total_plants").empty();
            $("#total_plants").append(total_plants);

            var total_energy_generation = summary_info.total_energy;
            total_energy_generation = total_energy_generation.split(" ");

            $("#total_energy_generation").empty();
            $("#total_energy_generation").append(total_energy_generation[0] + '<span style="font-size: small" id="total_energy_generation_unit"> '+ total_energy_generation[1] +'</span>');

            var net_assets = summary_info.total_capacity;
            net_assets = net_assets.split(" ");

            $("#net_assets_value").empty();
            $("#net_assets_value").append(net_assets[0] + '<span style="font-size: small" id="net_assets_unit"> '+net_assets[1]+'</span>');

            var live_plants = 0;

            for(var each_plant = 0; each_plant < summary_info.plants.length; each_plant++) {
                if(summary_info.plants[each_plant].status == "connected") {
                    live_plants++;
                }
            }

            $("#live_plants").empty();
            $("#live_plants").append(live_plants);*/

            var prediction_deviation = summary_info.prediction_deviation;

            if(summary_info.prediction_deviation) {
                prediction_deviation = summary_info.prediction_deviation;
            } else {
                prediction_deviation = "N/A";
            }

            $("#prediction_deviation").empty();
            $("#prediction_deviation").append(prediction_deviation);

            var value_predicted_today;

            if(summary_info.total_today_predicted_energy_value) {
                value_predicted_today = summary_info.total_today_predicted_energy_value;
                value_predicted_today = value_predicted_today.split(" ");
                value_predicted_today = parseInt(value_predicted_today[0]) + '<span style="font-size: small" id="total_energy_generation_unit"> '+ value_predicted_today[1] +'</span>';
            } else {
                value_predicted_today = "N/A";
            }

            $("#value_predicted_today").empty();
            $("#value_predicted_today").append(value_predicted_today);

            var strings_performing_low;

            if(summary_info.string_errors_smbs) {
                strings_performing_low = summary_info.string_errors_smbs
            } else {
                strings_performing_low = "N/A";
            }

            $("#strings_performing_low").empty();
            $("#strings_performing_low").append(strings_performing_low);

            var total_generation_timestamps = [], total_generation_energy = [];
            var pr_timestamps = [], pr_values = [], pr_text = [], timestamps_cuf = [], values_cuf = [], cuf_text = [];
            var grid_unavailability_timestamps = [], grid_unavailability_values = [], grid_unavailability_text = [], grid_unavailability_cirle = [];
            var equipment_unavailability_timestamps = [], equipment_unavailability_values = [], equipment_unavailability_text = [], equipment_unavailability_cirle = [];
            var ac_loss_timestamps = [], ac_loss_values = [], ac_loss_text = [];
            var conversion_loss_timestamps = [], conversion_loss_values = [], conversion_loss_text = [];
            var dc_loss_timestamps = [], dc_loss_values = [], dc_loss_text = [];

            if(summary_info.past_generations) {
                for(var i = 0; i < summary_info.past_generations.length; i++) {

                    if (i == 0 ) {
                        var generation_unit = summary_info.past_generations[i].energy.split(" ")[1];
                    }
                    var total_generation_date = new Date(summary_info.past_generations[i].timestamp);
                    total_generation_date = dateFormat(total_generation_date, "mmm dd");
                    var total_generation_value = parseFloat(summary_info.past_generations[i].energy);
                    total_generation_timestamps.push(total_generation_date);
                    total_generation_energy.push(total_generation_value);

                    if(summary_info.past_pr) {
                        var pr_date = new Date(summary_info.past_pr[i].timestamp);
                        pr_date = dateFormat(pr_date, "mmm dd");
                        var value_pr = parseFloat(summary_info.past_pr[i].pr);
                        pr_timestamps.push(pr_date);
                        pr_values.push(value_pr);
                    }

                    if(summary_info.past_cuf) {
                        var cuf_date = new Date(summary_info.past_cuf[i].timestamp);
                        cuf_date = dateFormat(cuf_date, "mmm dd");
                        var cuf_value = parseFloat(summary_info.past_cuf[i].cuf);
                        timestamps_cuf.push(cuf_date);
                        values_cuf.push(cuf_value);
                    }

                    if(summary_info.past_grid_unavailability) {
                        var date_grid_unavailability = new Date(summary_info.past_grid_unavailability[i].timestamp);
                        date_grid_unavailability = dateFormat(date_grid_unavailability, "mmm dd");
                        var grid_unavailability_value = parseFloat(summary_info.past_grid_unavailability[i].unavailability);
                        var grid_availability_value = 100 - grid_unavailability_value;
                        grid_unavailability_timestamps.push(date_grid_unavailability);
                        grid_unavailability_values.push(grid_availability_value);
                        /*grid_unavailability_text.push((dateFormat(date_grid_unavailability, "dd-mm-yyyy").toString()).concat('<br>Grid'));
                        grid_unavailability_cirle.push(parseInt(grid_unavailability_value * 1000));*/
                    }

                    if(summary_info.past_equipment_unavailability) {
                        var date_equipment_unavailability = new Date(summary_info.past_equipment_unavailability[i].timestamp);
                        date_equipment_unavailability = dateFormat(date_equipment_unavailability, "mmm dd");
                        var equipment_unavailability_value = parseFloat(summary_info.past_equipment_unavailability[i].unavailability);
                        var equipment_availability_value = 100 - equipment_unavailability_value;
                        equipment_unavailability_timestamps.push(date_equipment_unavailability);
                        equipment_unavailability_values.push(equipment_availability_value);
                        /*equipment_unavailability_text.push((dateFormat(date_equipment_unavailability, "dd-mm-yyyy").toString()).concat('<br>Equipment'));
                        equipment_unavailability_cirle.push(parseInt(equipment_unavailability_value * 1000));*/
                    }

                    if(summary_info.past_ac_loss) {
                        var date_ac_loss = new Date(summary_info.past_ac_loss[i].timestamp);
                        date_ac_loss = dateFormat(date_ac_loss, "mmm dd");
                        var ac_loss_value = parseFloat(summary_info.past_ac_loss[i].ac_energy_loss);
                        ac_loss_timestamps.push(date_ac_loss);
                        ac_loss_values.push(ac_loss_value);
                        /*ac_loss_text.push((date_ac_loss.toString()).concat('<br>AC Loss: ' + ac_loss_value));*/
                    }

                    if(summary_info.past_conversion_loss) {
                        var date_conversion_loss = new Date(summary_info.past_conversion_loss[i].timestamp);
                        date_conversion_loss = dateFormat(date_conversion_loss, "mmm dd");
                        var conversion_loss_value = parseFloat(summary_info.past_conversion_loss[i].conversion_loss);
                        conversion_loss_timestamps.push(date_conversion_loss);
                        conversion_loss_values.push(conversion_loss_value);
                        /*conversion_loss_text.push((date_conversion_loss.toString()).concat('<br>Conversion Loss: ' + conversion_loss_value));*/
                    }

                    if(summary_info.past_dc_loss) {
                        var date_dc_loss = new Date(summary_info.past_dc_loss[i].timestamp);
                        date_dc_loss = dateFormat(date_dc_loss, "mmm dd");
                        var dc_loss_value = parseFloat(summary_info.past_dc_loss[i].dc_energy_loss);
                        dc_loss_timestamps.push(date_dc_loss);
                        dc_loss_values.push(dc_loss_value);
                        /*dc_loss_text.push((date_dc_loss.toString()).concat('<br>DC Loss: ' + dc_loss_value));*/
                    }
                }
            }

            var barmode;
            var color_relative;

            /*if(summary_info.past_generations || summary_info.past_ac_loss || summary_info.past_conversion_loss || summary_info.past_dc_loss) {
                var generation_title = "Generation";
                var generation_div_name = "generation";
                var y_axis_title = "generation";
                all_x_arrays = [total_generation_timestamps];
                all_y_arrays = [total_generation_energy];
                all_array_titles = ['Generation', 'AC Loss', 'Conversion Loss', 'DC Loss'];
                var color_relative = ['#B5E3F2', '#00ABD9', '#BED73E', "#ffa726"];
                var page = 1;
                var b_m = 30, t_m = 10;

                barmode = "relative";
                var morris_data = [];
                for (var k = 0; k < total_generation_timestamps.length; k++) {
                    morris_data.push({x: total_generation_timestamps[k].toString(),
                                      y: total_generation_energy[k]})
                }

                relative_bar_chart_plotly(all_x_arrays, all_y_arrays, color_relative, all_array_titles, generation_title, generation_div_name, barmode, 30, 5, page, b_m, t_m)
            } else {
                $("#generation").empty();
                $("#generation").append("<div class='alert alert-warning' id='alert'>No data for Weekly Energy Generation.</div>");
            }*/

            /*if(summary_info.past_generations || summary_info.past_ac_loss || summary_info.past_conversion_loss || summary_info.past_dc_loss) {
                var generation_title = "Generation & Losses";
                var generation_div_name = "generation";
                var y_axis_title = "Generation and Losses";
                all_x_arrays = [total_generation_timestamps, ac_loss_timestamps, conversion_loss_timestamps, dc_loss_timestamps];
                all_y_arrays = [total_generation_energy, ac_loss_values, conversion_loss_values, dc_loss_values];
                all_array_titles = ['Generation', 'AC Loss', 'Conversion Loss', 'DC Loss'];
                var color_relative = ['#B5E3F2', '#00ABD9', '#BED73E', "#ffa726"];
                var page = 1;
                var b_m = 30, t_m = 10;

                barmode = "relative";
                var morris_data = [];
                for (var k = 0; k < total_generation_timestamps.length; k++) {
                    morris_data.push({x: total_generation_timestamps[k].toString(),
                                      y: total_generation_energy[k]})
                }

                // Use Morris.Bar
                Morris.Bar({
                  element: 'generation',
                  data: morris_data,
                  xkey: 'x',
                  ykeys: ['y'],
                  labels: ['Plant Generation'],
                  stacked: true,
                    hideHover: 'auto',
                    postUnits: ' '.concat(generation_unit)
                });
                //relative_bar_chart_plotly(all_x_arrays, all_y_arrays, color_relative, all_array_titles, generation_title, generation_div_name, barmode, 30, 5, page, b_m, t_m)
            } else {
                $("#generation").empty();
                $("#generation").append("<div class='alert alert-warning' id='alert'>No data for Weekly Energy Generation.</div>");
            }*/

            /*var page = 1;

            if(summary_info.past_pr || summary_info.past_cuf) {
                var name1 = 'PR';
                var name2 = 'CUF';
                var title_dual_axis_chart = "PR and CUF";
                var div_name = 'cuf_pr';
                var scatter_chart = 0;

                t_m = 10;

                dual_axis_chart_plotly(pr_timestamps, pr_values, timestamps_cuf, values_cuf, pr_text, cuf_text, name1, name2, title_dual_axis_chart, div_name, page, scatter_chart, 40, 40, 30, 30);
            } else {
                $("#cuf_pr").empty();
                $("#cuf_pr").append("<div class='alert alert-warning' id='alert'>No data for PR and CUF.</div>");
            }

            if(summary_info.past_grid_unavailability || summary_info.past_equipment_unavailability) {
                var availability_title = "Availability";
                var availability_div_name = "availability";
                y_axis_title = "Availability";
                var all_x_arrays = [grid_unavailability_timestamps, equipment_unavailability_timestamps];
                var all_y_arrays = [total_generation_energy, grid_unavailability_values, equipment_unavailability_values];
                var all_array_titles = ['Grid Avail.', 'Equipment Avail.'];
                var all_texts = [grid_unavailability_text, equipment_unavailability_text];
                var marker_circle = [grid_unavailability_cirle, equipment_unavailability_cirle];

                barmode = "group";
                b_m = 30, t_m = 2;
                var page = 1;
                color_relative = ['#B5E3F2', '#00ABD9', '#BED73E', "#ffa726"];

                relative_bar_chart_plotly(all_x_arrays, all_y_arrays, color_relative, all_array_titles, availability_title, availability_div_name, barmode, 30, 5, page, b_m, t_m);
            } else {
                $("#availability").empty();
                $("#availability").append("<div class='alert alert-warning' id='alert'>No data for Availability.</div>");
            }*/


            /*if(summary_info.client_past_ac_loss || summary_info.client_past_conversion_loss || summary_info.client_past_dc_loss) {
                var losses_title = "Losses";
                var losses_div_name = "losses";
                y_axis_title = "Losses";
                all_x_arrays = [ac_loss_timestamps, conversion_loss_timestamps, dc_loss_timestamps];
                all_y_arrays = [ac_loss_values, conversion_loss_values, dc_loss_values];
                var all_texts = [ac_loss_text, conversion_loss_text, dc_loss_text];
                all_array_titles = ['AC Losses', 'Conversion Losses', 'DC Losses'];

                barmode = "relative";

                relative_bar_chart_plotly(all_x_arrays, all_y_arrays, all_array_titles, losses_title, losses_div_name, barmode, 30, 5, page, b_m, t_m)
            } else {
                $("#losses").empty();
                $("#losses").append("<div class='alert alert-warning' id='alert'>No data for Weekly Losses.</div>");
            }*/


/*
            var values_grid_availability = [];

            var grid_unavailability = parseFloat(summary_info.grid_unavailability);
            var grid_availability = 100 - grid_unavailability;

            values_grid_availability.push({label: "Grid Available", value: grid_availability});
            values_grid_availability.push({label: "Grid Down", value: parseFloat(summary_info.grid_unavailability)});
            var colors = ['#B5E3F2', '#00ABD9', '#BED73E', "#ffa726"];

            var grid_div_name = "grid_availability";

            $("#grid_availability").empty();
            morris_donut_chart(values_grid_availability, grid_div_name, colors);

            var values_equipment_availability = [];

            var equipment_availability = parseFloat(summary_info.equipment_unavailability);
            equipment_availability = 100 - equipment_availability;

            values_equipment_availability.push({label: "Equipments Up", value: equipment_availability});
            values_equipment_availability.push({label: "Devices Down", value: parseFloat(summary_info.equipment_unavailability)});

            var equipment_availability_div_name = "equipment_availability";

            $("#equipment_availability").empty();
            morris_donut_chart(values_equipment_availability, equipment_availability_div_name, colors);
*/
            
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

            $('.chart').easyPieChart({
                easing: 'easeOutElastic',
                delay: 3000,
                barColor: '#69c',
                trackColor: '#ace',
                scaleColor: false,
                lineWidth: 30,
                trackWidth: 18,
                lineCap: 'butt',
                size: 110,
                onStep: function(from, to, percent) {
                    $(this.el).find('.percent').text(percent);
                }
            });

            /*$("#inverters_need_cleaning").empty();
            $("#inverters_need_cleaning").append(summary_info.total_inverter_cleaning_numbers);

            $("#smbs_low_current_strings").empty();
            $("#smbs_low_current_strings").append(summary_info.total_low_anomaly_smb_numbers);

            $("#smbs_high_current_strings").empty();
            $("#smbs_high_current_strings").append(summary_info.total_high_anomaly_smb_numbers);

            var total_generation = summary_info.plant_total_energy;
            $("#total_generation").text(total_generation);

            var irradiation = summary_info.irradiation;
            if(plant_slug == "uran" || plant_slug == "rrkabel" || plant_slug == "unipatch" || plant_slug == "waaneep" || plant_slug == "growels" || plant_slug == "raheja") {
                if(irradiation != undefined && irradiation != "NA") {
                    $('#irradiation').text(parseFloat(irradiation*1000).toFixed(2).toString().concat(" W/m").concat(String.fromCharCode(178)));
                } else {
                    $('#irradiation').text("NA");
                }     
            } else {
                if(irradiation != undefined && irradiation != "NA") {
                    $('#irradiation').text(parseFloat(irradiation).toFixed(3).toString().concat(" kW/m").concat(String.fromCharCode(178)));
                } else {
                    $('#irradiation').text("NA");
                }
            }

            var plant_generation_today = summary_info.plant_generation_today;
            if(plant_generation_today != undefined && plant_generation_today != "NA") {
                $("#generation_today").text(plant_generation_today);
            } else {
                $("#co2_savings").text((0.00).toString().concat(" Kg"));
            }

            if(summary_info.pvsyst_generation) {
                $("#generation_expected").show();
                $("#generation_expected_div").show();
                $("#generation_expected").text("/".concat((parseFloat(summary_info.pvsyst_generation)).toFixed(2).toString()));
            } else {
                $("#generation_expected").hide();
                $("#generation_expected_div").hide();
            }

            if(summary_info.pvsyst_tilt_angle) {
                $("#pvsyst_tilt_angle").show();
                $("#pvsyst_tilt_angle_div").show();
                $("#pvsyst_tilt_angle").text("/".concat((parseFloat(summary_info.pvsyst_tilt_angle)).toString().concat(String.fromCharCode(176))));
            } else {
                $("#pvsyst_tilt_angle").hide();
                $("#pvsyst_tilt_angle_div").hide();
            }

            if(summary_info.pvsyst_generation) {
                $("#generation_expected").show();
                $("#generation_expected_div").show();
                $("#generation_expected").text("/".concat((parseFloat(summary_info.pvsyst_generation)).toFixed(2).toString()));
            } else {
                $("#generation_expected").hide();
                $("#generation_expected_div").hide();
            }*/

            /*if(summary_info.past_kwh_per_meter_square) {
                $("#insolation").empty();
                $("#insolation").append(summary_info.past_kwh_per_meter_square[(summary_info.past_kwh_per_meter_square.length)-1].kwh_value);

                var insolation_dates = [], insolation_values = [];

                for(var i = 0; i < summary_info.past_kwh_per_meter_square.length; i++) {
                    var insolation_timestamps = new Date(summary_info.past_kwh_per_meter_square[i].timestamp);
                    insolation_timestamps = dateFormat(insolation_timestamps, "mmm dd, yyyy");
                    insolation_dates.push(insolation_timestamps);
                    insolation_values.push(parseFloat(summary_info.past_kwh_per_meter_square[i].kwh_value));
                }

                var chart_title = '';
                var div_name = 'insolation_chart';
                var y_axis_title = 'kWh/m^2';
                var div_name = 'insolation_chart';
                var color_array = ["#46bbdc"];
                
                var page = 1;
                var l_m = 40, r_m = 40, b_m = 30, t_m = 30;

                basic_bar_chart_plotly(insolation_dates, insolation_values, color_array, chart_title, y_axis_title, div_name, l_m, r_m, page, b_m, t_m)

            } else {
                $("#insolation").empty();
                $("#insolation").append("0");

                $("#insolation_chart").empty();
                $("#insolation_chart").append("<div class='alert alert-warning' id='alert'>No data for insolation.</div>");
            }*/

            if(!summary_info.residual) {
                $("#residualstab").hide();
                $("#residuals-lft").hide();

            } else { 
                $("#residuals_bar").empty();
                $("#residuals_bar").append("<svg style='float: left;'></svg>")

                var inverters = [];
                var residuals = [];
                var color = [];
                var residual_data = [];

                for(var inverter in summary_info.residual) {
                    if((summary_info.residual).hasOwnProperty(inverter)) {
                        inverters.push(inverter);
                        residuals.push(summary_info.residual[inverter]);
                    }
                }

                for(var n= 0; n < inverters.length ; n++) {
                    if(residuals[n] < 0) {
                        residual_data.push({"label": inverters[n], "value": residuals[n], "color": "#f76549"});
                    } else {
                        residual_data.push({"label": inverters[n], "value": residuals[n], "color": "#46bbdc"});
                    }
                }

                // package the data
                var packagedData = [{
                    "key": "RESIDUAL DATA FOR EACH CHART",
                    "values": residual_data
                }];

                // plot the chart
                residual_inverters_chart(packagedData);

            }

            /*var tickets_name = [], values_tickets = [];

            tickets_name.push("Open");
            tickets_name.push("Closed");
            tickets_name.push("Unacknowledged");
            values_tickets.push({label: "Closed Tickets", value: summary_info.total_closed_tickets});
            values_tickets.push({label: "Open Tickets", value: summary_info.total_open_tickets});
            values_tickets.push({label: "Unacknowledged Tickets", value: summary_info.total_unacknowledged_tickets});

            var tickets_div_name = "tickets";*/

            /*$("#tickets").empty();
            tickets_donut_chart(values_tickets, tickets_div_name);*/

            /*var values_losses = [];

            values_losses.push({label: "AC Losses", value: parseFloat(summary_info.client_ac_loss)});
            values_losses.push({label: "Conversion Losses", value: parseFloat(summary_info.client_conversion_loss)});
            values_losses.push({label: "DC Losses", value: parseFloat(summary_info.client_dc_loss)});

            var loss_div_name = "loss";*/

            /*$("#loss").empty();
            tickets_donut_chart(values_losses, loss_div_name);*/

            /*var ctx = $("#tickets");

            var data = {
                labels: tickets_name,
                datasets: [
                    {
                        data: values_tickets,
                        backgroundColor: [
                            "#ef5349",
                            "#36a2eb",
                            "#565656"
                        ],
                        hoverBackgroundColor: [
                            "#ef5349",
                            "#36a2eb",
                            "#565656"
                        ]
                    }]
            };

            var myDoughnutChart = new Chart(ctx, {
                type: 'doughnut',
                data: data,
                options: {
                    title: {
                        display: false,
                        text: 'Tickets'
                    }
                }
            });*/

            /*$("#plant_blocks").empty();

            for(var i = 0; i < summary_info.plants.length; i++) {
                $("#plant_blocks").append("<div class='col-lg-4'><div class='plant-box'><a href='/solar/plant/" + summary_info.plants[i].plant_slug + "/'><div class='row'><div class='col-lg-5'><h3><strong>" + summary_info.plants[i].plant_name + "</strong></h3><p><i class='fa fa-map-marker'></i> " + summary_info.plants[i].plant_location + "</p><button class='btn btn-outline' id='status_button" + i + "' type='button'><i class='fa' id='status_icon" + i + "'></i> <span id='plant_status" + i + "'></span> </button></div><div class='col-lg-7' style='margin-top: 25px;'>Plant Capacity: <strong>" + summary_info.plants[i].plant_capacity + " kW </strong> <br>Today's Gen.: <strong>" + summary_info.plants[i].plant_generation_today + "</strong> <br>Inv. Connected: <strong>" + summary_info.plants[i].connected_inverters + "</strong> <br>Inv. Disconnected: <strong>" + summary_info.plants[i].disconnected_inverters + "</strong> <br>Sending Invalid Data: <strong>" + summary_info.plants[i].invalid_inverters + "</strong> <br></div></div></a></div></div>");
                if(summary_info.plants[i].status == 'connected') {
                    $("#status_button"+i).addClass('btn-primary');
                    $("#status_icon"+i).addClass('fa-primary');
                    $("#plant_status"+i).append("No issues!");
                } else if (summary_info.plants[i].status == 'disconnected') {
                    $("#status_button"+i).addClass('btn-danger');
                    $("#status_icon"+i).addClass('fa-danger');
                    $("#plant_status"+i).append("Error!");
                } else {
                    $("#status_button"+i).addClass('btn-info');
                    $("#status_icon"+i).addClass('fa-info');
                    $("#plant_status"+i).append("No inverters!");
                }
            }*/

            /*$('#plants_table').html('');
            $('<div class="ibox-content" id="data_table"> ' +
            '</div>').appendTo('#plants_table');

            $('#plants_table').append("<table class='table table-striped table-bordered table-hover dataScroll dataTables-example'> <thead> <tr id='heading_table'> </tr></thread> <tbody id='table_body'> </tbody></table>");
            $('#heading_table').append("<th>Sites</th><th>Capacity (kW)</th><th>Active Power (kW)</th><th>Specific Production (kWh)</th><th>Irradiance (kW/"+ 'm'.concat(String.fromCharCode(178)) + ")</th><th>CO2</th><th>Inverters Disconnected</th>");

            for(var invidual_array = 0; invidual_array < summary_info.plants.length; invidual_array++) {
                $('#table_body').append("<tr id='row"+invidual_array+"'> </tr>");
                $('#row'+invidual_array).append("<td>" + summary_info.plants[invidual_array].plant_name + "</td><td>" + summary_info.plants[invidual_array].plant_capacity + "</td><td>" + (summary_info.plants[invidual_array].current_power).toFixed(2) + "</td><td>NA</td><td>" + summary_info.plants[invidual_array].irradiation + "</td><td>" + summary_info.plants[invidual_array].plant_co2 + "</td><td>" + summary_info.plants[invidual_array].disconnected_inverters + "</td>");
            }

            $('.dataTables-example').dataTable({
                responsive: true,
                "dom": '<"top"iflp<"clear">>rt',
                "tableTools": {
                    "sSwfPath": "/static/dataglen/js/copy_csv_xls_pdf.swf"
                },
                "fnRowCallback": function( nRow, aData, iDisplayIndex, iDisplayIndexFull ) {

                    var inverters_disconnected = parseFloat(aData[6]);

                    if ( inverters_disconnected > 0 ) {
                        $('td', nRow).css('background-color', '#EF4754');
                        $('td', nRow).css('color', 'Black');
                    } else {
                        $('td', nRow).css('background-color', '#6DC3AA');
                        $('td', nRow).css('color', 'Black');
                    }
                },
                buttons: [
                    'copy', 'csv', 'excel', 'pdf', 'print'
                ]
            });*/

        }
    });

}

function residual_inverters_chart(packagedData){

    nv.addGraph(function() {
      var chart = nv.models.discreteBarChart()
            .x(function(d) {
                return d.label
            })    //Specify the data accessors.
            .y(function(d) {
                return d.value
            })
            .showValues(false)
            /*#ff7f0e*/
            .margin({top: 5, right: 0, bottom: 68, left: 60})
            ;

        chart.tooltip.enabled(true);

        chart.yAxis
              .axisLabel("Residuals (kWh)")
              .tickFormat(d3.format(",.2f"));

        chart.xAxis
            .rotateLabels(-31);

      d3.select('#residuals_bar svg')
          .datum(packagedData)
          .call(chart);

      nv.utils.windowResize(chart.update);

      return chart;
    });
}

$("#info_button_alarms_raised").click(function() { 
    $("#info_modal").modal({
        showClose: false
    });

    $("#modal_info").empty();
    $("#modal_info").append("<div class='row text-center'><span class='text-2x text-bold'>All Tickets</span></div><br/>");

    $("#modal_info").append('<div class="panel-body"><table class="table table-vcenter"><thead><tr><th class="text-center min-width">Plant Name</th><th class="text-center">Devices Impacted</th><th class="text-center">Ticket Link</th></tr></thead><tbody id="table_data"></tbody></table></div>');
    $("#table_data").empty();

    for(var i = 0; i < client_data.client_current_inverter_error_details.length; i++) {
        if(client_data.client_current_inverter_error_details[i].plant_name) {
            $("#table_data").append("<tr id='modal_row"+i+"'><td class='text-center'><span class='text-semibold'>" + client_data.client_current_inverter_error_details[i].plant_name + "</span></td><td class='text-center'><span class='text-semibold'>" + client_data.client_current_inverter_error_details[i].affected_inverters_number + "</span></td><td class='text-center'><span class='text-semibold'><a href='" + client_data.client_current_inverter_error_details[i].ticket_url + "'>Check Here</a></span></td></tr>");
        }
    }

});

$("#info_button_inverters_need_cleaning").click(function() { 
    $("#info_modal").modal({
        showClose: false
    });

    $("#modal_info").empty();
    $("#modal_info").append("<div class='row text-center'><span class='text-2x text-bold'>Inverters Require Cleaning</span></div><br/>");

    $("#modal_info").append('<div class="panel-body"><table class="table table-hover table-vcenter"><thead><tr><th class="text-center min-width">Plant Name</th><th class="text-center">Devices Impacted</th></tr></thead><tbody id="table_data"></tbody></table></div>');
    $("#table_data").empty();

    for(var i = 0; i < client_data.client_inverter_cleaning_details.length; i++) {
        if(client_data.client_inverter_cleaning_details[i].plant_name) {
            $("#table_data").append("<tr id='modal_row"+i+"'><td class='text-center'><span class='text-semibold'>" + client_data.client_inverter_cleaning_details[i].plant_name + "</span></td><td class='text-center'><span class='text-semibold'>" + client_data.client_inverter_cleaning_details[i].inverters_required_cleaning_numbers + "</span></td></tr>");
        }
    }

});

$("#info_button_smb_high_current_strings").click(function() { 
    $("#info_modal").modal({
        showClose: false
    });

    $("#modal_info").empty();
    $("#modal_info").append("<div class='row text-center'><span class='text-2x text-bold'>SMBs With High Current Anomaly</span></div><br/>");

    $("#modal_info").append('<div class="panel-body"><table class="table table-hover table-vcenter"><thead><tr><th class="text-center min-width">Plant Name</th><th class="text-center">Devices Impacted</th></tr></thead><tbody id="table_data"></tbody></table></div>');
    $("#table_data").empty();

    for(var i = 0; i < client_data.client_string_anomaly_details.length; i++) {
        if(client_data.client_string_anomaly_details[i].plant_name) {
            $("#table_data").append("<tr id='modal_row"+i+"'><td class='text-center'><span class='text-semibold'>" + client_data.client_string_anomaly_details[i].plant_name + "</span></td><td class='text-center'><span class='text-semibold'>" + client_data.client_string_anomaly_details[i].high_anomaly_affected_ajbs_number + "</span></td></tr>");
        }
    }

});

$("#info_button_smb_low_current_strings").click(function() { 
    $("#info_modal").modal({
        showClose: false
    });

    $("#modal_info").empty();
    $("#modal_info").append("<div class='row text-center'><span class='text-2x text-bold'>SMBs With Low Current Anomaly</span></div><br/>");

    $("#modal_info").append('<div class="panel-body"><table class="table table-hover table-vcenter"><thead><tr><th class="text-center min-width">Plant Name</th><th class="text-center">Devices Impacted</th></tr></thead><tbody id="table_data"></tbody></table></div>');
    $("#table_data").empty();

    for(var i = 0; i < client_data.client_string_anomaly_details.length; i++) {
        if(client_data.client_string_anomaly_details[i].plant_name) {
            $("#table_data").append("<tr id='modal_row"+i+"'><td class='text-center'><span class='text-semibold'>" + client_data.client_string_anomaly_details[i].plant_name + "</span></td><td class='text-center'><span class='text-semibold'>" + client_data.client_string_anomaly_details[i].low_anomaly_affected_ajbs_number + "</span></td></tr>");
        }
    }

});

function sparkline_bar_chart(id, data_array, date_values, units, parameter) {

    var label;

    if(parameter == "PR") {
        label = "Performance Ratio";
    } else {
        label = "Energy Generation";
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
        zeroAxis: false,
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

function power_irradiation_chart(st, et) {

    $.ajax({
        type: "GET",
        url: "/api/solar/plants/".concat(plant_slug).concat('/irradiation-power/'),
        data: {startTime: (st), endTime: (et)},
        success: function(power_irradiation) {
            
            /*var power_timestamps = [], power_values = [], irradiation_timestamps = [], irradiation_values = [], power_text = [], irradiation_text = [];

            for(var i = 0; i < power_irradiation.data.length; i++) {
                var power_date = new Date(power_irradiation.data[i].timestamp);
                power_date = dateFormat(power_date, "mmm dd HH:MM:ss");
                var power_value = parseFloat(power_irradiation.data[i].power);
                power_timestamps.push(power_date);
                power_values.push(power_value);
                power_text.push((dateFormat(power_date, "HH:MM:ss").toString()).concat('<br>Power : ' + power_value.toFixed(2) + " kW"));

                var irradiation_date = new Date(power_irradiation.data[i].timestamp);
                irradiation_date = dateFormat(irradiation_date, "mmm dd HH:MM:ss");
                var irradiation_value = parseFloat(power_irradiation.data[i].irradiation);
                irradiation_timestamps.push(irradiation_date);
                irradiation_values.push(irradiation_value);
                irradiation_text.push((dateFormat(irradiation_date, "HH:MM:ss").toString()).concat('<br>Irradiation : ' + irradiation_value.toFixed(2) + " kWh/m".concat(String.fromCharCode(178))));
            }

            var name1 = 'POWER';
            var name2 = 'IRRADIATION';
            var title_dual_axis_chart = "Today's Power and Irradiation";
            var div_name = 'power_irradiation';
            var page = 1;
            var scatter_chart = 1;

            dual_axis_chart_plotly(power_timestamps, power_values, irradiation_timestamps, irradiation_values, power_text, irradiation_text, name1, name2, title_dual_axis_chart, div_name, page, scatter_chart, 70, 65, 40, 10);*/

            var power_data = [], irradiation_data = [], timestamps = [], inverters_down = [], modbus_error = [], annotation_array = [];

            if(power_irradiation.data) {
                for(var j = 0; j < power_irradiation.data.length; j++) {
                    power_data.push(power_irradiation.data[j].power);
                    irradiation_data.push(power_irradiation.data[j].irradiation);
                    timestamps.push(new Date(power_irradiation.data[j].timestamp).valueOf());
                }

                var power_max_value = Math.max.apply(null, power_data);
                console.log(power_max_value);

                for(var m = 0; m < power_irradiation.data.length; m++) {
                    if(m < power_irradiation.data.length-1) {
                        if(power_irradiation.data[m].Inverters_down > 0) {
                            annotation_array.push({
                                type: 'box',
                                xScaleID: 'x-axis-0',
                                yScaleID: 'y-axis-1',
                                // Left edge of the box. in units along the x axis
                                xMin: new Date(power_irradiation.data[m].timestamp).valueOf(),
                                xMax: new Date(power_irradiation.data[m+1].timestamp).valueOf(),
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
                        if(power_irradiation.data[m].modbus_read_error == true) {
                            annotation_array.push({
                                type: 'box',
                                xScaleID: 'x-axis-0',
                                yScaleID: 'y-axis-1',
                                // Left edge of the box. in units along the x axis
                                xMin: new Date(power_irradiation.data[m].timestamp).valueOf(),
                                xMax: new Date(power_irradiation.data[m+1].timestamp).valueOf(),
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
                $("#no_power_and_irradiation").empty();
                $("#no_power_and_irradiation").append("<div class='alert alert-warning' id='alert'>No data for power and irradiation.</div>");
            }

        },
        error: function(data) {
            console.log("error_streams_data");
            data = null;
        }
    });

}

function weather_current(plant_location, summary_info) {

    if(typeof plant_location !== 'undefined') {
        $.ajax({
            type: "GET",
            async: false,
            url: "https://api.worldweatheronline.com/premium/v1/weather.ashx".concat("?key=39217aee72de46088c4145902170302&q=").concat(plant_location).concat("&num_of_day=1").concat("&format=json"),
            success: function(weather_data) {
                var temp;
                if(summary_info.ambient_temperature) {
                    temp = parseInt(summary_info.ambient_temperature) + '<span style="font-size: small" id="ac_capacity_unit"> ' + String.fromCharCode(176) + 'C</span>';
                } else {
                    temp = weather_data.data.current_condition[0].FeelsLikeC;
                    temp = Math.round(temp) + '<span style="font-size: small" id="ac_capacity_unit"> ' + String.fromCharCode(176) + 'C</span>';
                }
                $('#temperature').append(temp);
                var max_temp = weather_data.data.weather[0].maxtempC;
                var min_temp = weather_data.data.weather[0].mintempC;
                $('#minmax').text(Math.round(max_temp).toString().concat(String.fromCharCode(176)).concat("/").concat(Math.round(min_temp).toString().concat(String.fromCharCode(176))));
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
                $('#windspeed').append(Math.round(wind));
                var clouds_description = weather_data.data.current_condition[0].weatherDesc[0].value;
                $('#weather_status').text(clouds_description);
                var weather_description_icon = null;
                var time_of_day = new Date(summary_info.updated_at);
                time_of_day = new Date(time_of_day.toString());
                console.log(time_of_day.getHours());
                time_of_day = time_of_day.getHours();
                if(clouds_description == "Sunny") {
                    weather_description_icon = "clear_day_status_icon";
                } else if(clouds_description == "Haze") {
                    weather_description_icon = "mist_or_fog_icon";
                } else if(clouds_description == "Rain") {
                    weather_description_icon = "rain_icon";
                } else if(clouds_description == "Thunderstorm") {
                    weather_description_icon = "thuderstorm_icon";
                } else if(clouds_description == "Snow") {
                    weather_description_icon = "snow_icon";
                } else if(clouds_description == "Wind") {
                    weather_description_icon = "wind_status_icon";
                } else if(clouds_description == "Clear" && time_of_day < 19) {
                    weather_description_icon = "clear_day_status_icon";
                } else if(clouds_description == "Clear" && time_of_day >= 19) {
                    weather_description_icon = "clear_night_status_icon";
                } else if(clouds_description == "Cloudy" && time_of_day < 19) {
                    weather_description_icon = "partly_cloudy_sunny_day_icon";
                } else if(clouds_description == "Cloudy" && time_of_day >= 19) {
                    weather_description_icon = "partly_cloudy_night_icon";
                } else {
                    weather_description_icon = "partly_cloudy_sunny_day_icon";
                }
                $('<canvas/>').attr({id:weather_description_icon, width: '65', height: '65'}).appendTo("#weather_icon");
                var precipitation = weather_data.data.current_condition[0].precipMM;
                $('#precipitation').append(precipitation);
                $('#clouds_cover').append(weather_data.data.current_condition[0].cloudcover);
            },
            error: function(weather_data){
                console.log("no data");
            }
        });
    } else {
        $('#no_weather').empty();
        $('#no_weather').append("No weather report.");

        $(".canvas_icon").empty();
        $("#windspeed_unit").empty();
        $("#precipitation_unit").empty();
    }

}

function morris_chart() {

    var day_data = [
        {"elapsed": "Oct-12", "value": 24, b:2},
        {"elapsed": "Oct-13", "value": 34, b:22},
        {"elapsed": "Oct-14", "value": 33, b:7},
        {"elapsed": "Oct-15", "value": 22, b:6},
        {"elapsed": "Oct-16", "value": 28, b:17},
        {"elapsed": "Oct-17", "value": 60, b:15},
        {"elapsed": "Oct-18", "value": 60, b:17},
        {"elapsed": "Oct-19", "value": 70, b:7},
        {"elapsed": "Oct-20", "value": 67, b:18},
        {"elapsed": "Oct-21", "value": 86, b: 18},
        {"elapsed": "Oct-22", "value": 86, b: 18},
        {"elapsed": "Oct-23", "value": 113, b: 29},
        {"elapsed": "Oct-24", "value": 130, b: 23},
        {"elapsed": "Oct-25", "value": 114, b:10},
        {"elapsed": "Oct-26", "value": 80, b:22},
        {"elapsed": "Oct-27", "value": 109, b:7},
        {"elapsed": "Oct-28", "value": 100, b:6},
        {"elapsed": "Oct-29", "value": 105, b:17},
        {"elapsed": "Oct-30", "value": 110, b:15},
        {"elapsed": "Oct-31", "value": 102, b:17},
        {"elapsed": "Nov-01", "value": 107, b:7},
        {"elapsed": "Nov-02", "value": 60, b:18},
        {"elapsed": "Nov-03", "value": 67, b: 18},
        {"elapsed": "Nov-04", "value": 76, b: 18},
        {"elapsed": "Nov-05", "value": 73, b: 29},
        {"elapsed": "Nov-06", "value": 94, b: 13},
        {"elapsed": "Nov-07", "value": 135, b:2},
        {"elapsed": "Nov-08", "value": 154, b:22},
        {"elapsed": "Nov-09", "value": 120, b:7},
        {"elapsed": "Nov-10", "value": 100, b:6},
        {"elapsed": "Nov-11", "value": 130, b:17},
        {"elapsed": "Nov-12", "value": 100, b:15},
        {"elapsed": "Nov-13", "value": 60, b:17},
        {"elapsed": "Nov-14", "value": 70, b:7},
        {"elapsed": "Nov-15", "value": 67, b:18},
        {"elapsed": "Nov-16", "value": 86, b: 18},
        {"elapsed": "Nov-17", "value": 86, b: 18},
        {"elapsed": "Nov-18", "value": 113, b: 29},
        {"elapsed": "Nov-19", "value": 130, b: 23},
        {"elapsed": "Nov-20", "value": 114, b:10},
        {"elapsed": "Nov-21", "value": 80, b:22},
        {"elapsed": "Nov-22", "value": 109, b:7},
        {"elapsed": "Nov-23", "value": 100, b:6},
        {"elapsed": "Nov-24", "value": 105, b:17},
        {"elapsed": "Nov-25", "value": 110, b:15},
        {"elapsed": "Nov-26", "value": 102, b:17},
        {"elapsed": "Nov-27", "value": 107, b:7},
        {"elapsed": "Nov-28", "value": 60, b:18},
        {"elapsed": "Nov-29", "value": 67, b: 18},
        {"elapsed": "Nov-30", "value": 76, b: 18},
        {"elapsed": "Des-01", "value": 73, b: 29},
        {"elapsed": "Des-02", "value": 94, b: 13},
        {"elapsed": "Des-03", "value": 79, b: 24}
    ];

    var chart = Morris.Area({
        element : 'morris-chart-network',
        data: day_data,
        axes:false,
        xkey: 'elapsed',
        ykeys: ['value', 'b'],
        labels: ['Download Speed', 'Upload Speed'],
        yLabelFormat :function (y) { return y.toString() + ' Mb/s'; },
        gridEnabled: false,
        gridLineColor: 'transparent',
        lineColors: ['#82c4f8','#0d92fc'],
        lineWidth:[0,0],
        pointSize:[0,0],
        fillOpacity: 1,
        gridTextColor:'#999',
        parseTime: false,
        resize:true,
        behaveLikeLine : true,
        hideHover: 'auto'
    });

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