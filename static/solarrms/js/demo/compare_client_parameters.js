$(document).ready(function() {
    
    $("#breadcrumb_page_path").empty();
    $("#breadcrumb_page_path").append('<li class="text-center text-bold" ><a href="#">Client</a></li><li class="text-center text-bold"><a href="#">Client Dashboard</a></li><li class="text-center text-bold"><a href="#">Plant Dashboard</a></li><li class="text-center text-bold"><a href="#">Reports</a></li>')

    plant_names(plant_info);
});

$('.datepicker').datepicker({
    autoclose: true,
    todayHighlight: true,
    startView: "days",
    minViewMode: "days",
    format: "dd-mm-yyyy"
});

$('.datepicker_end_time').datepicker({
    autoclose: true,
    todayHighlight: true,
    startView: "days",
    minViewMode: "days",
    format: "dd-mm-yyyy"
});

function get_dates(){
    // get the start date
    var st = $(".datepicker").val();

    console.log(st);

    st = st.split("-");
    st = st[2] + "-" + st[1] + "-" + st[0];    

    /*var st = new Date();*/
    if (st == '') {
        st = new Date();
    } else {
        st = new Date(st);
    }

    var e = "";

    // prepare an end date
    if(aggregator_string == false) {
        e = new Date(st.getTime());
        e = new Date(e.setDate(st.getDate() + 1));
    } else {
        var et = $(".datepicker_end_time").val();
        if(aggregator_time_string == "MINUTE") {
            var e = new Date(st.getTime());
            e = new Date(e.setDate(st.getDate() + 1));
        } else {
            if(et == '') {
                $("#client_spinner").hide();

                noty_message("Please select an end date!", 'error', 5000)
                return;
            } else {
                et = et.split("-");
                et = et[2] + "-" + et[1] + "-" + et[0];
                e = new Date(et);
            }
        }
    }

    st = dateFormat(st, "yyyy-mm-dd");
    e = dateFormat(e, "yyyy-mm-dd");

    return [st, e];
}

function plant_names(plant_info) {

    console.log(plant_info);

    for(var plant_names = 0; plant_names < plant_info.length; plant_names++) {
        $("#plant_names_dropdown").append("<option value='" + plant_info[plant_names].plant_slug + "' sourceKey='" + plant_info[plant_names].plant_slug + "'>" + plant_info[plant_names].plant_name + "</option>");
    }

    $("#plant_names_dropdown").SumoSelect({triggerChangeCombined: false, search: true, searchText: 'Search Plant Names', placeholder: 'Plant Names'});

    $("#plant_names_dropdown").hide();

    $("#client_spinner").hide();

}

var slugs_selected = [];

$("#devices-button").click(function() {

    $("#client_spinner").show();

    var plant_names_selected = [];

    $('#plant_names_dropdown option:selected').each(function(i) {
        plant_names_selected.push($(this).val());
    });

    console.log(plant_names_selected);

    devices(plant_names_selected);

})

