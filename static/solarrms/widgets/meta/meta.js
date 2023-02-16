$(document).ready(function() {
    meta_widget();
});

function get_dates_last_2week(){
    // get the end date as the selected/today's date
    var etw = new Date();
    // prepare a start date
    var stw = new Date(etw.getTime());
    etw = new Date(etw.setDate(etw.getDate() + 1));
    stw = new Date(stw.setDate(etw.getDate() - 14));
    // convert them into strings
    stw = dateFormat(stw, "yyyy-mm-dd");
    etw = dateFormat(etw, "yyyy-mm-dd");

    return [stw, etw];
}

function meta_widget() {

    if(plant_slug == "uran") {
        $("#uran_meta").append("<hr class='mar-no' style='padding-bottom: 7px'><span class='pull-left text-lg text-semibold'>Owner: Seabird Marines <br>Panel type: 310wp Renesola Poly <br>Power temp. coefficient: -0.40% per degree <br>Panel tilt: -10° <br>Inverter types: 50kw-Delta</span>");
    } else if(plant_slug == "rrkabel") {
        $("#rrkabel_meta").append("<hr class='mar-no' style='padding-bottom: 7px'><span class='pull-left text-lg text-semibold'>Owner: R R Kabel <br>Panel type: 315wp JA Solar Poly <br>Power temp. coefficient: -0.410 %/degree <br>Panel tilt: -4° <br>Inverter types: 50kw-Delta</span>");
    } else {
        $("#all_meta").append("<h3><a style='color:white' href={% url 'solar:inverters-status' plant.slug %}>" + present_devices_disconnected + " Devices Disconnected</a></h3></span>");
        $("#sparkline_all").append("<div class='pad-btm pad-lft pad-rgt text-center'><div id='demo-sparkline-line'></div></div>");
        last_weeks_energy_data();
    }

    var inverters_status_info = inverters_status_function();

    $("#devices_disconnected").append(present_devices_disconnected);

    var performance_ratio = inverters_status_info.performance_ratio;
    if(performance_ratio != undefined && performance_ratio != "NA") {
        performance_ratio = performance_ratio.toFixed(2);
        $('#performance_ratio').text((parseFloat(performance_ratio)).toString());
    } else {
        $('#performance_ratio').text("NA");   
    }

    var plant_generation_today = inverters_status_info.plant_generation_today;
    if(plant_generation_today != undefined && plant_generation_today != "NA") {
        $("#generation_today").text((parseFloat(plant_generation_today)).toFixed(2).toString().concat(" kWh"));
    }
}

function last_weeks_energy_data() {

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
            for(var n= data.length-1; n >=0 ; n--) {
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