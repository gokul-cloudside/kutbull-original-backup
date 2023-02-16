$(document).ready(function() {

    $("#breadcrumb_page_path").empty();
    $("#breadcrumb_page_path").append('<li class="text-center text-bold" ><a href="#">Client</a></li><li class="text-center text-bold"><a href="#">Client Dashboard</a></li><li class="text-center text-bold"><a href="#">Plant Dashboard</a></li><li class="text-center text-bold"><a href="#">Inverter Power</a></li>');

    plant_dropdown();
    group_dropdown();
});

$(function() {
$(".datetimepicker_inverters_power_start_time").datetimepicker({
    timepicker: false,
    format: 'd/m/Y',
    scrollMonth:false,
    scrollTime:false,
    scrollInput:false
});
});
$(function() {
    $(".datetimepicker_groups_power_start_time").datetimepicker({
        timepicker: false,
        format: 'd/m/Y',
        scrollMonth:false,
        scrollTime:false,
        scrollInput:false
    });
});
function limit_plant_future_date() {
$(function(){
    $('#inverters_power_start_time').datetimepicker({
        onShow:function( ct ){
            this.setOptions({
                maxDate: new Date()
            })
        }
    });
});
}

function select_all_inverters() {
    $('#inverters_dropdown_compare option').prop('selected', true);

    var fields_inverters_compare = [];  

    $('#inverters_dropdown_compare > option:selected').each(function() {
        fields_inverters_compare.push($(this).val());
    });
    fields_inverters_compare.shift();
}

jQuery('#inverter_powertab a').click(function (e) {
    e.preventDefault()
    jQuery(this).tab('show')
    jQuery(window).trigger('resize'); // Added this line to force NVD3 to redraw the chart
})

jQuery('#group_powertab a').click(function (e) {
    e.preventDefault()
    jQuery(this).tab('show')
    jQuery(window).trigger('resize'); // Added this line to force NVD3 to redraw the chart
})

function redraw_window() {
$('a[data-toggle="tab"]').on('shown.bs.tab', function (e) {
    e.preventDefault();
    window.dispatchEvent(new Event('resize'));
});
}

function get_dates(id){
  // get the startTime date
  var st = $('#'+id).val();
  if (st == '') {
    st = new Date();
  }
  else {
    var date = [];
    date = st.split('/');
    st = date[2] + "/" + date[1] + "/" + date[0];
    st = new Date(st);
  }
  // prepare an end date
  var e = new Date(st.getTime());
  e = new Date(e.setDate(st.getDate() + 1));
  // convert them into strings
  st = dateFormat(st, "yyyy/mm/dd");
  e = dateFormat(e, "yyyy/mm/dd");

  return [st, e]
}

var inverters_data = [];

function plant_dropdown() {
    $('#inverters_dropdown_compare').empty();
    /*$('#inverters_dropdown_compare').append("<option value='' disabled selected>--Pick an Inverter--</option>");*/
    $.ajax({
        type: "GET",
        url: "/api/solar/plants/".concat(plant_slug).concat('/inverters/'),
        success: function(inverters) {
            inverters_data = inverters;
            join_inverter_names(inverters);
        },
        error: function(data) {
            console.log("error_streams_data");
            data = null;
        }
    });
}

function plant_inverters() {

    var inverter_id = "inverters_power_start_time"

    var dates = get_dates(inverter_id);
    var st = dates[0];
    var et = dates[1];
    var stream_name = "ACTIVE_POWER";

    $('#inverters_dropdown').empty();
    $('#inverters_dropdown').append("<option value='' disabled selected>--Pick an Inverter--</option>");
    var power_fields_inverters = [];
    var power_fields_sourcekeys = [];
    $('#inverters_dropdown_compare > option:selected').each(function() {
        power_fields_sourcekeys.push($(this).val());
        power_fields_inverters.push($(this).text());
    });
    /*plant_inverters_processing(inverters_data, power_fields_inverters);*/
    var power_inverter_data = inverters_csv_parse_data(st, et, power_fields_sourcekeys, stream_name);
    console.log(power_inverter_data);
    power_parse(power_inverter_data, power_fields_sourcekeys, power_fields_inverters);
}

