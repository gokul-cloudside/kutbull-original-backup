$(document).ready(function() {
    start_year();
    year_energy_data();
});

function start_year() {
    var st = new Date();
    var year = st.getFullYear();
    for(var i = year; i >= year - 5; i--) {
        $("#start_energy_year").append("<option value=" + i + ">" + i + "</option>")
    }
}

function get_year() {
    var year = $("#start_energy_year").val();
    var st = year+"-01-01";
    var et = year+"-12-31";

    return [st, et];
}

/*Energy Data for a year*/

function year_energy_data() {

    var dates_year = get_year();
    var st = dates_year[0];
    var et = dates_year[1];
    
    $("#energy_heading").empty();
    
    $.ajax({
        type: "GET",
        url: "/api/solar/plants/".concat(plant_slug).concat('/energy/').concat("?startTime=").concat(st).concat("&endTime=").concat(et).concat("&aggregator=MONTH&meter=1"),
        /*data: {startTime: (st), endTime: (et), aggregator: "MONTH"},*/
        success: function(data) {
            if(data == '') {
                $("#year_energy_chart").empty();
                $("#year_energy_chart_no_data").empty();
                $("#year_energy_chart_no_data").append("<div class='alert alert-warning'>No data for the year</div>");
                return;
            } else {
                $("#year_energy_chart_no_data").empty();
                $("#year_energy_chart").empty();
                $("#year_energy_chart").append("<div class='row' id='month_bar_chart'></div>");
                $("#year_energy_chart").append("<div class='col-lg-2'></div><div class='col-lg-8'><h3 class='cumulative_year_energy text-center'>Cumulative Generation for <span id='year_energy'></span> : </h3></div>");
                $("#year_energy_chart").append("<svg></svg>");
            }

            var y_date = new Date();
            var month_energy = 0;
            var cumulative_energy = 0;
            var arrayData = [];

            // populate the data array and calculate the day_energy
            for(var n= 0; n < data.length ; n++) {
                month_energy = parseFloat(data[n].energy);
                cumulative_energy = cumulative_energy + month_energy;
                y_date = new Date(data[n].timestamp);
                y_date = dateFormat(y_date, "yyyy/mm/dd");
                arrayData.push({"label": y_date, "value": parseFloat(month_energy/1000).toFixed(3)});
            }

            cumulative_energy = (cumulative_energy/1000).toFixed(3);

            $(".cumulative_year_energy").append(cumulative_energy+" MWh");

            // package the data
            var packagedData = [{
                "key": "Energy GENERATION OF THIS YEAR FROM" + dateFormat(st, "yyyy-mm-dd") + "to" + dateFormat(et, "yyyy-mm-dd") + month_energy + "kWh",
                "values": arrayData
            }];

            // plot the chart
            yearly_bar_chart(packagedData);
        },
        error: function(data) {
            console.log("error_streams_data");
            data = null;
        }
    });
}
function yearly_bar_chart(packagedData){

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
                var bar_value = d.value;
                var value = bar_value;
                var float_value = parseFloat(bar_value);
                return float_value })
            .showValues(true)
            .color(['#B4D3E5'])
            /*#ff7f0e*/
            .margin({top: 5, right: 0, bottom: 70, left: 60})
          ;

        chart.tooltip.enabled(false);

        chart.yAxis
              .axisLabel("Energy (MWh)")
              .tickFormat(d3.format(",.2f"));

      d3.select('#year_energy_chart svg')
          .datum(packagedData)
          .call(chart);

      nv.utils.windowResize(chart.update);

      $("#year_energy").append(year[0]);
      $("#energy_heading").append(year[0] + "'s");

      return chart;
    },function(){
        d3.selectAll(".nv-bar").on('click',
            function(d){

                d3.select(this);

                var plot_id = "year_energy_chart";

                var tab_id = "year";

                var st = d.label;

                var dt = new Date(st);
                dt.setMonth(dt.getMonth() + 1);
                var etw = new Date(dt);
                
                /*var date = new Date(etw);
                var lastDay = new Date(date.getFullYear(), date.getMonth() + 1, 0);
                etw = etw[0] + "-" + etw[1] + "-" + lastDay.getDate();*/
                // convert them into strings

                var stw = dateFormat(st, "yyyy-mm-dd");
                etw = dateFormat(etw, "yyyy-mm-dd");

                month_energy_from_bar(stw, etw, tab_id, plot_id);
        });
    });
}

