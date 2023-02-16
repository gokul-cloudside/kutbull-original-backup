
// Widgets.js
// ====================================================================
// This file should not be included in your project.
// This is just a sample how to initialize plugins or components.
//
// - ThemeOn.net -


$(document).ready(function() {
	// GAUGE PLUGIN
	// =================================================================
	// Require Gauge.js
	// -----------------------------------------------------------------
	// http://bernii.github.io/gauge.js/
	// =================================================================

	var opts = {
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

	var target = document.getElementById('current-power'); // your canvas element
	var gauge = new Gauge(target).setOptions(opts);
	gauge.maxValue = plant_capacity; // set max gauge value
	gauge.animationSpeed = 32; // set animation speed (32 is default value)
	gauge.set(1);
	gauge.set(0);
	if( current_power > 0) {
		gauge.set(current_power); // set actual value
	} else {
	}

	// WEATHER UPDATE
	// =================================================================
	// OPENWEATHERMAP
	$.ajax({
    	type: "GET",
     	url: "http://api.openweathermap.org/data/2.5/weather?q=".concat(plant_location).concat("&appid=55a58424ea4a9952725a85746ecb3ecb"),
    	success: function(weather_data) {
			var temp = weather_data.main.temp - 273.15;
			$('#temperature').text(Math.round(temp).toString().concat(String.fromCharCode(176)));
    		var max_temp = weather_data.main.temp_max;
    		max_temp = max_temp - 273.15;
    		var min_temp = weather_data.main.temp_min;
    		min_temp = min_temp - 273.15;
			$('#minmax').text(Math.round(max_temp).toString().concat(String.fromCharCode(176)).concat("/").concat(Math.round(min_temp).toString().concat(String.fromCharCode(176))));
    		var wind = weather_data.wind.speed;
			$('#windspeed').text(Math.round(wind).toString().concat("mps"));
    		var clouds_description = weather_data.weather[0].description;
			$('#comments').text(clouds_description);
    		var humidity = weather_data.main.humidity;
			$('#humidity').text(Math.round(humidity).toString().concat("%"));
      	},
      	error: function(weather_data){
        	console.log("no data");
      	}
   	});
    
    get_dates_last_2week();
	limit_plant_future_date();
    last_weeks_energy_data();
	/*limit_plant_future_energy_month_date();*/
	power_data();

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
        console.log(mon + ' ' + sun);
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

function limit_plant_future_energy_day_date() {
    $(function(){
        $('#start_energy_day').datetimepicker({
            onShow:function( ct ){
                this.setOptions({
                    maxDate: new Date()
                })
            }
        });
    });
  }

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
    stw = new Date(stw.setDate(etw.getDate() - 14));
    // convert them into strings
    stw = dateFormat(stw, "yyyy-mm-dd");
    etw = dateFormat(etw, "yyyy-mm-dd");

    return [stw, etw];
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
            tooltipPrefix :'KWh - ',
            spotColor:'#ffffff',
            valueSpots : {
                '0:': '#ffffff'
            },
            tooltipFormatter: function(sparkline, options, field) {
                return date_values[field.x].format("dd/mm/yyyy") + ":" + field.y.toFixed(2) + " KWH";
            }
        });
    }

function redraw_window() {
    $('a[data-toggle="tab"]').on('shown.bs.tab', function (e) {
        window.dispatchEvent(new Event('resize'));
    });
  }

function get_dates(id){
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

    return [st, e];
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

/*Power Data for a day*/

function power_data() {

    var id = '#start';

    var dates = get_dates(id);
    var st = dates[0];
    var e = dates[1];

    var $el = null;
    var relTime = null;

    $.ajax({
        type: "GET",
        url: "/api/solar/plants/".concat(plant_slug).concat('/power/'),
        data: {startTime: st, endTime: e},
        beforeSend: function() {
            /*$('#power-panel-network-update').show();*/
            /*$el = $(this);
            $el.niftyOverlay('show');*/
            /*relTime = setInterval(function(){
                $el.niftyOverlay('hide');
                clearInterval(relTime);
            },2000);*/
        },
        complete: function() {
            /*$('#power-panel-network-update').hide();*/
        },
        success: function(data) {
            if(data == '') {
                $("#power_chart").empty();
                $("#power_chart").append("<div class='alert alert-warning'> No data for the date </div>");

                $(".plant-power-generation h2").empty();
                return;
            } else {
                $("#power_chart").empty();
                $("#power_chart").append("<svg></svg>");
            }

            var arrayData = [];

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

            // package the data
            //var packagedData = [{
            //    "key": "PLANT GENERATION ON DATE " + dateFormat(st, "yyyy-mm-dd") + " in kW",
            //    "values": arrayData,
            //    "color": "#4C85AB"
            //}];
            // plot the chart
            plant_power_generation_chart(st, arrayData);
            /*#B4D3E5*/
        },
        error: function(data) {
            console.log("error_streams_data");
            data = null;
        },
    });
    return 1;
}

function plant_power_generation_chart(st, data) {
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
                    if(key.point[1] !=  '0') {
                        return '<p>' + key.point[0].format("dd/mm/yyyy HH:MM") + " : " + key.point[1].toFixed(2) + ' KW' + '</p>' ;
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
                    return d3.time.format('%H:%M %d/%m')(new Date(d))
                });

            live_chart.yAxis
                  .axisLabel("Power (kW)")
                  .tickFormat(d3.format(",.2f"));
            
            live_chart.interactiveLayer.tooltip.headerFormatter(function (d) {
                return d3.time.format('%x %-I %p')(new Date(d));
            });
            d3.select('#power_chart svg')
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

/*Energy Data for a month*/