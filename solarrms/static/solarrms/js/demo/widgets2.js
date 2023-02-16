// Widgets.js
// ====================================================================
// This file should not be included in your project.
// This is just a sample how to initialize plugins or components.
//
// - ThemeOn.net -

var opts = {};
var target = null;
var gauge = null;

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

var windspeed_unipatch = 0;
var status_data = 0;

$(document).ready(function() {
    // GAUGE PLUGIN
    // =================================================================
    // Require Gauge.js
    // -----------------------------------------------------------------
    // http://bernii.github.io/gauge.js/
    // =================================================================

    if (plant_slug != 'uran' && plant_slug != 'rrkabel' && plant_slug != 'unipatch') {
        opts = {
            lines: 10, // The number of lines to draw
            angle: 0, // The length of each line
            lineWidth: 0.41, // The line thickness
            pointer: {
                length: 0.75, // The radius of the inner circle
                strokeWidth: 0.035, // The rotation offset
                color: '#769f48' // Fill color
            },
            limitMax: 'true', // If true, the pointer will not go past the end of the gauge
            colorStart: '#fff', // Colors
            colorStop: '#fff', // just experiment with them
            strokeColor: '#8ab75a', // to see which ones work best for you
            generateGradient: true
        };

        target = document.getElementById('current-power'); // your canvas element
        gauge = new Gauge(target).setOptions(opts);
        gauge.maxValue = plant_capacity; // set max gauge value
        gauge.animationSpeed = 32; // set animation speed (32 is default value)
        gauge.set(1);
        gauge.set(0);
        if( current_power > 0) {
            gauge.set(current_power); // set actual value
        } else {
        }
    }

    // WEATHER UPDATE
    // =================================================================
    // OPENWEATHERMAP

    $.ajax({
        type: "GET",
        url: "https://api.worldweatheronline.com/premium/v1/weather.ashx".concat("?key=7ec3bc2ef94e4bfa8b0101346172001&q=").concat(plant_location).concat("&num_of_day=1").concat("&format=json"),
        success: function(weather_data) {
            var temp = weather_data.data.current_condition[0].FeelsLikeC;
            $('#temperature').text(Math.round(temp).toString().concat(String.fromCharCode(176)));
            var max_temp = weather_data.data.weather[0].maxtempC;
            var min_temp = weather_data.data.weather[0].mintempC;
            $('#minmax').text(Math.round(max_temp).toString().concat(String.fromCharCode(176)).concat("/").concat(Math.round(min_temp).toString().concat(String.fromCharCode(176))));
            var wind = "";
            if(plant_slug == "uran" || plant_slug == "rrkabel") {
                wind = weather_data.data.current_condition[0].windspeedKmph;
                $('#windspeed').text(Math.round(wind).toString().concat("kmph"));         
            } else if(plant_slug == "unipatch") {
                windspeed_unipatch = 1;
            } else {
                wind = weather_data.data.current_condition[0].windspeedMiles;
                $('#windspeed').text(Math.round(wind).toString().concat("mph"));
            }
            var clouds_description = weather_data.data.current_condition[0].weatherDesc[0].value;
            $('#comments').text(clouds_description);
            var precipitation = weather_data.data.current_condition[0].precipMM;
            $('#precipitation').text((precipitation).toString());
        },
        error: function(weather_data){
            console.log("no data");
        }
    });

    limit_plant_future_date();
    /*limit_plant_future_energy_month_date();*/

    var dates = get_dates();
    var st = dates[0];
    var et = dates[1];
    /*power_data(plant_slug, st, et, 'power_chart', sourcekey);*/

    power_irradiation_data(plant_slug, st, et);

    start_year();

    if(plant_slug == 'uran' || plant_slug == 'rrkabel' || plant_slug == 'unipatch') {
        year_energy_data();
    }

    inverters_status_chart();
    setInterval(function () {
        inverters_status_chart();
        power_irradiation_data(plant_slug, st, et);
    }, 1000*60);

    var month = ["January", "February", "March", "April", "May", "June",
      "July", "August", "September", "October", "November", "December"
    ];
    var d = new Date();
    var date = d.getDate();

    if(date == 1 || date == 21 || date == 31) {
        date = date + "<sup>st</sup>";
    } else if(date == 2 || date == 22) {
        date = date + "<sup>nd</sup>";
    } else if(date == 3 || date == 23) {
        date = date + "<sup>rd</sup>";
    } else {
        date = date + "<sup>th</sup>";
    }

    $("#date_today_generation").append("(" + date + " " + month[d.getMonth()] + ", " + d.getFullYear() + ")");

    sparkline_bar_chart();

    residuals_bar_chart();

    if(plant_slug == "palladam" || plant_slug == "waaneep") {
        energy_prediction();
    }
    
});

$(function() {
    $(".datetimepicker_start").datetimepicker({
        timepicker: false,
        format: 'Y/m/d',
        scrollMonth:false,
        scrollTime:false,
        scrollInput:false
    });
    $(".datetimepicker_start").on('change', function(ev) {
        $(this).datetimepicker('hide');
    });
});