function devices(plant_names_selected) {

    var plant_slugs_selected = {
        "plant_slugs": plant_names_selected
    }

    $.ajax({
        type: "POST",
        dataType: "json",
        contentType: "application/json; charset=utf-8",
        url: "/api/v1/solar/devices/",
        data: JSON.stringify(plant_slugs_selected),
        success: function(devices_list) {

            console.log(devices_list);

            var plant_slug_devices = [];

            $("#plant_meta_source").empty();
            $("#plant_solar_metrics").empty();
            $("#energy_meters").empty();
            $("#inverters").empty();
            $("#ajbs").empty();

            var plant_meta_source_flag = 0;
            var solar_metrics_flag = 0;
            var energy_meters_flag = 0;
            var transformers_flag = 0;
            var inverters_flag = 0;
            var ajbs_flag = 0;

            for(var plant_name = 0; plant_name < plant_names_selected.length; plant_name++) {
                console.log(plant_names_selected[plant_name]);
                console.log(devices_list[plant_names_selected[plant_name]]);
                if("plant_meta_source" in devices_list[plant_names_selected[plant_name]]) {
                    plant_meta_source_flag = 1;

                    if(plant_name == 0) {
                        $("#plant_meta_source").append('<div class="col-md-12"><div class="form-group"><select class="form-control" id="plant_meta_source_names_dropdown" multiple></select></div></div><div class="col-md-12"><div class="form-group"><select class="form-control" id="plant_meta_source_stream_dropdown" multiple></select></div></div>');
                    }

                    $("#plant_meta_source_names_dropdown").append("<optgroup label='" + plant_names_selected[plant_name] + "' class='group-plant_meta_source-" + plant_name + "'>" + (plant_names_selected[plant_name]).toString() + "</optgroup>");

                    for(var plant_meta_source_device_name in devices_list[plant_names_selected[plant_name]].plant_meta_source.plant_meta_source_names) {

                        $(".group-plant_meta_source-"+plant_name).append("<option value='" + devices_list[plant_names_selected[plant_name]].plant_meta_source.plant_meta_source_names[plant_meta_source_device_name] + "' sourceKey='" + devices_list[plant_names_selected[plant_name]].plant_meta_source.plant_meta_source_names[plant_meta_source_device_name] + "'>" + plant_meta_source_device_name + "</option>")
                    }
                }

                if("solar_metrics" in devices_list[plant_names_selected[plant_name]]) {
                    solar_metrics_flag = 1;

                    if(plant_name == 0) {
                        $("#plant_solar_metrics").append('<div class="col-md-12"><div class="form-group"><select class="form-control" id="plant_solar_metrics_names_dropdown" multiple></select></div></div><div class="col-md-12"><div class="form-group"><select class="form-control" id="plant_solar_metrics_stream_dropdown" multiple></select></div></div>');
                    }

                    $("#plant_solar_metrics_names_dropdown").append("<optgroup label='" + plant_names_selected[plant_name] + "' class='group-plant_solar_metrics-" + plant_name + "'>" + (plant_names_selected[plant_name]).toString() + "</optgroup>");

                    for(var solar_metric_device_name in devices_list[plant_names_selected[plant_name]].solar_metrics.solar_metric_names) {
                        $(".group-plant_solar_metrics-"+plant_name).append("<option value='" + devices_list[plant_names_selected[plant_name]].solar_metrics.solar_metric_names[solar_metric_device_name] + "' sourceKey='" + devices_list[plant_names_selected[plant_name]].solar_metrics.solar_metric_names[solar_metric_device_name] + "'>" + solar_metric_device_name + "</option>")
                    }
                }
                    
                if("energy_meters" in devices_list[plant_names_selected[plant_name]]) {
                    energy_meters_flag = 1;

                    if(plant_name == 0) {
                        $("#energy_meters").append('<div class="col-md-12"><div class="form-group"><select class="form-control" id="energy_meters_names_dropdown" multiple></select></div></div><div class="col-md-12"><div class="form-group"><select class="form-control" id="energy_meters_streams_dropdown" multiple></select></div></div>');
                    }

                    $("#energy_meters_names_dropdown").append("<optgroup label='" + plant_names_selected[plant_name] + "' class='group-energy_meters-" + plant_name + "'>" + (plant_names_selected[plant_name]).toString() + "</optgroup>");

                    for(var energy_meter_device_name in devices_list[plant_names_selected[plant_name]].energy_meters.energy_meter_names) {
                        $(".group-energy_meters-"+plant_name).append("<option value='" + devices_list[plant_names_selected[plant_name]].energy_meters.energy_meter_names[energy_meter_device_name] + "' sourceKey='" + devices_list[plant_names_selected[plant_name]].energy_meters.energy_meter_names[energy_meter_device_name] + "'>" + energy_meter_device_name + "</option>")
                    }
                }

                if("inverters" in devices_list[plant_names_selected[plant_name]]) {
                    inverters_flag = 1;

                    if(plant_name == 0) {
                        $("#inverters").append('<div class="col-md-12"><div class="form-group"><select class="form-control" id="inverters_names_dropdown" multiple></select></div></div><div class="col-md-12"><div class="form-group"><select class="form-control" id="inverters_streams_dropdown" multiple></select></div></div>');
                    }

                    $("#inverters_names_dropdown").append("<optgroup label='" + plant_names_selected[plant_name] + "' class='group-inverters-" + plant_name + "'>" + (plant_names_selected[plant_name]).toString() + "</optgroup>");

                    if(devices_list[plant_names_selected[plant_name]].inverters.inverter_names) {
                        for(var inverter_name in devices_list[plant_names_selected[plant_name]].inverters.inverter_names) {
                            $(".group-inverters-"+plant_name).append("<option value='" + devices_list[plant_names_selected[plant_name]].inverters.inverter_names[inverter_name] + "' sourceKey='" + devices_list[plant_names_selected[plant_name]].inverters.inverter_names[inverter_name] + "'>" + inverter_name + "</option>")
                        }    
                    } else {
                        for(var inverter_group in devices_list[plant_names_selected[plant_name]].inverters) {
                            $("#inverters_names_dropdown").append("<optgroup label='" + inverter_group + "' class='group-inverters-" + inverter_group + "'>Group - " + inverter_group + "</optgroup>");
                            for(var inv in devices_list[plant_names_selected[plant_name]].inverters[inverter_group]) {
                                $(".group-inverters-"+inverter_group).append("<option value='" + devices_list[plant_names_selected[plant_name]].inverters[inverter_group][inv] + "' sourceKey='" + devices_list[plant_names_selected[plant_name]].inverters[inverter_group][inv] + "'>" + inv + "</option>")
                            }
                        }
                    }
                }

                if("ajbs" in devices_list[plant_names_selected[plant_name]]) {
                    ajbs_flag = 1;

                    if(plant_name == 0) {
                        $("#ajbs").append('<div class="col-md-12"><div class="form-group"><select class="form-control" id="ajbs_names_dropdown" multiple></select></div></div><div class="col-md-12"><div class="form-group"><select class="form-control" id="ajbs_streams_dropdown" multiple></select></div></div>');
                    }

                    $("#ajbs_names_dropdown").append("<optgroup label='" + plant_names_selected[plant_name] + "' class='group-ajbs-" + plant_name + "'>" + (plant_names_selected[plant_name]).toString() + "</optgroup>");

                    if(devices_list[plant_names_selected[plant_name]].ajbs.ajb_names) {
                        for(var ajb_name in devices_list[plant_names_selected[plant_name]].ajbs.ajb_names) {
                            $(".group-ajbs-"+plant_name).append("<option value='" + devices_list[plant_names_selected[plant_name]].ajbs.ajb_names[ajb_name] + "' sourceKey='" + devices_list[plant_names_selected[plant_name]].ajbs.ajb_names[ajb_name] + "'>" + ajb_name + "</option>")
                        }    
                    } else {
                        for(var ajb_group in devices_list[plant_names_selected[plant_name]].ajbs) {
                            $("#ajbs_names_dropdown").append("<optgroup label='" + ajb_group + "' class='group-smbs-" + ajb_group + "'>" + ajb_group + "</optgroup>");
                            for(var ajb in devices_list[plant_names_selected[plant_name]].ajbs[ajb_group]) {
                                $(".group-smbs-"+ajb_group).append("<option value='" + devices_list[plant_names_selected[plant_name]].ajbs[ajb_group][ajb] + "' sourceKey='" + devices_list[plant_names_selected[plant_name]].ajbs[ajb_group][ajb] + "'>" + ajb + "</option>")
                            }
                        }
                    }
                }
            }

            if("plant_meta_streams" in devices_list) {
                for(var stream in devices_list.plant_meta_streams) {
                    $("#plant_meta_source_stream_dropdown").append("<option value='" + devices_list.plant_meta_streams[stream] + "'>" + devices_list.plant_meta_streams[stream] + "</option>")
                }
            } else {
                $("#plant_meta_source").empty();
                $("#plant_meta_source").append("<h4 class='text-center'>No Plant Metric Sources</h4>");
            }

            if("solar_metric_streams" in devices_list) {
                for(var stream in devices_list.solar_metric_streams) {
                    $("#plant_solar_metrics_stream_dropdown").append("<option value='" + devices_list.solar_metric_streams[stream] + "'>" + devices_list.solar_metric_streams[stream] + "</option>")
                }
            } else {
                $("#plant_solar_metrics").empty();
                $("#plant_solar_metrics").append("<h4 class='text-center'>No Plant Metrics</h4>");
            }

            if("energy_meter_streams" in devices_list) {
                for(var stream in devices_list.energy_meter_streams) {
                    $("#energy_meters_streams_dropdown").append("<option value='" + devices_list.energy_meter_streams[stream] + "'>" + devices_list.energy_meter_streams[stream] + "</option>")
                }
            } else {
                $("#energy_meters").empty();
                $("#energy_meters").append("<h4 class='text-center'>No Energy Meters</h4>");
            }

            if("inverter_streams" in devices_list) {
                for(var stream in devices_list.inverter_streams) {
                    $("#inverters_streams_dropdown").append("<option value='" + devices_list.inverter_streams[stream] + "'>" + devices_list.inverter_streams[stream] + "</option>")
                }
            } else {
                $("#inverters").empty();

                if(client_slug == "edp") {
                    $("#inverters").append("<h4 class='text-center'>No Inverter Devices</h4>");
                } else {
                    $("#inverters").append("<h4 class='text-center'>No Panel Devices</h4>");
                }
            }

            if("ajb_streams" in devices_list) {
                for(var stream in devices_list.ajb_streams) {
                    $("#ajbs_streams_dropdown").append("<option value='" + devices_list.ajb_streams[stream] + "'>" + devices_list.ajb_streams[stream] + "</option>")
                }
            } else {
                $("#ajbs").empty();
                $("#ajbs").append("<h4 class='text-center'>No SMB Devices</h4>");
            }

             /*$("#categories_dropdown").SumoSelect({placeholder: 'Categories'});*/

            $("#plant_meta_source_names_dropdown").SumoSelect({triggerChangeCombined: false, search: true, searchText: 'Search Plant Metrics', placeholder: 'Plant Metrics Option', selectAll: select_all});
            $("#plant_meta_source_stream_dropdown").SumoSelect({triggerChangeCombined: false, search: true, searchText: 'Search Plant Parameters', placeholder: 'Plant Metrics Stream', selectAll: select_all});

            $("#plant_solar_metrics_names_dropdown").SumoSelect({triggerChangeCombined: false, search: true, searchText: 'Search Plant Solar Metrics', placeholder: 'Plant Solar Metrics', selectAll: select_all});
            $("#plant_solar_metrics_stream_dropdown").SumoSelect({triggerChangeCombined: false, search: true, searchText: 'Search Metrics', placeholder: 'Metrics', selectAll: select_all});

            $("#energy_meters_names_dropdown").SumoSelect({triggerChangeCombined: false, search: true, searchText: 'Search Energy Meters', placeholder: 'Energy Meter Options', selectAll: select_all});
            $("#energy_meters_streams_dropdown").SumoSelect({triggerChangeCombined: false, search: true, searchText: 'Search Energy Parameters', placeholder: 'Energy Meter Streams', selectAll: select_all});

            if(client_slug == "edp") {
                $("#inverters_names_dropdown").SumoSelect({triggerChangeCombined: false, search: true, searchText: 'Search Panel Devices', placeholder: 'Panel Devices', selectAll: select_all});
                $("#inverters_streams_dropdown").SumoSelect({triggerChangeCombined: false, search: true, searchText: 'Search Panel Parameters', placeholder: 'Panel Streams', selectAll: select_all});
            } else {
                $("#inverters_names_dropdown").SumoSelect({triggerChangeCombined: false, search: true, searchText: 'Search Inverter Devices', placeholder: 'Inverter Devices', selectAll: select_all});
                $("#inverters_streams_dropdown").SumoSelect({triggerChangeCombined: false, search: true, searchText: 'Search Inverter Parameters', placeholder: 'Inverter Streams', selectAll: select_all});
            }

            $("#ajbs_names_dropdown").SumoSelect({triggerChangeCombined: false, search: true, searchText: 'Search SMB Devices', placeholder: 'SMB Devices', selectAll: select_all});
            $("#ajbs_streams_dropdown").SumoSelect({triggerChangeCombined: false, search: true, searchText: 'Search SMB Parameters', placeholder: 'SMB Device Streams', selectAll: select_all});

            $("#inverters_names_dropdown").hide();
            $("#inverters_streams_dropdown").hide();

            $("#ajbs_names_dropdown").hide();
            $("#ajbs_streams_dropdown").hide();

            $("#plant_meta_source_names_dropdown").hide();
            $("#plant_meta_source_stream_dropdown").hide();

            $("#plant_solar_metrics_names_dropdown").hide();
            $("#plant_solar_metrics_stream_dropdown").hide();

            $("#energy_meters_names_dropdown").hide();
            $("#energy_meters_streams_dropdown").hide();

            slugs_selected = plant_names_selected;

            $("#client_spinner").hide();
        },
        error: function(data) {
            console.log("error_streams_data");
            data = null;

            $("#client_spinner").hide();
        }
    });

}

