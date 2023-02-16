$(document).ready(function() {

    $(function () {
      $('[data-toggle="tooltip"]').tooltip()
    });

    var client_data = null;
    var bounds_leaflet_map = null;
    var map = null;

    var r1 = new Date();
    $("#loading_row").show();
    console.log("after show: ", new Date() - r1);

    var r2 = new Date();
    dashboard_clients();
    console.log("after dashboard_clients: ", new Date() - r2);

    var r3 = new Date();
    $("#loading_row").hide();
    console.log("after hide: ", new Date() - r3);


    setInterval(function () {
        client_data = null;
        bounds_leaflet_map = null;
        map = null;
        dashboard_clients();
    }, 5000*60);

});

function plant_map(plants) {
    var bounds = new google.maps.LatLngBounds();
    var infowindow = new google.maps.InfoWindow(); /* SINGLE */
    var dashboard_map = new google.maps.Map(document.getElementById('dashboard-geocoding-map'), {
      zoom: 5,
      center: new google.maps.LatLng(19.9705, 79.3015),
      scrollwheel: false
    });
    dashboard_map.fitBounds(bounds);

    var date = new Date();

    var hour = date.getHours();
    var icon_url;
    if(hour < 18 && hour > 05) {
        icon_url = '/static/solarrms/img/generation_day.png'
    } else {
        icon_url = '/static/solarrms/img/night.png'
    }

    for(var i = 0; i < plants.length; i++) {
        placeMarker( plants[i] );
    }

    function placeMarker( plant ) {
        var latLng = new google.maps.LatLng(plant.latitude, plant.longitude);
        var dashboard_marker = new google.maps.Marker({
            position : latLng,
            animation: google.maps.Animation.DROP,
            icon: {
                url: icon_url,
                scaledSize: new google.maps.Size(50, 50), // scaled size
                origin: new google.maps.Point(0,0), // origin
                anchor: new google.maps.Point(0, 0) // anchor
            },
            map : dashboard_map
        });
        bounds.extend(dashboard_marker.position);
        google.maps.event.addListener(dashboard_marker, 'mouseover', function(){
            infowindow.close(); // Close previously opened infowindow
            var url = "/solar/plant/".concat(plant.plant_slug);
            infowindow.setContent( '<div><a href=' + url.toString() + '><h3 style="color: blue">'  +
                    plant.plant_name + '</h3> <span>' +
                    plant.plant_location + ' </span><br/><span> Generation Today : ' +
                    plant.plant_generation_today + '</span><br/><span> Devices Connected : ' +
                    plant.connected_inverters + '</span><br/><span> Devices Disconnected : ' +
                    plant.disconnected_inverters + '</span></a></div>');
            infowindow.open(dashboard_map, dashboard_marker);
        });

        google.maps.event.addListener(dashboard_map, 'click', function() {
            infowindow.close();
        });
    }
}

$("#close_slider").click(function() {

    var effect = 'slide';

    // Set the options for the effect type chosen
    var options = { direction: 'left' };

    // Set the duration (default: 400 milliseconds)
    var duration = 500;

    $('#slider').hide(effect, options, duration)
});