function power_parse(power_inverter_data, power_fields_sourcekeys, power_fields_inverters) {

    var arrayData = [];
    var arrayValue = [];
    var multilineInvertersArray = [];
    var stackedAreaArray = [];

    for (var i = 0; i < power_fields_inverters.length; i++) {
        arrayData = [];
        arrayValue = [];
        for (var j = 1; j < power_inverter_data.data.length - 1; j++) {
            var d = new Date(power_inverter_data.data[j][0]);
            var date = d.getTime();
            var date_form_api = new Date(date - (330 * 60000));
            if (power_inverter_data.data[j][i+1] != '') {
                var val_dt = parseFloat(power_inverter_data.data[j][i+1]);
            } else {
                var val_dt = null;
            }
            arrayData.push({x: date_form_api, y: val_dt});
            arrayValue.push([date_form_api, val_dt]);
        }
        multilineInvertersArray.push({
            "key": power_fields_inverters[i],
            "values": arrayData
        });
        stackedAreaArray.push({
            "key": power_fields_inverters[i],
            "values": arrayValue
        });
        $('#inverters_dropdown').append("<option value=" + power_fields_inverters[i] + ">" + power_fields_inverters[i] + "</option>");
    }
    
    inverter_multiple_line_chart(multilineInvertersArray);
    inverter_generation_chart(stackedAreaArray);
    $('#inverters_dropdown').change(function() {
        $('#inverters_dropdown option:selected').each(function() {
            single_inverter_chart(power_inverter_data, power_fields_sourcekeys, power_fields_inverters, multilineInvertersArray, stackedAreaArray)
        });
    });
}

function single_inverter_chart(power_inverter_data, power_fields_sourcekeys, power_fields_inverters, multilineInvertersArray, stackedAreaArray) {
    
    var line_chart_single_inverter = [];

    var inverter_name = $("#inverters_dropdown").val();
    for(var i = 0; i < multilineInvertersArray.length; i++) {
        if(inverter_name == multilineInvertersArray[i].key) {
            line_chart_single_inverter.push(multilineInvertersArray[i]);
            line_chart_packaged_data = [];
            line_chart_packaged_data = line_chart_single_inverter; 
            break;
        }
    }
    inverter_multiple_line_chart(line_chart_packaged_data);
}

function hasWhiteSpace(inverter_name) {
    return inverter_name.indexOf(' ') > 0;
}

function join_inverter_names(inverters) {

    var inverters_dropdown_compare_names = [];
    var compare_inverter_dropdown_num = 0;

    for(var i = 0; i < inverters.length; i++) {

        var inverter_name = inverters[i].name;
        var check_inverters_names_spaces = hasWhiteSpace(inverter_name);

        if(check_inverters_names_spaces == true) {
            var joined_name = inverters[i].name.split(' ').join('_');
            inverters_dropdown_compare_names.push(joined_name);
        } else {
            inverters_dropdown_compare_names.push(inverters[i].name);
        }

        $('#inverters_dropdown_compare').append("<option value='" + inverters[i].sourceKey + "' sourceKey='" + inverters[i].sourceKey + "'>" + inverters[i].name + "</option>");
        compare_inverter_dropdown_num++;
    }   
}