function convert_strings_to_dates (data) {
    // array of arrays with a y in each array
    for (var i = 0; i < data.length; i++){
        var arr = [];
        arr = data[i].x.map(function(d){return new Date(d)});
        data[i].x = arr;
    }

    return data;
}
function multiple_chart(multiple_parameters) {

    $("#multiple_parameter_no_data").empty();
    $("#client_spinner").show();

    var dates = get_dates();
    var st = dates[0];
    var et = dates[1];

    aggregator_period_string = $("#aggregator_period_dropdown").val();

    aggregator_type_string = $("#aggregator_type").text();

    if(aggregator_type_string == "Mean") {
        aggregator_type_string = "mean";
    } else if(aggregator_type_string == "Minimum") {
        aggregator_type_string = "min";
    } else if(aggregator_type_string == "Maximum") {
        aggregator_type_string = "max";
    }

    if(aggregator_string == true) {

        aggregator_period_string = $("#aggregator_period_dropdown").val();

        if(aggregator_time_string == undefined || aggregator_time_string == "Average Unit") {
            $("#client_spinner").hide();

            noty_message("Please select an Average Unit", "error", 5000);
            return;
        } else if(aggregator_period_string == null || aggregator_period_string == "Average Interval") {
            $("#client_spinner").hide();

            noty_message("Please select an Average Interval", "error", 5000);
            return;
        } else if(aggregator_type_string == undefined) {
            $("#client_spinner").hide();

            noty_message("Please select an Aggregator Type", "error", 5000);
            return;
        }

        api_url = "/api/v1/solar/plants/".concat(slugs_selected[0]).concat('/multiple_devices_streams/').concat("?startTime="+st).concat("&endTime="+et).concat("&data_aggregation=true&aggregator="+aggregator_time_string).concat("&aggregation_period="+aggregator_period_string).concat("&aggregation_type="+aggregator_type_string);

    } else {

        api_url = "/api/v1/solar/plants/".concat(slugs_selected[0]).concat('/multiple_devices_streams/').concat("?startTime="+st).concat("&endTime="+et);

    }

    $.ajax({
        type: "POST",
        dataType: "json",
        contentType: "application/json; charset=utf-8",
        url: api_url,
        data: JSON.stringify(multiple_parameters),
        success: function(multiple_data_array){
            console.log(multiple_data_array);

            $("#multiple_parameter_no_data").empty();
            var units = Object.keys(multiple_data_array);
            
            var mf = ((units.length+1)/2);
            var x_domain = [0.05* mf, 1 - 0.05*mf];

            if(units.length < 1) {

                $("#client_spinner").hide();

                noty_message("No data for the selected devices and date", "information", 4000);
                return;
                
                $("#multiple_parameter_download_no_data").empty();
                $("#multiple-parameters-li").addClass("disabled");
                $("#multiple-parameters-before-li").addClass("disabled");

            } else {

                $("#multiple_parameter_download_no_data").empty();

                var traces = [];

                var colors = ["#e74c3c", "#2672a6", "#26a69a", "#f9b450", "#2980b9", "#ffd226", "#9f5594", "#33373a"];

                var colors_counter = 0;

                for(var unit in multiple_data_array) {
                    for(var parameter in multiple_data_array[unit]) {
                        multiple_data_array[unit][parameter]["marker"] = {
                            color: colors[colors_counter]
                        };
                        multiple_data_array[unit][parameter]["unit"] = unit;
                    }
                    colors_counter++;
                    traces.push(multiple_data_array[unit]);
                }

                traces = [].concat.apply([], traces);

                var tooltip_array = [];

                for(var i = 0; i < traces.length; i++) {
                    tooltip_array = [];
                    for(var j = 0; j < traces[i].y.length; j++) {
                        tooltip_array.push("(" + dateFormat(traces[i].x[j], "mmm dd HH:MM") + ", " + traces[i].y[j] + " " + traces[i].unit + ")" + " - " + traces[i].name);
                    }
                    traces[i]["text"] = tooltip_array;
                    traces[i]["hoverinfo"] = 'text';
                }

                var chart_legend_flag = 0;

                if(traces.length > 20) {
                    chart_legend_flag = false;
                } else {
                    chart_legend_flag = true;
                }

                var colors_single = 0;

                if(units.length == 1) {
                    for(var single_unit = 0; single_unit < traces.length; single_unit++) {
                        console.log(colors[colors_single]);
                        traces[single_unit].marker.color = colors[colors_single];
                        colors_single++;
                        if(colors_single == (colors.length)) {
                            colors_single = 0;
                        }
                    }
                }

                var t0 = new Date();
                var data = convert_strings_to_dates(traces);
                console.log("conversion time: ", new Date() - t0);

                var layout = {
                    title: '',
                    margin: {
                        l: 70,
                        r: 65,
                        b: 40,
                        t: 10,
                        pad: 0
                    },
                    xaxis: {
                        domain: x_domain,
                        showgrid: false
                    },
                    yaxis: {
                        title: units[0],
                        titlefont: {color: colors[0]}, 
                        tickfont: {color: colors[0]}
                    },
                    showlegend: chart_legend_flag,
                    legend: {
                        x: mf*0.05,
                        y: -0.2,
                        orientation: "h"
                    },
                    font: {
                        family: 'Helvetica',
                        size: 11,
                        weight: 'normal',
                        color: "#000000"
                    }
                };

                var y2 = {};

                if(units.length >= 2) {
                    y2 = {
                        title: units[1],
                        titlefont: {color: colors[1]}, 
                        tickfont: {color: colors[1]},
                        anchor: 'x', 
                        overlaying: 'y', 
                        side: 'right'
                    };

                    layout["yaxis2"] = y2;
                }

                var side;
                var anchor;
                var pos = 0;
                var left_pos = 0;
                var right_pos = 1;

                for(var unit_count = 2; unit_count < units.length; unit_count++) {
                    if(unit_count % 2 == 0) {
                        pos = left_pos;
                        side = 'left';
                        anchor = 'free';
                        pos = pos + 0.05;
                        left_pos = pos;
                    } else {
                        pos = right_pos;
                        side = 'right';
                        anchor = 'free';
                        pos = pos - 0.05;
                        right_pos = pos;
                    } 

                    layout["yaxis"+((unit_count+1).toString())] = {
                        title: units[unit_count],
                        titlefont: {color: colors[unit_count]}, 
                        tickfont: {color: colors[unit_count]},
                        anchor: anchor,
                        overlaying: 'y',
                        side: side,
                        position: parseFloat(pos.toFixed(2))
                    }
                }

                /*Plotly.newPlot('multiple_parameters_chart', data, layout, {displaylogo: false, modeBarButtonsToRemove: ['sendDataToCloud', 'lasso2d', 'select2d', , 'zoom2d', 'pan2d', 'zoomIn2d', 'zoomOut2d', 'autoScale2d', 'resetScale2d', 'hoverClosestCartesian', 'hoverCompareCartesian']});*/
                Plotly.newPlot('multiple_parameters_chart', data, layout, {displaylogo: false, modeBarButtonsToRemove: ['sendDataToCloud', 'lasso2d', 'select2d', 'pan2d', 'autoScale2d', 'resetScale2d', 'hoverClosestCartesian', 'hoverCompareCartesian']});

                $("#multiple-parameters-li").removeClass("disabled");
                $("#multiple-parameters-before-li").removeClass("disabled");

                $("#client_spinner").hide();
            }
        },
        error: function(data){
            console.log("no data");

            $("#multiple_parameter_download_no_data").empty();

            $("#client_spinner").hide();

            noty_message("No data for the selected devices and date", "information", 4000);
            return;
        }
    });


}

