$(document).ready(function() {

    $("#breadcrumb_page_path").empty();
    $("#breadcrumb_page_path").append('<li class="text-center text-bold" ><a href="#">Client</a></li><li class="text-center text-bold"><a href="#">Client Dashboard</a></li><li class="text-center text-bold"><a href="#">Plant Dashboard</a></li><li class="text-center text-bold"><a href="#">Performance Ratio</a></li>');

    limit_plant_future_performance_ratio_day_date();
	if(plant_metadata_calculate_hourly_pr) {
        day_performance_ratio_data();
    } else {
        $("#weeklist").addClass("active");
        $("#week_performance_ratio-lft").addClass("in active");
        week_performance_ratio_data();
    }
});

$(function() {
    $(".datetimepicker_start_performance_ratio_day").datetimepicker({
        timepicker: false,
        format: 'd/m/Y',
        scrollMonth:false,
        scrollTime:false,
        scrollInput:false
    });
    $(".datetimepicker_start_performance_ratio_day").on('change', function(ev) {
        $(this).datetimepicker('hide');
    });
});

$(function() {
    $("#start_performance_ratio_month").MonthPicker({
        Button: false
    });
});        


function limit_plant_future_performance_ratio_day_date() {
    $(function(){
        $('#start_performance_ratio_day').datetimepicker({
            onShow:function( ct ){
                this.setOptions({
                    maxDate: new Date()
                })
            }
        });
    });
  }

function get_dates(id){
    // get the start date
    var st = $(id).val();
    /*var st = new Date();*/
    if (st == '') {
        st = new Date();
    } else {
        var date = [];
        date = st.split('/');
        st = date[2] + "/" + date[1] + "/" + date[0];
        st = new Date(st);
    }
    // prepare an end date
    var e = new Date(st.getTime());
    e = new Date(e.setDate(st.getDate() + 1));
    // convert them into strings

    st = dateFormat(st, "yyyy-mm-dd");
    e = dateFormat(e, "yyyy-mm-dd");

    return [st, e];
}

function get_dates_performance_ratio_week(id){
    // get the start date
    var st = $(id).val();
    /*var st = new Date();*/
    if (st == '') {
        st = new Date();
    } else {
        var date = [];
        date = st.split('/');
        st = date[2] + "/" + date[1] + "/" + date[0];
        st = new Date(st);
    }
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
        var date = [];
        date = etw.split('/');
        etw = date[2] + "/" + date[1] + "/" + date[0];
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
    var etw = $('#start_performance_ratio_month').val();

    if (etw == '') {
        etw = new Date();
        etw.setMonth(etw.getMonth()+1);
        etw.setDate(0);

        etw = dateFormat(etw, "yyyy-mm-dd");

        // prepare a start date
        var stw = new Date(etw);
        stw = dateFormat(stw, "yyyy-mm-dd");
        var st = stw.split("-");
        stw = st[0] + "-" + st[1] + "-" + "01";
    } else {
        var e = etw.split("/");
        var stw = e[1] + "-" + e[0] + "-" + "01";
        var date = new Date(stw);
        var lastDay = new Date(date.getFullYear(), date.getMonth() + 1, 0);
        etw = e[1] + "-" + e[0] + "-" + lastDay.getDate();
    }

    return [stw, etw];
}

/*$(function() {
    $("#start_performance_ratio_week").datePicker({selectWeek:true,closeOnSelect:false});
});*/

