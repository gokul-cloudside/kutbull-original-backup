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

$(document).ready(function() {
    // GAUGE PLUGIN
    // =================================================================
    // Require Gauge.js
    // -----------------------------------------------------------------
    // http://bernii.github.io/gauge.js/
    // =================================================================

    // WEATHER UPDATE
    // =================================================================
    // OPENWEATHERMAP

    $.ajax({
        type: "GET",
        url: "https://api.worldweatheronline.com/premium/v1/weather.ashx".concat("?key=251e1fb4e5d04bde99c65144162009&q=").concat(plant_location).concat("&num_of_day=1").concat("&format=json"),
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

    plant_summary();
    setInterval(function () {
        plant_summary();
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

    function sparkline_bar_chart(pr_week) {

        if(pr_week == '' || !pr_week) {
            $("#pr_bar").empty();
            $("#pr_bar").append("<div>No PR for the week.</div>");
            return;
        } else {
            $("#pr_bar").empty();
            $("#pr_bar").append("<svg></svg>");
        }

        var pr_value = [];
        var date = [];

        for(var i = 0; i < pr_week.length; i++) {

            if(plant_slug == "uran" || plant_slug == "rrkabel" || plant_slug == "unipatch" || plant_slug == "waaneep" || plant_slug == "growels" || plant_slug == "raheja") {
                pr_value.push((parseFloat(pr_week[i].pr) * 100).toFixed(2));
            } else {
                pr_value.push((parseFloat(pr_week[i].pr)).toFixed(2));
            }

            date.push(new Date(pr_week[i].timestamp));

        }

        performance_ratio_bar_chart_sparkline(st, e, pr_value, date);

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
    var block_color = "";
    var block_style = "";
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
                    block_color = '';
                    block_style = 'width: 150px; background-color:#f3f307;';
                } else {
                    block_color = 'btn-success';
                    block_style = 'width: 150px;';
                }
            } else if (data.inverters[i].connected == "disconnected") {
                block_color = 'btn-danger';
                block_style = 'width: 150px;';
            }
            else {
                block_color = 'btn-info';
                block_style = 'width: 150px;';
            }

            var success = $('<div class="col-lg-2 pad-all" id="div'+d_north+'" style="text-align:center;"> ' +
                '<div class="row"> ' + '<div class="col-lg-1"></div>' + '<strong>' + data.inverters[i].name + '</strong>' + ' </div> ' +
                '<button class="btn btn-lg '+block_color+' mar-lft" inverter_number="'+i+'" id="inverter_button_value_'+i+'" style="'+block_style+'">' + generation.toFixed(2) +
                ' kWh </button>' + '<div class="row"> ' + '<div class="col-lg-1"></div>' + '<strong>' + current_power.toFixed(2) + ' kW</strong>' + ' </div> ' + '</div>');
            $("#north-row"+north_row_count).append(success);

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
                    block_color = '';
                    block_style = 'width: 150px; background-color:#f3f307;';
                } else {
                    block_color = 'btn-success';
                    block_style = 'width: 150px;';
                }
            } else if (data.inverters[i].connected == "disconnected") {
                block_color = 'btn-danger';
                block_style = 'width: 150px;';
            }
            else {
                block_color = 'btn-info';
                block_style = 'width: 150px;';
            }

            var success = $('<div class="col-lg-2 pad-all" id="div'+d_south+'" style="text-align:center;"> ' +
                '<div class="row"> ' + '<div class="col-lg-1"></div>' + '<strong>' + data.inverters[i].name + '</strong>' + ' </div> ' +
                '<button class="btn btn-lg '+block_color+' mar-lft" inverter_number="'+i+'" id="inverter_button_value_'+i+'" style="'+block_style+'">' + generation.toFixed(2) +
                ' kWh </button>' + '<div class="row"> ' + '<div class="col-lg-1"></div>' + '<strong>' + current_power.toFixed(2) + ' kW</strong>' + ' </div> ' + '</div>');
            $("#south-row"+south_row_count).append(success);

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
                    block_color = '';
                    block_style = 'width: 150px; background-color:#f3f307;';
                } else {
                    block_color = 'btn-success';
                    block_style = 'width: 150px;';
                }
            } else if (data.inverters[i].connected == "disconnected") {
                block_color = 'btn-danger';
                block_style = 'width: 150px;';
            }
            else {
                block_color = 'btn-info';
                block_style = 'width: 150px;';
            }

            var success = $('<div class="col-lg-2 pad-all" id="div'+d_east+'" style="text-align:center;"> ' +
                '<div class="row"> ' + '<div class="col-lg-1"></div>' + '<strong>' + data.inverters[i].name + '</strong>' + ' </div> ' +
                '<button class="btn btn-lg '+block_color+' mar-lft" inverter_number="'+i+'" id="inverter_button_value_'+i+'" style="'+block_style+'">' + generation.toFixed(2) +
                ' kWh </button>' + '<div class="row"> ' + '<div class="col-lg-1"></div>' + '<strong>' + current_power.toFixed(2) + ' kW</strong>' + ' </div> ' + '</div>');
            $("#east_row"+east_row_count).append(success);

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
                    block_color = '';
                    block_style = 'width: 150px; background-color:#f3f307;';
                } else {
                    block_color = 'btn-success';
                    block_style = 'width: 150px;';
                }
            } else if (data.inverters[i].connected == "disconnected") {
                block_color = 'btn-danger';
                block_style = 'width: 150px;';
            }
            else {
                block_color = 'btn-info';
                block_style = 'width: 150px;';
            }

            var success = $('<div class="col-lg-2 pad-all" id="div'+d_west+'" style="text-align:center;"> ' +
                '<div class="row"> ' + '<div class="col-lg-1"></div>' + '<strong>' + data.inverters[i].name + '</strong>' + ' </div> ' +
                '<button class="btn btn-lg '+block_color+' mar-lft" inverter_number="'+i+'" id="inverter_button_value_'+i+'" style="'+block_style+'">' + generation.toFixed(2) +
                ' kWh </button>' + '<div class="row"> ' + '<div class="col-lg-1"></div>' + '<strong>' + current_power.toFixed(2) + ' kW</strong>' + ' </div> ' + '</div>');
            $("#west_row"+west_row_count).append(success);

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
                    block_color = '';
                    block_style = 'width: 150px; background-color:#f3f307;';
                } else {
                    block_color = 'btn-success';
                    block_style = 'width: 150px;';
                }
            } else if (data.inverters[i].connected == "disconnected") {
                block_color = 'btn-danger';
                block_style = 'width: 150px;';
            }
            else {
                block_color = 'btn-info';
                block_style = 'width: 150px;';
            }

            var success = $('<div class="col-lg-2 pad-all" id="div'+d_south_west+'" style="text-align:center;"> ' +
                '<div class="row"> ' + '<div class="col-lg-1"></div>' + '<strong>' + data.inverters[i].name + '</strong>' + ' </div> ' +
                '<button class="btn btn-lg '+block_color+' mar-lft" inverter_number="'+i+'" id="inverter_button_value_'+i+'" style="'+block_style+'">' + generation.toFixed(2) +
                ' kWh </button>' + '<div class="row"> ' + '<div class="col-lg-1"></div>' + '<strong>' + current_power.toFixed(2) + ' kW</strong>' + ' </div> ' + '</div>');
            $("#south_west_row"+south_west_row_count).append(success);

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
                    block_color = '';
                    block_style = 'width: 150px; background-color:#f3f307;';
                } else {
                    block_color = 'btn-success';
                    block_style = 'width: 150px;';
                }
            } else if (data.inverters[i].connected == "disconnected") {
                block_color = 'btn-danger';
                block_style = 'width: 150px;';
            }
            else {
                block_color = 'btn-info';
                block_style = 'width: 150px;';
            }

            var success = $('<div class="col-lg-2 pad-all" id="div'+d_east_west+'" style="text-align:center;"> ' +
                '<div class="row"> ' + '<div class="col-lg-1"></div>' + '<strong>' + data.inverters[i].name + '</strong>' + ' </div> ' +
                '<button class="btn btn-lg '+block_color+' mar-lft" inverter_number="'+i+'" id="inverter_button_value_'+i+'" style="'+block_style+'">' + generation.toFixed(2) +
                ' kWh </button>' + '<div class="row"> ' + '<div class="col-lg-1"></div>' + '<strong>' + current_power.toFixed(2) + ' kW</strong>' + ' </div> ' + '</div>');
            $("#east_west_row"+east_west_row_count).append(success);

            east_west_elements++;
            d_east_west++;
        }
        $("#inverter_button_value_"+i).click(function() {

            var inverter = $(this).attr('inverter_number');

            $("#inverter_name").empty();
            $("#inverter_name").append(inverter_name);

            $("#status_name").empty();
            $("#status_name").append("<div class='text-semibold'>Inverter Name : " + data.inverters[inverter].name + "</div>");
            $("#status_connected").empty();
            $("#status_connected").append("<div class='text-semibold'>Connection Status : " + data.inverters[inverter].connected + "</div>");
            $("#status_orientation").empty();
            $("#status_orientation").append("<div class='text-semibold'>Inverter Orientation : " + data.inverters[inverter].orientation + "</div>");
            $("#status_capacity").empty();
            $("#status_capacity").append("<div class='text-semibold'>Inverter Capacity : " + data.inverters[inverter].capacity + " kW</div>");
            $("#status_power").empty();
            $("#status_power").append("<div class='text-semibold'>Current Power : " + data.inverters[inverter].power + " kW</div>");
            $("#status_generation").empty();
            $("#status_generation").append("<div class='text-semibold'>Current Generation : " + data.inverters[inverter].generation + " kWh</div>");
            $("#status_total_yield").empty();
            $("#status_total_yield").append("<div class='text-semibold'>Total Yield : " + data.inverters[inverter].total_yield + " kWh</div>");
            $("#status_inside_temperature").empty();
            $("#status_inside_temperature").append("<div class='text-semibold'>Inside Temperature : " + data.inverters[inverter].inside_temperature + "</div>");
            $("#status_last_three_errors").empty();
            var last_three_errors_length = data.inverters[inverter].last_three_errors.length
            if(last_three_errors_length > 0) {
                $("#status_last_three_errors").append("<div class='text-semibold'>Last Three Errors : " + data.inverters[inverter].last_three_errors + "</div>");
            } else {
                $("#status_last_three_errors").append("<div class='text-semibold'>Last Three Errors : No Errors </div>");
            }

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
    var block_color = "";
    var block_style = "";
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
                    block_color = '';
                    block_style = 'background-color:#f3f307;';
                } else {
                    block_color = 'btn-success';
                    block_style = '';
                }
            } else if (data.inverters[i].connected == "disconnected") {
                block_color = 'btn-danger';
                block_style = '';
            }
            else {
                block_color = 'btn-info';
                block_style = '';
            }

            var success = $('<div class="col-lg-1 mar-top mar-btm" id="div'+d_north+'" style="text-align:center; padding-left:0px; padding-right:0px;"> ' +
                '<div class="row"> ' + '<div class="col-lg-1"></div>' + '<strong>' + data.inverters[i].name + '</strong>' + ' </div> ' +
                '<button class="btn btn-lg '+block_color+' mar-lft" inverter_number="'+i+'" id="inverter_button_value_'+i+'" style="'+block_style+'">' + generation.toFixed(2) +
                ' kWh </button>' + '<div class="row"> ' + '<div class="col-lg-1"></div>' + '<strong>' + current_power.toFixed(2) + ' kW</strong>' + ' </div> ' + '</div>');
            $("#north-row"+north_row_count).append(success);

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
                    block_color = '';
                    block_style = 'background-color:#f3f307;';
                } else {
                    block_color = 'btn-success';
                    block_style = '';
                }
                $("#south-row"+south_row_count).append(success);
            } else if (data.inverters[i].connected == "disconnected") {
                block_color = 'btn-danger';
                block_style = '';
            }
            else {
                block_color = 'btn-info';
                block_style = '';
            }

            var success = $('<div class="col-lg-1 mar-top mar-btm" id="div'+d_south+'" style="text-align:center; padding-left:0px; padding-right:0px;"> ' +
                '<div class="row"> ' + '<div class="col-lg-1"></div>' + '<strong>' + data.inverters[i].name + '</strong>' + ' </div> ' +
                '<button class="btn btn-lg '+block_color+' mar-lft" inverter_number="'+i+'" id="inverter_button_value_'+i+'" style="'+block_style+'">' + generation.toFixed(2) +
                ' kWh </button>' + '<div class="row"> ' + '<div class="col-lg-1"></div>' + '<strong>' + current_power.toFixed(2) + ' kW</strong>' + ' </div> ' + '</div>');
            $("#south-row"+south_row_count).append(success);

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
                    block_color = '';
                    block_style = 'background-color:#f3f307;';
                } else {
                    block_color = 'btn-success';
                    block_style = '';
                }
            } else if (data.inverters[i].connected == "disconnected") {
                block_color = 'btn-danger';
                block_style = '';
            }
            else {
                block_color = 'btn-info';
                block_style = '';
            }

            var success = $('<div class="col-lg-1 mar-top mar-btm" id="div'+d_east+'" style="text-align:center; padding-left:0px; padding-right:0px;"> ' +
                '<div class="row"> ' + '<div class="col-lg-1"></div>' + '<strong>' + data.inverters[i].name + '</strong>' + ' </div> ' +
                '<button class="btn btn-lg '+block_color+' mar-lft" inverter_number="'+i+'" id="inverter_button_value_'+i+'" style="'+block_style+'">' + generation.toFixed(2) +
                ' kWh </button>' + '<div class="row"> ' + '<div class="col-lg-1"></div>' + '<strong>' + current_power.toFixed(2) + ' kW</strong>' + ' </div> ' + '</div>');
            $("#east-row"+east_row_count).append(success);

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
                    block_color = '';
                    block_style = 'background-color:#f3f307;';
                } else {
                    block_color = 'btn-success';
                    block_style = '';
                }
            } else if (data.inverters[i].connected == "disconnected") {
                block_color = 'btn-danger';
                block_style = '';
            }
            else {
                block_color = 'btn-info';
                block_style = '';
            }

            var success = $('<div class="col-lg-1 mar-top mar-btm" id="div'+d_west+'" style="text-align:center; padding-left:0px; padding-right:0px;"> ' +
                '<div class="row"> ' + '<div class="col-lg-1"></div>' + '<strong>' + data.inverters[i].name + '</strong>' + ' </div> ' +
                '<button class="btn btn-lg '+block_color+' mar-lft" inverter_number="'+i+'" id="inverter_button_value_'+i+'" style="'+block_style+'">' + generation.toFixed(2) +
                ' kWh </button>' + '<div class="row"> ' + '<div class="col-lg-1"></div>' + '<strong>' + current_power.toFixed(2) + ' kW</strong>' + ' </div> ' + '</div>');
            $("#west_row"+west_row_count).append(success);

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
                    block_color = '';
                    block_style = 'background-color:#f3f307;';
                } else {
                    block_color = 'btn-success';
                    block_style = '';
                }
            } else if (data.inverters[i].connected == "disconnected") {
                block_color = 'btn-danger';
                block_style = '';
            }
            else {
                block_color = 'btn-info';
                block_style = '';
            }

            var success = $('<div class="col-lg-1 mar-top mar-btm" id="div'+d_south_west+'" style="text-align:center; padding-left:0px; padding-right:0px;"> ' +
                '<div class="row"> ' + '<div class="col-lg-1"></div>' + '<strong>' + data.inverters[i].name + '</strong>' + ' </div> ' +
                '<button class="btn btn-lg '+block_color+' mar-lft" inverter_number="'+i+'" id="inverter_button_value_'+i+'" style="'+block_style+'">' + generation.toFixed(2) +
                ' kWh </button>' + '<div class="row"> ' + '<div class="col-lg-1"></div>' + '<strong>' + current_power.toFixed(2) + ' kW</strong>' + ' </div> ' + '</div>');
            $("#south_west_row"+south_west_row_count).append(success);

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
                    block_color = '';
                    block_style = 'background-color:#f3f307;';
                } else {
                    block_color = 'btn-success';
                    block_style = '';
                }
            } else if (data.inverters[i].connected == "disconnected") {
                block_color = 'btn-danger';
                block_style = '';
            }
            else {
                block_color = 'btn-info';
                block_style = '';
            }

            var success = $('<div class="col-lg-1 mar-top mar-btm" id="div'+d_east_west+'" style="text-align:center; padding-left:0px; padding-right:0px;"> ' +
                '<div class="row"> ' + '<div class="col-lg-1"></div>' + '<strong>' + data.inverters[i].name + '</strong>' + ' </div> ' +
                '<button class="btn btn-lg '+block_color+' mar-lft" inverter_number="'+i+'" id="inverter_button_value_'+i+'" style="'+block_style+'">' + generation.toFixed(2) +
                ' kWh </button>' + '<div class="row"> ' + '<div class="col-lg-1"></div>' + '<strong>' + current_power.toFixed(2) + ' kW</strong>' + ' </div> ' + '</div>');
            $("#east_west_row"+east_west_row_count).append(success);

            east_west_elements++;
            d_east_west++;
        }
        $("#inverter_button_value_"+i).click(function() {

            var inverter = $(this).attr('inverter_number');

            $("#inverter_name").empty();
            $("#inverter_name").append(inverter_name);

            $("#status_name").empty();
            $("#status_name").append("<div class='text-semibold'>Inverter Name : " + data.inverters[inverter].name + "</div>");
            $("#status_connected").empty();
            $("#status_connected").append("<div class='text-semibold'>Connection Status : " + data.inverters[inverter].connected + "</div>");
            $("#status_orientation").empty();
            $("#status_orientation").append("<div class='text-semibold'>Inverter Orientation : " + data.inverters[inverter].orientation + "</div>");
            $("#status_capacity").empty();
            $("#status_capacity").append("<div class='text-semibold'>Inverter Capacity : " + data.inverters[inverter].capacity + " kW</div>");
            $("#status_power").empty();
            $("#status_power").append("<div class='text-semibold'>Current Power : " + data.inverters[inverter].power + " kW</div>");
            $("#status_generation").empty();
            $("#status_generation").append("<div class='text-semibold'>Current Generation : " + data.inverters[inverter].generation + " kWh</div>");
            $("#status_total_yield").empty();
            $("#status_total_yield").append("<div class='text-semibold'>Total Yield : " + data.inverters[inverter].total_yield + " kWh</div>");
            $("#status_inside_temperature").empty();
            $("#status_inside_temperature").append("<div class='text-semibold'>Inside Temperature : " + data.inverters[inverter].inside_temperature + "</div>");
            $("#status_last_three_errors").empty();
            var last_three_errors_length = data.inverters[inverter].last_three_errors.length
            if(last_three_errors_length > 0) {
                $("#status_last_three_errors").append("<div class='text-semibold'>Last Three Errors : " + data.inverters[inverter].last_three_errors + "</div>");
            } else {
                $("#status_last_three_errors").append("<div class='text-semibold'>Last Three Errors : No Errors </div>");
            }

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

    var block_color = "";
    var block_style = "";

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
                        block_color = '';
                        block_style = 'width: 150px; background-color:#f3f307;';
                    } else {
                        block_color = 'btn-success';
                        block_style = 'width: 150px;';
                    }
                } else if (data.inverters[j].connected == "disconnected") {
                    block_color = 'btn-danger';
                    block_style = 'width: 150px;';
                }
                else {
                    block_color = 'btn-info';
                    block_style = 'width: 150px;';
                }

                var success = $('<div class="col-lg-2 pad-all" id="div'+d_solar_group+'" style="text-align:center;"> ' +
                    '<div class="row"> ' + '<div class="col-lg-1"></div>' + '<strong>' + data.inverters[j].name + '</strong>' + ' </div> ' +
                    '<button class="btn btn-lg '+block_color+' mar-lft" inverter_number="'+j+'" id="inverter_button_value_'+j+'" style="'+block_style+'">' + generation.toFixed(2) +
                    ' kWh </button>' + '<div class="row"> ' + '<div class="col-lg-1"></div>' + '<strong>' + current_power.toFixed(2) + ' kW</strong>' + ' </div> ' + '</div>');
                $("#"+all_groups[i]+ "-" + solar_group_row).append(success);

                solar_group_element++;
                d_solar_group++;

                $("#inverter_button_value_"+j).click(function() {

                    var inverter = $(this).attr('inverter_number');

                    $("#inverter_name").empty();
                    $("#inverter_name").append(inverter_name);

                    $("#status_name").empty();
                    $("#status_name").append("<div class='text-semibold'>Inverter Name : " + data.inverters[inverter].name + "</div>");
                    $("#status_connected").empty();
                    $("#status_connected").append("<div class='text-semibold'>Connection Status : " + data.inverters[inverter].connected + "</div>");
                    $("#status_orientation").empty();
                    $("#status_orientation").append("<div class='text-semibold'>Inverter Orientation : " + data.inverters[inverter].orientation + "</div>");
                    $("#status_capacity").empty();
                    $("#status_capacity").append("<div class='text-semibold'>Inverter Capacity : " + data.inverters[inverter].capacity + " kW</div>");
                    $("#status_power").empty();
                    $("#status_power").append("<div class='text-semibold'>Current Power : " + data.inverters[inverter].power + " kW</div>");
                    $("#status_generation").empty();
                    $("#status_generation").append("<div class='text-semibold'>Current Generation : " + data.inverters[inverter].generation + " kWh</div>");
                    $("#status_total_yield").empty();
                    $("#status_total_yield").append("<div class='text-semibold'>Total Yield : " + data.inverters[inverter].total_yield + " kWh</div>");
                    $("#status_inside_temperature").empty();
                    $("#status_inside_temperature").append("<div class='text-semibold'>Inside Temperature : " + data.inverters[inverter].inside_temperature + "</div>");
                    $("#status_last_three_errors").empty();
                    var last_three_errors_length = data.inverters[inverter].last_three_errors.length
                    if(last_three_errors_length > 0) {
                        $("#status_last_three_errors").append("<div class='text-semibold'>Last Three Errors : " + data.inverters[inverter].last_three_errors + "</div>");
                    } else {
                        $("#status_last_three_errors").append("<div class='text-semibold'>Last Three Errors : No Errors </div>");
                    }

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
                    block_color = '';
                    block_style = 'width: 150px; background-color:#f3f307;';
                } else {
                    block_color = 'btn-success';
                    block_style = 'width: 150px;';
                }
                $("#not_grouped"+not_group_row).append(success);
            } else if (data.inverters[j].connected == "disconnected") {
                block_color = 'btn-danger';
                block_style = 'width: 150px;';
            }
            else {
                block_color = 'btn-info';
                block_style = 'width: 150px;';
            }

            var success = $('<div class="col-lg-2 pad-all" id="div'+d_not_group+'" style="text-align:center;"> ' +
                '<div class="row"> ' + '<div class="col-lg-1"></div>' + '<strong>' + data.inverters[j].name + '</strong>' + ' </div> ' +
                '<button class="btn btn-lg '+block_color+' mar-lft" inverter_number="'+j+'" id="inverter_button_value_'+j+'" style="'+block_style+'">' + generation.toFixed(2) +
                ' kWh </button>' + '<div class="row"> ' + '<div class="col-lg-1"></div>' + '<strong>' + current_power.toFixed(2) + ' kW</strong>' + ' </div> ' + '</div>');
            $("#not_grouped"+not_group_row).append(success);

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

