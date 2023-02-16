$(document).ready(function() {

    summary_page_api();

    var dates = get_dates();
    var st = dates[0];
    var et = dates[1];

    power_irradiation_chart(plant_slug, st, et);

    transformers_chart();

});

function redraw_window() {
    $('a[data-toggle="tab"]').on('shown.bs.tab', function (e) {
        window.dispatchEvent(new Event('resize'));
    });
}

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

function summary_page_api() {

    $.ajax({
        type: "GET",
        url: "/api/v1/solar/client/summary/",
        success: function(summary_data) {

            summary_data = {"plant_name":"Waaneep Solar","plant_slug":"waaneep","plant_logo":"http://www.waaneep.com/images/headers/WaaneepLogo.png","plant_location":"Ichhawar, Madhya Pradesh","plant_capacity":50000.0,"latitude":23.2599,"longitude":77.4126,"performance_ratio":0.76,"cuf":0.06,"grid_unavailability":"0 %","equipment_unavailability":"1.14 %","unacknowledged_tickets":67,"open_tickets":0,"closed_tickets":1171,"plant_generation_today":"64380.00 kWh","plant_total_energy":"127.05 GWh","plant_co2":"45066.00 Kg","current_power":0.0,"irradiation":0.0,"connected_inverters":67,"disconnected_inverters":0,"invalid_inverters":0,"connected_smbs":379,"disconnected_smbs":23,"invalid_smbs":0,"network_up":"Yes","module_temperature":0.0,"ambient_temperature":0.0,"windspeed":0.0,"dc_loss":"0.00 kWh","conversion_loss":"0.00 kWh","ac_loss":"0.00 kWh","status":"connected","pvsyst_generation":"222.50 Mwh","pvsyst_pr":0.795,"pvsyst_tilt_angle":27.0,"updated_at":"2016-12-08T09:20:50.756000Z","past_generations":[{"timestamp":"2016-12-01T18:30:00Z","energy":"265.23 Mwh"},{"timestamp":"2016-12-02T18:30:00Z","energy":"231.59 Mwh"},{"timestamp":"2016-12-03T18:30:00Z","energy":"232.61 Mwh"},{"timestamp":"2016-12-04T18:30:00Z","energy":"7998.00 kWh"},{"timestamp":"2016-12-05T18:30:00Z","energy":"184.47 Mwh"},{"timestamp":"2016-12-06T18:30:00Z","energy":"258.74 Mwh"},{"timestamp":"2016-12-07T18:30:00Z","energy":"64380.00 kWh"}],"past_pr":[{"timestamp":"2016-12-01T18:30:00Z","pr":0.8},{"timestamp":"2016-12-07T18:30:00Z","pr":0.76}],"past_cuf":[{"timestamp":"2016-12-01T18:30:00Z","cuf":0.22},{"timestamp":"2016-12-02T18:30:00Z","cuf":0.19},{"timestamp":"2016-12-03T18:30:00Z","cuf":0.19},{"timestamp":"2016-12-04T18:30:00Z","cuf":0.25},{"timestamp":"2016-12-05T18:30:00Z","cuf":0.15},{"timestamp":"2016-12-06T18:30:00Z","cuf":0.18},{"timestamp":"2016-12-07T18:30:00Z","cuf":0.06}],"past_grid_unavailability":[{"timestamp":"2016-12-01T18:30:00Z","unavailability":"1.36 %"},{"timestamp":"2016-12-02T18:30:00Z","unavailability":"0.00 %"},{"timestamp":"2016-12-03T18:30:00Z","unavailability":"0.00 %"},{"timestamp":"2016-12-04T18:30:00Z","unavailability":"0.00 %"},{"timestamp":"2016-12-05T18:30:00Z","unavailability":"5.30 %"},{"timestamp":"2016-12-06T18:30:00Z","unavailability":"0.00 %"},{"timestamp":"2016-12-07T18:30:00Z","unavailability":"0.00 %"}],"past_equipment_unavailability":[{"timestamp":"2016-12-01T18:30:00Z","unavailability":"0.18 %"},{"timestamp":"2016-12-02T18:30:00Z","unavailability":"2.34 %"},{"timestamp":"2016-12-03T18:30:00Z","unavailability":"1.54 %"},{"timestamp":"2016-12-04T18:30:00Z","unavailability":"0.46 %"},{"timestamp":"2016-12-05T18:30:00Z","unavailability":"1.18 %"},{"timestamp":"2016-12-06T18:30:00Z","unavailability":"4.69 %"},{"timestamp":"2016-12-07T18:30:00Z","unavailability":"1.14 %"}],"past_dc_loss":[{"timestamp":"2016-12-01T18:30:00Z","dc_energy_loss":"21616.92 kWh"},{"timestamp":"2016-12-02T18:30:00Z","dc_energy_loss":"5985.23 kWh"},{"timestamp":"2016-12-03T18:30:00Z","dc_energy_loss":"16175.19 kWh"},{"timestamp":"2016-12-04T18:30:00Z","dc_energy_loss":"0.00 kWh"}],"past_conversion_loss":[{"timestamp":"2016-12-01T18:30:00Z","conversion_loss":"4666.58 kWh"},{"timestamp":"2016-12-02T18:30:00Z","conversion_loss":"824.08 kWh"},{"timestamp":"2016-12-03T18:30:00Z","conversion_loss":"2195.25 kWh"},{"timestamp":"2016-12-04T18:30:00Z","conversion_loss":"0.00 kWh"}],"past_ac_loss":[{"timestamp":"2016-12-01T18:30:00Z","ac_energy_loss":"-7111.07 kWh"},{"timestamp":"2016-12-02T18:30:00Z","ac_energy_loss":"-6785.05 kWh"},{"timestamp":"2016-12-03T18:30:00Z","ac_energy_loss":"-6593.72 kWh"},{"timestamp":"2016-12-04T18:30:00Z","ac_energy_loss":"0.00 kWh"}],"residual":{"Inverter_18.4":256.11,"Inverter_19.3":251.1,"Inverter_19.2":250.5,"Inverter_18.1":235.0,"Inverter_18.2":231.01,"Inverter_18.3":235.97,"Inverter_8.2":254.64,"Inverter_14.1":232.25,"Inverter_14.2":252.39,"Inverter_9.4":232.74,"Inverter_9.3":252.99,"Inverter_9.2":235.2,"Inverter_8.4":278.61,"Inverter_17.2":255.58,"Inverter_17.1":226.63,"Inverter_13.3":239.16,"Inverter_10.4":262.44,"Inverter_4.4":250.06,"Inverter_16.1":237.9,"Inverter_12.2":221.26,"Inverter_4.3":263.02,"Inverter_16.4":228.01,"Inverter_12.1":225.11,"Inverter_15.4":241.08,"Inverter_5.1":259.38,"Inverter_15.1":236.01,"Inverter_15.3":236.6,"Inverter_15.2":231.63,"Inverter_11.1":266.56,"Inverter_19.1":247.62,"Inverter_11.3":265.18,"Inverter_11.2":271.25,"Inverter_11.4":264.3,"Inverter_10.2":267.81,"Inverter_10.3":264.63,"Inverter_7.1":256.3,"Inverter_2.1":268.88,"Inverter_2.2":262.32,"Inverter_2.3":266.26,"Inverter_2.4":270.34,"Inverter_3.3":273.29,"Inverter_10.1":262.08,"Inverter_16.2":238.07,"Inverter_6.2":262.47,"Inverter_13.2":253.44,"Inverter_1.4":163.26,"Inverter_1.3":247.09,"Inverter_13.1":241.07,"Inverter_1.1":266.61,"Inverter_1.2":267.4,"Inverter_3.4":273.16,"Inverter_4.2":258.3,"Inverter_7.3":269.06,"Inverter_7.2":266.37,"Inverter_16.3":257.87,"Inverter_6.1":264.49,"Inverter_8.3":265.47,"Inverter_19.4":226.87,"Inverter_3.1":274.17,"Inverter_13.4":253.97,"Inverter_8.1":256.88,"Inverter_5.2":271.98,"Inverter_20.1":199.27,"Inverter_4.1":250.1,"Inverter_3.2":272.92}};

            console.log(summary_data);

            var energy_timestamps = [], energy_values = [];
            var pr_timestamps = [], pr_values = [], pr_text = [], timestamps_cuf = [], values_cuf = [], cuf_text = [];
            var ac_loss_timestamps = [], ac_loss_values = [];
            var conversion_loss_timestamps = [], conversion_loss_values = [];
            var dc_loss_timestamps = [], dc_loss_values = [];
            var grid_unavailability_timestamps = [], grid_unavailability_values = [];
            var equipment_unavailability_timestamps = [], equipment_unavailability_values = [];

            for(var i = 0; i < summary_data.past_generations.length; i++) {
                var energy_date = new Date(summary_data.past_generations[i].timestamp);
                energy_date = dateFormat(energy_date, "yyyy-mm-dd HH:MM:ss");
                var energy_value = parseFloat(summary_data.past_generations[i].energy);
                energy_timestamps.push(energy_date);
                energy_values.push(energy_value);

                if(summary_data.past_pr[i]) {
                    var pr_date = new Date(summary_data.past_pr[i].timestamp);
                    pr_date = dateFormat(pr_date, "yyyy-mm-dd HH:MM:ss");
                    var value_pr = parseFloat(summary_data.past_pr[i].pr);
                    pr_timestamps.push(pr_date);
                    pr_values.push(value_pr);
                    pr_text.push((dateFormat(pr_date, "dd-mm-yyyy").toString()).concat('<br>PR'));
                }

                if(summary_data.past_cuf[i]) {
                    var cuf_date = new Date(summary_data.past_cuf[i].timestamp);
                    cuf_date = dateFormat(cuf_date, "yyyy-mm-dd HH:MM:ss");
                    var cuf_value = parseFloat(summary_data.past_cuf[i].cuf);
                    timestamps_cuf.push(cuf_date);
                    values_cuf.push(cuf_value);
                    cuf_text.push((dateFormat(cuf_date, "dd-mm-yyyy").toString()).concat('<br>CUF'));
                }

                if(summary_data.past_ac_loss[i]) {
                    var date_ac_loss = new Date(summary_data.past_ac_loss[i].timestamp);
                    date_ac_loss = dateFormat(date_ac_loss, "yyyy-mm-dd HH:MM:ss");
                    var ac_loss_value = parseFloat(summary_data.past_ac_loss[i].ac_energy_loss);
                    ac_loss_timestamps.push(date_ac_loss);
                    ac_loss_values.push(ac_loss_value);
                }

                if(summary_data.past_conversion_loss[i]) {
                    var date_conversion_loss = new Date(summary_data.past_conversion_loss[i].timestamp);
                    date_conversion_loss = dateFormat(date_conversion_loss, "yyyy-mm-dd HH:MM:ss");
                    var conversion_loss_value = parseFloat(summary_data.past_conversion_loss[i].conversion_loss);
                    conversion_loss_timestamps.push(date_conversion_loss);
                    conversion_loss_values.push(conversion_loss_value);
                }

                if(summary_data.past_dc_loss[i]) {
                    var date_dc_loss = new Date(summary_data.past_dc_loss[i].timestamp);
                    date_dc_loss = dateFormat(date_dc_loss, "yyyy-mm-dd HH:MM:ss");
                    var dc_loss_value = parseFloat(summary_data.past_dc_loss[i].dc_energy_loss);
                    dc_loss_timestamps.push(date_dc_loss);
                    dc_loss_values.push(dc_loss_value);
                }

                if(summary_data.past_grid_unavailability[i]) {
                    var grid_unavailability_date = new Date(summary_data.past_grid_unavailability[i].timestamp);
                    grid_unavailability_date = dateFormat(grid_unavailability_date, "yyyy-mm-dd HH:MM:ss");
                    var grid_unavailability_value = parseFloat(summary_data.past_grid_unavailability[i].unavailability);
                    grid_unavailability_timestamps.push(grid_unavailability_date);
                    grid_unavailability_values.push(grid_unavailability_value);
                }

                if(summary_data.past_equipment_unavailability[i]) {
                    var equipment_unavailability_date = new Date(summary_data.past_equipment_unavailability[i].timestamp);
                    equipment_unavailability_date = dateFormat(equipment_unavailability_date, "yyyy-mm-dd HH:MM:ss");
                    var equipment_unavailability_value = parseFloat(summary_data.past_equipment_unavailability[i].unavailability);
                    equipment_unavailability_timestamps.push(equipment_unavailability_date);
                    equipment_unavailability_values.push(equipment_unavailability_value);
                }
            }

            var energy_title = "Weekly Energy";
            var energy_div_name = "weekly_energy_generation";
            var y_axis_title = "Weekly Energy";
            var page = 1;
            var b_m = 30, t_m = 30;

            basic_bar_chart_plotly(energy_timestamps, energy_values, y_axis_title, "", energy_title, energy_div_name, 30, 5, page, b_m, t_m);

            var name1 = 'PR';
            var name2 = 'CUF';
            var title_dual_axis_chart = "PR and CUF";
            var div_name = 'cuf_pr';
            var scatter_chart = 0;

            dual_axis_chart_plotly(pr_timestamps, pr_values, timestamps_cuf, values_cuf, pr_text, cuf_text, name1, name2, title_dual_axis_chart, div_name, page, scatter_chart, 40, 40, 30, 30);

            if(summary_data.residual) {

                var inverters = [];
                var residuals = [];
                var color = [];
                var residual_data = [];

                for(var inverter in summary_data.residual) {
                    if((summary_data.residual).hasOwnProperty(inverter)) {
                        inverters.push(inverter);
                        residuals.push(summary_data.residual[inverter]);
                    }
                }

                var residuals_title = "Residual Chart";
                var residuals_div_name = "residuals";
                var y_axis_title = "Residuals";
                var page = 1;
                var b_m = 80, t_m = 30;

                basic_bar_chart_plotly(inverters, residuals, y_axis_title, "", residuals_title, residuals_div_name, 30, 5, page, b_m, t_m);
                
            }

            /*var availability_title = "";
            var availability_div_name = "unavailability";
            y_axis_title = "Unavailability";
            var all_x_arrays = [grid_unavailability_timestamps, equipment_unavailability_timestamps];
            var all_y_arrays = [grid_unavailability_values, equipment_unavailability_values];
            var all_array_titles = ['Grid Unavailability', 'Equipment Unavailability'];

            b_m = 40, t_m = 5;

            relative_bar_chart_plotly(all_x_arrays, all_y_arrays, all_array_titles, availability_title, availability_div_name, 20, 5, page, b_m, t_m);*/

            /*var losses_title = "";
            var losses_div_name = "losses";
            y_axis_title = "Losses";
            all_x_arrays = [ac_loss_timestamps, conversion_loss_timestamps, dc_loss_timestamps];
            all_y_arrays = [ac_loss_values, conversion_loss_values, dc_loss_values];
            all_array_titles = ['AC Losses', 'Conversion Losses', 'DC Losses'];

            relative_bar_chart_plotly(all_x_arrays, all_y_arrays, all_array_titles, losses_title, losses_div_name, 30, 5, page, b_m, t_m);*/

            var values_tickets = [];

            values_tickets.push({label: "Closed Tickets", value: summary_data.closed_tickets});
            values_tickets.push({label: "Open Tickets", value: summary_data.open_tickets});
            values_tickets.push({label: "Unacknowledged Tickets", value: summary_data.unacknowledged_tickets});
            var colors = ['#29808E', '#8A6B3D', '#739EA7'];

            var tickets_div_name = "tickets";

            $("#tickets").empty();
            morris_donut_chart(values_tickets, tickets_div_name, colors);

            var values_grid_unavailability = [];

            var grid_availability = parseFloat(summary_data.grid_unavailability);
            grid_availability = 100 - grid_availability;

            values_grid_unavailability.push({label: "Grid Avail.", value: grid_availability});
            values_grid_unavailability.push({label: "Grid Unavail.", value: parseFloat(summary_data.grid_unavailability)});
            var colors = ['#29808E', '#8A6B3D', '#739EA7'];

            var grid_div_name = "grid_unavailability";

            $("#grid_unavailability").empty();
            morris_donut_chart(values_grid_unavailability, grid_div_name, colors);

            var values_equipment_unavailability = [];

            var equipment_availability = parseFloat(summary_data.equipment_unavailability);
            equipment_availability = 100 - equipment_availability;

            values_equipment_unavailability.push({label: "Equipment Avail.", value: equipment_availability});
            values_equipment_unavailability.push({label: "Equipment Unavail.", value: parseFloat(summary_data.equipment_unavailability)});
            var colors = ['#29808E', '#8A6B3D', '#739EA7'];

            var equipment_unavailability_div_name = "equipment_unavailability";

            $("#equipment_unavailability").empty();
            morris_donut_chart(values_equipment_unavailability, equipment_unavailability_div_name, colors);

            const data = [
                ['Todays Energy', parseFloat(summary_data.plant_generation_today)], ['AC Losses', parseFloat(summary_data.ac_loss)], ['Conversion Losses', parseFloat(summary_data.conversion_loss)], ['DC Losses', parseFloat(summary_data.dc_loss)]
            ];
            const options = { block: { dynamicHeight: false } };

            const chart = new D3Funnel('#losses_funnel');
            chart.draw(data, options);
        },
        error: function(data) {
            console.log("error_streams_data");
            data = null;
        }
    });

}