$(function() {
    $(".datetimepicker_start_week").datetimepicker({
        timepicker: false,
        format: 'Y/m/d',
        scrollMonth:false,
        scrollTime:false,
        scrollInput:false
    });
    $(".datetimepicker_start_week").on('change', function(ev) {
        $(this).datetimepicker('hide');
    });
});

$(function() {
    $("#start_energy_month").MonthPicker({
        Button: false
    });
});

/*$(function() {
    $("#start_energy_week").datePicker({selectWeek:true,closeOnSelect:false});
});*/

$(function() {
    $('#start_energy_week').datepicker({onSelect: function() {
        var mon = $(this).datepicker('getDate');
        mon.setDate(mon.getDate() + 1 - (mon.getDay() || 7));
        var sun = new Date(mon.getTime());
        sun.setDate(sun.getDate() + 6);
        mon = dateFormat(mon, "yyyy/mm/dd");
        sun = dateFormat(sun, "yyyy/mm/dd");
        $("#week_range").empty();
        $("#week_range").append(mon + " - " + sun);
        /*alert(mon + ' ' + sun);*/
    }});
});

function limit_plant_future_date() {
    $(function(){
        $('#start').datetimepicker({
            onShow:function( ct ){
                this.setOptions({
                    maxDate: new Date()
                })
            }
        });
    });
  }

/*function limit_plant_future_energy_month_date() {
    $(function(){
        $('#start_energy_month').datetimepicker({
            onShow:function( ct ){
                this.setOptions({
                    maxDate: new Date()
                })
            }
        });
    });
  }*/

  function get_dates_last_2week(){

    // get the end date as the selected/today's date
    var etw = new Date();
    /*if (etw == '') {
        etw = new Date();
    } else {
        etw = new Date(etw);
    }*/
    // add a day in etw
    // prepare a start date
    var stw = new Date(etw.getTime());
    etw = new Date(etw.setDate(etw.getDate() + 1));
    stw = new Date(stw.setDate(etw.getDate() - 14));
    // convert them into strings
    stw = dateFormat(stw, "yyyy-mm-dd");
    etw = dateFormat(etw, "yyyy-mm-dd");

    return [stw, etw];
}

function last_weeks_energy_data() {

    if(plant_slug == 'chemtrolsd') {

        $("#demo-sparkline-line").empty();
        $("#demo-sparkline-line").append("<div id='chemtrolsd_temperature' class='text-semibold'></div>");
        $('#chemtrolsd_temperature').append("Temperature : 25" + String.fromCharCode(176) + "C");
        $("#demo-sparkline-line").append("<div id='chemtrolsd_humidity' class='text-semibold'></div>");
        $("#chemtrolsd_humidity").append("Humidity : 80%");
        return;

    }

    var dates = get_dates_last_2week();
    var st = dates[0];
    var et = dates[1];

    $.ajax({
        type: "GET",
        url: "/api/solar/plants/".concat(plant_slug).concat('/energy/'),
        data: {startTime: (st), endTime: (et), aggregator: "DAY"},
        success: function(data) {
            if(data == '') {
                $("#demo-sparkline-line").empty();
                $("#demo-sparkline-line").append("<div>No data for last 2 weeks.</div>");
                return;
            } else {
                $("#demo-sparkline-line").empty();
                $("#demo-sparkline-line").append("<svg></svg>");
            }

            var energy_values = [];
            var date_values = [];

            // populate the data array and calculate the day_energy
            for(var n = 0; n < data.length; n++) {
                energy_values.push(parseFloat(data[n].energy));
                date_values.push(new Date(data[n].timestamp));
            }
            
            // plot the chart
            sparkline_energy_chart_last_2week(st, et, energy_values, date_values);
        },
        error: function(data) {
            console.log("error_streams_data");
            data = null;
        }
    });
}

    function get_week_dates(){
        // get the end date as the selected/today's date

        var today = new Date();
        var mon = new Date();
        mon.setDate(mon.getDate() + 1 - (mon.getDay() || 7));
        var sun = new Date(mon.getTime());
        sun.setDate(sun.getDate() + 6);
        mon = dateFormat(mon, "yyyy-mm-dd");
        sun = dateFormat(sun, "yyyy-mm-dd");

        return [mon, sun];
    }

    function sparkline_bar_chart() {

        var dates = get_dates_last_2week();
        st = dates[0];
        e = dates[1];
        
        $.ajax({
            type: "GET",
            url: "/api/solar/plants/".concat(plant_slug).concat('/performance/'),
            data: {startTime: (st), endTime: (e), aggregator: "DAY"},
            success: function(pr_week) {
                if(pr_week == '') {
                    $("#pr_bar").empty();
                    $("#pr_bar").append("<div>No PR for the week.</div>");
                    return;
                } else {
                    $("#pr_bar").empty();
                    $("#pr_bar").append("<svg></svg>");
                }

                var pr_value = [];
                var date = [];

                for(var i = pr_week.length - 1; i >= 0; i--) {

                    if(plant_slug == "uran" || plant_slug == "rrkabel" || plant_slug == "unipatch" || plant_slug == "waaneep" || plant_slug == "growels" || plant_slug == "raheja") {
                        pr_value.push((parseFloat(pr_week[i].performance_ratio) * 100).toFixed(2));
                    } else {
                        pr_value.push((parseFloat(pr_week[i].performance_ratio)).toFixed(2));
                    }

                    date.push(new Date(pr_week[i].timestamp));

                }

                performance_ratio_bar_chart_sparkline(st, e, pr_value, date);

            },
            error: function(data) {
                console.log("error_streams_data");
                data = null;
            }
        });
    }

    function performance_ratio_bar_chart_sparkline(st, e, pr_value, date_values) {
        var barEl = $("#pr_bar");
        var barValues = pr_value;
        var barValueCount = barValues.length;
        var barSpacing = 1;

        var height_chart = 0;

        if(status_data.pvsyst_generation && status_data.pvsyst_pr) {
            height_chart = 31;
        } else {
            height_chart = 64;
        }

        height_chart = height_chart.toString();

        barEl.sparkline(barValues, {
            type: 'bar',
            height: height_chart,
            barWidth: Math.round((barEl.parent().width() - ( barValueCount - 1 ) * barSpacing ) / barValueCount),
            barSpacing: barSpacing,
            zeroAxis: false,
            tooltipChartTitle: 'Performance Ratio',
            tooltipSuffix: '',
            barColor: 'rgba(255,255,255,.7)',
            tooltipFormatter: function(sparkline, options, field) {
                if(plant_slug == "uran" || plant_slug == "rrkabel" || plant_slug == "unipatch" || plant_slug == "waaneep" || plant_slug == "growels" || plant_slug == "raheja") {

                    return 'Performance Ratio for ' + date_values[field[0].offset].format("dd/mm/yyyy") + " : " + field[0].value.toFixed(2) + "%";

                } else {

                    return 'Performance Ratio for ' + date_values[field[0].offset].format("dd/mm/yyyy") + " : " + field[0].value.toFixed(2);

                }
            }
        });

    }

    function sparkline_energy_chart_last_2week(st, et, energy_values, date_values){

        $("#demo-sparkline-line").sparkline(energy_values, {
            type: 'line',
            width: '100%',
            height: '40',
            spotRadius: 2,
            lineWidth:2,
            lineColor:'#ffffff',
            fillColor: false,
            minSpotColor :false,
            maxSpotColor : false,
            highlightLineColor : '#ffffff',
            highlightSpotColor: '#ffffff',
            tooltipChartTitle: 'Energy',
            tooltipPrefix :'kWh - ',
            spotColor:'#ffffff',
            valueSpots : {
                '0:': '#ffffff'
            },
            tooltipFormatter: function(sparkline, options, field) {
                return date_values[field.x].format("dd/mm/yyyy") + " : " + field.y.toFixed(2) + " kWh";
            }
        });
    }

