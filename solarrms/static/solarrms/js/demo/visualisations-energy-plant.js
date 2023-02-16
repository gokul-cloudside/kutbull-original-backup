$(document).ready(function() {

    $("#breadcrumb_page_path").empty();
    $("#breadcrumb_page_path").append('<li class="text-center text-bold" ><a href="#">Client</a></li><li class="text-center text-bold"><a href="#">Client Dashboard</a></li><li class="text-center text-bold"><a href="#">Plant Dashboard</a></li><li class="text-center text-bold"><a href="#">Energy</a></li>')

    /*limit_plant_future_energy_day_date();
    day_energy_data();
    start_year();

    if(plant_slug == "uran" || plant_slug == "rrkabel" || plant_slug == "unipatch") {
        $("#title").empty();
        $("#title").append("Inverters Energy Generation");
    } else {
        $("#title").append("Energy Generation");
    }*/
});

$('.datepicker_start_days').datepicker({
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

function datepicker_start_day_range() {

    var end_date = new Date();
    end_date.setDate(end_date.getDate());

    var next_date = new Date();
    next_date.setDate(next_date.getDate()+1);

    $('.datepicker_start_days_range').datepicker({
        endDate: end_date,
        autoclose: true,
        todayHighlight: true,
        startView: "days",
        minViewMode: "days",
        format: "dd-mm-yyyy"
    });

    $('.datepicker_end_days_range').datepicker({
        endDate: next_date,
        autoclose: true,
        todayHighlight: true,
        startView: "days",
        minViewMode: "days",
        format: "dd-mm-yyyy"
    });
}

var plant_parameter = "", aggregator_string = "";

$(".dropdown_energy_aggregator-selected li a").click(function(){
    $("#dropdown_energy_aggregator").html();
    $("#dropdown_energy_aggregator").html($(this).text());

    aggregator_string = $(this).text();

    if(aggregator_string == "WEEK") {

        $("#datepicker_selected_datetime").empty();
        $("#datepicker_selected_datetime").append('<input type="text" class="form-control datepicker_start_days" id="datepicker_selected_picker" placeholder="Pick a Date" style="height: 31px;">');
        datepicker_start_day();

    } else if(aggregator_string == "MONTH") {

        $("#datepicker_selected_datetime").empty();
        $("#datepicker_selected_datetime").append('<input type="text" class="form-control datepicker_start_months" id="datepicker_selected_picker" placeholder="Pick a Month" style="height: 31px;">');
        datepicker_start_month();

    } else if(aggregator_string == "YEAR") {

        $("#datepicker_selected_datetime").empty();
        $("#datepicker_selected_datetime").append('<input type="text" class="form-control datepicker_start_years" id="datepicker_selected_picker" placeholder="Pick a Year" style="height: 31px;">');
        datepicker_start_year();

    } else if(aggregator_string == "DATE RANGE") {

        $("#datepicker_selected_datetime").empty();
        $("#datepicker_selected_datetime").append('<div class="col-lg-6 col-md-6 col-sm-6"><input type="text" class="form-control datepicker_start_days_range" id="datepicker_selected_picker_start_range" placeholder="Pick a Start Date" style="height: 31px;"></div><div class="col-lg-6 col-md-6 col-sm-6"><input type="text" class="form-control datepicker_end_days_range" id="datepicker_selected_picker_end_range" placeholder="Pick an End Date" style="height: 31px;"></div>');
        datepicker_start_day_range();

    }

    if(aggregator_string == "DATE RANGE") {
        $("#date_div").removeClass("col-lg-4 col-md-4 col-sm-4");
        $("#date_div").addClass("col-lg-6 col-md-6 col-sm-6");
    } else {
        $("#date_div").removeClass("col-lg-6 col-md-6 col-sm-6");
        $("#date_div").addClass("col-lg-4 col-md-4 col-sm-4");
    }

    $("#user_alert").empty();
    $("#alert_div").hide();

    $("#date_div").show();
    $("#update_button_div").show();

});

$("#energy_value-update").on('click', function() {

    $("#client_spinner").show();

    console.log("update");

    aggregator_string = $("#dropdown_energy_aggregator").text();
    if(aggregator_string == "Select a Time Period") {

        $("#client_spinner").hide();

        noty_message("Please select a time period!", 'error', 5000)
        return;
    }

    if(aggregator_string != "DATE RANGE") {
        var st = $("#datepicker_selected_picker").val();
        console.log(st);
        if(st == "") {
            $("#client_spinner").hide();

            noty_message("Please select a Date!", 'error', 5000)
            return;
        }
    }

    if(aggregator_string == "WEEK") {
        energy_chart(st, "WEEK");
    } else if(aggregator_string == "MONTH") {
        energy_chart(st, "MONTH");
    } else if(aggregator_string == "YEAR") {
        energy_chart(st, "YEAR");
    } else if(aggregator_string == "DATE RANGE") {

        var st = $("#datepicker_selected_picker_start_range").val();
        console.log(st);
        if(st == "") {
            $("#client_spinner").hide();

            noty_message("Please select a Start Date!", 'error', 5000)
            return;
        }

        var et = $("#datepicker_selected_picker_end_range").val();
        console.log(et);
        if(et == "") {
            $("#client_spinner").hide();

            noty_message("Please select an End Date!", 'error', 5000)
            return;
        }

        energy_chart_range(st, et, "WEEK");
    }

    console.log(aggregator_string);
    console.log(st);
    
})

function get_dates(st) {

    var et = new Date();

    st = st.split("-");

    if(aggregator_string == "WEEK") {
        st = st[2] + "-" + st[1] + "-" + st[0];
        st = new Date(st);
        et = new Date(st);
        st.setDate(st.getDate() - 7);

    } else if(aggregator_string == "MONTH") {
        st = st[1] + "-" + st[0];
        st = new Date(st);
        st = new Date(st.getFullYear(), st.getMonth(), 1);
        et = new Date(st.getFullYear(), st.getMonth() + 1, 0);

    } else if(aggregator_string == "YEAR") {
        st = new Date(st);
        st = new Date(st.getFullYear() + "-" + "01" + "-" + "01");
        et = new Date(st.getFullYear() + "-" + "12" + "-" + "31");

    }

    st = dateFormat(st, "yyyy-mm-dd");
    et = dateFormat(et, "yyyy-mm-dd");

    return [st, et];

}

/*Energy Data for a month*/

function month_energy_data(st) {

    $("#energy_chart").empty();
    $("#energy_chart").append("<svg style='height: 40vh;'></svg>");

    var dates = get_dates(st);

    var st = dates[0];
    var e = dates[1];
    
    $.ajax({
        type: "GET",
        url: "/api/solar/plants/".concat(plant_slug).concat('/energy/'),
        data: {startTime: (st), endTime: (e), aggregator: "DAY", offline: 1},
        success: function(data) {

            if(data == '') {
                noty_message("No data for the week!", 'error', 5000)
                return;
            } else {
                var y_date = new Date();
                var day_energy = 0;
                var month_pvsyst_expected = 0;
                var cumulative_energy = 0;
                var arrayData = [];
                var month_counter = 0;

                var data_index = 0;

                var day_energy_unit;

                // populate the data array and calculate the day_energy
                for(var n= 0; n < data.length ; n++) {
                    day_energy_unit = data[n].energy;
                    day_energy = parseFloat(data[n].energy);
                    day_energy_unit = day_energy_unit.split(" ");
                    if(data[n].pvsyst_generation) {
                        
                        data_index = n;
                        month_counter++;

                    }
                    cumulative_energy = cumulative_energy + parseFloat(data[n].energy);
                    y_date = new Date(data[n].timestamp);
                    y_date = dateFormat(y_date, "yyyy-mm-dd");
                    arrayData.push({"label": y_date, "value": parseFloat(day_energy.toFixed(0)), "color": "#0b62a4"});
                }

                if(month_counter > 0) {

                    month_pvsyst_expected = parseFloat(data[data_index].pvsyst_generation).toFixed(0);

                    $("#month_energy_expected").empty();
                    $("#month_energy_expected").append("<div class='col-lg-2'></div><div class='col-lg-8'><h3 class='month_pvsyst text-center'>PVsyst Generation for <span id='month_energy_pvsyst'></span> : <span id='month_pvsyst_data'></span></h3></div>");

                    $("#month_pvsyst_data").append(month_pvsyst_expected + " " + day_energy_unit[1]);
                }

                cumulative_energy = (cumulative_energy).toFixed(0);

                $(".cumulative_month_energy").append(cumulative_energy+" " + day_energy_unit[1]);

                // package the data
                var packagedData = [{
                    "key": "Energy GENERATION OF THIS MONTH FROM" + dateFormat(st, "yyyy-mm-dd") + "to" + dateFormat(e, "yyyy-mm-dd") + day_energy + "kWh",
                    "values": arrayData
                }];
                // plot the chart
                monthly_bar_chart(packagedData, day_energy_unit[1]);   
            }
        },
        error: function(data) {
            console.log("error_streams_data");
            data = null;
        }
    });
}
function monthly_bar_chart(packagedData, day_energy_unit){

    $("#badge-row-day-energy-month").empty();

    var month_name = null;

    nv.addGraph(function() {
      var chart = nv.models.discreteBarChart()
            .x(function(d) {
                var month_date = new Date(d.label);
                var locale = "en-us";
                month_name = month_date.toLocaleString(locale, { month: "long" });
                return d.label })    //Specify the data accessors.
            .y(function(d) { return d.value })
            .showValues(true)
            .color(['#B4D3E5'])
            /*#ff7f0e*/
            .margin({top: 5, right: 0, bottom: 70, left: 60})
            /*.tooltip.contentGenerator(function(key, y, e, graph) {
                if(key.data.value !=  '0') {
                    return '<p>' + key.data.label + " : " + key.data.value.toFixed(2) + ' MWh' + '</p>' ;
                }
            })*/
          ;

           /*chart.tooltip.contentGenerator(function(key, y, e, graph) {
                if(key.data.value !=  '0') {
                    return '<p>' + key.data.label + " : " + key.data.value.toFixed(2) + ' MWh' + '</p>' ;
                }
            });*/

        chart.tooltip.enabled(false);

        chart.xAxis
            .tickFormat(function (d) {
                return d3.time.format('%d')(new Date(d))
            });

        chart.yAxis
              .axisLabel("Energy (" + day_energy_unit + ")")
              .tickFormat(d3.format(",.2f"));

      d3.select('#energy_chart svg')
          .datum(packagedData)
          .call(chart);

      nv.utils.windowResize(chart.update);

      $("#month_energy").append(month_name);
      $("#month_energy_pvsyst").append(month_name);
      $(".nvd3-svg").css("float", "left");

      return chart;
    });/*,function(){
        d3.selectAll(".nv-bar").on('click',
            function(d){
                d3.select(this);

                var plot_id = "month_energy_chart";

                var tab_id = "month";

                var st = d.label;
                st = new Date(st);
                var et = new Date(st.getTime());
                et = new Date(et.setDate(st.getDate() + 1));
                // convert them into strings

                st = dateFormat(st, "yyyy-mm-dd");
                et = dateFormat(et, "yyyy-mm-dd");

                day_power_from_bar(st, et, tab_id, plot_id);
        });
    });*/
}

function day_power_from_bar(st, et, tab_id, plot_id) {

    $("#"+tab_id+"tab").empty();
    $("#"+tab_id+"tab").append("Day");

    $(".col-md-6_"+tab_id).append("<div class='row'></div><div class='row pull-right' id='legend-badge-row-"+tab_id+"'></div>");

    $.ajax({
        type: "GET",
        url: "/api/solar/plants/".concat(plant_slug).concat('/power/'),
        data: {startTime: (st), endTime: (et)},
        success: function(data) {
            if(data == '') {
                $("#"+plot_id).empty();
                $("#month_energy_no_data").empty();
                $("#month_energy_no_data").append("<div class='alert alert-warning'>No data for the month</div>");
                return;
            } else {
                $("#month_energy_no_data").empty();
                $("#"+plot_id).empty();
                $("#"+plot_id).append("<div class='col-lg-2'></div><div class='col-lg-12'><h3 class='days_energy text-center'>Energy Generation for " + dateFormat(st, 'dd-mm-yyyy') +" : </h3></div>");
                $("#"+plot_id).append("<svg></svg>");
            }

            var arrayData = [];

            $.ajax({
                type: "GET",
                url: "/api/solar/plants/".concat(plant_slug).concat('/energy/'),
                data: {startTime: st, endTime: et, aggregator: "DAY", offline: 1},
                success: function(data) {
                    var day_energy = data[0].energy;
                    day_energy = day_energy/1000;
                    day_energy = day_energy.toFixed(0);
                    $(".days_energy").append(day_energy+" MWh");

                    if(data[0].pvsyst_generation) {

                        var pvsyst_expected_day = (parseFloat(data[0].pvsyst_generation).toFixed(0))/1000;
                        $("#" + tab_id + "_energy_expected").empty();
                        $("#" + tab_id + "_energy_expected").append("<div class='col-lg-2'></div><div class='col-lg-8'><h3 class='"+tab_id+"_pvsyst text-center'>PVsyst Generation for " + dateFormat(st, 'dd-mm-yyyy') + " : " + pvsyst_expected_day + " MWh</h3></div>")
                    }
                },
                error: function(data) {
                    console.log("error_streams_data");
                    data = null;
                },
            });

            // populate the data array and calculate the day_energy
            for(var n= data.length-1; n >=0 ; n--) {
                var local_values = [];
                var ts = new Date(data[n].timestamp);

                local_values.push([ts, 0.0]);
                local_values.push([new Date(ts.setSeconds(ts.getSeconds() + 1)), parseFloat(data[n].power)]);
                arrayData.push({"values": local_values,
                                "key": dateFormat(data[n].timestamp, 'yyyy-mm-dd HH:MM:ss').concat(" : ").concat(parseFloat(data[n].power).toString()),
                                "color":"#4C85AB"});
            }

            // plot the chart
            day_line_energy_chart_from_bar_chart(arrayData, plot_id);
        },
        error: function(data) {
            console.log("error_streams_data");
            data = null;
        }
    });
}

function day_line_energy_chart_from_bar_chart(data, plot_id) {

    nv.addGraph(function () {
        live_chart = nv.models.lineChart()
            .x(function (d) { return d[0] })
            .y(function (d) { return d[1] })
            .showYAxis(true)
            .showLegend(false)
            .showXAxis(true)
            .margin({top: 5, right: 44, bottom: 20, left: 65})
            .useInteractiveGuideline(false)
            .clipEdge(true)
            
        live_chart.tooltip.contentGenerator(function(key, y, e, graph) {
            if(key.point[1] !=  '0') {
                return '<p>' + key.point[0].format("dd/mm/yyyy HH:MM") + " : " + key.point[1].toFixed(0) + ' kW' + '</p>' ;
            }
        })

        live_chart.interactiveLayer.tooltip
              .headerFormatter(function(d, i) {
                return nv.models.axis().tickFormat()(d, i);
        });
        live_chart.xAxis
              .axisLabel("")
              .tickFormat(function (d) {
                return d3.time.format('%I:%M %p')(new Date(d))
            });
        live_chart.yAxis
              .axisLabel("Power (kW)")
              .tickFormat(d3.format(",.2f"));
        
        live_chart.interactiveLayer.tooltip.headerFormatter(function (d) {
            return d3.time.format('%x %-I %p')(new Date(d));
        });
        d3.select('#'+ plot_id +' svg')
                  .datum(data)
                  .call(live_chart);
        nv.utils.windowResize(live_chart.update);

        $(".nvd3-svg").css("float", "left");

        return live_chart;
    });
}

function day_energy_data() {

    $("#weektab").empty();
    $("#weektab").append("Week");

    $("#yeartab").empty();
    $("#yeartab").append("Year");

    $("#monthtab").empty();
    $("#monthtab").append("Month");

    $("#daytab").empty();
    $("#daytab").append("Day");
    var id = '#start_energy_day'

    var dates = get_dates(id);
    var st = dates[0];
    var et = dates[1];

    $.ajax({
        type: "GET",
        url: "/api/solar/plants/".concat(plant_slug).concat('/energy/'),
        data: {startTime: (st), endTime: (et), aggregator: "FIVE_MINUTES", offline: 1},
        success: function(data) {
            if(data == '') {
                $("#day_energy_chart").empty();
                $("#day_energy_no_data").empty();
                $("#day_energy_no_data").append("<div class='alert alert-warning' style='margin-bottom: 0px;'>No data for the day</div>");
                return;
            } else {
                $("#day_energy_chart").empty();
                $("#day_energy_chart").append("<div class='col-lg-2'></div><div class='col-lg-12'><h3 class='todays_energy text-center'>Energy Generation for " + dateFormat(st, 'dd-mm-yyyy') + " : </h3></div>");
                $("#day_energy_no_data").empty();
                $("#day_energy_chart").append("<svg></svg>");
            }

            /*var arrayData = [];

            // populate the data array and calculate the day_energy
            for(var n= data.length-1; n >=0 ; n--) {
                day_energy = day_energy + parseInt(data[n].energy);
                arrayData.push([new Date(data[n].timestamp), parseInt(data[n].energy)]);
            }
            day_energy = day_energy.toFixed(2);*/

            var arrayData = [];

            $.ajax({
                type: "GET",
                url: "/api/solar/plants/".concat(plant_slug).concat('/energy/'),
                data: {startTime: st, endTime: et, aggregator: "DAY", offline: 1},
                success: function(data) {
                    /*$("#legend-badge-row").empty();
                    $("#legend-badge-row").append("<div class='col-md-4'></div><span class='badge' style='margin-top: 10px;' id='badge-row-day-energy'></span>");
                    $("#badge-row-day-energy").empty();
                    $("#badge-row-day-energy").append("<div class='pull-left'>The energy for&nbsp;</div>")
                    $("#badge-row-day-energy").append("<div id='today_date' class='pull-left'></div>");
                    $("#badge-row-day-energy").append("<div id='today_energy' class='pull-left' style='margin-left: 7px;margin-right: 7px;'></div>");*/

                    var day_energy = data[0].energy;
                    day_energy = day_energy/1000;
                    day_energy = day_energy.toFixed(0);
                    /*$("#today_date").empty();
                    $("#today_date").append(st+" - ");
                    $("#today_energy").empty();
                    $("#today_energy").append(day_energy + " MWh");*/

                    $(".todays_energy").append(day_energy+" MWh");

                    if(data[0].pvsyst_generation) {

                        var pvsyst_expected_day = (parseFloat(data[0].pvsyst_generation).toFixed(0))/1000;
                        $("#day_energy_expected").empty();
                        $("#day_energy_expected").append("<div class='col-lg-2'></div><div class='col-lg-8'><h3 class='day_pvsyst text-center'>PVsyst Generation for " + dateFormat(st, 'dd-mm-yyyy') + " : " + pvsyst_expected_day + " MWh</h3></div>")
                    }
                },
                error: function(data) {
                    console.log("error_streams_data");
                    data = null;
                },
            });

            // populate the data array and calculate the day_energy
            for(var n= data.length-1; n >=0 ; n--) {
                var local_values = [];
                var ts = new Date(data[n].timestamp);

                local_values.push([ts, 0.0]);
                local_values.push([new Date(ts.setSeconds(ts.getSeconds() + 1)), parseFloat(data[n].energy)]);
                arrayData.push({"values": local_values,
                                "key": dateFormat(data[n].timestamp, 'yyyy-mm-dd HH:MM:ss').concat(" : ").concat(parseFloat(data[n].energy).toString()),
                                "color":"#4C85AB"});
            }

            // package the data
            /*var packagedData = [{
                "key": "Energy GENERATION ON DATE " + dateFormat(st, "yyyy-mm-dd") + " in kW",
                "values": arrayData,
                "color": "#4C85AB"
            }];*/
            // plot the chart
            day_line_energy_chart(arrayData);
        },
        error: function(data) {
            console.log("error_streams_data");
            data = null;
        }
    });
}

function day_line_energy_chart(data) {
    nv.addGraph(function () {
        live_chart = nv.models.lineChart()
            .x(function (d) { return d[0] })
            .y(function (d) { return d[1] })
            .showYAxis(true)
            .showLegend(false)
            .showXAxis(true)
            .margin({top: 5, right: 44, bottom: 20, left: 65})
            .useInteractiveGuideline(false)
            .clipEdge(true)
            /*.tooltip.contentGenerator(function(key, y, e, graph) {
                if(key.point[1] !=  '0') {
                    return '<p>' + key.point[0].format("dd/mm/yyyy HH:MM") + " : " + key.point[1].toFixed(2) + ' KWH' + '</p>' ;
                }
            })*/;

            live_chart.tooltip.contentGenerator(function(key, y, e, graph) {
                if(key.point[1] !=  '0') {
                    return '<p>' + key.point[0].format("dd/mm/yyyy HH:MM") + " : " + key.point[1].toFixed(0) + ' kWH' + '</p>' ;
                }
            });

        live_chart.interactiveLayer.tooltip
              .headerFormatter(function(d, i) {
                return nv.models.axis().tickFormat()(d, i);
        });
        live_chart.xAxis
              .axisLabel("")
              .tickFormat(function (d) {
                return d3.time.format('%I:%M %p')(new Date(d))
            });
        live_chart.yAxis
              .axisLabel("Energy (kWh)")
              .tickFormat(d3.format(",.2f"));
        
        live_chart.interactiveLayer.tooltip.headerFormatter(function (d) {
            return d3.time.format('%x %-I %p')(new Date(d));
        });
        d3.select('#day_energy_chart svg')
                  .datum(data)
                  .call(live_chart);
        nv.utils.windowResize(live_chart.update);

        $(".nvd3-svg").css("float", "left");

        return live_chart;
    });
}

function week_energy_data(st) {

    $("#energy_chart").empty();
    $("#energy_chart").append("<svg style='height: 40vh;'></svg>");

    var dates = get_dates(st);

    var st = dates[0];
    var e = dates[1];

    $.ajax({
        type: "GET",
        url: "/api/solar/plants/".concat(plant_slug).concat('/energy/'),
        data: {startTime: (st), endTime: (e), aggregator: "DAY", offline: 1},
        success: function(data) {
            if(data == '') {
                noty_message("No data for the week!", 'error', 5000)
                return;
            } else {
                var y_date = new Date();
                var day_energy = 0;
                var cumulative_energy = 0;
                var arrayData = [];

                var week_counter = 0;

                var day_energy_unit;

                // populate the data array and calculate the day_energy
                for(var n= 0; n < data.length ; n++) {
                    day_energy_unit = data[n].energy;
                    day_energy_unit = day_energy_unit.split(" ");
                    day_energy = parseFloat(data[n].energy);
                    /*cumulative_energy = cumulative_energy + parseInt(data[n].energy);*/
                    y_date = new Date(data[n].timestamp);
                    y_date = dateFormat(y_date, "yyyy-mm-dd");
                    if(data[n].pvsyst_generation) {
                        week_counter++;
                    }
                    arrayData.push({"label": y_date, "value": parseFloat(day_energy.toFixed(0)), "color": "#0b62a4"});
                }

                if(week_counter > 0) {

                    $("#week_energy_expected").empty();
                    $("#week_energy_expected").append("<div class='col-lg-2'></div><div class='col-lg-8'><h3 class='week_pvsyst text-center'>PVsyst Generation for the week : </h3><br/><h5 class='text-center'><span id='pvsyst_week_per_day' style='font-size: 19px;'></span></h5></div>")

                    for(var i = 0; i < data.length; i++) {

                        if(data[i].pvsyst_generation) {
                            var pvsyst_expected_day = (parseFloat(data[i].pvsyst_generation).toFixed(0));
                            y_date = new Date(data[i].timestamp);
                            y_date = dateFormat(y_date, "yyyy-mm-dd");
                            if(i == data.length-1) {
                                $("#pvsyst_week_per_day").append(y_date + " : " + pvsyst_expected_day + day_energy_unit[1]);
                            } else {
                                $("#pvsyst_week_per_day").append(y_date + " : " + pvsyst_expected_day + day_energy_unit[1]);
                            }
                        }

                    }
                }

                cumulative_energy = (cumulative_energy/1000).toFixed(0);

                $("#week_energy").append(cumulative_energy+" " + day_energy_unit[1]);

                // package the data
                var packagedData = [{
                    "key": "Energy generation of this week from" + dateFormat(st, "yyyy-mm-dd") + "to" + dateFormat(e, "yyyy-mm-dd") + day_energy + "kWh",
                    "values": arrayData
                }];
                // plot the chart
                weekly_bar_chart(packagedData, day_energy_unit);
            }
        },
        error: function(data) {
            console.log("error_streams_data");
            data = null;
        }
    });
}

function weekly_bar_morris_chart(data) {

    /*
 * Play with this code and it'll update in the panel opposite.
 *
 * Why not try some of the options above?
 */
Morris.Bar({
  element: 'bar-example',
  data: data,
  xkey: 'xAxis',
  ykeys: ['yAxis'],
  labels: ['unit']
});

var thisDate,thisData;
$( "#bar-example svg rect" ).on('click', function() {
    // Find data and date in the actual morris diply below the graph.
    thisDate = $(".morris-hover-row-label").html();
    thisDataHtml = $(".morris-hover-point").html().split(":");
    thisData = thisDataHtml[1].trim();
    
    // alert !!
    alert( "Data: "+thisData+"\nDate: "+thisDate );
});


}

function weekly_bar_chart(packagedData, day_energy_unit){
    nv.addGraph(function() {
        var chart = nv.models.discreteBarChart()
            .x(function(d) { 
                var date = d.label;
                date = dateFormat(date, 'dd/mm/yyyy');
                return date; })    //Specify the data accessors.
            .y(function(d) { return d.value })
            .showValues(true)
            .color(['#B4D3E5'])
            .margin({top: 5, right: 0, bottom: 12, left: 60});
            /*.tooltip.contentGenerator(function(key, y, e, graph) {
                if(key.data.value !=  '0') {
                    return '<p>' + key.data.label + " : " + key.data.value.toFixed(2) + ' MWh' + '</p>' ;
                }
            })*/

        /*chart.tooltip.contentGenerator(function(key, y, e, graph) {
            if(key.data.value !=  '0') {
                return '<p>' + key.data.label + " : " + key.data.value.toFixed(2) + ' MWh' + '</p>' ;
            }
        })*/

        chart.tooltip.enabled(false);

        chart.yAxis
              .axisLabel("Energy (" + day_energy_unit[1] + ")")
              .tickFormat(d3.format(",.2f"));

        d3.select('#energy_chart svg')
          .datum(packagedData)
          .call(chart);

        nv.utils.windowResize(chart.update);

        $(".nvd3-svg").css("float", "left");

        return chart;
    })/*,function(){
    d3.selectAll(".nv-bar").on('click',
        function(d){
            d3.select(this);

            var plot_id = "week_energy_chart";

            var tab_id = "week";

            $("#week-badge-row").hide();

            var st = d.label;
            st = new Date(st);
            var et = new Date(st.getTime());
            et = new Date(et.setDate(st.getDate() + 1));
            // convert them into strings

            st = dateFormat(st, "yyyy-mm-dd");
            et = dateFormat(et, "yyyy-mm-dd");

            day_power_from_bar(st, et, tab_id, plot_id);
        });
    });*/
}

/*Energy Data for a year*/

function year_energy_data(st) {

    $("#energy_chart").empty();
    $("#energy_chart").append("<svg style='height: 40vh;'></svg>");

    var dates = get_dates(st);

    var st = dates[0];
    var e = dates[1];

    $.ajax({
        type: "GET",
        url: "/api/solar/plants/".concat(plant_slug).concat('/energy/'),
        data: {startTime: (st), endTime: (e), aggregator: "MONTH", offline: 1},
        success: function(data) {
            if(data == '') {
                noty_message("No data for the year!", 'error', 5000)
                return;
            } else {
                var y_date = new Date();
                var month_energy = 0;
                var cumulative_energy = 0;
                var arrayData = [];

                var year_counter = 0;

                var month_energy_unit;

                // populate the data array and calculate the day_energy
                for(var n= 0; n < data.length ; n++) {
                    month_energy = parseFloat(data[n].energy);
                    cumulative_energy = cumulative_energy + month_energy;
                    month_energy_unit = (data[n].energy).split(" ");
                    y_date = new Date(data[n].timestamp);
                    y_date = dateFormat(y_date, "yyyy/mm/dd");
                    if(data[n].pvsyst_generation) {

                        year_counter++;

                    }
                    arrayData.push({"label": y_date, "value": parseFloat(month_energy).toFixed(0), "color": "#0b62a4"});
                }

                cumulative_energy = (cumulative_energy).toFixed(0);

                $(".cumulative_year_energy").append(cumulative_energy + " " + month_energy_unit[1]);

                // package the data
                var packagedData = [{
                    "key": "Energy GENERATION OF THIS YEAR FROM" + dateFormat(st, "yyyy-mm-dd") + "to" + dateFormat(e, "yyyy-mm-dd") + month_energy + "kWh",
                    "values": arrayData
                }];

                if(year_counter > 0) {

                    $("#year_energy_expected").empty();
                    $("#year_energy_expected").append("<div class='col-lg-2'></div><div class='col-lg-8'><h3 class='year_pvsyst text-center'>PVsyst Estimated Generation for <span id='year_energy_pvsyst'></span> : </h3><br/><h5 class='text-center'><span id='pvsyst_week_per_month' style='font-size: 19px;'></span></h5></div>");

                    for(var i = 0; i < data.length; i++) {

                        var pvsyst_expected_month = (parseFloat(data[i].pvsyst_generation).toFixed(0));
                        y_date = new Date(data[i].timestamp);
                        y_date = dateFormat(y_date, "mm");
                        if(i == data.length-1) {
                            $("#pvsyst_week_per_month").append(y_date + " : " + pvsyst_expected_month + " " + month_energy_unit[1]);
                        } else {
                            $("#pvsyst_week_per_month").append(y_date + " : " + pvsyst_expected_month + " " + month_energy_unit[1]);
                        }
                    }

                }

                // plot the chart
                yearly_bar_chart(packagedData, month_energy_unit);
            }
        },
        error: function(data) {
            console.log("error_streams_data");
            data = null;
        }
    });
}
function yearly_bar_chart(packagedData, month_energy_unit){

    var year = [];

    nv.addGraph(function() {
      var chart = nv.models.discreteBarChart()
            .x(function(d) { 
                var month_date = new Date(d.label);
                var locale = "en-us";
                var month = month_date.toLocaleString(locale, { month: "long" });

                var date = d.label;
                year = date.split('/');

                return month; 
            })    //Specify the data accessors.
            .y(function(d) { 
                var float_value = d.value;
                float_value = parseFloat(float_value);
                return float_value })
            .showValues(true)
            .color(['#B4D3E5'])
            /*#ff7f0e*/
            .margin({top: 5, right: 0, bottom: 70, left: 60})
            /*.tooltip.contentGenerator(function(key, y, e, graph) {
                var month_date = new Date(key.data.label);
                var locale = "en-us";
                var month = month_date.toLocaleString(locale, { month: "long" });
                if(key.data.value !=  '0') {
                    return '<p>' + month + " : " + key.data.value + ' MWh' + '</p>' ;
                }
            })*/
          ;

        /*live_chart.tooltip.contentGenerator(function(key, y, e, graph) {
            var month_date = new Date(key.data.label);
            var locale = "en-us";
            var month = month_date.toLocaleString(locale, { month: "long" });
            if(key.data.value !=  '0') {
                return '<p>' + month + " : " + key.data.value + ' MWh' + '</p>' ;
            }
        })*/

        /*chart.xAxis
            .rotateLabels(-45);*/

        chart.tooltip.enabled(false);

        chart.yAxis
              .axisLabel("Energy (" + month_energy_unit[1] + ")")
              .tickFormat(d3.format(",.2f"));

      d3.select('#energy_chart svg')
          .datum(packagedData)
          .call(chart);

      nv.utils.windowResize(chart.update);

      $("#year_energy").append(year[0]);
      $("#year_energy_pvsyst").append(year[0]);
      $(".nvd3-svg").css("float", "left");

      return chart;
    });
}

function month_energy_from_bar(st, et, tab_id, plot_id) {

    $("#" + plot_id).empty();
    $("#" + plot_id).append("<svg></svg>");

    $("#"+tab_id+"tab").empty();
    $("#"+tab_id+"tab").append("Month");
    
    $.ajax({
        type: "GET",
        url: "/api/solar/plants/".concat(plant_slug).concat('/energy/'),
        data: {startTime: (st), endTime: (et), aggregator: "DAY", offline: 1},
        success: function(data) {
            if(data == '') {
                $("#year_energy_chart").empty();
                $("#year_energy_no_data").empty();
                $("#year_energy_no_data").append("<div class='alert alert-warning'>No data for the month</div>");
                return;
            } else {
                $("#year_energy_no_data").empty();
                $("#year_energy_chart").empty();
                $("#year_energy_chart").append("<div class='row' id='month_bar_chart'></div>");
                $("#year_energy_chart").append("<div class='col-lg-2'></div><div class='col-lg-8'><h3 class='cumulative_month_energy text-center'>Cumulative Generation for <span id='month_energy_bar'></span> : </h3></div>");
                $("#year_energy_chart").append("<svg></svg>");
            }

            var y_date = new Date();
            var day_energy = 0;
            var cumulative_energy = 0;
            var arrayData = [];

            var year_month_counter = 0
            var data_pos = 0;

            // populate the data array and calculate the day_energy
            for(var n= 0; n < data.length ; n++) {
                day_energy = parseFloat(data[n].energy);
                if(data[n].pvsyst_generation) {

                    year_month_counter++;

                    data_pos = n;

                }
                cumulative_energy = cumulative_energy + parseFloat(data[n].energy);
                y_date = new Date(data[n].timestamp);
                y_date = dateFormat(y_date, "yyyy/mm/dd");
                arrayData.push({"label": y_date, "value": parseFloat(day_energy.toFixed(0))/1000, "color": "#0b62a4"});
            }

            if(year_month_counter > 0) {

                month_pvsyst_expected = parseFloat(data[data_pos].pvsyst_generation).toFixed(0);
                month_pvsyst_expected = month_pvsyst_expected/1000;

                $("#"+ tab_id +"_energy_expected").empty();
                $("#"+ tab_id +"_energy_expected").append("<div class='col-lg-2'></div><div class='col-lg-8'><h3 class='"+tab_id+"_pvsyst text-center'>PVsyst Generation for <span id='"+tab_id+"_energy_pvsyst'></span> : <span id='"+tab_id+"_pvsyst_data'></span></h3></div>");

                $("#"+ tab_id +"_pvsyst_data").append(month_pvsyst_expected + " MWh");

            }

            cumulative_energy = (cumulative_energy/1000).toFixed(0);

            $(".cumulative_month_energy").append(cumulative_energy+" MWh");

            // package the data
            var packagedData = [{
                "key": "Energy GENERATION OF THIS MONTH FROM" + dateFormat(st, "yyyy-mm-dd") + "to" + dateFormat(et, "yyyy-mm-dd") + day_energy + "kWh",
                "values": arrayData
            }];
            // plot the chart
            monthly_bar_chart_from_bar(packagedData, plot_id);
        },
        error: function(data) {
            console.log("error_streams_data");
            data = null;
        }
    });
}
function monthly_bar_chart_from_bar(packagedData, plot_id){

    var month_name = null;

    nv.addGraph(function() {
      var chart = nv.models.discreteBarChart()
            .x(function(d) { 
                var month_date = new Date(d.label);
                var locale = "en-us";
                month_name = month_date.toLocaleString(locale, { month: "long" });
                return d.label })    //Specify the data accessors.
            .y(function(d) { 
                var bar_value = d.value;
                var value = (bar_value).toString();
                return d.value })
            .showValues(true)
            .color(['#B4D3E5'])
            /*#ff7f0e*/
            .margin({top: 5, right: 0, bottom: 70, left: 60})
            /*.tooltip.contentGenerator(function(key, y, e, graph) {
                if(key.data.value !=  '0') {
                    return '<p>' + key.data.label + " : " + key.data.value.toFixed(2) + ' MWh' + '</p>' ;
                }
            })*/
          ;

        /*chart.tooltip.contentGenerator(function(key, y, e, graph) {
            if(key.data.value !=  '0') {
                return '<p>' + key.data.label + " : " + key.data.value.toFixed(2) + ' MWh' + '</p>' ;
            }
        });*/

        chart.tooltip.enabled(false);

        chart.xAxis
            .tickFormat(function (d) {
                return d3.time.format('%d')(new Date(d))
            });

        chart.yAxis
              .axisLabel("Energy (MWh)")
              .tickFormat(d3.format(",.3f"));

      d3.select('#'+plot_id+' svg')
          .datum(packagedData)
          .call(chart);

      nv.utils.windowResize(chart.update);

      $("#month_energy_bar").append(month_name);
      $(".nvd3-svg").css("float", "left");

      return chart;
    },function(){
        d3.selectAll(".nv-bar").on('click',
            function(d){
                d3.select(this);

                var plot_id = "year_energy_chart";

                var tab_id = "year";

                d3.select(".d3-tip").remove();

                var st = d.label;
                st = new Date(st);
                var et = new Date(st.getTime());
                et = new Date(et.setDate(st.getDate() + 1));
                // convert them into strings

                st = dateFormat(st, "yyyy-mm-dd");
                et = dateFormat(et, "yyyy-mm-dd");

                day_power_from_bar(st, et, tab_id, plot_id);
        });
    });
}

function epoch_to_date(epoch) {
    var date = new Date(epoch);
    date = dateFormat(date, "dd-mm-yyyy");
    return date;
}

function epoch_to_month(epoch) {
    var date = new Date(epoch);
    date = dateFormat(date, "dd-mmm");
    return date;
}

function epoch_to_year(epoch) {
    var date = new Date(epoch);
    date = dateFormat(date, "mmm");
    return date;
}

function energy_chart(st, text) {

    var dates = get_dates(st);

    st = dates[0];
    var et = dates[1];

    if (aggregator_string == "WEEK" || aggregator_string == "MONTH") {
        aggregator_string = "DAY";
    } else if (aggregator_string == "YEAR") {
        aggregator_string = "MONTH";
    }

    $.ajax({
        type: "GET",
        url: "/api/solar/plants/".concat(plant_slug).concat('/energy/'),
        data: {startTime: (st), endTime: (et), aggregator: aggregator_string, offline: 1},
        success: function(data) {
            if(data == '') {
                $("#client_spinner").hide();

                noty_message("No Energy for the selected " + text + "!", 'error', 5000)
                return;
            } else {
                
                var energy_unit = (data[0].energy).split(" ");

                var timestamp = [], energy_values = [], pvsyst_energy_annotation = [], pvsyst_energy = [], predicted_energy = [], lower_data = [], higher_data = [];

                var monitor_height = window.screen.availHeight;
                var monitor_width = window.screen.availWidth;

                var annotation_line = monitor_width/3.5;
                annotation_line = annotation_line/(data.length);

                // populate the data array and calculate the day_energy
                for(var energy = 0; energy < data.length; energy++) {
                    timestamp.push(new Date(data[energy].timestamp));
                    energy_values.push(parseFloat(data[energy].energy).toFixed(2));
                    if(data[energy].pvsyst_generation) {
                        pvsyst_energy.push({x: new Date(data[energy].timestamp), y: (parseFloat(data[energy].pvsyst_generation)).toFixed(2), r: 5});
                        /*pvsyst_energy_annotation.push({
                            type: 'box',
                            xScaleID: 'x-axis-1',
                            yScaleID: 'y-axis-0',
                            // Left edge of the box. in units along the x axis
                            xMax: new Date(data[energy].timestamp).valueOf() + 1000,
                            xMin: new Date(data[energy].timestamp).valueOf(),
                            // Right edge of the box
                            // Top edge of the box in units along the y axis
                            yMax: parseFloat(data[energy].pvsyst_generation) * 0.9999,

                            // Bottom edge of the box
                            yMin: parseFloat(data[energy].pvsyst_generation),

                            label: "Pvsyst Energy",
                            backgroundColor: 'rgba(101, 33, 171, 0.5)',
                            borderColor: 'rgb(101, 33, 171)',
                            borderWidth: 1,
                            onMouseover: function(e) {
                                console.log(e);
                                console.log('Box', e.type, this);

                                $("#annotation_tooltip").show();

                                var time = new Date(this._model.ranges["x-axis-0"].min);
                                time = dateFormat(time, "dd-mm-yyyy");
                                $("#annotation_tooltip").empty();
                                $("#annotation_tooltip").append("Pvsyst Energy " + time);
                            },
                            onMouseleave: function(e) {
                                $("#annotation_tooltip").hide();
                            }
                        })*/
                    }
                    if(data[energy].lower_bound) {
                        lower_data.push({x: new Date(data[energy].timestamp), y: (parseFloat(data[energy].lower_bound)).toFixed(2)});
                    }
                    if(data[energy].upper_bound) {
                        higher_data.push({x: new Date(data[energy].timestamp), y: (parseFloat(data[energy].upper_bound)).toFixed(2)});
                    }
                    if(data[energy].predicted_energy) {
                        predicted_energy.push({x: new Date(data[energy].timestamp), y: (parseFloat(data[energy].predicted_energy)).toFixed(2)});
                    }

                }

                energy_chart_plot(timestamp, energy_values, pvsyst_energy, predicted_energy, lower_data, higher_data, "Energy (" + energy_unit[1] + ")", "Predicted (" + energy_unit[1] + ")", "Pvsyst (" + energy_unit[1] + ")", "Lower Bound (" + energy_unit[1] + ")", "Upper Bound (" + energy_unit[1] + ")", text, annotation_line);

            }

            $("#client_spinner").hide();
        },
        error: function(data) {

            $("#client_spinner").hide();

            noty_message("No Energy for the selected " + text + "!", 'error', 5000)
            return;
        }
    });

}

function energy_chart_range(st, et, text) {

    console.log(st);
    console.log(et);

    st = st.split("-");
    st = st[2] + "-" + st[1] + "-" + st[0];
    st = new Date(st);

    et = et.split("-");
    et = et[2] + "-" + et[1] + "-" + et[0];
    et = new Date(et);

    st = dateFormat(st, "yyyy-mm-dd");
    et = dateFormat(et, "yyyy-mm-dd");

    if (aggregator_string == "WEEK" || aggregator_string == "MONTH") {
        aggregator_string = "DAY";
    } else if (aggregator_string == "YEAR") {
        aggregator_string = "MONTH";
    }

    $.ajax({
        type: "GET",
        url: "/api/solar/plants/".concat(plant_slug).concat('/energy/'),
        data: {startTime: (st), endTime: (et), aggregator: "DAY", offline: 1},
        success: function(data) {
            if(data == '') {
                $("#client_spinner").hide();

                noty_message("No Energy for the selected " + text + "!", 'error', 5000)
                return;
            } else {
                
                var energy_unit = (data[0].energy).split(" ");

                var timestamp = [], energy_values = [], pvsyst_energy_annotation = [], pvsyst_energy = [], predicted_energy = [], lower_data = [], higher_data = [];

                var monitor_height = window.screen.availHeight;
                var monitor_width = window.screen.availWidth;

                var annotation_line = monitor_width/3.5;
                annotation_line = annotation_line/(data.length);

                // populate the data array and calculate the day_energy
                for(var energy = 0; energy < data.length; energy++) {
                    timestamp.push(new Date(data[energy].timestamp));
                    energy_values.push(parseFloat(data[energy].energy).toFixed(2));
                    if(data[energy].pvsyst_generation) {
                        pvsyst_energy.push({x: new Date(data[energy].timestamp), y: (parseFloat(data[energy].pvsyst_generation)).toFixed(2), r: 5});
                        /*pvsyst_energy_annotation.push({
                            type: 'box',
                            xScaleID: 'x-axis-1',
                            yScaleID: 'y-axis-0',
                            // Left edge of the box. in units along the x axis
                            xMax: new Date(data[energy].timestamp).valueOf() + 1000,
                            xMin: new Date(data[energy].timestamp).valueOf(),
                            // Right edge of the box
                            // Top edge of the box in units along the y axis
                            yMax: parseFloat(data[energy].pvsyst_generation) * 0.9999,

                            // Bottom edge of the box
                            yMin: parseFloat(data[energy].pvsyst_generation),

                            label: "Pvsyst Energy",
                            backgroundColor: 'rgba(101, 33, 171, 0.5)',
                            borderColor: 'rgb(101, 33, 171)',
                            borderWidth: 1,
                            onMouseover: function(e) {
                                console.log(e);
                                console.log('Box', e.type, this);

                                $("#annotation_tooltip").show();

                                var time = new Date(this._model.ranges["x-axis-0"].min);
                                time = dateFormat(time, "dd-mm-yyyy");
                                $("#annotation_tooltip").empty();
                                $("#annotation_tooltip").append("Pvsyst Energy " + time);
                            },
                            onMouseleave: function(e) {
                                $("#annotation_tooltip").hide();
                            }
                        })*/
                    }
                    if(data[energy].lower_bound) {
                        lower_data.push({x: new Date(data[energy].timestamp), y: (parseFloat(data[energy].lower_bound)).toFixed(2)});
                    }
                    if(data[energy].upper_bound) {
                        higher_data.push({x: new Date(data[energy].timestamp), y: (parseFloat(data[energy].upper_bound)).toFixed(2)});
                    }
                    if(data[energy].predicted_energy) {
                        predicted_energy.push({x: new Date(data[energy].timestamp), y: (parseFloat(data[energy].predicted_energy)).toFixed(2)});
                    }

                }

                energy_chart_plot(timestamp, energy_values, pvsyst_energy, predicted_energy, lower_data, higher_data, "Energy (" + energy_unit[1] + ")", "Predicted (" + energy_unit[1] + ")", "Pvsyst (" + energy_unit[1] + ")", "Lower Bound (" + energy_unit[1] + ")", "Upper Bound (" + energy_unit[1] + ")", text, annotation_line);

            }

            $("#client_spinner").hide();
        },
        error: function(data) {

            $("#client_spinner").hide();

            noty_message("No Energy for the selected Date Range!", 'error', 5000)
            return;
        }
    });

}

function energy_chart_plot(timestamp, values, pvsyst_values, predicted_energy, lower_data, higher_data, plant_parameter_label, predicted_bound_label, pvsyst_energy_label, lower_bound_label, higher_bound_label, text, annotation_line) {

    $("#energy_headings").empty();

    var chart_data = {
        "labels": timestamp,
        "datasets": []
    };
    var y_axes_values;
    var energy_present_counter = 1;

    var energy_present = [predicted_energy, pvsyst_values, lower_data, higher_data];

    var energy_labels = [predicted_bound_label, pvsyst_energy_label, lower_bound_label, higher_bound_label];
    var energy_color = ['rgba(239, 83, 80, 1)', 'rgba(38, 50, 56, 1)', 'rgba(255, 167, 38, 1)', 'rgba(88, 86, 20, 1)'];
    var energy_heading = ["label-danger", "label-dark", "label-warning", "label-success"];

    console.log(energy_present);

    for(energy_count = 0; energy_count < energy_present.length; energy_count++) {
        if(_.some(energy_present[energy_count])) {
            $("#energy_headings").append("<div class='col-lg-2 col-md-2 col-sm-2'><span class='label " + energy_heading[energy_count] + "' style='background-color: " + energy_color[energy_count] + "'></span> <span>" + energy_labels[energy_count] + "</span></div>");
            chart_data.datasets.push({
                type: 'line',
                label: energy_labels[energy_count],
                backgroundColor: 'rgba(0, 0, 0, 0)',
                borderColor: 'rgba(0, 0, 0, 0)',
                fillColor: 'rgba(0, 0, 0, 0)',
                pointBackgroundColor: energy_color[energy_count],
                pointBorderColor: energy_color[energy_count],
                pointStyle: "line",
                pointBorderWidth: 3,
                pointRadius: annotation_line,
                pointHoverRadius: annotation_line,
                data: energy_present[energy_count]
            });
        } else {
            energy_present_counter++;
        }
    }

    $("#energy_headings").append("<div class='col-lg-2 col-md-2 col-sm-2'><span class='label label-default' style='background-color: #4889bb;'></span> <span>" + plant_parameter_label + "</span></div>");

    chart_data.datasets.push({
        label: plant_parameter_label,
        backgroundColor: 'rgba(72, 137, 187, 1)',
        borderColor: 'rgba(72,137,187,1)',
        data: values,
        pointBorderColor : 'rgba(0,0,0,0)',
        pointBackgroundColor : 'rgba(0,0,0,0)'
    });

    y_axes_values = [{
        gridLines: {
            display: true
        },
        position: 'left',
        scaleLabel: {
            display: true,
            labelString: plant_parameter_label
        },
        ticks: {
            beginAtZero: true
        }
    }];

    $('#energy_chart').remove(); // this is my <canvas> element
    $('#download_html_to_pdf').append('<canvas id="energy_chart"><canvas>');
    var ctx = document.getElementById("energy_chart");

    var myBarChart = new Chart(ctx, {
        type: 'bar',
        responsive: true,
        data: chart_data,
        options: {
            elements:{
                point: {
                    radius: 0
                }
            },
            tooltips: {
                intersect: false,
                mode: 'index'
            },
            legend: {
                display: false
            },
            responsive: true,
            maintainAspectRatio: false,

            title: {
                display: false,
                text: 'Chart.js Scatter Chart'
            },
            scales: {
                xAxes: [{
                    gridLines: {display: false},
                    position: 'bottom',
                    ticks: {
                        userCallback: function(v) {
                            if(text == "WEEK") {
                                return epoch_to_date(v)    
                            } else if(text == "MONTH") {
                                return epoch_to_month(v)
                            } else if(text == "YEAR") {
                                return epoch_to_year(v)
                            }
                        },
                        reverse: true
                    }
                }],
                yAxes: y_axes_values,
            },
            /*annotation: {
                drawTime: "afterDraw",
                events: ['mouseover'],
                annotations: pvsyst_values_annotation
            }
            animation: {
                duration: 2000,
                onComplete: function (animation) {

                    console.log(this);

                    console.log("animation done");
                    ctx = this.chart.ctx;
                    ctx.font = this.chart.ctx.font;
                    ctx.fillStyle = this.chart.ctx.textColor;
                    ctx.textAlign = "center";
                    ctx.textBaseline = "middle";
                    var chart = this;
                    var datasets = this.data.datasets;
                    var tooltip = this.tooltip._model;

                    this.data.datasets.forEach(function (dataset, i) {
                        ctx.fillText(value, tooltip.x, tooltip.y);
                    })
                }
            }*/
        }
    });

}