/*function plant_inverters_processing(inverters, power_fields_inverters) {

    var dates = get_dates();
    var st = dates[0];
    var e = dates[1];
    var all_inverters_data = [];
    var inverters_without_data = 0;

    var data_dicts = [];

    var data_ti = [];

    var inverters_dropdown_names = [];

    var inverter_dropdown_num = 0;

    var stream = "ACTIVE_POWER";

    for(var i = 0; i < inverters.length; i++) {
        for(var j = 0; j < power_fields_inverters.length; j++) {
            if(inverters[i].name == power_fields_inverters[j]) {
                $.ajax({
                    type: "GET",
                    async: false,
                    url: "/api/solar/plants/".concat(plant_slug).concat('/inverters/').concat(inverters[i].sourceKey).concat('/data/'),
                    data: {streamNames: stream, startTime: (st), endTime: (e)},
                    beforeSend: function() {
                        var $el = $("#download-inverters-data");
                        $el.niftyOverlay('show');
                    },
                    complete: function(){
                        var $el = $("#download-inverters-data");
                        $el.niftyOverlay('hide');
                    },
                    success: function(data) {
                        if (data.streams[0].values.length != 0){
                            var packedData = {"name": inverters[i].name, "data": {}};
                            var packedTs = [];

                            inverters_dropdown_names.push(packedData.name);
                            all_inverters_data.push(data);

                            for(var z = 0; z < data.streams[0].timestamps.length; z++) {
                                packedData.data[data.streams[0].timestamps[z]] =  data.streams[0].values[z];
                                packedTs.push(data.streams[0].timestamps[z]);
                            }*/

                            /*data.streams[0].timestamps.forEach(function(datapoint) {
                                packedData.data[datapoint.timestamps] = datapoint.values;
                                packedTs.push(datapoint.timestamps);
                            });*/

                            /*data_dicts.push(packedData);
                            data_ti.push(packedTs);
                            $('#inverters_dropdown').append("<option value=" + power_fields_inverters[j] + ">" + power_fields_inverters[j] + "</option>");
                        } else {
                            console.log("no data");
                        }
                    },
                    error: function(data) {
                        console.log("error_getting_inverter_data");
                    }
                });  
            }
        }
    }*/

    /*for(i = 0; i < inverters.length; i++) {
        $.ajax({
            type: "GET",
            async: false,
            url: "/api/solar/plants/".concat('{{ plant_slug }}').concat('/inverters/').concat(inverters[i].sourceKey).concat('/energy/'),
            data: {startTime: (st), endTime: (e), aggregator: "FIVE_MINUTES"},
            success: function(data) {
                if (data.length != 0){
                    var packedData = {"name": inverters[i].name, "data": {}};
                    var packedTs = [];

                    var inverter_name = packedData.name;
                    var check_inverters_names_spaces = hasWhiteSpace(inverter_name);

                    if(check_inverters_names_spaces == true) {
                        var joined_name = packedData.name.split(' ').join('_');
                        inverters_dropdown_names.push(joined_name);
                    } else {
                         inverters_dropdown_names.push(packedData.name);
                    }
                    all_inverters_data.push(data);
                    
                    data.forEach(function(datapoint) {
                        packedData.data[datapoint.timestamp] = datapoint.energy;
                        packedTs.push(datapoint.timestamp);
                    });

                    data_dicts.push(packedData);
                    data_ti.push(packedTs);
                    $('#inverters_dropdown').append("<option value=" + inverters_dropdown_names[inverter_dropdown_num] + ">" + inverters[i].name + "</option>");
                    inverter_dropdown_num++;
                } else {
                    console.log("no data");
                }
            },
            error: function(data) {
                console.log("error_getting_inverter_data");
            }
        });
    }*/

    //if(all_inverters_data.length == inverters.length) {
      /*if (1) {
        // if all inverters have no data, show an error message
        for(var i = 0; i < all_inverters_data.length; i++) {
            if(all_inverters_data[i].streams[0].values == '') {
                inverters_without_data++;
            }
        }

        if(inverters_without_data == all_inverters_data.length) {
            $("#multiple_line_chart").empty();
            $("#multiple_line_chart").append("<div class='alert alert-warning' id='alert-inverter'></div>");
            $("#alert-inverter").empty();
            $("#alert-inverter").append("No data for the date.");

            $("#stacked_chart").empty();
            $("#stacked_chart").append("<div class='alert alert-warning' id='alert-stack'></div>");
            $("#alert-stack").empty();
            $("#alert-stack").append("No data for the date.");
            return;

        } else {
            $("#multiple_line_chart").empty();
            $("#multiple_line_chart").append("<svg style='height: 220px;'>");

            $("#stacked_chart").empty();
            $("#stacked_chart").append("<svg style='float: left;'></svg>");
        }

        inverter_package_data(inverters_dropdown_names, data_ti, all_inverters_data, data_dicts);
        $('#inverters_dropdown').change(function() {
            $('#inverters_dropdown option:selected').each(function() {
                inverter_package_data(inverters_dropdown_names, data_ti, all_inverters_data, data_dicts)
            });
        });
    } // add an else part else
}*/