function dates_performance_ratio_week() {

    var default_date = $('#start_performance_ratio_week').val();

    if(default_date == '') {
        var today = new Date();
        var mon = new Date();
        mon.setDate(mon.getDate() + 1 - (mon.getDay() || 7));
        var sun = new Date(mon.getTime());
        sun.setDate(sun.getDate() + 6);
        mon = dateFormat(mon, "yyyy-mm-dd");
        sun = dateFormat(sun, "yyyy-mm-dd");
        /*$("badge-row-performance_ratio-week").append("<div class='pull-left'>The chart for week : </div>")*/
        $("#week_range_start").empty();
        $("#week_range_start").append("<div id='week_start_date' value='"+mon+"'>"+mon+"</div>");

        $("#week_range_to").empty();
        $("#week_range_to").append("<div id='week_start_to'> to </div>");

        $("#week_range_end").empty();
        $("#week_range_end").append("<div id='week_end_date' value='"+sun+"'>"+sun+"</div>");
    } 
            
    $('#start_performance_ratio_week').datepicker({onSelect: function() {
        var mon = $(this).datepicker('getDate');
        mon.setDate(mon.getDate() + 1 - (mon.getDay() || 7));
        var sun = new Date(mon.getTime());
        sun.setDate(sun.getDate() + 6);
        mon = dateFormat(mon, "yyyy-mm-dd");
        sun = dateFormat(sun, "yyyy-mm-dd");
        $("#week_range_start").empty();
        $("#week_range_start").append("<div id='week_start_date' value='"+mon+"'>"+mon+"</div>");

        $("#week_range_to").empty();
        $("#week_range_to").append("<div id='week_start_to'> to </div>");

        $("#week_range_end").empty();
        $("#week_range_end").append("<div id='week_end_date' value='"+sun+"'>"+sun+"</div>");

    /*alert(mon + ' ' + sun);*/
    }});

}

jQuery('#weektab').click(function (e) {
    e.preventDefault();
    jQuery(this).tab('show');
    jQuery(window).trigger('resize'); // Added this line to force NVD3 to redraw the chart
});

function redraw_window() {
    $('a[data-toggle="tab"]').on('shown.bs.tab', function (e) {
        e.preventDefault();
        window.dispatchEvent(new Event('resize'));
    });
  }

/*performance_ratio Data for a month*/

function month_performance_ratio_data() {
    var dates = get_month_dates();
    st = dates[0];
    e = dates[1];
    
    $.ajax({
        type: "GET",
        url: "/api/solar/plants/".concat(plant_slug).concat('/performance/'),
        data: {startTime: (st), endTime: (e), aggregator: "DAY"},
        success: function(data) {
            if(data == '') {
                $("#month_performance_ratio_chart").empty();
                $("#month_performance_ratio_no_data").empty();
                $("#month_performance_ratio_no_data").append("<div class='alert alert-warning'>No data for the month</div>");
                return;
            } else {
                $("#month_performance_ratio_no_data").empty();
                $("#month_performance_ratio_chart").empty();
                $("#month_performance_ratio_chart").append("<div class='row' id='month_bar_chart'></div>");
                $("#month_performance_ratio_chart").append("<svg></svg>");
            }

            var y_date = new Date();
            var day_performance_ratio = 0;
            var cumulative_performance_ratio = 0;
            var arrayData = [];

            var month_counter = 0;

            var data_index = 0;

            // populate the data array and calculate the day_performance_ratio
            for(var n= data.length-1; n >=0 ; n--) {
                day_performance_ratio = parseFloat(data[n].performance_ratio);
                if(data[n].pvsyst_pr) {
                    
                    data_index = n;
                    month_counter++;

                }
                y_date = new Date(data[n].timestamp);
                y_date = dateFormat(y_date, "yyyy/mm/dd");
                arrayData.push({"label": y_date, "value": (day_performance_ratio.toFixed(3))});
            }

            // package the data
            var packagedData = [{
                "key": "PERFORMANCE RATIO GENERATION OF THIS MONTH FROM" + dateFormat(st, "yyyy-mm-dd") + "to" + dateFormat(e, "yyyy-mm-dd") + day_performance_ratio,
                "values": arrayData
            }];

            if(month_counter > 0) {

                var month_pvsyst_expected = parseFloat(data[data_index].pvsyst_pr).toFixed(2);

                var month_is = new Date(data[data_index].timestamp);
                month_is = parseInt(dateFormat(month_is, "mm"));

                var month = ["January", "February", "March", "April", "May", "June","July", "August", "September", "October", "November", "December"];

                $("#month_performance_ratio_expected").empty();
                $("#month_performance_ratio_expected").append("<div class='col-lg-2'></div><div class='col-lg-8'><h3 class='month_pvsyst text-center'>PVsyst PR for <span id='month_pr_pvsyst'></span> : <span id='month_pr_data'></span></h3></div>");

                $("#month_pr_pvsyst").empty();
                $("#month_pr_pvsyst").append(month[month_is]);
                $("#month_pr_data").empty();
                $("#month_pr_data").append(month_pvsyst_expected);
            }

            // plot the chart
            monthly_bar_chart(packagedData);
        },
        error: function(data) {
            console.log("error_streams_data");
            data = null;
        }
    });
}
function monthly_bar_chart(packagedData){
    nv.addGraph(function() {
      var chart = nv.models.discreteBarChart()
            .x(function(d) { return d.label })    //Specify the data accessors.
            .y(function(d) { return d.value })
            .showValues(true)
            .color(['#B4D3E5'])
            /*#ff7f0e*/
            .margin({top: 5, right: 0, bottom: 70, left: 40})
            /*.tooltipContent(function(key, y, e, graph) {
                if(key.data.value !=  '0') {
                    return '<p>' + key.data.label + " : " + key.data.value.toFixed(2) + '</p>' ;
                }
            })*/
          ;

        chart.tooltip.enabled(false);

        chart.xAxis
            .tickFormat(function (d) {
                return d3.time.format('%d')(new Date(d))
            });

      d3.select('#month_performance_ratio_chart svg')
          .datum(packagedData)
          .call(chart);

      nv.utils.windowResize(chart.update);

      $(".nvd3-svg").css("float", "left");

      return chart;
    });
}