function data_download(download_parameters) {    

    $("#client_spinner").show();

    var dates = get_dates();
    var st = dates[0] + " 00:00:00";
    var et = dates[1] + " 00:00:00";

    var multiple_download_url;

    aggregator_period_string = $("#aggregator_period_dropdown").val();

    aggregator_type_string = $("#aggregator_type").text();    

    if(aggregator_type_string == "Mean") {
        aggregator_type_string = "mean";
    } else if(aggregator_type_string == "Minimum") {
        aggregator_type_string = "min";
    } else if(aggregator_type_string == "Maximum") {
        aggregator_type_string = "max";
    }
    
    if(aggregator_string == true) {

        aggregator_period_string = $("#aggregator_period_dropdown").val();

        if(aggregator_time_string == undefined || aggregator_time_string == "Average Unit") {
            $("#client_spinner").hide();

            noty_message("Please select an Aggregator Time", "error", 5000);
            return;
        } else if(aggregator_period_string == null || aggregator_period_string == "Average Interval") {
            $("#client_spinner").hide();

            noty_message("Please select an Aggregator Period", "error", 5000);
            return;
        } else if(aggregator_type_string == undefined) {
            $("#client_spinner").hide();

            noty_message("Please select an Aggregator Type", "error", 5000);
            return;
        }

        multiple_download_url = "/api/v1/solar/plants/".concat(slugs_selected[0]).concat('/multiple_devices_streams/data/download/').concat("?startTime="+st).concat("&endTime="+et).concat("&data_aggregation=true&aggregator="+aggregator_time_string).concat("&aggregation_period="+aggregator_period_string).concat("&aggregation_type="+aggregator_type_string);

    } else {

        multiple_download_url = "/api/v1/solar/plants/".concat(slugs_selected[0]).concat('/multiple_devices_streams/data/download/').concat("?startTime="+st).concat("&endTime="+et);

    }

    var form = $('<form></form>').attr('action', multiple_download_url).attr('method', 'post');
    form.append($("<input></input>").attr('type', 'hidden').attr('name', "csrfmiddlewaretoken").attr('value', getCookie('csrftoken')));
    form.append($("<input></input>").attr('type', 'hidden').attr('name', 'params').attr('value', JSON.stringify(download_parameters)));
    form.appendTo('body').submit().remove();

    /*$.ajax({
        type: "POST",
        dataType: "json",
        contentType: "application/json; charset=utf-8",
        url: multiple_download_url,
        headers : {
            Authorization : 'Bearer ' + csrftoken
        },
        data: JSON.stringify(download_parameters),
        success: function(multiple_data_array){
            
            console.log(multiple_data_array);

        },
        error: function(data){
            console.log("no data");
            
            $("#multiple_parameter_download_no_data").empty();
            $("#multiple_parameter_download_no_data").append("<div class='alert alert-warning' id='alert'><button type='button' class='close' data-dismiss='alert' aria-label='Close'><span aria-hidden='true'>&times;</span></button>No data to download for selected parameters.</div>");
        }
    });*/
    
    $("#client_spinner").hide();

}