function inverter_package_data(inverters_dropdown_names, data_ti, data, data_dicts){
    var filtered_timestamps = [];
    filtered_timestamps = data_ti[0];
    j = 1;
    filtered_timestamps = _.union.apply(_, data_ti);
    filtered_timestamps = _.sortBy(filtered_timestamps, function(timestamp){return new Date(timestamp)});
    var all_inverters_union_data = []; 
    var line_chart_packaged_data = [];
    var line_chart_single_inverter = [];   
    for (var inverter_num = 0;
         inverter_num < data_dicts.length;
         inverter_num++){
        var single_inverter_datapoints = [];
        var line_chart_data = [];
        filtered_timestamps.forEach(function(ts){
            var x_point = new Date(ts);
            if (typeof(data_dicts[inverter_num].data[ts]) == 'undefined') {
                single_inverter_datapoints.push([x_point, 0.0]);
                line_chart_data.push({x: x_point, y: 0.0});
            } else {
                var value = parseFloat(data_dicts[inverter_num].data[ts]);
                single_inverter_datapoints.push([x_point, value]);
                line_chart_data.push({x: x_point, y: value});
            }
        });
        
        all_inverters_union_data.push({
            "key": data_dicts[inverter_num].name,
            "values": single_inverter_datapoints});

        line_chart_packaged_data.push({
            "key": data_dicts[inverter_num].name,
            "values": line_chart_data});

    }

    var inverter_name = $("#inverters_dropdown").val();
    for(var i = 0; i < inverters_dropdown_names.length; i++) {
        if(inverter_name == inverters_dropdown_names[i]) {
            line_chart_single_inverter.push(line_chart_packaged_data[i]);
            line_chart_packaged_data = [];
            line_chart_packaged_data = line_chart_single_inverter; 
            break;
        }
    }

    inverter_multiple_line_chart(line_chart_packaged_data);
    inverter_generation_chart(all_inverters_union_data);
}

function inverter_generation_chart(packagedData) {
    $("#stacked_chart").empty();
    $("#stacked_chart").append("<svg style='float: left;'></svg>")

    nv.addGraph(function () {
        stacked_chart = nv.models.stackedAreaChart()
                      .margin({right: 0})
                      .x(function(d) { return d[0] })   //We can modify the data accessor functions...
                      .y(function(d) { return d[1] })   //...in case your data is formatted differently.
                      .useInteractiveGuideline(true)  //We want nice looking tooltips and a guideline!
                      .showLegend(false)       //Show the legend, allowing users to turn on/off line series.
                      .showControls(false)
                      .margin({top: 5, right: 31, bottom: 20, left: 65});

        stacked_chart.xAxis
                .axisLabel("Time")
                .tickFormat(function (d) {
                return d3.time.format('%I:%M %p')(new Date(d))
            });

        stacked_chart.interactiveLayer.tooltip
                    .headerFormatter(function(d, i) {
            return nv.models.axis().tickFormat()(d, i);
        });

        stacked_chart.yAxis
                .axisLabel("Power (kW)")
                .tickFormat(d3.format(",.2f"));

        d3.select('#stacked_chart svg')
                  .datum(packagedData)
                  .call(stacked_chart);

        nv.utils.windowResize(stacked_chart.update);
    });
}
function inverter_multiple_line_chart(packagedData) {
    $("#multiple_line_chart").empty();
    $("#multiple_line_chart").append("<svg style='float: left;'></svg>")

    nv.addGraph(function() {
        color = ["#1F77B4","#AEC7E8","#FF0018","#FF00B1","#00ADFF","#00FF4E","#91FF00","#FFF700","#ff7f0e"];
        line_chart = nv.models.lineChart()
                .margin({top: 5, right: 31, bottom: 20, left: 65})
                .useInteractiveGuideline(true)  //We want nice looking tooltips and a guideline!
                .showLegend(false)       //Show the legend, allowing users to turn on/off line series.
                .showYAxis(true)        //Show the y-axis
                .showXAxis(true)        //Show the x-axis
                ;

        line_chart.xAxis
            .axisLabel('')
            .tickFormat(function (d) {
                return d3.time.format('%I:%M %p')(new Date(d))
            });

        line_chart.yAxis
          .axisLabel('Power (kW)')
          .tickFormat(d3.format('.02f'));

        d3.select('#multiple_line_chart svg')
                .datum(packagedData)
                .call(line_chart);

        nv.utils.windowResize(function() { line_chart.update() });
    });
}

    function inverter_data() {

        $.ajax({
            type: "GET",
            url: "/solar/plant/".concat(plant_slug).concat('/power/'),
            data: {startTime: st, endTime: e},
            success: function(data) {
                
            },
            error: function(data) {
                console.log("error_streams_data");
                data = null;
            },
        });

    }