function plant_summary() {

    $.ajax({
        type: "GET",
        url: "/api/v1/solar/plants/".concat(plant_slug).concat('/summary/'),
        success: function(plant_summary_data) {

            plant_summary_data = {"plant_name":"Waaneep Solar","plant_slug":"demodemo","plant_logo":null,"plant_location":"Ichhawar, Madhya Pradesh","plant_capacity":50000.0,"latitude":23.2599,"longitude":77.4126,"performance_ratio":0.81,"cuf":0.19,"grid_unavailability":"0 %","equipment_unavailability":"2.01 %","unacknowledged_tickets":66,"open_tickets":0,"closed_tickets":144,"plant_generation_today":"81789.00 kWh","plant_total_energy":"114.67 GWh","plant_co2":"57252.30 Kg","current_power":38331.0,"irradiation":0.87,"connected_inverters":67,"disconnected_inverters":0,"invalid_inverters":0,"module_temperature":0.0,"ambient_temperature":27.9899997711,"windspeed":6.51779985428,"dc_loss":"855.34 kWh","conversion_loss":"3333.73 kWh","ac_loss":"-1076.17 kWh","status":"connected","updated_at":"2016-10-25T05:20:33.438000Z","past_generations":[{"timestamp":"2016-10-18T18:30:00Z","energy":"290.61 Mwh"},{"timestamp":"2016-10-19T18:30:00Z","energy":"286.63 Mwh"},{"timestamp":"2016-10-20T18:30:00Z","energy":"285.84 Mwh"},{"timestamp":"2016-10-21T18:30:00Z","energy":"286.50 Mwh"},{"timestamp":"2016-10-22T18:30:00Z","energy":"374.63 Mwh"},{"timestamp":"2016-10-23T18:30:00Z","energy":"373.94 Mwh"},{"timestamp":"2016-10-24T18:30:00Z","energy":"81789.00 kWh"}],"past_pr":[{"timestamp":"2016-10-18T18:30:00Z","pr":0.75},{"timestamp":"2016-10-19T18:30:00Z","pr":0.74},{"timestamp":"2016-10-20T18:30:00Z","pr":0.75},{"timestamp":"2016-10-21T18:30:00Z","pr":0.74},{"timestamp":"2016-10-22T18:30:00Z","pr":0.73},{"timestamp":"2016-10-23T18:30:00Z","pr":1.2},{"timestamp":"2016-10-24T18:30:00Z","pr":0.81}],"past_cuf":[{"timestamp":"2016-10-18T18:30:00Z","cuf":0.24},{"timestamp":"2016-10-19T18:30:00Z","cuf":0.24},{"timestamp":"2016-10-20T18:30:00Z","cuf":0.21},{"timestamp":"2016-10-21T18:30:00Z","cuf":0.24},{"timestamp":"2016-10-22T18:30:00Z","cuf":0.23},{"timestamp":"2016-10-23T18:30:00Z","cuf":0.39},{"timestamp":"2016-10-24T18:30:00Z","cuf":0.19}],"past_grid_unavailability":[{"timestamp":"2016-10-18T18:30:00Z","unavailability":"3.48 %"},{"timestamp":"2016-10-19T18:30:00Z","unavailability":"3.79 %"},{"timestamp":"2016-10-20T18:30:00Z","unavailability":"2.58 %"},{"timestamp":"2016-10-21T18:30:00Z","unavailability":"3.94 %"},{"timestamp":"2016-10-22T18:30:00Z","unavailability":"4.09 %"},{"timestamp":"2016-10-23T18:30:00Z","unavailability":"4.70 %"},{"timestamp":"2016-10-24T18:30:00Z","unavailability":"0.00 %"}],"past_equipment_unavailability":[{"timestamp":"2016-10-18T18:30:00Z","unavailability":"2.48 %"},{"timestamp":"2016-10-19T18:30:00Z","unavailability":"3.28 %"},{"timestamp":"2016-10-20T18:30:00Z","unavailability":"2.00 %"},{"timestamp":"2016-10-21T18:30:00Z","unavailability":"2.77 %"},{"timestamp":"2016-10-22T18:30:00Z","unavailability":"3.57 %"},{"timestamp":"2016-10-23T18:30:00Z","unavailability":"2.66 %"},{"timestamp":"2016-10-24T18:30:00Z","unavailability":"2.01 %"}],"past_dc_loss":[{"timestamp":"2016-10-18T18:30:00Z","dc_energy_loss":"25832.38 kWh"},{"timestamp":"2016-10-19T18:30:00Z","dc_energy_loss":"26950.29 kWh"},{"timestamp":"2016-10-20T18:30:00Z","dc_energy_loss":"21342.44 kWh"},{"timestamp":"2016-10-21T18:30:00Z","dc_energy_loss":"23984.24 kWh"},{"timestamp":"2016-10-22T18:30:00Z","dc_energy_loss":"22946.67 kWh"},{"timestamp":"2016-10-23T18:30:00Z","dc_energy_loss":"13902.34 kWh"},{"timestamp":"2016-10-24T18:30:00Z","dc_energy_loss":"855.34 kWh"}],"past_conversion_loss":[{"timestamp":"2016-10-18T18:30:00Z","conversion_loss":"5063.08 kWh"},{"timestamp":"2016-10-19T18:30:00Z","conversion_loss":"5695.12 kWh"},{"timestamp":"2016-10-20T18:30:00Z","conversion_loss":"4993.94 kWh"},{"timestamp":"2016-10-21T18:30:00Z","conversion_loss":"5031.90 kWh"},{"timestamp":"2016-10-22T18:30:00Z","conversion_loss":"5751.26 kWh"},{"timestamp":"2016-10-23T18:30:00Z","conversion_loss":"9421.05 kWh"},{"timestamp":"2016-10-24T18:30:00Z","conversion_loss":"3333.73 kWh"}],"past_ac_loss":[{"timestamp":"2016-10-18T18:30:00Z","ac_energy_loss":"-3117.99 kWh"},{"timestamp":"2016-10-19T18:30:00Z","ac_energy_loss":"-3079.26 kWh"},{"timestamp":"2016-10-20T18:30:00Z","ac_energy_loss":"-3106.87 kWh"},{"timestamp":"2016-10-21T18:30:00Z","ac_energy_loss":"-3157.58 kWh"},{"timestamp":"2016-10-22T18:30:00Z","ac_energy_loss":"-3010.46 kWh"},{"timestamp":"2016-10-23T18:30:00Z","ac_energy_loss":"-2751.83 kWh"},{"timestamp":"2016-10-24T18:30:00Z","ac_energy_loss":"-1076.17 kWh"}]};

            console.log(plant_summary_data);

            if(plant_summary_data == '') {

                console.log("no data");
                return;

            } else {

                var opts = {};
                var target = null;
                var gauge = null;

                if (plant_slug != 'uran' && plant_slug != 'rrkabel' && plant_slug != 'unipatch') {
                    opts = {
                        lines: 10, // The number of lines to draw
                        angle: 0, // The length of each line
                        lineWidth: 0.41, // The line thickness
                        pointer: {
                            length: 0.75, // The radius of the inner circle
                            strokeWidth: 0.035, // The rotation offset
                            color: '#ffff00' // Fill color
                        },
                        limitMax: 'true', // If true, the pointer will not go past the end of the gauge
                        colorStart: '#fff', // Colors
                        colorStop: '#fff', // just experiment with them
                        strokeColor: '#ffff00', // to see which ones work best for you
                        generateGradient: true
                    };

                    target = document.getElementById('current_power_chart'); // your canvas element
                    gauge = new Gauge(target).setOptions(opts);
                    gauge.maxValue = plant_summary_data.plant_capacity; // set max gauge value
                    gauge.animationSpeed = 32; // set animation speed (32 is default value)
                    gauge.set(1);
                    gauge.set(0);
                    if( plant_summary_data.current_power > 0) {
                        gauge.set(plant_summary_data.current_power); // set actual value
                    } else {
                    }
                }

                /*var present_time = new Date();
                present_time = dateFormat(present_time, "dd-mm-yyyy HH:MM");
                $("#present_time").empty();
                $("#present_time").append("(Last Updated : " + present_time + ")");

                sparkline_bar_chart(plant_summary_data.past_pr);*/

                /*var total_generation = plant_summary_data.plant_total_energy;
                $("#total_generation").text(total_generation);*/

                var ambient_temperature = plant_summary_data.ambient_temperature;
                if(ambient_temperature != undefined && ambient_temperature != "NA") {
                    $("#ambient_temp").text((parseFloat(ambient_temperature).toFixed(2)).toString().concat(String.fromCharCode(176)).concat("C"));
                } else {
                    $("#ambient_temp").text("NA");
                }

                var irradiation = plant_summary_data.irradiation;
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

                var module_temperature = plant_summary_data.module_temperature;

                if(module_temperature != undefined && module_temperature != "NA") {
                    $('#module_temp').text(Math.round(parseFloat(module_temperature).toFixed(2)).toString().concat(String.fromCharCode(176)).concat("C"));
                } else {
                    $('#module_temp').text("NA");
                }

                var plant_generation_today = plant_summary_data.plant_generation_today;
                if(plant_generation_today != undefined && plant_generation_today != "NA") {
                    $("#todays_generation").text(plant_generation_today);
                    var co2 = plant_summary_data.plant_co2;
                    $("#co2_savings").text(co2);
                } else {
                    $("#todays_generation").text("NA");
                    $("#co2_savings").text((0.00).toString().concat(" Kg"));
                }

                var current_power = plant_summary_data.current_power;
                $("#current_power_value").empty();
                $("#current_power_value").text(current_power);

                var plant_capacity = plant_summary_data.plant_capacity;
                $("#plant_capacity").empty();
                $("#plant_capacity").text(plant_capacity);

                var total_generation = plant_summary_data.plant_total_energy;

                $("#total_generation").empty();
                $("#total_generation").text(total_generation);

                var pr_value = plant_summary_data.performance_ratio;
                if(plant_slug == "uran" || plant_slug == "rrkabel" || plant_slug == "unipatch" || plant_slug == "waaneep" || plant_slug == "growels" || plant_slug == "raheja") {
                    pr_value = (((parseFloat(pr_value) * 100.0)).toFixed(2)).toString() + "%";
                } else {
                    pr_value = parseFloat(pr_value);
                    pr_value = pr_value.toFixed(2);
                }

                if(pr_value != undefined && pr_value != "NA") {
                    $('#pr').text(pr_value);
                } else {
                    $('#pr').text("NA");
                }

                var cuf = plant_summary_data.cuf;

                $("#cuf").empty();
                $("#cuf").text(cuf);

                var co2 = plant_summary_data.plant_co2;

                $("#co2_value").empty();
                $("#co2_value").text(co2);

                /*$("#current_power_chart").append("<div class='chart' id='current_power_easy_pie_chart' data-percent='"+current_power+"'>"+current_power+"</div>");

                $('#current_power_easy_pie_chart').easyPieChart({
                    barColor :'#ffffff',
                    scaleColor:'#8b5284',
                    trackColor : '#8b5284',
                    lineCap : 'round',
                    lineWidth :8,
                    onStep: function(plant_capacity, current_power, percent) {
                        $(this.el).find('.pie-value').text(Math.round(percent) + 'kW');
                    }
                });*/
                
                var generation_timestamps = [], generation_energy = [];
                var pr_timestamps = [], pr_values = []
                var timestamps_cuf = [], values_cuf = [];
                var grid_unavail_timestamps = [], grid_unavail_values = [];
                var equipment_unavail_timestamps = [], equipment_unavail_values = [];

                for(var i = 0; i < plant_summary_data.past_generations.length; i++) {
                    var generation_date = new Date(plant_summary_data.past_generations[i].timestamp);
                    generation_date = dateFormat(generation_date, "yyyy-mm-dd HH:MM:ss");
                    var generation_value = (plant_summary_data.past_generations[i].energy);
                    generation_timestamps.push(generation_date);
                    generation_energy.push(generation_value);

                    if(plant_summary_data.past_pr) {
                        var pr_date = new Date(plant_summary_data.past_pr[i].timestamp);
                        pr_date = dateFormat(pr_date, "yyyy-mm-dd HH:MM:ss");
                        var value_pr = null;
                        if(plant_slug == "uran" || plant_slug == "rrkabel" || plant_slug == "unipatch" || plant_slug == "waaneep" || plant_slug == "growels" || plant_slug == "raheja") {
                            value_pr = parseFloat(plant_summary_data.past_pr[i].pr);
                        } else {
                            value_pr = parseFloat(plant_summary_data.past_pr[i].pr) * 100 ;
                        }
                        pr_timestamps.push(pr_date);
                        pr_values.push(value_pr);
                    }

                    if(plant_summary_data.past_grid_unavailability) {
                        var grid_unavail_date = new Date(plant_summary_data.past_grid_unavailability[i].timestamp);
                        grid_unavail_date = dateFormat(grid_unavail_date, "yyyy-mm-dd HH:MM:ss");
                        var grid_unavail_value = parseFloat(plant_summary_data.past_grid_unavailability[i].unavailability);
                        grid_unavail_timestamps.push(grid_unavail_date);
                        grid_unavail_values.push(grid_unavail_value);
                    }

                    if(plant_summary_data.past_equipment_unavailability) {
                        var equipment_unavail_date = new Date(plant_summary_data.past_grid_unavailability[i].timestamp);
                        equipment_unavail_date = dateFormat(equipment_unavail_date, "yyyy-mm-dd HH:MM:ss");
                        var equipment_unavail_value = parseFloat(plant_summary_data.past_grid_unavailability[i].unavailability);
                        equipment_unavail_timestamps.push(equipment_unavail_date);
                        equipment_unavail_values.push(equipment_unavail_value);
                    }                    

                }

                /*var generation_title = "Generation";
                var generation_div_name = "inverters_energy_charts";
                var y_axis_title = "Generation";
                var width = 230;
                var height = 166;
                var page = 2;

                basic_bar_chart_plotly(generation_timestamps, generation_energy, y_axis_title, "", generation_title, generation_div_name, 95, 20, page, height, width);

                var pr_title = "PR";
                var pr_div_name = "performance_ratio_chart";
                var y_axis_title = "PR";
                var width = 230;
                var height = 166;
                var page = 2;

                basic_bar_chart_plotly(pr_timestamps, pr_values, y_axis_title, "", pr_title, pr_div_name, 50, 20, page, height, width);*/
                
                /*var grid_unavailability_title = "Grid Unavailability";
                var grid_unavailability_div_name = "last_seven_days_grid_availability";
                y_axis_title = "Grid Unavailability";
                var width = 250;
                var height = 166;
                var page = 2;

                basic_bar_chart_plotly(grid_unavail_timestamps, grid_unavail_values, y_axis_title, "", grid_unavailability_title, grid_unavailability_div_name, 35, 20, page, height, width);

                var equipment_unavailability_title = "Equipment Unavailability";
                var equipment_unavailability_div_name = "last_seven_days_equipment_availability";
                y_axis_title = "Equipment Unavailability";
                width = 250;
                height = 166;
                var page = 2;

                basic_bar_chart_plotly(equipment_unavail_timestamps, equipment_unavail_values, y_axis_title, "", equipment_unavailability_title, equipment_unavailability_div_name, 35, 20, page, height, width);*/

                var width = 250;
                var height = 166;
                var page = 2;

                var unavailability_title = "Weekly Chart";
                var unavailability_div_name = "last_seven_days_grid_and_equipment_availability";
                y_axis_title = "Grid and Equipment Unavailability";
                var all_x_arrays = [grid_unavail_timestamps, equipment_unavail_timestamps];
                var all_y_arrays = [grid_unavail_values, equipment_unavail_values];
                var all_array_titles = ['Grid Unavailability', 'Equipment Unavailability'];

                relative_bar_chart_plotly(all_x_arrays, all_y_arrays, all_array_titles, unavailability_title, unavailability_div_name, 20, 20, page, height, width);

                var performance_ratio_title = "Performance Ratio";
                var performance_ratio_div_name = "last_seven_days_performance_ratio";
                y_axis_title = "Performance Ratio";
                width = 250;
                height = 166;
                var page = 2;

                basic_bar_chart_plotly(pr_timestamps, pr_values, y_axis_title, "", performance_ratio_title, performance_ratio_div_name, 35, 20, page, height, width);

                var energy_generation_title = "Energy Generation";
                var energy_generation_div_name = "last_seven_days_energy_generation";
                y_axis_title = "Energy Generation";
                width = 250;
                height = 166;
                var page = 2;

                basic_bar_chart_plotly(generation_timestamps, generation_energy, y_axis_title, "", energy_generation_title, energy_generation_div_name, 65, 20, page, height, width);

                var energy_chart1 = "seven_energy1";
                var energy_chart2 = "seven_energy2";
                var energy_chart3 = "seven_energy3";
                var energy_chart4 = "seven_energy4";

                basic_bar_chart_plotly(generation_timestamps, generation_energy, y_axis_title, "", energy_generation_title, energy_chart1, 65, 10, page, height, width);
                basic_bar_chart_plotly(generation_timestamps, generation_energy, y_axis_title, "", energy_generation_title, energy_chart2, 65, 10, page, height, width);
                basic_bar_chart_plotly(generation_timestamps, generation_energy, y_axis_title, "", energy_generation_title, energy_chart3, 65, 10, page, height, width);
                basic_bar_chart_plotly(generation_timestamps, generation_energy, y_axis_title, "", energy_generation_title, energy_chart4, 65, 10, page, height, width);

                var grid_ctx = $("#today_grid_availability");

                var grid_unavailability = parseFloat(plant_summary_data.grid_unavailability);
                var grid_availability = 100.00 - grid_unavailability;
                var grid_label = ["Grid Avail.", "Grid Unavail."];
                var grid_data = [
                    {label: "Grid Avail.", value: grid_availability}, 
                    {label: "Grid Unavail.", value: grid_unavailability}
                ];
                var div_name = "today_grid_availability";

                /*availability_doughnut_chart_summary(grid_label, grid_data, grid_ctx);*/

                $("#today_grid_availability").empty();
                availability_donut_chart(grid_data, div_name);

                var equipment_ctx = $("#today_equipment_availability");

                var equipment_unavailability = parseFloat(plant_summary_data.equipment_unavailability);
                var equipment_availability = 100.00 - equipment_unavailability;
                var equipment_label = ["Equip. Avail.", "Equip. Unavail."];
                var equipment_data = [
                    {label: "Equip. Avail.", value: equipment_availability}, 
                    {label: "Equip. Unavail.", value: equipment_unavailability}
                ];

                div_name = "today_equipment_availability";

                /*availability_doughnut_chart_summary(equipment_label, equipment_data, equipment_ctx);*/

                $("#today_equipment_availability").empty();
                availability_donut_chart(equipment_data, div_name);

                var inverter_status = [plant_summary_data.connected_inverters, plant_summary_data.disconnected_inverters, plant_summary_data.invalid_inverters];
                var inverter_status_headings = {
                    0: "Inverters Connected",
                    1: "Inverters Disconnected",
                    2: "Invalid Inverters"
                };
                
                inverters_status_pie_chart(inverter_status, inverter_status_headings);

                $("#inverters_connected").empty();
                $("#inverters_connected").append("<span class='label label-success' style='font-weight: 700;font-size: 11px;'>Connected : " + plant_summary_data.connected_inverters + "</span>");
                $("#inverters_disconnected").empty();
                $("#inverters_disconnected").append("<span class='label label-danger' style='font-weight: 700;font-size: 11px;'>Disconnected : " + plant_summary_data.disconnected_inverters + "</span>");
                $("#inverters_invalid").empty();
                $("#inverters_invalid").append("<span class='label label-info' style='font-weight: 700;font-size: 11px;'>Invalid : " + plant_summary_data.invalid_inverters + "</span>");

                $("#top_left_info").empty();

                if(plant_summary_data.pvsyst_generation && plant_summary_data.pvsyst_pr && plant_summary_data.pvsyst_tilt_angle) {
                    $("#top_left_info").append("<div class='row' style='padding-top: 15px;'><div class='col-md-4'><div class='col-md-12 text-center'><i class='ion-ios-bolt fa-3x text-center' aria-hidden='true' style='color: #000000;'></i></div><div class='col-md-12'><div class='row text-center'><span class='text-x text-bold' id='pvsyst_generation' style='color: #000000;'>" + plant_summary_data.pvsyst_generation + "</span></div><div class='row text-center'><p class='text-uppercase text-center'><small style='color: #000000;font-weight: 700;font-size: 11px;'>Pvsyst Generation</small></p></div></div></div><div class='col-md-4'><div class='col-md-12 text-center'><i class='ion-ios-pulse fa-3x text-center' aria-hidden='true' style='color: #000000;'></i></div><div class='col-md-12'><div class='row text-center'><span class='text-x text-bold' id='pvsyst_pr' style='color: #000000;'>" + plant_summary_data.pvsyst_pr + "</span></div><div class='row text-center'><p class='text-uppercase text-center'><small style='color: #000000;font-weight: 700;font-size: 11px;'>Pvsyst PR</small></p></div></div></div><div class='col-md-4'><div class='col-md-12 text-center'><i class='ion-ios-infinite fa-3x text-center' aria-hidden='true' style='color: #000000;'></i></div><div class='col-md-12'><div class='row text-center'><span class='text-x text-bold' id='pvsyst_tilt' style='color: #000000;'>" + plant_summary_data.pvsyst_tilt_angle + "</span></div></div><div class='col-md-12 text-center'><p class='text-uppercase text-center'><small style='color: #000000;font-weight: 700;font-size: 11px;'>Pvsyst Tilt Angle</small></p></div></div>");
                } else if(plant_summary_data.past_dc_loss && plant_summary_data.past_conversion_loss && plant_summary_data.past_ac_loss) {
                    $("#top_left_info").append("<div class='row' style='padding-top: 15px;'><div class='col-md-4'><div class='col-md-12 text-center'><i class='ion-ios-close-outline fa-3x text-center' aria-hidden='true' style='color: #000000;'></i></div><div class='col-md-12'><div class='row text-center'><span class='text-x text-bold' id='dc_loss' style='color: #000000;'>" + plant_summary_data.dc_loss + "</span></div><div class='row text-center'><p class='text-uppercase text-center'><small style='color: #000000;font-weight: 700;font-size: 11px;'>DC Loss</small></p></div></div></div><div class='col-md-4'><div class='col-md-12 text-center'><i class='ion-ios-pie-outline fa-3x text-center' aria-hidden='true' style='color: #000000;'></i></div><div class='col-md-12'><div class='row text-center'><span class='text-x text-bold' id='conversion_loss' style='color: #000000;'>" + plant_summary_data.conversion_loss + "</span></div><div class='row text-center'><p class='text-uppercase text-center'><small style='color: #000000;font-weight: 700;font-size: 11px;'>Conversion Loss</small></p></div></div></div><div class='col-md-4'><div class='col-md-12 text-center'><i class='ion-ios-locked-outline fa-3x text-center' aria-hidden='true' style='color: #000000;'></i></div><div class='col-md-12'><div class='row text-center'><span class='text-x text-bold' id='ac_loss' style='color: #000000;'>" + plant_summary_data.ac_loss + "</span></div></div><div class='col-md-12 text-center'><p class='text-uppercase text-center'><small style='color: #000000;font-weight: 700;font-size: 11px;'>AC Loss</small></p></div></div>");

                    /*var dc_loss_timestamps = [], dc_loss_energy = [];
                    var conversion_loss_timestamps = [], conversion_loss_energy = [];
                    var ac_loss_timestamps = [], ac_loss_energy = [];

                    for(var i = 0; i < plant_summary_data.past_dc_loss.length; i++) {

                        var dc_loss_date = new Date(plant_summary_data.past_dc_loss[i].timestamp);
                        dc_loss_date = dateFormat(dc_loss_date, "yyyy-mm-dd HH:MM:ss");
                        var dc_loss_value = (plant_summary_data.past_dc_loss[i].dc_energy_loss);
                        dc_loss_timestamps.push(dc_loss_date);
                        dc_loss_energy.push(dc_loss_value);

                        var conversion_loss_date = new Date(plant_summary_data.past_conversion_loss[i].timestamp);
                        conversion_loss_date = dateFormat(conversion_loss_date, "yyyy-mm-dd HH:MM:ss");
                        var conversion_loss_value = (plant_summary_data.past_conversion_loss[i].conversion_loss);
                        conversion_loss_timestamps.push(conversion_loss_date);
                        conversion_loss_energy.push(conversion_loss_value);

                        var ac_loss_date = new Date(plant_summary_data.past_ac_loss[i].timestamp);
                        ac_loss_date = dateFormat(ac_loss_date, "yyyy-mm-dd HH:MM:ss");
                        var ac_loss_value = (plant_summary_data.past_ac_loss[i].ac_energy_loss);
                        ac_loss_timestamps.push(ac_loss_date);
                        ac_loss_energy.push(ac_loss_value);

                    }

                    var losses_title = "Losses";
                    var losses_div_name = "loss_chart";
                    y_axis_title = "Losses";
                    var all_x_arrays = [dc_loss_timestamps, conversion_loss_timestamps, ac_loss_timestamps];
                    var all_y_arrays = [dc_loss_energy, conversion_loss_energy, ac_loss_energy];
                    var all_array_titles = ['DC Losses', 'Conversion Losses', 'AC Losses'];

                    relative_bar_chart_plotly(all_x_arrays, all_y_arrays, all_array_titles, losses_title, losses_div_name, 30, 20, page, height, width);*/

                }

                /*var performance_ratio = plant_summary_data.performance_ratio;
                if(plant_slug == "uran" || plant_slug == "rrkabel" || plant_slug == "unipatch" || plant_slug == "waaneep" || plant_slug == "growels" || plant_slug == "raheja") {
                    performance_ratio = (((parseFloat(performance_ratio) * 100.0)).toFixed(2)).toString() + "%";
                } else {
                    performance_ratio = parseFloat(performance_ratio);
                    performance_ratio = performance_ratio.toFixed(2);
                }

                if(performance_ratio != undefined && performance_ratio != "NA") {
                    $('#performance_ratio').text(performance_ratio);
                } else {
                    $('#performance_ratio').text("NA");
                }*/

                /*if (plant_slug != 'uran' && plant_slug != 'rrkabel' && plant_slug != 'unipatch') {
                    var current_power = plant_summary_data.current_power;
                    if(current_power != undefined && current_power != "NA") {
                        $("#demo-gauge-text").text((parseFloat(current_power)).toFixed(2).toString().concat(" kW"));
                        gauge.set(current_power); // set actual value
                    }
                }*/

                /*if(windspeed_unipatch == 1) {
                    var wind = data.windspeed;
                    $('#windspeed').text((parseFloat(wind)).toFixed(2).toString().concat("kmph"));
                }*/

                var ut = plant_summary_data.unacknowledged_tickets;
                var ot = plant_summary_data.open_tickets;
                var ct = plant_summary_data.closed_tickets;
                $("#unacknowledged_tickets").text(ut);
                $("#open_tickets").text(ot);
                $("#closed_tickets").text(ct);

                /*if (plant_slug != 'uran' && plant_slug != 'rrkabel' && plant_slug != 'unipatch') {*/
                    
                if(plant_summary_data.pvsyst_generation) {
                    $("#generation_expected").show();
                    $("#generation_expected_div").show();
                    $("#generation_expected").text("/".concat((parseFloat(plant_summary_data.pvsyst_generation)).toFixed(2).toString()));
                } else {
                    $("#generation_expected").hide();
                    $("#generation_expected_div").hide();
                }

                if(plant_summary_data.pvsyst_tilt_angle) {
                    $("#pvsyst_tilt_angle").show();
                    $("#pvsyst_tilt_angle_div").show();
                    $("#pvsyst_tilt_angle").text("/".concat((parseFloat(plant_summary_data.pvsyst_tilt_angle)).toString().concat(String.fromCharCode(176))));
                } else {
                    $("#pvsyst_tilt_angle").hide();
                    $("#pvsyst_tilt_angle_div").hide();
                }

                if(plant_summary_data.pvsyst_generation) {
                    $("#generation_expected").show();
                    $("#generation_expected_div").show();
                    $("#generation_expected").text("/".concat((parseFloat(plant_summary_data.pvsyst_generation)).toFixed(2).toString()));
                } else {
                    $("#generation_expected").hide();
                    $("#generation_expected_div").hide();
                }

                if(plant_slug == "waaneep" || plant_slug == "growels" || plant_slug == "raheja") {

                    if(plant_summary_data.pvsyst_pr) {
                        var expected_performance = plant_summary_data.pvsyst_pr * 100;
                        $("#expected_performance_ratio").show();
                        $("#expected_performance_ratio_div").show();
                        $("#expected_performance_ratio").text("/".concat((parseFloat(expected_performance)).toFixed(2).toString().concat("%")));
                    } else {
                        $("#expected_performance_ratio").hide();
                        $("#expected_performance_ratio_div").hide();
                    }
                } else {
                    
                    if(plant_summary_data.pvsyst_pr) {
                        $("#expected_performance_ratio").show();
                        $("#expected_performance_ratio_div").show();
                        $("#expected_performance_ratio").text("/".concat((parseFloat(plant_summary_data.pvsyst_pr)).toFixed(2).toString()));
                    } else {
                        $("#expected_performance_ratio").hide();
                        $("#expected_performance_ratio_div").hide();
                    }

                }
                /*}*/

                var cuf = plant_summary_data.cuf;

                /*if (plant_slug != 'uran' && plant_slug != 'rrkabel' && plant_slug != 'unipatch') {*/
                    
                    $("#cuf_value").empty();
                    $("#cuf_value").text((parseFloat(cuf)).toFixed(2).toString());

                /*}*/

                if (plant_slug != 'uran' && plant_slug != 'rrkabel' && plant_slug != 'unipatch') {
                    
                    $("#devices_disconnected").empty();
                    $("#devices_disconnected").append("<i class='fa fa-times' aria-hidden='true'></i> : " + plant_summary_data.disconnected_inverters + " Disconnected");

                    $("#devices_connected").empty();
                    $("#devices_connected").append("<i class='fa fa-check' aria-hidden='true'></i> : " + plant_summary_data.connected_inverters + " Connected");

                }
            }
        },
        error: function(data) {
            console.log("error_streams_data");
            data = null;
        }
    });
}