function redraw_window() {
    $('a[data-toggle="tab"]').on('shown.bs.tab', function (e) {
        window.dispatchEvent(new Event('resize'));
    });
  }


function get_dates_energy_week(id){
    // get the start date
    var st = $(id).val();
    /*var st = new Date();*/
    if (st == '')
        st = new Date();
    else
        st = new Date(st);
    // prepare an end date
    var e = new Date(st.getTime());
    e = new Date(e.setDate(st.getDate() + 1));
    // convert them into strings

    st = dateFormat(st, "yyyy-mm-dd");
    e = dateFormat(e, "yyyy-mm-dd");

    /*st = convert_date_format_to(st);
    e = convert_date_format_to(e);*/

    return [st, e];
}

function get_dates_week(){
    // get the end date as the selected/today's date
    var etw = $('#start_week').val();
    if (etw == '') {
        etw = new Date();
    } else {
        etw = new Date(etw);
    }
    // add a day in etw
    etw.setDate(etw.getDate() + 1);
    // prepare a start date
    var stw = new Date(etw.getTime());
    stw = new Date(stw.setDate(etw.getDate() - 7));
    // convert them into strings
    stw = dateFormat(stw, "yyyy-mm-dd");
    etw = dateFormat(etw, "yyyy-mm-dd");
    return [stw, etw];
}

function get_month_dates(){
    // get the end date as the selected/today's date
    var etw = $('#start_energy_month').val();

    if (etw == '') {
        etw = new Date();
        etw.setMonth(etw.getMonth()+1);
        etw.setDate(0);
        // prepare a start date
        var stw = new Date(etw.getTime());
        stw = new Date(stw.setDate(01));

        stw = dateFormat(stw, "yyyy-mm-dd");
        etw = dateFormat(etw, "yyyy-mm-dd");
    } else {
        var e = etw.split("/");
        var stw = e[1] + "-" + e[0] + "-" + "01";
        var date = new Date(stw);
        var lastDay = new Date(date.getFullYear(), date.getMonth() + 1, 0);
        etw = e[1] + "-" + e[0] + "-" + lastDay.getDate();
    }

    return [stw, etw];
}