function power_irradiation_chart(plant_slug, st, et) {

    $.ajax({
        type: "GET",
        url: "/api/solar/plants/".concat(plant_slug).concat('/irradiation-power/'),
        data: {startTime: (st), endTime: (et)},
        success: function(power_irradiation) {
            
            power_irradiation = [
    {
        "timestamp": "2016-09-29T06:31:00.000Z",
        "power": 40148.0,
        "irradiation": 0.9611848755
    },
    {
        "timestamp": "2016-09-29T06:33:00.000Z",
        "power": 39979.0,
        "irradiation": 0.9666361694
    },
    {
        "timestamp": "2016-09-29T06:34:00.000Z",
        "power": 39748.0,
        "irradiation": 0.9810574951
    },
    {
        "timestamp": "2016-09-29T06:36:00.000Z",
        "power": 38969.0,
        "irradiation": 0.9854825439
    },
    {
        "timestamp": "2016-09-29T06:38:00.000Z",
        "power": 31666.0,
        "irradiation": 0.7253786621
    },
    {
        "timestamp": "2016-09-29T06:39:00.000Z",
        "power": 28595.0,
        "irradiation": 1.0080675659
    },
    {
        "timestamp": "2016-09-29T06:41:00.000Z",
        "power": 23961.0,
        "irradiation": 0.3920018311
    },
    {
        "timestamp": "2016-09-29T06:43:00.000Z",
        "power": 16304.0,
        "irradiation": 0.4334998474
    },
    {
        "timestamp": "2016-09-29T06:44:00.000Z",
        "power": 19547.0,
        "irradiation": 0.3667044983
    },
    {
        "timestamp": "2016-09-29T06:46:00.000Z",
        "power": 23997.0,
        "irradiation": 0.5894555664
    },
    {
        "timestamp": "2016-09-29T06:48:00.000Z",
        "power": 25110.0,
        "irradiation": 0.3641921082
    },
    {
        "timestamp": "2016-09-29T06:49:00.000Z",
        "power": 28919.0,
        "irradiation": 1.0103533935
    },
    {
        "timestamp": "2016-09-29T06:51:00.000Z",
        "power": 42863.0,
        "irradiation": 0.8592358398
    },
    {
        "timestamp": "2016-09-29T06:53:00.000Z",
        "power": 37209.0,
        "irradiation": 1.0108265381
    },
    {
        "timestamp": "2016-09-29T06:54:00.000Z",
        "power": 32735.0,
        "irradiation": 0.7912543335
    },
    {
        "timestamp": "2016-09-29T06:56:00.000Z",
        "power": 22189.0,
        "irradiation": 0.3542557678
    },
    {
        "timestamp": "2016-09-29T06:58:00.000Z",
        "power": 20769.0,
        "irradiation": 0.3819855347
    },
    {
        "timestamp": "2016-09-29T06:59:00.000Z",
        "power": 21033.0,
        "irradiation": 0.5933407593
    },
    {
        "timestamp": "2016-09-29T07:01:00.000Z",
        "power": 24078.0,
        "irradiation": 0.3185422974
    },
    {
        "timestamp": "2016-09-29T07:02:00.000Z",
        "power": 12054.0,
        "irradiation": 0.2775507812
    },
    {
        "timestamp": "2016-09-29T07:04:00.000Z",
        "power": 11117.0,
        "irradiation": 0.2716862793
    },
    {
        "timestamp": "2016-09-29T07:06:00.000Z",
        "power": 9467.0,
        "irradiation": 0.2224111633
    },
    {
        "timestamp": "2016-09-29T07:07:00.000Z",
        "power": 19169.0,
        "irradiation": 0.2834286194
    },
    {
        "timestamp": "2016-09-29T07:09:00.000Z",
        "power": 29843.0,
        "irradiation": 0.9452840576
    },
    {
        "timestamp": "2016-09-29T07:11:00.000Z",
        "power": 41879.0,
        "irradiation": 0.9746998901
    },
    {
        "timestamp": "2016-09-29T07:12:00.000Z",
        "power": 42269.0,
        "irradiation": 1.0171975098
    },
    {
        "timestamp": "2016-09-29T07:14:00.000Z",
        "power": 43010.0,
        "irradiation": 1.0303193359
    },
    {
        "timestamp": "2016-09-29T07:16:00.000Z",
        "power": 42114.0,
        "irradiation": 0.9978513184
    },
    {
        "timestamp": "2016-09-29T07:17:00.000Z",
        "power": 26946.0,
        "irradiation": 0.3073864136
    },
    {
        "timestamp": "2016-09-29T07:19:00.000Z",
        "power": 10983.0,
        "irradiation": 0.2735455933
    },
    {
        "timestamp": "2016-09-29T07:21:00.000Z",
        "power": 16016.0,
        "irradiation": 0.3570547485
    },
    {
        "timestamp": "2016-09-29T07:22:00.000Z",
        "power": 18083.0,
        "irradiation": 0.3142972107
    },
    {
        "timestamp": "2016-09-29T07:24:00.000Z",
        "power": 21599.0,
        "irradiation": 0.377473877
    },
    {
        "timestamp": "2016-09-29T07:26:00.000Z",
        "power": 30112.0,
        "irradiation": 0.9561933594
    },
    {
        "timestamp": "2016-09-29T07:27:00.000Z",
        "power": 34257.0,
        "irradiation": 1.0132856445
    },
    {
        "timestamp": "2016-09-29T07:29:00.000Z",
        "power": 32761.0,
        "irradiation": 0.8832869873
    }
]

            console.log(power_irradiation);

            var power_timestamps = [], power_values = [], irradiation_timestamps = [], irradiation_values = [], power_text = [], irradiation_text = [];

            for(var i = 0; i < power_irradiation.length; i++) {
                var power_date = new Date(power_irradiation[i].timestamp);
                power_date = dateFormat(power_date, "yyyy-mm-dd HH:MM:ss");
                var power_value = parseFloat(power_irradiation[i].power);
                power_timestamps.push(power_date);
                power_values.push(power_value);
                power_text.push((dateFormat(power_date, "HH:MM:ss").toString()).concat('<br>Power'));

                var irradiation_date = new Date(power_irradiation[i].timestamp);
                irradiation_date = dateFormat(irradiation_date, "yyyy-mm-dd HH:MM:ss");
                var irradiation_value = parseFloat(power_irradiation[i].irradiation);
                irradiation_timestamps.push(irradiation_date);
                irradiation_values.push(irradiation_value);
                irradiation_text.push((dateFormat(irradiation_date, "HH:MM:ss").toString()).concat('<br>Irradiation'));
            }

            var name1 = 'POWER';
            var name2 = 'IRRADIATION';
            var title_dual_axis_chart = "Today's Power and Irradiation";
            var div_name = 'power_irradiation';
            var page = 1;
            var scatter_chart = 1;

            dual_axis_chart_plotly(power_timestamps, power_values, irradiation_timestamps, irradiation_values, power_text, irradiation_text, name1, name2, title_dual_axis_chart, div_name, page, scatter_chart, 40, 40, 30, 30);

        },
        error: function(data) {
            console.log("error_streams_data");
            data = null;
        }
    });

}