function day_performance_ratio_data() {

    var id = '#start_performance_ratio_day'

    var dates = get_dates(id);
    var st = dates[0];
    var et = dates[1];

    $.ajax({
        type: "GET",
        url: "/api/solar/plants/".concat(plant_slug).concat('/performance/'),
        data: {startTime: (st), endTime: (et), aggregator: "HOUR"},
        success: function(data) {
            if(data == '') {
                $("#legend-badge-row").empty();
                $("#legend-badge-row").append("<div class='col-md-4'></div><span class='badge pull-right' style='margin-top: 10px;' id='badge-row-day-performance_ratio'></span>");
                $("#badge-row-day-performance_ratio").empty();
                $("#badge-row-day-performance_ratio").append("<div class='pull-left'>The performance ratio for&nbsp;</div>")
                $("#badge-row-day-performance_ratio").append("<div id='today_date' class='pull-left'></div>");
                $("#badge-row-day-performance_ratio").append("<div id='today_performance_ratio' class='pull-left' style='margin-left: 7px;margin-right: 7px;'></div>");

                $("#today_date").empty();
                $("#today_date").append(st+" - ");
                $("#today_performance_ratio").empty();
                $("#today_performance_ratio").append("No performance ratio for this date.");
            	$("#day_performance_ratio_chart").empty();
                $("#day_performance_ratio_no_data").empty();
                $("#day_performance_ratio_no_data").append("<div class='alert alert-warning' style='margin-bottom: 0px;'>No data for the day</div>");
                return;
            } else {
                $("#day_performance_ratio_chart").empty();
                $("#day_performance_ratio_no_data").empty();
                $("#day_performance_ratio_chart").append("<svg></svg>");
            }

            /*var arrayData = [];

            // populate the data array and calculate the day_performance_ratio
            for(var n= data.length-1; n >=0 ; n--) {
                day_performance_ratio = day_performance_ratio + parseFloat(data[n].performance_ratio);
                arrayData.push([new Date(data[n].timestamp), parseFloat(data[n].performance_ratio)]);
            }
            day_performance_ratio = day_performance_ratio.toFixed(2);*/

            var arrayData = [];

            $.ajax({
                type: "GET",
                url: "/api/solar/plants/".concat(plant_slug).concat('/performance/'),
                data: {startTime: st, endTime: et, aggregator: "DAY"},
                success: function(data) {
                    $("#legend-badge-row").empty();
                    $("#legend-badge-row").append("<div class='col-md-4'></div><span class='badge' style='margin-top: 10px;' id='badge-row-day-performance_ratio'></span>");
                    $("#badge-row-day-performance_ratio").empty();
                    $("#badge-row-day-performance_ratio").append("<div class='pull-left'>The performance ratio for&nbsp;</div>")
                    $("#badge-row-day-performance_ratio").append("<div id='today_date' class='pull-left'></div>");
                    $("#badge-row-day-performance_ratio").append("<div id='today_performance_ratio' class='pull-left' style='margin-left: 7px;margin-right: 7px;'></div>");

                    var day_performance_ratio = data[0].performance_ratio;
                    day_performance_ratio = day_performance_ratio.toFixed(3);
                    $("#today_date").empty();
                    $("#today_date").append(st+" - ");
                    $("#today_performance_ratio").empty();
                    $("#today_performance_ratio").append(day_performance_ratio);

                    if(data[0].pvsyst_pr) {

                        var pvsyst_pr_day = (parseFloat(data[0].pvsyst_pr)).toFixed(2);

                        $("#day_performance_ratio_expected").empty();
                        $("#day_performance_ratio_expected").append("<div class='col-lg-2'></div><div class='col-lg-8'><h3 class='day_pvsyst text-center'>PVsyst PR for " + dateFormat(st, 'dd-mm-yyyy') + " : " + pvsyst_pr_day + "</h3></div>");
                    }
                },
                error: function(data) {
                    console.log("error_streams_data");
                    data = null;
                },
            });

            // populate the data array and calculate the day_performance_ratio
            for(var n= data.length-1; n >=0 ; n--) {
				var local_values = [];
				var ts = new Date(data[n].timestamp);

				local_values.push([ts, 0.0]);
                local_values.push([new Date(ts.setSeconds(ts.getSeconds() + 1)), parseFloat(data[n].performance_ratio)]);
				arrayData.push({"values": local_values,
								"key": dateFormat(data[n].timestamp, 'yyyy-mm-dd HH:MM:ss').concat(" : ").concat(parseFloat(data[n].performance_ratio).toString()),
								"color":"#4C85AB"});
            }

            // package the data
            /*var packagedData = [{
                "key": "performance_ratio GENERATION ON DATE " + dateFormat(st, "yyyy-mm-dd") + " in kW",
                "values": arrayData,
                "color": "#4C85AB"
            }];*/
            // plot the chart
            day_line_performance_ratio_chart(arrayData);
        },
        error: function(data) {
            console.log("error_streams_data");
            data = null;
        }
    });
}