function availability_doughnut_chart_summary(chart_labels, chart_data, ctx) {

    var data = {
        labels: chart_labels,
        datasets: [
            {
                data: chart_data,
                backgroundColor: [
                    "#36a2eb",
                    "#ef5349"
                ],
                hoverBackgroundColor: [
                    "#36a2eb",
                    "#ef5349"
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
            },
            legend: {
                display: true,
                position: 'right'
            }
        }
    });

}

function availability_donut_chart(data, div_name) {

    Morris.Donut({
        element: div_name,
        data: data,
        colors: [
            '#36a2eb',
            '#ef5349',
            '#afd2f0'
        ],
        resize:true
    });

}

function inverters_status_pie_chart(inverter_status_values, inverter_status_headings) {

    $("#inverters_status_connection").sparkline(inverter_status_values, {
        type: 'pie',
        width: '75',
        height: '75',
        tooltipChartTitle: 'Inverter Status',
        tooltipValueLookups: inverter_status_headings,
        sliceColors: ['#91c957', '#f76549', '#46bbdc', '#2d4859','#fe7211','#7ad689','#128376'],
        tooltipFormatter: function(sparkline, options, field) {
            return options.mergedOptions.tooltipValueLookups[field.offset] + " : " + field.value;
        }
    });

}

function inverter_blocks() {

    $.ajax({
        type: "GET",
        url: "/api/v1/solar/plants/".concat(plant_slug).concat('/live/'),
        success: function(inverter_group_data) {

            console.log(inverter_group_data);

            if(inverter_group_data == '') {
                    
            } else {
                if(plant_slug == "palladam" || plant_slug == "thuraiyur") {
                    return plot_labels_orientation_seven(inverter_group_data, 7);
                } else {
                    return plot_labels_orientation(inverter_group_data, 5);
                }
            }

        },
        error: function(data) {
            console.log("error_streams_data");
            data = null;
        }
    });

}