function residuals_bar_chart() {

    $.ajax({
        type: "GET",
        url: "/api/v1/solar/plants/".concat(plant_slug).concat('/summary/'),
        success: function(summary_data){
            if(summary_data.past_kwh_per_meter_square) {
                $("#insolation").empty();
                $("#insolation").append(summary_data.past_kwh_per_meter_square[(summary_data.past_kwh_per_meter_square.length)-1].kwh_value);

                var insolation_dates = [], insolation_values = [];

                for(var i = 0; i < summary_data.past_kwh_per_meter_square.length; i++) {
                    var insolation_timestamps = new Date(summary_data.past_kwh_per_meter_square[i].timestamp);
                    insolation_timestamps = dateFormat(insolation_timestamps, "mmm dd, yyyy");
                    insolation_dates.push(insolation_timestamps);
                    insolation_values.push(parseFloat(summary_data.past_kwh_per_meter_square[i].kwh_value));
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
            }

            if(!summary_data.residual) {
                $("#residualstab").hide();
                $("#residuals-lft").hide();

            } else { 
                $("#residuals_bar").empty();
                $("#residuals_bar").append("<svg style='float: left;'></svg>")

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
        },
        error: function(data){
            console.log("no data");
            
            $("#residuals_bar").empty();
            $("#residuals_bar").append("<div class='alert alert-warning' id='alert'>No data for groups.</div>");
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

function energy_prediction() {

    /*$.ajax({
        type: "GET",
        url: "/api/v1/solar/plants/".concat(plant_slug).concat('/summary/'),
        success: function(summary_data){
            if(!summary_data.residual) {
                $("#energy_prediction_chart").empty();
                $("#energy_prediction_chart").append("<div class='alert alert-warning' id='alert'>No data for Inverter Residuals for last 1 week.</div>");

            } else {

                

            }
        },
        error: function(data){
            console.log("no data");
            
            $("#energy_prediction_chart").empty();
            $("#energy_prediction_chart").append("<div class='alert alert-warning' id='alert'>No data for Inverter Residuals for last 1 week.</div>");
        }
    });*/
    
    var data = [];
    var original_data = [];

    if(plant_slug == "palladam") {
            data = [
            {
                "timestamp": "2016-12-02T00:30:00Z",
                "energy": 30.76
            }, {
                "timestamp": "2016-12-02T01:30:00Z",
                "energy": 142.07
            }, {
                "timestamp": "2016-12-02T02:30:00Z",
                "energy": 305.24
            }, {
                "timestamp": "2016-12-02T03:30:00Z",
                "energy": 450.07
            }, {
                "timestamp": "2016-12-02T04:30:00Z",
                "energy": 532.92
            }, {
                "timestamp": "2016-12-02T05:30:00Z",
                "energy": 587.67
            }, {
                "timestamp": "2016-12-02T06:30:00Z",
                "energy": 581.84
            }, {
                "timestamp": "2016-12-02T07:30:00Z",
                "energy": 544.69
            }, {
                "timestamp": "2016-12-02T08:30:00Z",
                "energy": 470.53
            }, {
                "timestamp": "2016-12-02T09:30:00Z",
                "energy": 350.56
            }, {
                "timestamp": "2016-12-02T10:30:00Z",
                "energy": 208.97
            }, {
                "timestamp": "2016-12-02T11:30:00Z",
                "energy": 75.99
            }, {
                "timestamp": "2016-12-02T12:30:00Z",
                "energy": 9.02
            }
        ];

        original_data =  [
            {
                "energy": "NA",
                "timestamp": "2016-12-02T00:30:00Z"
            },
            {
                "energy": "NA",
                "timestamp": "2016-12-02T01:30:00Z"
            },
            {
                "energy": "NA",
                "timestamp": "2016-12-02T02:30:00Z"
            },
            {
                "energy": "NA",
                "timestamp": "2016-12-02T03:30:00Z"
            },
            {
                "energy": "NA",
                "timestamp": "2016-12-02T04:30:00Z"
            },
            {
                "energy": "NA",
                "timestamp": "2016-12-02T05:30:00Z"
            },
            {
                "energy": "NA",
                "timestamp": "2016-12-02T06:30:00Z"
            },
            {
                "energy": "NA",
                "timestamp": "2016-12-02T07:30:00Z"
            },
            {
                "energy": "NA",
                "timestamp": "2016-12-02T08:30:00Z"
            },
            {
                "energy": "NA",
                "timestamp": "2016-12-02T09:30:00Z"
            },
            {
                "energy": "NA",
                "timestamp": "2016-12-02T10:30:00Z"
            },
            {
                "energy": "NA",
                "timestamp": "2016-12-02T11:30:00Z"
            },
            {
                "energy": "NA",
                "timestamp": "2016-12-02T12:30:00Z"
            },
            {
                "energy": "NA",
                "timestamp": "2016-12-02T13:30:00Z"
            }
        ];

    } else if(plant_slug == "waaneep") {
        data = [
            {
                "timestamp": "2016-12-02T00:30:00Z",
                "energy": 160
            }, {
                "timestamp": "2016-12-02T01:30:00Z",
                "energy": 2826
            }, {
                "timestamp": "2016-12-02T02:30:00Z",
                "energy": 19876
            }, {
                "timestamp": "2016-12-02T03:30:00Z",
                "energy": 32942.52
            }, {
                "timestamp": "2016-12-02T04:30:00Z",
                "energy": 37782.85
            }, {
                "timestamp": "2016-12-02T05:30:00Z",
                "energy": 40639.41
            }, {
                "timestamp": "2016-12-02T06:30:00Z",
                "energy": 41421.88
            }, {
                "timestamp": "2016-12-02T07:30:00Z",
                "energy": 38703.89
            }, {
                "timestamp": "2016-12-02T08:30:00Z",
                "energy": 33037.35
            }, {
                "timestamp": "2016-12-02T09:30:00Z",
                "energy": 24887.78
            }, {
                "timestamp": "2016-12-02T10:30:00Z",
                "energy": 12171.51
            }, {
                "timestamp": "2016-12-02T11:30:00Z",
                "energy": 4056.41
            }, {
                "timestamp": "2016-12-02T12:30:00Z",
                "energy": 214.96
            }
        ];

        original_data =  [
            {
                "energy": 0.0,
                "timestamp": "2016-12-02T00:30:00Z"
            },
            {
                "energy": 2426.0,
                "timestamp": "2016-12-02T01:30:00Z"
            },
            {
                "energy": 16396.0,
                "timestamp": "2016-12-02T02:30:00Z"
            },
            {
                "energy": 29178.0,
                "timestamp": "2016-12-02T03:30:00Z"
            },
            {
                "energy": 35389.0,
                "timestamp": "2016-12-02T04:30:00Z"
            },
            {
                "energy": 40777.0,
                "timestamp": "2016-12-02T05:30:00Z"
            },
            {
                "energy": 40895.0,
                "timestamp": "2016-12-02T06:30:00Z"
            },
            {
                "energy": 38489.0,
                "timestamp": "2016-12-02T07:30:00Z"
            },
            {
                "energy": 32747.0,
                "timestamp": "2016-12-02T08:30:00Z"
            },
            {
                "energy": "NA",
                "timestamp": "2016-12-02T09:30:00Z"
            },
            {
                "energy": "NA",
                "timestamp": "2016-12-02T10:30:00Z"
            },
            {
                "energy": "NA",
                "timestamp": "2016-12-02T11:30:00Z"
            },
            {
                "energy": "NA",
                "timestamp": "2016-12-02T12:30:00Z"
            },
            {
                "energy": "NA",
                "timestamp": "2016-12-02T13:30:00Z"
            }
        ];
    }
    
    
    var arrayData = [];
    var prediction_energy = []

    for(var n= 0; n < data.length ; n++) {
        var date = new Date(data[n].timestamp);
        date = dateFormat(date, "yyyy-mm-dd HH:MM:ss");
        arrayData.push({"x": date, "y": data[n].energy , "color": "#46bbdc"});
    }

    var packagedData = [];

    // package the data
    packagedData.push({
        "key": "ENERGY PREDICTION",
        "values": arrayData
    });

    var arrayData2 = [];
    var original_energy = []

    for(var n= 0; n < original_data.length ; n++) {
        var date = new Date(original_data[n].timestamp);
        date = dateFormat(date, "yyyy-mm-dd HH:MM:ss");
        arrayData2.push({"x": date, "y": original_data[n].energy , "color": "#91c957"});
    }

    // package the data
    packagedData.push({
        "key": "ORIGINAL ENERGY",
        "values": arrayData2
    });

    var svg1 = "energy_prediction_chart";
    var svg2 = "original_energy_chart";

    var chart_title1 = "Energy Predicted";
    var chart_title2 = "Original Energy";

    // plot the chart
    energy_prediction_bar_chart(packagedData, chart_title1, svg1);

}

function energy_prediction_bar_chart(packagedData, chart_title, svg_title){

    nv.addGraph(function() {
      var chart = nv.models.multiBarChart()
            /*#ff7f0e*/
            .color(['#46bbdc', '#91c957'])
            .margin({top: 5, right: 0, bottom: 68, left: 60})
            ;

        chart.yAxis
              .axisLabel("kWh")
              .tickFormat(d3.format(',.1f'));

        chart.xAxis
            .rotateLabels(-31)
            .tickFormat(function (d) {
                return d3.time.format('%I:%M %p')(new Date(d))
            });

        chart.tooltip.enabled(true);

      d3.select('#' + svg_title + ' svg')
          .datum(packagedData)
          .call(chart);

      nv.utils.windowResize(chart.update);

      return chart;
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

    if(data.solar_groups.length > 0) {
        groups_inverter_power(data);    
    } else {
        $("#group_powertab").hide();
    }

}

function groups_inverter_power(data) {

    var dates = get_dates();
    var st = dates[0];
    var et = dates[1];

    var groups_name = [];

    groups_name = data.solar_groups;
    groups_name = groups_name.toString();

    groupInvertersMultipleArray = [];

    $.ajax({
        type: "GET",
        url: "/api/solar/plants/".concat(plant_slug).concat('/groups-power/'),
        data: {startTime: (st), endTime: (et), groupNames: groups_name},
        success: function(group_power){
            if(group_power == "") {
                $("#group_power_chart").empty();
                $("#group_power_chart").append("<div class='alert alert-warning' id='alert'>No data for groups.</div>");

            } else { 
                $("#group_power_chart").empty();
                $("#group_power_chart").append("<svg style='float: left;'></svg>")

                for (var i = 0; i < data.solar_groups.length; i++) {
                    arrayData = [];
                    for (var j = 0; j < group_power.length; j++) {
                        var d = new Date(group_power[j].timestamp);
                        var date = d.getTime();
                        var date_form_api = new Date(date);

                        var val_dt = 0;

                        if(group_power[j].hasOwnProperty(data.solar_groups[i])) {
                            if(group_power[j][data.solar_groups[i]] != null) {
                                val_dt = parseFloat(group_power[j][data.solar_groups[i]]);   
                            } else {
                                val_dt = null;
                            }
                        } else {
                            val_dt = null;
                        }
                        arrayData.push({x: date_form_api, y: val_dt});
                    }
                    groupInvertersMultipleArray.push({
                        "key": data.solar_groups[i],
                        "values": arrayData
                    });
                }

                group_power_multiple_line_chart(groupInvertersMultipleArray);

            }
        },
        error: function(data){
            console.log("no data");
            
            $("#group_power_chart").empty();
            $("#group_power_chart").append("<div class='alert alert-warning' id='alert'>No data for groups.</div>");
        }
    });

}

function group_power_multiple_line_chart(packagedData) {
    $("#multiple_line_chart").empty();
    $("#multiple_line_chart").append("<svg style='float: left;'></svg>")

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

        d3.select('#group_power_chart svg')
                .datum(packagedData)
                .call(line_chart);

        nv.utils.windowResize(function() { line_chart.update() });
    });
}

function inverters_status_chart() {

    $.ajax({
        type: "GET",
        url: "/api/solar/plants/".concat(plant_slug).concat('/status/'),
        success: function(data) {
            
            console.log(data);

            status_data = data;

            var inverters_len = Object.keys(data.inverters).length;
            var present_time = new Date();
            present_time = dateFormat(present_time, "dd-mm-yyyy HH:MM");
            $("#present_time").empty();
            $("#present_time").append("(Last Updated : " + present_time + ")");

            /*if (inverters_len < 9) {*/

            var total_generation = data.plant_total_energy;
            $("#total_generation").text(((total_generation)));

            var irradiation = data.irradiation;
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

            var module_temperature = data.module_temperature;

            if(plant_slug == "uran" || plant_slug == "rrkabel" || plant_slug == "unipatch") {
                if(module_temperature != undefined && module_temperature != "NA" && module_temperature != 0 && module_temperature != 0.0) {
                    $('#module_temp').empty();
                    $('#module_temp').show();
                    $('#module_temp').append('Module Temp. : <span id="module_temperature"> </span>')
                    $('#module_temperature').text(Math.round(parseFloat(module_temperature)).toString().concat(String.fromCharCode(176)).concat("C"));
                } else {
                    $('#module_temp').hide();
                    $('#module_temp').empty();
                }    
            } else {
                if(module_temperature != undefined && module_temperature != "NA") {
                    $('#module_temp').empty();
                    $('#module_temp').show();
                    $('#module_temp').append('Module Temp. : <span id="module_temperature"> </span>');
                    $('#module_temperature').text(Math.round(parseFloat(module_temperature)).toString().concat(String.fromCharCode(176)).concat("C"));
                } else {
                    $('#module_temp').empty();
                    $('#module_temp').hide();
                    $('#module_temperature').text("NA");
                }
            }

            var performance_ratio = data.performance_ratio;

            performance_ratio = (parseInt(performance_ratio * 100.0)).toString() + "%";

            if(performance_ratio != undefined && performance_ratio != "NA") {
                $('#performance_ratio').text(performance_ratio);
            } else {
                $('#performance_ratio').text("NA");
            }

            if (plant_slug != 'uran' && plant_slug != 'rrkabel' && plant_slug != 'unipatch') {
                var current_power = data.current_power;
                if(current_power != undefined && current_power != "NA") {
                    $("#demo-gauge-text").text((parseFloat(current_power)).toFixed(2).toString().concat(" kW"));
                    gauge.set(current_power); // set actual value
                }
            }

            var plant_generation_today = data.plant_generation_today;
            if(plant_generation_today != undefined && plant_generation_today != "NA") {
                $("#generation_today").text(plant_generation_today);
                var co2 = data.plant_co2;
                $("#co2_savings").text(co2);
            } else {
                $("#co2_savings").text((0.00).toString().concat(" Kg"));
            }

            if(windspeed_unipatch == 1) {
                var wind = data.windspeed;
                $('#windspeed').text((parseFloat(wind)).toFixed(2).toString().concat("kmph"));
            }

            var ut = data.unacknowledged_tickets;
            var ot = data.open_tickets;
            var ct = data.closed_tickets;
            $("#unacknowledged_tickets").text(ut);
            $("#open_tickets").text(ot);
            $("#closed_tickets").text(ct);

            if (plant_slug != 'uran' && plant_slug != 'rrkabel' && plant_slug != 'unipatch') {
                
                if(data.pvsyst_generation) {
                    $("#generation_expected").show();
                    $("#generation_expected_div").show();
                    $("#generation_expected").text("/".concat((parseFloat(data.pvsyst_generation)).toFixed(2).toString()));
                } else {
                    $("#generation_expected").hide();
                    $("#generation_expected_div").hide();
                }

                if(data.pvsyst_tilt_angle) {
                    $("#pvsyst_tilt_angle").show();
                    $("#pvsyst_tilt_angle_div").show();
                    $("#pvsyst_tilt_angle").text("/".concat((parseFloat(data.pvsyst_tilt_angle)).toString().concat(String.fromCharCode(176))));
                } else {
                    $("#pvsyst_tilt_angle").hide();
                    $("#pvsyst_tilt_angle_div").hide();
                }

                if(data.pvsyst_generation) {
                    $("#generation_expected").show();
                    $("#generation_expected_div").show();
                    $("#generation_expected").text("/".concat((parseFloat(data.pvsyst_generation)).toFixed(2).toString()));
                } else {
                    $("#generation_expected").hide();
                    $("#generation_expected_div").hide();
                }

                if(data.pvsyst_pr) {
                    var expected_performance = parseInt(data.pvsyst_pr * 100);
                    $("#expected_performance_ratio").show();
                    $("#expected_performance_ratio_div").show();
                    $("#expected_performance_ratio").text("/".concat(expected_performance).toString().concat("%"));
                } else {
                    $("#expected_performance_ratio").hide();
                    $("#expected_performance_ratio_div").hide();
                }
            }

            var cuf = parseInt(data.cuf*100);

            $("#cuf_value").empty();
            $("#cuf_value").text((cuf).toString().concat("%"));

            if (plant_slug != 'uran' && plant_slug != 'rrkabel' && plant_slug != 'unipatch') {
                
                var inverters_connected = 0;
                var inverters_disconnected = 0;

                for(var i = 0; i < data.inverters.length; i++) {

                    if(data.inverters[i].connected == "connected") {

                        inverters_connected++;

                    } else if(data.inverters[i].connected == "disconnected") {

                        inverters_disconnected++;

                    }

                }

                $("#devices_disconnected").empty();
                $("#devices_disconnected").append("<i class='fa fa-times' aria-hidden='true'></i> : " + inverters_disconnected + " Disconnected");

                $("#devices_connected").empty();
                $("#devices_connected").append("<i class='fa fa-check' aria-hidden='true'></i> : " + inverters_connected + " Connected");

            }

            if(plant_slug == "palladam" || plant_slug == "thuraiyur") {
                return plot_labels_orientation_seven(data, 7);
            } else {
                return plot_labels_orientation(data, 5);
            }
            

            /*
            } else {
                var labels_div = $('#inverter_status');
                labels_div.innerHTML = "";
<<<<<<< HEAD
            }

            var arrayData = [];
            var n_charts = 1;
=======
                var svg = $('<svg> </svg>');
                labels_div.append(svg);
            }*/

            /*var arrayData = [];
>>>>>>> plant_dashboard
            for (var inverter_name in data.inverters) {
                if (data.inverters.hasOwnProperty(inverter_name)) {
                    console.log(data.inverters[inverter_name]);
                    var generation = data.inverters[inverter_name].generation/1000.0;
                    if (data.inverters[inverter_name].connected == true)
                        arrayData.push({"label": inverter_name, "value": generation.toFixed(2), "color": "#91c957"});
                    else
                        arrayData.push({"label": inverter_name, "value": generation.toFixed(2), "color": "#f76549"});
                }

                if (arrayData.length > 10) {
                    var svg = $('<div id=chart_' + n_charts + '><svg> </svg></div>');
                    labels_div.append(svg);

                    var packagedData = [{
                        "key": "Inverters Status",
                        "values": arrayData
                    }];
                    inverter_bar_chart('#chart_' + n_charts + ' svg', packagedData);
                    arrayData = [];
                    n_charts = n_charts + 1;
                }
            }

            if (arrayData.length > 0) {
                var svg = $('<div id=chart_' + n_charts + '><svg> </svg></div>');
                labels_div.append(svg);

                var packagedData = [{
                    "key": "Inverters Status",
                    "values": arrayData
                }];
                inverter_bar_chart('#chart_' + n_charts + ' svg', packagedData);
            }
<<<<<<< HEAD
=======
            var packagedData = [{
                "key": "Inverters Status",
                "values": arrayData
            }];
            inverter_bar_chart(packagedData);
>>>>>>> plant_dashboard*/
        },
        error: function(data) {
            console.log("error_streams_data");
            data = null;
        }
    });
}
function inverter_bar_chart(svg, packagedData){
    nv.addGraph(function() {
        var chart = nv.models.discreteBarChart()
            .x(function(d) { return d.label })    //Specify the data accessors.
            .y(function(d) { return d.value })
            .showValues(true)
                .showYAxis(false)
                .showXAxis(true)
            .margin({top: 5, right: 0, bottom: 70, left: 35})
            .tooltipContent(function(key, y, e, graph) {
                if(key.data.value !=  '0') {
                    return '<p>' + key.data.label + " : " + key.data.value + ' MWh' + '</p>' ;
                }
            })
          ;

        chart.xAxis
            .rotateLabels(0);

        d3.select(svg)
          .datum(packagedData)
          .call(chart);

        nv.utils.windowResize(chart.update);

        return chart;
    });
}

function power_irradiation_data(plant_slug, st, et) {

    $.ajax({
        type: "GET",
        url: "/api/solar/plants/".concat(plant_slug).concat('/irradiation-power/'),
        data: {startTime: (st), endTime: (et)},
        success: function(data) {
            if(data == '') {
                $("#no_data_power_value").empty();
                $("#power_chart").empty();
                $("#power_chart").append("<div class='alert alert-warning'> No power for the date </div>");

                $(".plant-power-generation h2").empty();
                return;
            } else {
                $("#power_chart").empty();
                $("#power_chart").append("<svg></svg>");
            }

            var arrayData = [];

            var irradiation_reading = 0;

            // populate the data array and calculate the day_energy
            for(var n= data.length-1; n >=0 ; n--) {
                if(data[n].power > 0) {
                    var local_values = [];
                    var ts = new Date(data[n].timestamp);

                    local_values.push([ts, 0.0]);
                    if(data[n].irradiation != null) {
                        if(plant_slug == "uran" || plant_slug == "rrkabel" || plant_slug == "unipatch" || plant_slug == "waaneep" || plant_slug == "growels" || plant_slug == "raheja") {
                            local_values.push([new Date(ts.setSeconds(ts.getSeconds() + 1)), parseFloat(data[n].power), parseFloat(data[n].irradiation * 1000)]);
                        } else {
                            local_values.push([new Date(ts.setSeconds(ts.getSeconds() + 1)), parseFloat(data[n].power), parseFloat(data[n].irradiation)]);
                        }
                    } else {
                        local_values.push([new Date(ts.setSeconds(ts.getSeconds() + 1)), parseFloat(data[n].power), "NA"]);
                    }
                    arrayData.push({"values": local_values,
                                "key": dateFormat(data[n].timestamp, 'yyyy-mm-dd HH:MM:ss').concat(" : ").concat(parseFloat(data[n].power).toString()),
                                "color":"#4C85AB"});    
                }
            }

            if(plant_slug == "uran" || plant_slug == "rrkabel" || plant_slug == "unipatch" || plant_slug == "waaneep" || plant_slug == "growels" || plant_slug == "raheja") {
                irradiation_reading = "W/m".concat(String.fromCharCode(178));
            } else {
                irradiation_reading = "kW/m".concat(String.fromCharCode(178));
            }

            plant_irradiation_power_generation_chart(st, arrayData, irradiation_reading);

        },
        error: function(data) {
            console.log("error_streams_data");
            data = null;
        }
    });

}

function plant_irradiation_power_generation_chart(st, data, irradiation_reading) {
    $(".plant-power-generation h2").empty();
    $("#power_chart.svg.nvd3-svg").empty();

        nv.addGraph(function () {
            live_chart = nv.models.lineChart()
                .x(function (d) { return d[0] })
                .y(function (d) { return d[1] })
                .showYAxis(true)
                .showLegend(false)
                .showXAxis(true)
                .useInteractiveGuideline(false)
                .margin({top: 5, right: 44, bottom: 20, left: 65})
                .tooltipContent(function(key, y, e, graph) {
                    if(key.point[1] != 0) {
                        if(key.point[2] == "NA") {
                            return '<h4>' + key.point[0].format("dd/mm/yyyy HH:MM") + "</h4>\n<h6>Power : " + key.point[1].toFixed(2) + ' kW' + '</h6>\n<h6>Irradiation : NA </h6>';
                        } else {
                            return '<h4>' + key.point[0].format("dd/mm/yyyy HH:MM") + "</h4>\n<h6>Power : " + key.point[1].toFixed(2) + ' kW' + '</h6>\n<h6>Irradiation : ' + key.point[2].toFixed(2) + irradiation_reading + "</h6>";
                        }
                    }
                });

            live_chart.interactiveLayer.tooltip
                  .headerFormatter(function(d, i) {
                    return nv.models.axis().tickFormat()(d, i);
            });

            live_chart.xAxis
                .showMaxMin(true)
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
            d3.select("#power_chart svg")
                      .datum(data)
                      .call(live_chart);
            nv.utils.windowResize(live_chart.update);
            return live_chart;
        });

        /*d3.select('#power_chart svg').empty();
        d3.select('#power_chart svg')
              .datum(data)
              .call(live_chart);
        nv.utils.windowResize(live_chart.update);*/
    }

/*Power Data for a week*/

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