function day_line_performance_ratio_chart(data) {
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
            .tooltipContent(function(key, y, e, graph) {
                if(key.point[1] !=  '0') {
                    return '<p>' + key.point[0].format("dd/mm/yyyy HH:MM") + " : " + key.point[1].toFixed(3) + '</p>' ;
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
              .axisLabel("Performance Ratio")
              .tickFormat(d3.format(",.2f"));
        
        live_chart.interactiveLayer.tooltip.headerFormatter(function (d) {
            return d3.time.format('%x %-I %p')(new Date(d));
        });
        d3.select('#day_performance_ratio_chart svg')
                  .datum(data)
                  .call(live_chart);
        nv.utils.windowResize(live_chart.update);

        $(".nvd3-svg").css("float", "left");

        return live_chart;
    });
}

function week_performance_ratio_data() {

    dates_performance_ratio_week();

    var st = $('#week_start_date').attr('value');
    var e = $('#week_end_date').attr('value');
    
    $.ajax({
        type: "GET",
        url: "/api/solar/plants/".concat(plant_slug).concat('/performance/'),
        data: {startTime: (st), endTime: (e), aggregator: "DAY"},
        success: function(data) {
            if(data == '') {
                $("#week_performance_ratio_chart").empty();
                $("#week_performance_ratio_no_data").empty();
                $("#week_performance_ratio_no_data").append("<div class='alert alert-warning'>No data for the week</div>");
                return;
            } else {
                $("#week_performance_ratio_chart").empty();
                $("#week_performance_ratio_no_data").empty();
                $("#week_performance_ratio_chart").append("<svg></svg>");
            }

            var y_date = new Date();
            var day_performance_ratio = 0;
            var cumulative_performance_ratio = 0;
            var arrayData = [];

            var week_counter = 0;

            // populate the data array and calculate the day_performance_ratio
            for(var n= data.length-1; n >=0 ; n--) {
                day_performance_ratio = parseFloat(data[n].performance_ratio);
                if(data[n].pvsyst_pr) {
                    week_counter++;
                }
                cumulative_performance_ratio = cumulative_performance_ratio + parseFloat(data[n].performance_ratio);
                y_date = new Date(data[n].timestamp);
                y_date = dateFormat(y_date, "yyyy/mm/dd");
                arrayData.push({"label": y_date, "value": (day_performance_ratio.toFixed(3))});
            }

            // package the data
            var packagedData = [{
                "key": "performance_ratio generation of this week from" + dateFormat(st, "yyyy-mm-dd") + "to" + dateFormat(e, "yyyy-mm-dd") + day_performance_ratio,
                "values": arrayData
            }];

            if(week_counter > 0) {

                $("#week_performance_ratio_expected").empty();
                $("#week_performance_ratio_expected").append("<div class='col-lg-2'></div><div class='col-lg-8'><h3 class='week_pvsyst text-center'>PVsyst PR for the week : </h3><br/><h5 class='text-center'><span id='pvsyst_week_per_day' style='font-size: 19px;'></span></h5></div>")

                for(var i = 0; i < data.length; i++) {

                    if(data[i].pvsyst_pr) {
                        var pvsyst_expected_day = (parseFloat(data[i].pvsyst_pr).toFixed(2));
                        y_date = new Date(data[i].timestamp);
                        y_date = dateFormat(y_date, "yyyy/mm/dd");
                        if(i == data.length-1) {
                            $("#pvsyst_week_per_day").append(y_date + " : " + pvsyst_expected_day);
                        } else {
                            $("#pvsyst_week_per_day").append(y_date + " : " + pvsyst_expected_day + ", ");
                        }
                    }

                }
            }

            // plot the chart
            weekly_bar_chart(packagedData);
        },
        error: function(data) {
            console.log("error_streams_data");
            data = null;
        }
    });
}
function weekly_bar_chart(packagedData){
    nv.addGraph(function() {
      var chart = nv.models.discreteBarChart()
            .x(function(d) { return d.label })    //Specify the data accessors.
            .y(function(d) { return d.value })
            .showValues(true)
            .color(['#B4D3E5'])
            .margin({top: 5, right: 0, bottom: 12, left: 0})
            /*.tooltipContent(function(key, y, e, graph) {
                if(key.data.value !=  '0') {
                    return '<p>' + key.data.label + " : " + key.data.value.toFixed(2) + '</p>' ;
                }
            })*/;

        chart.tooltip.enabled(false);

        d3.select('#week_performance_ratio_chart svg')
            .datum(packagedData)
            .call(chart);

        nv.utils.windowResize(chart.update);

        $(".nvd3-svg").css("float", "left");

        return chart;
    });
}