function month_energy_from_bar(st, et, tab_id, plot_id) {
    
    $("#energy_heading").empty();

    $.ajax({
        type: "GET",
        url: "/api/solar/plants/".concat(plant_slug).concat('/energy/').concat("?startTime=").concat(st).concat("&endTime=").concat(et).concat("&aggregator=DAY&meter=1"),
        /*data: {startTime: (st), endTime: (et), aggregator: "DAY"},*/
        success: function(data) {
            if(data == '') {
                $("#year_energy_chart").empty();
                $("#year_energy_chart_no_data").empty();
                $("#year_energy_chart_no_data").append("<div class='alert alert-warning'>No data for the month</div>");
                return;
            } else {
                $("#year_energy_chart_no_data").empty();
                $("#year_energy_chart").empty();
                $("#year_energy_chart").append("<div class='row' id='month_bar_chart'></div>");
                $("#year_energy_chart").append("<div class='col-lg-2'></div><div class='col-lg-8'><h3 class='cumulative_month_energy text-center'>Cumulative Generation for <span id='month_energy_bar'></span> : </h3></div>");
                $("#year_energy_chart").append("<svg></svg>");
            }

            var y_date = new Date();
            var day_energy = 0;
            var cumulative_energy = 0;
            var arrayData = [];

            // populate the data array and calculate the day_energy
            for(var n= 0; n < data.length ; n++) {
                day_energy = parseFloat(data[n].energy);
                cumulative_energy = cumulative_energy + parseFloat(data[n].energy);
                y_date = new Date(data[n].timestamp);
                y_date = dateFormat(y_date, "yyyy/mm/dd");
                arrayData.push({"label": y_date, "value": parseFloat(day_energy.toFixed(3))/1000});
            }

            cumulative_energy = (cumulative_energy/1000).toFixed(3);

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
                var value = bar_value.toFixed(3);
                return value })
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

        chart.tooltip.enabled(false);

        chart.xAxis
            .tickFormat(function (d) {
                return d3.time.format('%d')(new Date(d))
            });

        chart.yAxis
              .axisLabel("Energy (MWh)")/*
              .tickFormat(d3.format(",.2f"))*/;

      d3.select('#year_energy_chart svg')
          .datum(packagedData)
          .call(chart);

      nv.utils.windowResize(chart.update);

      $("#month_energy_bar").append(month_name);
      $("#energy_heading").append(month_name + "'s");

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

function day_power_from_bar(st, et, tab_id, plot_id) {

    $("#energy_heading").empty();

    $.ajax({
        type: "GET",
        url: "/api/solar/plants/".concat(plant_slug).concat('/power/'),
        data: {startTime: (st), endTime: (et)},
        success: function(data) {
            if(data == '') {
                $("#month_energy_no_data").empty();
                $("#month_energy_no_data").append("<div class='alert alert-warning'>No data for the month</div>");
                return;
            } else {
                $("#month_energy_no_data").empty();
                $("#year_energy_chart").empty();
                $("#year_energy_chart").append("<div class='col-lg-2'></div><div class='col-lg-12'><h3 class='days_energy text-center'>Energy Generation for " + dateFormat(st, 'dd-mm-yyyy') +" : </h3></div>");
                $("#year_energy_chart").append("<svg></svg>");
            }

            var arrayData = [];

            $.ajax({
                type: "GET",
                url: "/api/solar/plants/".concat(plant_slug).concat('/energy/').concat("?startTime=").concat(st).concat("&endTime=").concat(et).concat("&aggregator=DAY&meter=1"),
                /*data: {startTime: st, endTime: et, aggregator: "DAY"},*/
                success: function(data) {
                    var day_energy = data[0].energy;
                    day_energy = day_energy/1000;
                    day_energy = day_energy.toFixed(3);

                    $(".days_energy").append(day_energy+" MWh");
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
            day_line_energy_chart_from_bar_chart(arrayData, plot_id, st);
        },
        error: function(data) {
            console.log("error_streams_data");
            data = null;
        }
    });
}

function day_line_energy_chart_from_bar_chart(data, plot_id, st) {

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
                    return '<p>' + key.point[0].format("dd/mm/yyyy HH:MM") + " : " + key.point[1].toFixed(2) + ' KW' + '</p>' ;
                }
            })*/;

        live_chart.tooltip.contentGenerator(function(key, y, e, graph) {
            if(key.point[1] !=  '0') {
                return '<p>' + key.point[0].format("dd/mm/yyyy HH:MM") + " : " + key.point[1].toFixed(3) + ' kW' + '</p>' ;
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
        d3.select('#year_energy_chart svg')
                  .datum(data)
                  .call(live_chart);

        $("#energy_heading").append(dateFormat(st, 'dd-mm-yyyy') + "'s");

        nv.utils.windowResize(live_chart.update);
        return live_chart;
    });
}