function dashboard_clients() {

    var t = new Date();
    $.ajax({
        type: "GET",
        async: false,
        url : "/api/v1/solar/client/summary/",
        success: function(summary_info){
            console.log("api time",new Date() - t);
            client_data = summary_info;



            var leaflet_status = 1;

            if(summary_info.plants[0].status) {
                all_plants(summary_info, leaflet_status);
            } else {

            }

            /*$("#dataglen_client").empty();
            $("#dataglen_client").append(summary_info.client_name);*/

            $("#client_image").empty();
            $("#client_image").append("<img class='logo-class' src='" + summary_info.client_logo + "' alt='DATAGLEN'>");

            var current_power;

            if(typeof summary_info.total_active_power !== 'undefined') {
                current_power = summary_info.total_active_power + " kW";
            } else {
                current_power = "N/A";
            }

            $("#current_power").empty();
            $("#current_power").append(current_power);

            var energy_today;

            if(typeof summary_info.energy_today !== 'undefined') {
                energy_today = summary_info.energy_today;
            } else {
                energy_today = "N/A";
            }

            $("#today_energy").empty();
            $("#today_energy").append(energy_today + ' <span class="text-thin" id="today_text" style="font-size: small;"></span>');

            $("#today_text").empty();

            var total_specific_yield;

            if(typeof summary_info.total_specific_yield !== 'undefined') {
                total_specific_yield = summary_info.total_specific_yield;
            } else {
                total_specific_yield = "N/A";
            }

            $("#total_specific_yield").empty();
            $("#total_specific_yield").append(total_specific_yield);

            var total_pr;

            if(typeof summary_info.total_pr !== 'undefined') {
                total_pr = parseInt(summary_info.total_pr * 100) + "%";
            } else {
                total_pr = "N/A";
            }

            $("#average_pr").empty();
            $("#average_pr").append(total_pr) + "%";

            var total_cuf;

            if(typeof summary_info.total_cuf !== 'undefined') {
                total_cuf = parseInt(summary_info.total_cuf * 100)
            } else {
                total_cuf = "N/A"
            }

            $("#average_cuf").empty();
            $("#average_cuf").append(total_cuf);

            var open_tickets;

            if(typeof summary_info.total_open_tickets !== 'undefined') {
                open_tickets = summary_info.total_open_tickets;
            } else {
                open_tickets = "N/A";
            }

            $("#open_tickets").empty();
            $("#open_tickets").append(open_tickets);

            var total_plants, live_plants = 0;

            if(summary_info.plants.length) {
                for(var each_plant = 0; each_plant < summary_info.plants.length; each_plant++) {
                    if(summary_info.plants[each_plant].status == "connected") {
                        live_plants++;
                    }
                }
                total_plants = summary_info.plants.length;
            } else {
                total_plants = 0;
                live_plants = 0;
            }

            $("#total_plants").empty();
            $("#total_plants").append(total_plants);

            $("#live_plants").empty();
            $("#live_plants").append(live_plants);

            var total_energy_generation;

            if(typeof summary_info.total_energy !== 'undefined') {
                total_energy_generation = summary_info.total_energy;
                total_energy_generation = total_energy_generation.split(" ");
                total_energy_generation = total_energy_generation[0] + '<span style="font-size: small" id="total_energy_generation_unit"> '+ total_energy_generation[1] +'</span>';
            } else {
                total_energy_generation = "N/A";
            }

            $("#total_energy_generation").empty();
            $("#total_energy_generation").append(total_energy_generation);

            var net_assets;

            if(typeof summary_info.total_capacity !== 'undefined') {
                net_assets = summary_info.total_capacity;
                net_assets = net_assets.split(" ");
                net_assets = net_assets[0] + '<span style="font-size: small" id="net_assets_unit"> '+net_assets[1]+'</span>';
            } else {
                net_assets = "N/A";
            }

            $("#net_assets_value").empty();
            $("#net_assets_value").append(net_assets);

            var prediction_deviation;

            if(typeof summary_info.prediction_deviation !== 'undefined') {
                prediction_deviation = summary_info.prediction_deviation;
            } else {
                prediction_deviation = "N/A";
            }

            $("#prediction_deviation").empty();
            $("#prediction_deviation").append(prediction_deviation);

            var value_predicted_today;

            if(typeof summary_info.total_today_predicted_energy_value !== 'undefined') {
                value_predicted_today = summary_info.total_today_predicted_energy_value
                value_predicted_today = value_predicted_today.split(" ");
                value_predicted_today = value_predicted_today[0] + '<span class="text-xs" style="font-size: xx-small" id="value_predicted_today_unit"> '+ value_predicted_today[1] +'</span>';
            } else {
                value_predicted_today = "N/A";
            }

            $("#value_predicted_today").empty();
            $("#value_predicted_today").append(value_predicted_today);

            var string_errors_smbs;

            if(typeof summary_info.string_errors_smbs !== 'undefined') {
                string_errors_smbs = summary_info.string_errors_smbs;
            } else {
                string_errors_smbs = "N/A";
            }

            $("#strings_performing_low").empty();
            $("#strings_performing_low").append(string_errors_smbs);

            var total_generation_timestamps = [], total_generation_energy = [];
            var pr_timestamps = [], pr_values = [], pr_text = [], timestamps_cuf = [], values_cuf = [], cuf_text = [];
            var grid_unavailability_timestamps = [], grid_unavailability_values = [], grid_unavailability_text = [], grid_unavailability_cirle = [];
            var equipment_unavailability_timestamps = [], equipment_unavailability_values = [], equipment_unavailability_text = [], equipment_unavailability_cirle = [];
            var ac_loss_timestamps = [], ac_loss_values = [], ac_loss_text = [];
            var conversion_loss_timestamps = [], conversion_loss_values = [], conversion_loss_text = [];
            var dc_loss_timestamps = [], dc_loss_values = [], dc_loss_text = [];

            if(summary_info.client_past_generations) {
                for(var i = 0; i < summary_info.client_past_generations.length; i++) {

                    if (i == 0 ) {
                        var generation_unit = summary_info.client_past_generations[i].energy.split(" ")[1];
                        console.log(generation_unit);
                    }
                    var total_generation_date = new Date(summary_info.client_past_generations[i].timestamp);
                    total_generation_date = dateFormat(total_generation_date, "mmm dd");
                    var total_generation_value = parseFloat(summary_info.client_past_generations[i].energy);
                    total_generation_timestamps.push(total_generation_date);
                    total_generation_energy.push(total_generation_value);

                    if(summary_info.client_past_pr) {
                        var pr_date = new Date(summary_info.client_past_pr[i].timestamp);
                        pr_date = dateFormat(pr_date, "mmm dd");
                        var value_pr = parseFloat(summary_info.client_past_pr[i].pr);
                        pr_timestamps.push(pr_date);
                        pr_values.push(value_pr);
                    }

                    if(summary_info.client_past_cuf) {
                        var cuf_date = new Date(summary_info.client_past_cuf[i].timestamp);
                        cuf_date = dateFormat(cuf_date, "mmm dd");
                        var cuf_value = parseFloat(summary_info.client_past_cuf[i].cuf);
                        timestamps_cuf.push(cuf_date);
                        values_cuf.push(cuf_value);
                    }

                    if(summary_info.client_past_grid_unavailability) {
                        var date_grid_unavailability = new Date(summary_info.client_past_grid_unavailability[i].timestamp);
                        date_grid_unavailability = dateFormat(date_grid_unavailability, "mmm dd");
                        var grid_unavailability_value = parseFloat(summary_info.client_past_grid_unavailability[i].unavailability);
                        var grid_availability_value = 100 - grid_unavailability_value;
                        grid_unavailability_timestamps.push(date_grid_unavailability);
                        grid_unavailability_values.push(grid_availability_value);
                        /*grid_unavailability_text.push((dateFormat(date_grid_unavailability, "dd-mm-yyyy").toString()).concat('<br>Grid'));
                        grid_unavailability_cirle.push(parseInt(grid_unavailability_value * 1000));*/
                    }

                    if(summary_info.client_past_equipment_unavailability) {
                        var date_equipment_unavailability = new Date(summary_info.client_past_equipment_unavailability[i].timestamp);
                        date_equipment_unavailability = dateFormat(date_equipment_unavailability, "mmm dd");
                        var equipment_unavailability_value = parseFloat(summary_info.client_past_equipment_unavailability[i].unavailability);
                        var equipment_availability_value = 100 - equipment_unavailability_value;
                        equipment_unavailability_timestamps.push(date_equipment_unavailability);
                        equipment_unavailability_values.push(equipment_availability_value);
                        /*equipment_unavailability_text.push((dateFormat(date_equipment_unavailability, "dd-mm-yyyy").toString()).concat('<br>Equipment'));
                        equipment_unavailability_cirle.push(parseInt(equipment_unavailability_value * 1000));*/
                    }

                    if(summary_info.client_past_ac_loss) {
                        var date_ac_loss = new Date(summary_info.client_past_ac_loss[i].timestamp);
                        date_ac_loss = dateFormat(date_ac_loss, "mmm dd");
                        var ac_loss_value = parseFloat(summary_info.client_past_ac_loss[i].ac_energy_loss);
                        ac_loss_timestamps.push(date_ac_loss);
                        ac_loss_values.push(ac_loss_value);
                        /*ac_loss_text.push((date_ac_loss.toString()).concat('<br>AC Loss: ' + ac_loss_value));*/
                    }

                    if(summary_info.client_past_conversion_loss) {
                        var date_conversion_loss = new Date(summary_info.client_past_conversion_loss[i].timestamp);
                        date_conversion_loss = dateFormat(date_conversion_loss, "mmm dd");
                        var conversion_loss_value = parseFloat(summary_info.client_past_conversion_loss[i].conversion_loss);
                        conversion_loss_timestamps.push(date_conversion_loss);
                        conversion_loss_values.push(conversion_loss_value);
                        /*conversion_loss_text.push((date_conversion_loss.toString()).concat('<br>Conversion Loss: ' + conversion_loss_value));*/
                    }

                    if(summary_info.client_past_dc_loss) {
                        var date_dc_loss = new Date(summary_info.client_past_dc_loss[i].timestamp);
                        date_dc_loss = dateFormat(date_dc_loss, "mmm dd");
                        var dc_loss_value = parseFloat(summary_info.client_past_dc_loss[i].dc_energy_loss);
                        dc_loss_timestamps.push(date_dc_loss);
                        dc_loss_values.push(dc_loss_value);
                        /*dc_loss_text.push((date_dc_loss.toString()).concat('<br>DC Loss: ' + dc_loss_value));*/
                    }
                }
            }

            var barmode;
            var color_relative;

            if(typeof summary_info.client_past_generations !== 'undefined' || typeof summary_info.client_past_ac_loss !== 'undefined' || typeof summary_info.client_past_conversion_loss !== 'undefined' || typeof summary_info.client_past_dc_loss !== 'undefined') {
                var generation_title = "Generation & Losses";
                var generation_div_name = "generation_and_losses";
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
                  element: 'generation_and_losses',
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
                $("#generation_and_losses").empty();
                $("#generation_and_losses").append("<div class='panel-body'><div class='alert alert-warning' id='alert'>No data for Weekly Energy Generation.</div></div>");
            }


/*
            if(summary_info.client_past_pr || summary_info.client_past_cuf) {
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
*/


/*
            if(typeof summary_info.client_past_grid_unavailability !== 'undefined' || typeof summary_info.client_past_equipment_unavailability !== 'undefined') {
                var availability_title = "Availability";
                var availability_div_name = "availability";
                y_axis_title = "Availability";
                var all_x_arrays = [grid_unavailability_timestamps, equipment_unavailability_timestamps];
                var all_y_arrays = [total_generation_energy, grid_unavailability_values, equipment_unavailability_values];
                var all_array_titles = ['Grid Avail.', 'Equipment Avail.'];
                /!*var all_texts = [grid_unavailability_text, equipment_unavailability_text];
                var marker_circle = [grid_unavailability_cirle, equipment_unavailability_cirle];*!/

                barmode = "group";
                b_m = 30, t_m = 2;

                relative_bar_chart_plotly(all_x_arrays, all_y_arrays, color_relative, all_array_titles, availability_title, availability_div_name, barmode, 30, 5, page, b_m, t_m);
            } else {
                $("#availability").empty();
                $("#availability").append("<div class='alert alert-warning' id='alert'>No data for Availability.</div>");
            }
*/


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
                onStep: function(from, to, percent) {
                    $(this.el).find('.percent').text(percent);
                }
            });

            var alarms_raised;

            if(typeof summary_info.total_inverter_error_numbers != 'undefined') {
                alarms_raised = summary_info.total_inverter_error_numbers + '<span class="text-xs" style="font-size: xx-small "> Inverters</span>';
            } else {
                alarms_raised = "N/A";
            }

            $("#alarms_raised").empty();
            $("#alarms_raised").append(alarms_raised);

            var total_inverters_need_cleaning;

            if(typeof summary_info.total_inverter_cleaning_numbers != 'undefined') {
                total_inverters_need_cleaning = summary_info.total_inverter_cleaning_numbers + '<span class="text-xs" style="font-size: xx-small "> Inverters Panels</span>';
            } else {
                total_inverters_need_cleaning = "N/A";
            }

            $("#inverters_need_cleaning").empty();
            $("#inverters_need_cleaning").append(total_inverters_need_cleaning);

            var smbs_down;

            if(typeof summary_info.total_disconnected_smbs !== 'undefined') {
                smbs_down = summary_info.total_disconnected_smbs;
            } else {
                smbs_down = "N/A";
            }

            $("#smbs_down").empty();
            $("#smbs_down").append(smbs_down);

            var inverters_down;

            if(typeof summary_info.total_disconnected_inverters !== 'undefined') {
                inverters_down = summary_info.total_disconnected_inverters;
            } else {
                inverters_down = "N/A";
            }

            $("#inverters_down").empty();
            $("#inverters_down").append(inverters_down);

            var total_low_anomaly_smb_numbers;

            if(typeof summary_info.total_low_anomaly_smb_numbers != 'undefined') {
                total_low_anomaly_smb_numbers = summary_info.total_low_anomaly_smb_numbers.toString() + '<span class="text-xs" style="font-size: xx-small "> SMBs</span>';
            } else {
                total_low_anomaly_smb_numbers = "N/A";
            }

            $("#smbs_low_current_strings").empty();
            $("#smbs_low_current_strings").append(total_low_anomaly_smb_numbers);

            var total_high_anomaly_smb_numbers;

            if(typeof summary_info.total_high_anomaly_smb_numbers != 'undefined') {
                total_high_anomaly_smb_numbers = summary_info.total_high_anomaly_smb_numbers.toString() + '<span class="text-xs" style="font-size: xx-small "> SMBs</span>';
            } else {
                total_high_anomaly_smb_numbers = "N/A";
            }

            $("#smbs_high_current_strings").empty();
            $("#smbs_high_current_strings").append(total_high_anomaly_smb_numbers);

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

            if(summary_info.plants) {
                foo_tables(summary_info.plants);    
            } else {
                $("#plants_table").empty();
                $("#plants_table").append("<div class='panel-body'><div class='alert alert-warning' id='alert'>No data for Availability.</div></div>")
            }

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

function foo_tables(plants) {

    console.log(plants);

    $("#plants_table").empty();

    $("#plants_table").append('<div class="panel-body pad-no table-responsive"><table id="demo-foo-row-toggler" class="table toggle-circle"><thead><tr><th data-toggle="true" style="width: 24%;">Plant Name</th><th class="text-center" style="width: 12%;">Energy</th><th class="text-center" style="width: 12%;">PR</th><th class="text-center" style="width: 18%;">Inv. / SMBs ' + '<i class="fa fa-long-arrow-down" aria-hidden="true" style="color: red;"></i>' + '</th><th style="width: 14%;">Predicted</th><th style="width: 15%;">Generation</th><th data-hide="all">Prediction Deviation</th></tr></thead><tbody id="foo_table_tbody"></tbody></table>');
    $("#foo_table_tbody").empty();

    for(var i = 0; i < plants.length; i++) {
        if(plants[i].status) {
            $("#foo_table_tbody").append('<tr id="row' + i + '" class="table-row"><tr>');
            var status = plants[i].status;
            /*var status_icon, status_icon_color;
            if(status == "connected") {
                status_icon = "fa fa-check-circle fa-x";
                status_icon_color = "green";
            } else if(status == "disconnected") {
                status_icon = "fa fa-times fa-x";
                status_icon_color = "red";
            }*/
            $("#row"+i).append('<td style="width: 25%;"><a href="' + "/solar/plant/" + plants[i].plant_slug + '/">' + plants[i].plant_name + '</a></td><td class="text-center" style="width: 12%;"><span id="energy_chart'+i+'"></span></td><td class="text-center" style="width: 12%;"><span id="pr_chart'+i+'"></span></td><td class="text-center" style="width: 18%;">' + plants[i].disconnected_inverters + ' / ' + plants[i].disconnected_smbs + '</td><td class="text-center" style="width: 14%;">' + plants[i].total_today_predicted_energy_value + '</td><td class="text-center" style="width: 15%;">' + plants[i].plant_generation_today + '</td><td class="text-center">' + plants[i].prediction_deviation + '</td>');
            var energy_id = "energy_chart"+i;
            var pr_id = "energy_chart"+i;
            var energy_date = [], energy_values = [];
            var pr_date = [], pr_values_array = [];
            
            if(plants[i].past_pr) {
                for(var individual_plant = 0; individual_plant < plants[i].past_pr.length; individual_plant++) {
                    var date = plants[i].past_pr[individual_plant].timestamp;
                    date = dateFormat(date, "mmm dd, yyyy");
                    pr_date.push(date);
                    var pr_value = plants[i].past_pr[individual_plant].pr;
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

    $(function() {
        $('.table').footable({
            "paging": {
                enabled: true
            }
        });
    });

}

function all_plants(summary_info, status) {

    $("#leaflet_map").empty();

    var latlng = [];
    var plants_location = [];

    var marker_color;

    var mapboxTiles = L.tileLayer('http://{s}.tiles.wmflabs.org/bw-mapnik/{z}/{x}/{y}.png', {
    });

    if(status != 0){
        // Create the map
        map = L.map('leaflet_map', {
            center: [28.7042,77.1025],
            scrollWheelZoom: false,
            zoomControl: false,
            zoom: 13
        }).addLayer(mapboxTiles);

        L.control.zoom({
            position: 'bottomleft'
        }).addTo(map);
    }

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
        iconUrl: 'https://harrywood.co.uk/maps/examples/leaflet/marker-icon-red.png',
        shadowUrl: '/static/solarrms/plugins/leafletjs/images/marker-shadow.png',

        iconSize:     [25, 41], // size of the icon
        shadowSize:   [41, 41], // size of the shadow
        iconAnchor:   [12, 41], // point of the icon which will correspond to marker's location
        shadowAnchor: [12, 41],  // the same for the shadow
        popupAnchor:  [-3, -76] // point from which the popup should open relative to the iconAnchor
    });

    var greenIcon = L.icon({
        iconUrl: 'https://camo.githubusercontent.com/256954f7aeac24805575508a3427a4956b5fb5b7/68747470733a2f2f7261772e6769746875622e636f6d2f706f696e7468692f6c6561666c65742d636f6c6f722d6d61726b6572732f6d61737465722f696d672f6d61726b65722d69636f6e2d677265656e2e706e673f7261773d74727565',
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

            });
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

            });;
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

            });;
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

        if(typeof client_data.plants[id].plant_name !== 'undefined') {
            plant_name = client_data.plants[id].plant_name
        } else {
            plant_name = "N/A";
        }

        $("#plant_name").empty();
        $("#plant_name").append(plant_name);

        var plant_current_power;

        if(typeof client_data.plants[id].current_power !== 'undefined') {
            plant_current_power = (client_data.plants[id].current_power).toFixed(2);
        } else {
            plant_current_power = "N/A";
        }

        $("#current_power_plant").empty();
        $("#current_power_plant").append(plant_current_power);

        var todays_plant_generation, todays_plant_generation_value, todays_plant_generation_unit;

        if(typeof client_data.plants[id].plant_generation_today !== 'undefined') {
            todays_plant_generation = client_data.plants[id].plant_generation_today;
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

        if(typeof client_data.plants[id].performance_ratio !== 'undefined' && typeof client_data.plants[id].cuf !== 'undefined') {
            pr = parseInt(client_data.plants[id].performance_ratio * 100);
            cuf = parseInt(client_data.plants[id].cuf * 100);
            pr_cuf_value = pr + "%/" + cuf + "%";
        } else {
            pr_cuf_value = "NA / NA"; 
        }

        $("#pr_cuf_plant").empty();
        $("#pr_cuf_plant").append(pr_cuf_value);

        var status = client_data.plants[id].status;
        var icon = null;
        var style = null;

        if(client_data.plants[id].status) {
            status = client_data.plants[id].status
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
        
        if(client_data.plants[id].updated_at) {
            last_updated = client_data.plants[id].updated_at;
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
}