function getCookie(name) {
    var cookieValue = null;
    if (document.cookie && document.cookie != '') {
        var cookies = document.cookie.split(';');
        for (var i = 0; i < cookies.length; i++) {
            var cookie = jQuery.trim(cookies[i]);
            // Does this cookie string begin with the name we want?
            if (cookie.substring(0, name.length + 1) == (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

$("#multiple_parameters-data_chart").on('click', function() {
    plot_multiple_parameters("chart");
})

$("#multiple_parameters-download").on('click', function() {
    plot_multiple_parameters("data_download");
})

$("#multiple-parameters-before-li").on('click', function() {
    if($("#multiple-parameters-before-li").hasClass("disabled") == false) {
        var st = $(".datepicker").val();

        if(st == "") {
            st = new Date();
        } else {
            st = st.split("-");
            st = st[2] + "-" + st[1] + "-" +st[0];
            st = new Date(st);    
        }
        st.setDate(st.getDate() - 1);
        st = dateFormat(st, "dd-mm-yyyy");

        $(".datepicker").val(st);
        plot_multiple_parameters("chart");
    }
})

$("#multiple-parameters-li").on('click', function() {
    if($("#multiple-parameters-li").hasClass("disabled") == false) {
        var st = $(".datepicker").val();

        if(st == "") {
            st = new Date();
        } else {
            st = st.split("-");
            st = st[2] + "-" + st[1] + "-" +st[0];
            st = new Date(st);
        }
        st.setDate(st.getDate() + 1);
        st = dateFormat(st, "dd-mm-yyyy");

        $(".datepicker").val(st);
        plot_multiple_parameters("chart");
    }
})

function plot_multiple_parameters(option) {

    $("#client_spinner").show();

    var multiple_parameters = {};
    var inverters_selected = [], inverter_parameters_selected = [];
    var ajbs_selected = [], ajb_parameters_selected = [];
    var plant_meta_selected = [], plant_meta_parameters_selected = [];
    var plant_solar_metrics_selected = [], plant_solar_metrics_parameters_selected = [];
    var energy_meters_selected = [], energy_meters_parameters_selected = [];
    var transformers_selected = [], transformers_parameters_selected = [];

    var streams_selected = false;

    $('#inverters_names_dropdown option:selected').each(function(i) {
        inverters_selected.push($(this).val());
    });

    console.log(inverters_selected);

    $('#inverters_streams_dropdown option:selected').each(function(i) {
        streams_selected = true;
        inverter_parameters_selected.push($(this).val());
    });

    console.log(inverter_parameters_selected);

    for(var i = 0; i < inverters_selected.length; i++) {
        multiple_parameters[inverters_selected[i].toString()] = inverter_parameters_selected;
    }

    $('#ajbs_names_dropdown option:selected').each(function(i) {
        ajbs_selected.push($(this).val());
    });

    $('#ajbs_streams_dropdown option:selected').each(function(i) {
        streams_selected = true;
        ajb_parameters_selected.push($(this).val());
    });

    for(var i = 0; i < ajbs_selected.length; i++) {
        multiple_parameters[ajbs_selected[i].toString()] = ajb_parameters_selected;
    }

    $('#plant_meta_source_names_dropdown option:selected').each(function(i) {
        plant_meta_selected.push($(this).val());
    });

    $('#plant_meta_source_stream_dropdown option:selected').each(function(i) {
        streams_selected = true;
        plant_meta_parameters_selected.push($(this).val());
    });

    for(var i = 0; i < plant_meta_selected.length; i++) {
        multiple_parameters[plant_meta_selected[i].toString()] = plant_meta_parameters_selected;
    }

    $('#plant_solar_metrics_names_dropdown option:selected').each(function(i) {
        plant_solar_metrics_selected.push($(this).val());
    });

    $('#plant_solar_metrics_stream_dropdown option:selected').each(function(i) {
        streams_selected = true;
        plant_solar_metrics_parameters_selected.push($(this).val());
    });

    for(var i = 0; i < plant_solar_metrics_selected.length; i++) {
        multiple_parameters[plant_solar_metrics_selected[i].toString()] = plant_solar_metrics_parameters_selected;
    }

    $('#energy_meters_names_dropdown option:selected').each(function(i) {
        energy_meters_selected.push($(this).val());
    });

    $('#energy_meters_streams_dropdown option:selected').each(function(i) {
        streams_selected = true;
        energy_meters_parameters_selected.push($(this).val());
    });

    for(var i = 0; i < energy_meters_selected.length; i++) {
        multiple_parameters[energy_meters_selected[i].toString()] = energy_meters_parameters_selected;
    }

    if (Object.keys(multiple_parameters).length == 0 ) {
        $("#client_spinner").hide();
        noty_message("Please select at least one device!", 'error', 5000)
        return;
    } else if (streams_selected == false) {
        $("#client_spinner").hide();
        noty_message("Please select at least one stream!", 'error', 5000)
        return;
    } else if ($(".datepicker").val() == '') {
        $("#client_spinner").hide();
        noty_message("Please select a date!", 'error', 5000)
        return;
    }

    if(option == "chart") {
        multiple_chart(multiple_parameters);
    } else {
        data_download(multiple_parameters);
    }

}

var aggregator_string = false, aggregator_time_string, aggregator_period_string, aggregator_type_string;

$(".aggregation_select-list>li>a").click(function(){
    $("#aggregator").html();
    $("#aggregator").html($(this).text());

    aggregator_string = $(this).text();

    if(aggregator_string == "Actual Data") {

        aggregator_string = false;
        $('#aggregator_time').empty();
        $('#aggregator_time').append("Average Unit");
        $("#aggregator_time_button").prop('disabled', true);
        $('#aggregator_period_dropdown').prop('selectedIndex', 0);
        $("#aggregator_period_dropdown").prop('disabled', true);
        $('#aggregator_type').empty();
        $('#aggregator_type').append("Mean");
        $("#aggregator_type_button").prop('disabled', true);
        $(".datepicker_end_time").empty();
        $(".datepicker_end_time").prop('disabled', true);

    } else if(aggregator_string == "Data Average") {

        aggregator_string = true;
        $("#aggregator_time_button").prop('disabled', false);
        $("#multiple-parameters-li").prop('disabled', true);
        $("#multiple-parameters-before-li").prop('disabled', true);

    }
});

$(".aggregator_time-list>li>a").click(function(){
    $("#aggregator_time").html();
    $("#aggregator_time").html($(this).text());

    $("#aggregator_period_div").empty();
    $("#aggregator_period_div").append('<div class="form-group">' +
                            '<select class="form-control aggregator_period_select" id="aggregator_period_dropdown">' +
                            '</select>' +
                        '</div>');

    aggregator_time_string = $(this).text();

    if(aggregator_time_string == "Minute") {

        var minute_array = [15, 30, 45, 60, 90, 120]

        aggregator_time_string = "MINUTE";
        $("#aggregator_period_dropdown").prop('disabled', false);
        $("#aggregator_type_button").prop('disabled', false);
        $(".datepicker_end_time").prop('disabled', true);
        $("#aggregator_period_dropdown").empty();

        $("#aggregator_period_dropdown").append("<option selected disabled>Average Interval</option>");

        for(var minute = 0; minute < minute_array.length; minute++) {
            $("#aggregator_period_dropdown").append("<option value='" + minute_array[minute] + "'>" + minute_array[minute] + "</option>");
        }
    } else if(aggregator_time_string == "Day") {

        var day_array = [1, 7];

        aggregator_time_string = "DAY";
        $("#aggregator_period_dropdown").prop('disabled', false);
        $("#aggregator_type_button").prop('disabled', false);
        $(".datepicker_end_time").prop('disabled', false);
        $("#aggregator_period_dropdown").empty();

        $("#aggregator_period_dropdown").append("<option selected disabled>Average Interval</option>");

        for(var day = 0; day < day_array.length; day++) {
            $("#aggregator_period_dropdown").append("<option value='" + day_array[day] + "'>" + day_array[day] + "</option>");
        }
    } else if(aggregator_time_string == "Month") {

        aggregator_time_string = "MONTH";
        $("#aggregator_period_dropdown").prop('disabled', false);
        $("#aggregator_type_button").prop('disabled', false);
        $(".datepicker_end_time").prop('disabled', false);
        $("#aggregator_period_dropdown").empty();

        $("#aggregator_period_dropdown").append("<option selected disabled>Average Interval</option>");

        var month = 1;
        $("#aggregator_period_dropdown").append("<option value='" + month + "'>" + month + "</option>");
    }

});

$(".aggregator_type-list>li>a").click(function(){
    $("#aggregator_type").html();
    $("#aggregator_type").html($(this).text());

    aggregator_type_string = $(this).text();

    if(aggregator_type_string == "Minimum") {
        aggregator_type_string = "min";
    } else if(aggregator_type_string == "Maximum") {
        aggregator_type_string = "max";
    } else if(aggregator_type_string == "Mean") {
        aggregator_type_string = "mean";
    }
});