function transformers_chart() {

    var transformer_data = [
        {
        "timestamp": "2016-09-29T04:30:00.000Z",
        "energy_input": 30.0,
        "energy_import": 40,
        "efficiency": 70
    },
    {
        "timestamp": "2016-09-29T05:30:00.000Z",
        "energy_input": 36.0,
        "energy_import": 47,
        "efficiency": 80
    },
    {
        "timestamp": "2016-09-29T06:30:00.000Z",
        "energy_input": 38.0,
        "energy_import": 48,
        "efficiency": 70
    },
    {
        "timestamp": "2016-09-29T07:30:00.000Z",
        "energy_input": 39.0,
        "energy_import": 50,
        "efficiency": 90
    },
    {
        "timestamp": "2016-09-29T08:30:00.000Z",
        "energy_input": 40.0,
        "energy_import": 53,
        "efficiency": 91
    },
    {
        "timestamp": "2016-09-29T09:30:00.000Z",
        "energy_input": 44.0,
        "energy_import": 55,
        "efficiency": 95
    },
    {
        "timestamp": "2016-09-29T10:30:00.000Z",
        "energy_input": 40.0,
        "energy_import": 51,
        "efficiency": 91
    },
    {
        "timestamp": "2016-09-29T11:30:00.000Z",
        "energy_input": 39.0,
        "energy_import": 45,
        "efficiency": 88
    },
    {
        "timestamp": "2016-09-29T12:30:00.000Z",
        "energy_input": 38.0,
        "energy_import": 40,
        "efficiency": 80
    }
    ];

    var energy_input_timestamps = [], energy_input_values = [], energy_import_timestamps = [], energy_import_values = [], efficiency_timestamps = [], efficiency_values = [];

    for(var i = 0; i < transformer_data.length; i++) {
        var energy_input_date = new Date(transformer_data[i].timestamp);
        energy_input_date = dateFormat(energy_input_date, "HH:MM");
        var energy_input_value = parseFloat(transformer_data[i].energy_input);
        energy_input_timestamps.push(energy_input_date);
        energy_input_values.push(energy_input_value);

        var energy_import_value = parseFloat(transformer_data[i].energy_import);
        energy_import_values.push(energy_import_value);

        var efficiency_value = parseFloat(transformer_data[i].efficiency);
        efficiency_values.push(efficiency_value);
    }

    var title_dual_axis_chart = '';
    var div_name = 'cuf_pr';
    var scatter_chart = 0;

    var all_x_arrays = [energy_input_timestamps, energy_input_timestamps, energy_input_timestamps];
    var all_y_arrays = [energy_input_values, energy_import_values, efficiency_values];
    var all_y_array_names = ['Input', 'Import', 'Efficiency'];
    var all_y_axis_number = ['y1', 'y1', 'y2'];
    var multiple_axis_chart_title = "Transformers";
    var multiple_axis_div_name = "transformers";
    var l_m = 40, r_m = 40, b_m = 30, t_m = 30;
    var page = 1;

    multiple_axis_chart_plotly(all_x_arrays, all_y_arrays, all_y_array_names, all_y_axis_number, multiple_axis_chart_title, multiple_axis_div_name, l_m, r_m, page, b_m, t_m);

}