function power_irradiation_data(plant_slug, st, et) {

    $.ajax({
        type: "GET",
        url: "/api/solar/plants/".concat(plant_slug).concat('/irradiation-power/'),
        data: {startTime: (st), endTime: (et)},
        success: function(data) {

            data = [{"timestamp":"2016-10-24T00:33:00.000Z","power":null,"irradiation":0.0095031557},{"timestamp":"2016-10-24T00:35:00.000Z","power":null,"irradiation":0.0097364025},{"timestamp":"2016-10-24T00:36:00.000Z","power":null,"irradiation":0.0094764986},{"timestamp":"2016-10-24T00:38:00.000Z","power":null,"irradiation":0.00984303},{"timestamp":"2016-10-24T00:39:00.000Z","power":null,"irradiation":0.0104361439},{"timestamp":"2016-10-24T00:41:00.000Z","power":null,"irradiation":0.0102628746},{"timestamp":"2016-10-24T00:43:00.000Z","power":null,"irradiation":0.0109892731},{"timestamp":"2016-10-24T00:44:00.000Z","power":null,"irradiation":0.0113291473},{"timestamp":"2016-10-24T00:46:00.000Z","power":null,"irradiation":0.0116756859},{"timestamp":"2016-10-24T00:48:00.000Z","power":null,"irradiation":0.0122354794},{"timestamp":"2016-10-24T00:49:00.000Z","power":null,"irradiation":0.0128952351},{"timestamp":"2016-10-24T00:51:00.000Z","power":null,"irradiation":0.0133817225},{"timestamp":"2016-10-24T00:53:00.000Z","power":null,"irradiation":0.0139748363},{"timestamp":"2016-10-24T00:54:00.000Z","power":null,"irradiation":0.0151810579},{"timestamp":"2016-10-24T00:56:00.000Z","power":null,"irradiation":0.016373951},{"timestamp":"2016-10-24T00:58:00.000Z","power":null,"irradiation":0.0180333366},{"timestamp":"2016-10-24T00:59:00.000Z","power":null,"irradiation":0.0196594028},{"timestamp":"2016-10-24T01:01:00.000Z","power":null,"irradiation":0.0218785839},{"timestamp":"2016-10-24T01:03:00.000Z","power":null,"irradiation":0.0237512245},{"timestamp":"2016-10-24T01:04:00.000Z","power":null,"irradiation":0.0259903965},{"timestamp":"2016-10-24T01:06:00.000Z","power":null,"irradiation":0.0285561161},{"timestamp":"2016-10-24T01:08:00.000Z","power":100.0,"irradiation":0.0314417171},{"timestamp":"2016-10-24T01:09:00.000Z","power":677.0,"irradiation":0.0345272446},{"timestamp":"2016-10-24T01:11:00.000Z","power":852.0,"irradiation":0.0377860374},{"timestamp":"2016-10-24T01:13:00.000Z","power":972.0,"irradiation":0.0410115128},{"timestamp":"2016-10-24T01:14:00.000Z","power":1088.0,"irradiation":0.0446368408},{"timestamp":"2016-10-24T01:16:00.000Z","power":1246.0,"irradiation":0.0481821976},{"timestamp":"2016-10-24T01:17:00.000Z","power":1379.0,"irradiation":0.0519408073},{"timestamp":"2016-10-24T01:19:00.000Z","power":1525.0,"irradiation":0.0562125626},{"timestamp":"2016-10-24T01:21:00.000Z","power":1706.0,"irradiation":0.0607375603},{"timestamp":"2016-10-24T01:22:00.000Z","power":1917.0,"irradiation":0.0648293839},{"timestamp":"2016-10-24T01:24:00.000Z","power":2152.0,"irradiation":0.0696142807},{"timestamp":"2016-10-24T01:26:00.000Z","power":2433.0,"irradiation":0.0741392746},{"timestamp":"2016-10-24T01:27:00.000Z","power":2740.0,"irradiation":0.0787242432},{"timestamp":"2016-10-24T01:29:00.000Z","power":3043.0,"irradiation":0.0839356537},{"timestamp":"2016-10-24T01:31:00.000Z","power":3313.0,"irradiation":0.0886672363},{"timestamp":"2016-10-24T01:32:00.000Z","power":3589.0,"irradiation":0.0944117813},{"timestamp":"2016-10-24T01:34:00.000Z","power":3872.0,"irradiation":0.0992033463},{"timestamp":"2016-10-24T01:36:00.000Z","power":4162.0,"irradiation":0.1052077942},{"timestamp":"2016-10-24T01:37:00.000Z","power":4438.0,"irradiation":0.1111989136},{"timestamp":"2016-10-24T01:39:00.000Z","power":4734.0,"irradiation":0.1167035446},{"timestamp":"2016-10-24T01:41:00.000Z","power":5013.0,"irradiation":0.1221681976},{"timestamp":"2016-10-24T01:42:00.000Z","power":5277.0,"irradiation":0.1273329544},{"timestamp":"2016-10-24T01:44:00.000Z","power":5555.0,"irradiation":0.1330441742},{"timestamp":"2016-10-24T01:46:00.000Z","power":5861.0,"irradiation":0.1393551788},{"timestamp":"2016-10-24T01:47:00.000Z","power":6144.0,"irradiation":0.1454062805},{"timestamp":"2016-10-24T01:49:00.000Z","power":6464.0,"irradiation":0.1506043549},{"timestamp":"2016-10-24T01:51:00.000Z","power":6784.0,"irradiation":0.1552826233},{"timestamp":"2016-10-24T01:52:00.000Z","power":7082.0,"irradiation":0.1594677429},{"timestamp":"2016-10-24T01:54:00.000Z","power":7382.0,"irradiation":0.1639660797},{"timestamp":"2016-10-24T01:56:00.000Z","power":7696.0,"irradiation":0.1697639465},{"timestamp":"2016-10-24T01:57:00.000Z","power":8042.0,"irradiation":0.1754685059},{"timestamp":"2016-10-24T01:59:00.000Z","power":8379.0,"irradiation":0.1812397003},{"timestamp":"2016-10-24T02:00:00.000Z","power":8740.0,"irradiation":0.1874774017},{"timestamp":"2016-10-24T02:02:00.000Z","power":9063.0,"irradiation":0.192635498},{"timestamp":"2016-10-24T02:04:00.000Z","power":9371.0,"irradiation":0.1984133606},{"timestamp":"2016-10-24T02:05:00.000Z","power":9706.0,"irradiation":0.2051575317},{"timestamp":"2016-10-24T02:07:00.000Z","power":10046.0,"irradiation":0.2129879761},{"timestamp":"2016-10-24T02:09:00.000Z","power":10351.0,"irradiation":0.2202386322},{"timestamp":"2016-10-24T02:10:00.000Z","power":10674.0,"irradiation":0.2266495972},{"timestamp":"2016-10-24T02:12:00.000Z","power":11012.0,"irradiation":0.2341868134},{"timestamp":"2016-10-24T02:14:00.000Z","power":11356.0,"irradiation":0.2413508301},{"timestamp":"2016-10-24T02:15:00.000Z","power":11666.0,"irradiation":0.2481349945},{"timestamp":"2016-10-24T02:17:00.000Z","power":11979.0,"irradiation":0.2550590973},{"timestamp":"2016-10-24T02:19:00.000Z","power":12342.0,"irradiation":0.263875824},{"timestamp":"2016-10-24T02:20:00.000Z","power":12709.0,"irradiation":0.2712597656},{"timestamp":"2016-10-24T02:22:00.000Z","power":13041.0,"irradiation":0.2797033081},{"timestamp":"2016-10-24T02:24:00.000Z","power":13351.0,"irradiation":0.2868473511},{"timestamp":"2016-10-24T02:25:00.000Z","power":13696.0,"irradiation":0.294651123},{"timestamp":"2016-10-24T02:27:00.000Z","power":14039.0,"irradiation":0.3021017151},{"timestamp":"2016-10-24T02:29:00.000Z","power":14367.0,"irradiation":0.3109984131},{"timestamp":"2016-10-24T02:30:00.000Z","power":14698.0,"irradiation":0.3179291992},{"timestamp":"2016-10-24T02:32:00.000Z","power":15011.0,"irradiation":0.3245600891},{"timestamp":"2016-10-24T02:34:00.000Z","power":15354.0,"irradiation":0.3320639648},{"timestamp":"2016-10-24T02:35:00.000Z","power":15698.0,"irradiation":0.3393079529},{"timestamp":"2016-10-24T02:37:00.000Z","power":15985.0,"irradiation":0.3444794006},{"timestamp":"2016-10-24T02:38:00.000Z","power":16306.0,"irradiation":0.3465319519},{"timestamp":"2016-10-24T02:40:00.000Z","power":16674.0,"irradiation":0.3514234924},{"timestamp":"2016-10-24T02:42:00.000Z","power":16990.0,"irradiation":0.3575612183},{"timestamp":"2016-10-24T02:43:00.000Z","power":17291.0,"irradiation":0.3637322693},{"timestamp":"2016-10-24T02:45:00.000Z","power":17600.0,"irradiation":0.3698433533},{"timestamp":"2016-10-24T02:47:00.000Z","power":17971.0,"irradiation":0.3857441406},{"timestamp":"2016-10-24T02:48:00.000Z","power":18340.0,"irradiation":0.3925282898},{"timestamp":"2016-10-24T02:50:00.000Z","power":18680.0,"irradiation":0.3988859558},{"timestamp":"2016-10-24T02:52:00.000Z","power":19004.0,"irradiation":0.3985660706},{"timestamp":"2016-10-24T02:53:00.000Z","power":19359.0,"irradiation":0.4130740356},{"timestamp":"2016-10-24T02:55:00.000Z","power":19707.0,"irradiation":0.4216375427},{"timestamp":"2016-10-24T02:57:00.000Z","power":20010.0,"irradiation":0.4266690369},{"timestamp":"2016-10-24T02:58:00.000Z","power":20315.0,"irradiation":0.4246430969},{"timestamp":"2016-10-24T03:00:00.000Z","power":20645.0,"irradiation":0.4417434387},{"timestamp":"2016-10-24T03:02:00.000Z","power":20912.0,"irradiation":0.4359922485},{"timestamp":"2016-10-24T03:03:00.000Z","power":21180.0,"irradiation":0.4448223267},{"timestamp":"2016-10-24T03:05:00.000Z","power":21485.0,"irradiation":0.4514865112},{"timestamp":"2016-10-24T03:07:00.000Z","power":21839.0,"irradiation":0.4645483704},{"timestamp":"2016-10-24T03:08:00.000Z","power":22195.0,"irradiation":0.476783844},{"timestamp":"2016-10-24T03:10:00.000Z","power":22468.0,"irradiation":0.4837945862},{"timestamp":"2016-10-24T03:12:00.000Z","power":22762.0,"irradiation":0.4903521729},{"timestamp":"2016-10-24T03:13:00.000Z","power":23114.0,"irradiation":0.4998086548},{"timestamp":"2016-10-24T03:15:00.000Z","power":23471.0,"irradiation":0.5054799194},{"timestamp":"2016-10-24T03:17:00.000Z","power":23744.0,"irradiation":0.5121174316},{"timestamp":"2016-10-24T03:18:00.000Z","power":24019.0,"irradiation":0.5139567871},{"timestamp":"2016-10-24T03:20:00.000Z","power":24335.0,"irradiation":0.5176687622},{"timestamp":"2016-10-24T03:21:00.000Z","power":24653.0,"irradiation":0.5285513916},{"timestamp":"2016-10-24T03:23:00.000Z","power":24918.0,"irradiation":0.53262323},{"timestamp":"2016-10-24T03:25:00.000Z","power":25121.0,"irradiation":0.5372614746},{"timestamp":"2016-10-24T03:26:00.000Z","power":25385.0,"irradiation":0.5366817017},{"timestamp":"2016-10-24T03:28:00.000Z","power":25669.0,"irradiation":0.5455651245},{"timestamp":"2016-10-24T03:30:00.000Z","power":25992.0,"irradiation":0.5533222046},{"timestamp":"2016-10-24T03:31:00.000Z","power":26319.0,"irradiation":0.5624988403},{"timestamp":"2016-10-24T03:33:00.000Z","power":26583.0,"irradiation":0.5644581299},{"timestamp":"2016-10-24T03:35:00.000Z","power":26864.0,"irradiation":0.5722818604},{"timestamp":"2016-10-24T03:36:00.000Z","power":27182.0,"irradiation":0.5808587036},{"timestamp":"2016-10-24T03:38:00.000Z","power":27417.0,"irradiation":0.584270813},{"timestamp":"2016-10-24T03:40:00.000Z","power":27681.0,"irradiation":0.5923677979},{"timestamp":"2016-10-24T03:41:00.000Z","power":27977.0,"irradiation":0.5979590454},{"timestamp":"2016-10-24T03:43:00.000Z","power":28213.0,"irradiation":0.6085418091},{"timestamp":"2016-10-24T03:45:00.000Z","power":28425.0,"irradiation":0.6140731201},{"timestamp":"2016-10-24T03:46:00.000Z","power":28651.0,"irradiation":0.6132001343},{"timestamp":"2016-10-24T03:48:00.000Z","power":28925.0,"irradiation":0.6191845703},{"timestamp":"2016-10-24T03:50:00.000Z","power":29186.0,"irradiation":0.6299539185},{"timestamp":"2016-10-24T03:51:00.000Z","power":29372.0,"irradiation":0.6339124756},{"timestamp":"2016-10-24T03:53:00.000Z","power":29622.0,"irradiation":0.6392105103},{"timestamp":"2016-10-24T03:55:00.000Z","power":29945.0,"irradiation":0.6506196289},{"timestamp":"2016-10-24T03:56:00.000Z","power":30148.0,"irradiation":0.6547714233},{"timestamp":"2016-10-24T03:58:00.000Z","power":30261.0,"irradiation":0.6587832642},{"timestamp":"2016-10-24T03:59:00.000Z","power":30508.0,"irradiation":0.663661438},{"timestamp":"2016-10-24T04:01:00.000Z","power":30832.0,"irradiation":0.6693660278},{"timestamp":"2016-10-24T04:03:00.000Z","power":31061.0,"irradiation":0.6848269653},{"timestamp":"2016-10-24T04:04:00.000Z","power":31195.0,"irradiation":0.6839873047},{"timestamp":"2016-10-24T04:06:00.000Z","power":31399.0,"irradiation":0.6889121094},{"timestamp":"2016-10-24T04:08:00.000Z","power":31592.0,"irradiation":0.6940702515},{"timestamp":"2016-10-24T04:09:00.000Z","power":31847.0,"irradiation":0.7012942505},{"timestamp":"2016-10-24T04:11:00.000Z","power":32127.0,"irradiation":0.7146226196},{"timestamp":"2016-10-24T04:13:00.000Z","power":32352.0,"irradiation":0.7216533813},{"timestamp":"2016-10-24T04:14:00.000Z","power":32517.0,"irradiation":0.7255385742},{"timestamp":"2016-10-24T04:16:00.000Z","power":32675.0,"irradiation":0.7264449463},{"timestamp":"2016-10-24T04:18:00.000Z","power":32950.0,"irradiation":0.7412994385},{"timestamp":"2016-10-24T04:19:00.000Z","power":33037.0,"irradiation":0.7360480347},{"timestamp":"2016-10-24T04:21:00.000Z","power":33179.0,"irradiation":0.7390136108},{"timestamp":"2016-10-24T04:23:00.000Z","power":33432.0,"irradiation":0.7447114868},{"timestamp":"2016-10-24T04:24:00.000Z","power":33623.0,"irradiation":0.7535882568},{"timestamp":"2016-10-24T04:26:00.000Z","power":33764.0,"irradiation":0.7586863403},{"timestamp":"2016-10-24T04:28:00.000Z","power":33978.0,"irradiation":0.7633513184},{"timestamp":"2016-10-24T04:29:00.000Z","power":34274.0,"irradiation":0.7795852661},{"timestamp":"2016-10-24T04:31:00.000Z","power":34511.0,"irradiation":0.7848699951},{"timestamp":"2016-10-24T04:33:00.000Z","power":34634.0,"irradiation":0.7865027466},{"timestamp":"2016-10-24T04:34:00.000Z","power":34754.0,"irradiation":0.7880688477},{"timestamp":"2016-10-24T04:36:00.000Z","power":34960.0,"irradiation":0.7940599365},{"timestamp":"2016-10-24T04:38:00.000Z","power":35176.0,"irradiation":0.8033765259},{"timestamp":"2016-10-24T04:39:00.000Z","power":35400.0,"irradiation":0.8087145386},{"timestamp":"2016-10-24T04:41:00.000Z","power":35542.0,"irradiation":0.8089344482},{"timestamp":"2016-10-24T04:42:00.000Z","power":35695.0,"irradiation":0.8148855591},{"timestamp":"2016-10-24T04:44:00.000Z","power":35842.0,"irradiation":0.8207234497},{"timestamp":"2016-10-24T04:46:00.000Z","power":36013.0,"irradiation":0.8280140991},{"timestamp":"2016-10-24T04:47:00.000Z","power":36036.0,"irradiation":null}];

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

            var power_timestamps = [], power_data = [], irradiation_timestamps = [], irradiation_data = [];

            for(var n = 0; n < data.length; n++) {
                var power_date = new Date(data[n].timestamp);
                power_date = dateFormat(power_date, "yyyy-mm-dd HH:MM:ss");
                var power_value = parseFloat(data[n].power);
                power_timestamps.push(power_date);
                power_data.push(power_value);

                var irradiation_value = parseFloat(data[n].irradiation);
                irradiation_data.push(irradiation_value);
            }

            var name1 = 'Power';
            var name2 = 'Irradiation';
            var title_dual_axis_chart = 'Power & Irradiation';
            var div_name = 'power_irradiation';
            var page = 1;

            dual_axis_chart_plotly(power_timestamps, power_data, power_timestamps, irradiation_value, name1, name2, title_dual_axis_chart, 0, 0, div_name, page);

            // populate the data array and calculate the day_energy
            /*for(var n= data.length-1; n >=0 ; n--) {
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

            plant_irradiation_power_generation_chart(st, arrayData, irradiation_reading);*/

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