function group_dropdown() {

    $.ajax({
        type: "GET",
        url: "/api/solar/plants/".concat(plant_slug).concat('/status/'),
        success: function(data) {

            status = data;
            $("#groups_dropdown_compare").empty();

            if(data.solar_groups.length > 0) {
                for(var i = 0; i < data.solar_groups.length; i++) {
                    $("#groups_dropdown_compare").append("<option value=" + data.solar_groups[i] + ">" + data.solar_groups[i] + "</option>")
                }    
            } else {
                $("#group_powertab").hide();
            }

        },
        error: function(data) {
            console.log("error_streams_data");
            data = null;
        }
    });

}

function groups_chart() {

    var groups = [];

    $('#groups_dropdown_compare > option:selected').each(function() {
        groups.push($(this).val());
    });

    var group_id = "groups_power_start_time";

    var dates = get_dates(group_id);
    var st = dates[0];
    var et = dates[1];

    var group_name = groups;
    group_name = group_name.toString();

    var groupInvertersMultipleArray = [];

    $.ajax({
        type: "GET",
        async: false,
        url: "/api/solar/plants/".concat(plant_slug).concat('/groups-power/'),
        data: {startTime: (st), endTime: (et), groupNames: group_name},
        success: function(group_power){
            if(group_power == "") {
                $("#group_multiple_line_chart").empty();
                $("#group_multiple_line_chart").append("<svg style='float: left;'></svg>")

                $("#group_power_no_data").empty();
                $("#group_power_no_data").append("<div class='alert alert-warning' id='alert'>No data for groups.</div>");

            } else {
                $("#group_multiple_line_chart").empty();
                $("#group_multiple_line_chart").append("<svg style='float: left;'></svg>")

                for (var i = 0; i < groups.length; i++) {
                    arrayData = [];
                    for (var j = 0; j < group_power.length; j++) {
                        var d = new Date(group_power[j].timestamp);
                        var date = d.getTime();
                        var date_form_api = new Date(date);

                        var val_dt = 0;

                        if(group_power[j].hasOwnProperty(groups[i])) {
                            if(group_power[j][groups[i]] != null) {
                                val_dt = parseFloat(group_power[j][groups[i]]);   
                            } else {
                                val_dt = null;
                            }
                        } else {
                            val_dt = null;
                        }
                        arrayData.push({x: date_form_api, y: val_dt});
                    }
                    groupInvertersMultipleArray.push({
                        "key": groups[i],
                        "values": arrayData
                    });
                }

                group_power_multiple_line_chart(groupInvertersMultipleArray);

            }
        },
        error: function(data){
            console.log("no data");

            $("#group_multiple_line_chart").empty();
            $("#group_multiple_line_chart").append("<svg style='float: left;'></svg>")

            $("#group_power_no_data").empty();
            $("#group_power_no_data").append("<div class='alert alert-warning' id='alert'>No data for groups.</div>");
        }
    });

}

function group_power_multiple_line_chart(packagedData) {
    $("#group_multiple_line_chart").empty();
    $("#group_multiple_line_chart").append("<svg style='float: left;'></svg>")

    nv.addGraph(function() {
        line_chart = nv.models.lineChart()
                .margin({top: 5, right: 31, bottom: 20, left: 65})
                .useInteractiveGuideline(true)  //We want nice looking tooltips and a guideline!
                .showLegend(false)       //Show the legend, allowing users to turn on/off line series.
                .showYAxis(true)        //Show the y-axis
                .showXAxis(true)        //Show the x-axis
                ;

        line_chart.xAxis
            .axisLabel('')
            .tickFormat(function (d) {
                return d3.time.format('%I:%M %p')(new Date(d))
            });

        line_chart.yAxis
          .axisLabel('Power (kW)')
          .tickFormat(d3.format('.02f'));

        d3.select('#group_multiple_line_chart svg')
                .datum(packagedData)
                .call(line_chart);

        nv.utils.windowResize(function() { line_chart.update() });
    });
}