$(document).ready(function() {

    $("#breadcrumb_page_path").empty();
    $("#breadcrumb_page_path").append('<li class="text-center text-bold" ><a href="#">Client</a></li><li class="text-center text-bold"><a href="#">Client Dashboard</a></li><li class="text-center text-bold"><a href="#">Plant Dashboard</a></li><li class="text-center text-bold"><a href="#">CUF</a></li>')

    limit_plant_future_cuf_day_date();
	if(plant_metadata_calculate_hourly_pr) {
        day_cuf_data();
    } else {
        $("#weeklist").addClass("active");
        $("#week_cuf-lft").addClass("in active");
        week_cuf_data();
    }
});

$(function() {
    $(".datetimepicker_start_cuf_day").datetimepicker({
        timepicker: false,
        format: 'd/m/Y',
        scrollMonth:false,
        scrollTime:false,
        scrollInput:false
    });
    $(".datetimepicker_start_cuf_day").on('change', function(ev) {
        $(this).datetimepicker('hide');
    });
});

$(function() {
    $("#start_cuf_month").MonthPicker({
        Button: false
    });
});        


function limit_plant_future_cuf_day_date() {
    $(function(){
        $('#start_cuf_day').datetimepicker({
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

function get_dates_cuf_week(id){
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
    var etw = $('#start_cuf_month').val();

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
    $("#start_cuf_week").datePicker({selectWeek:true,closeOnSelect:false});
});*/

function dates_cuf_week() {

    var default_date = $('#start_cuf_week').val();

    if(default_date == '') {
        var today = new Date();
        var mon = new Date();
        mon.setDate(mon.getDate() + 1 - (mon.getDay() || 7));
        var sun = new Date(mon.getTime());
        sun.setDate(sun.getDate() + 6);
        mon = dateFormat(mon, "yyyy-mm-dd");
        sun = dateFormat(sun, "yyyy-mm-dd");
        /*$("badge-row-cuf-week").append("<div class='pull-left'>The chart for week : </div>")*/
        $("#week_range_start").empty();
        $("#week_range_start").append("<div id='week_start_date' value='"+mon+"'>"+mon+"</div>");

        $("#week_range_to").empty();
        $("#week_range_to").append("<div id='week_start_to'> to </div>");

        $("#week_range_end").empty();
        $("#week_range_end").append("<div id='week_end_date' value='"+sun+"'>"+sun+"</div>");
    } 
            
    $('#start_cuf_week').datepicker({onSelect: function() {
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

/*cuf Data for a month*/

function month_cuf_data() {
    var dates = get_month_dates();
    st = dates[0];
    e = dates[1];
    
    $.ajax({
        type: "GET",
        url: "/api/solar/plants/".concat(plant_slug).concat('/CUF/'),
        data: {startTime: (st), endTime: (e), aggregator: "DAY"},
        success: function(data) {
            if(data == '') {
                $("#month_cuf_chart").empty();
                $("#month_cuf_no_data").empty();
                $("#month_cuf_no_data").append("<div class='alert alert-warning'>No data for the month</div>");
                return;
            } else {
                $("#month_cuf_no_data").empty();
                $("#month_cuf_chart").empty();
                $("#month_cuf_chart").append("<div class='row' id='month_bar_chart'></div>");
                $("#month_cuf_chart").append("<svg></svg>");
            }

            var y_date = new Date();
            var day_cuf = 0;
            var cumulative_cuf = 0;
            var arrayData = [];

            // populate the data array and calculate the day_cuf
            for(var n= data.length-1; n >=0 ; n--) {
                day_cuf = parseFloat(data[n].cuf);
                y_date = new Date(data[n].timestamp);
                y_date = dateFormat(y_date, "yyyy/mm/dd");
                arrayData.push({"label": y_date, "value": (day_cuf.toFixed(3))});
            }

            // package the data
            var packagedData = [{
                "key": "cuf GENERATION OF THIS MONTH FROM" + dateFormat(st, "yyyy-mm-dd") + "to" + dateFormat(e, "yyyy-mm-dd") + day_cuf,
                "values": arrayData
            }];
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

      d3.select('#month_cuf_chart svg')
          .datum(packagedData)
          .call(chart);

      nv.utils.windowResize(chart.update);

      $(".nvd3-svg").css("float", "left");

      return chart;
    });
}

function day_cuf_data() {

    var id = '#start_cuf_day'

    var dates = get_dates(id);
    var st = dates[0];
    var et = dates[1];

    $.ajax({
        type: "GET",
        url: "/api/solar/plants/".concat(plant_slug).concat('/CUF/'),
        data: {startTime: (st), endTime: (et), aggregator: "HOUR"},
        success: function(data) {
            if(data == '') {
                $("#legend-badge-row").empty();
                $("#legend-badge-row").append("<div class='col-md-4'></div><span class='badge pull-right' style='margin-top: 10px;' id='badge-row-day-cuf'></span>");
                $("#badge-row-day-cuf").empty();
                $("#badge-row-day-cuf").append("<div class='pull-left'>The cuf for&nbsp;</div>")
                $("#badge-row-day-cuf").append("<div id='today_date' class='pull-left'></div>");
                $("#badge-row-day-cuf").append("<div id='today_cuf' class='pull-left' style='margin-left: 7px;margin-right: 7px;'></div>");

                $("#today_date").empty();
                $("#today_date").append(st+" - ");
                $("#today_cuf").empty();
                $("#today_cuf").append("No cuf for this date.");
            	$("#day_cuf_chart").empty();
                $("#day_cuf_no_data").empty();
                $("#day_cuf_no_data").append("<div class='alert alert-warning' style='margin-bottom: 0px;'>No data for the day</div>");
                return;
            } else {
                $("#day_cuf_chart").empty();
                $("#day_cuf_no_data").empty();
                $("#day_cuf_chart").append("<svg></svg>");
            }

            /*var arrayData = [];

            // populate the data array and calculate the day_cuf
            for(var n= data.length-1; n >=0 ; n--) {
                day_cuf = day_cuf + parseFloat(data[n].cuf);
                arrayData.push([new Date(data[n].timestamp), parseFloat(data[n].cuf)]);
            }
            day_cuf = day_cuf.toFixed(2);*/

            var arrayData = [];

            $.ajax({
                type: "GET",
                url: "/api/solar/plants/".concat(plant_slug).concat('/CUF/'),
                data: {startTime: st, endTime: et, aggregator: "DAY"},
                success: function(data) {
                    $("#legend-badge-row").empty();
                    $("#legend-badge-row").append("<div class='col-md-4'></div><span class='badge' style='margin-top: 10px;' id='badge-row-day-cuf'></span>");
                    $("#badge-row-day-cuf").empty();
                    $("#badge-row-day-cuf").append("<div class='pull-left'>The cuf for&nbsp;</div>")
                    $("#badge-row-day-cuf").append("<div id='today_date' class='pull-left'></div>");
                    $("#badge-row-day-cuf").append("<div id='today_cuf' class='pull-left' style='margin-left: 7px;margin-right: 7px;'></div>");

                    var day_cuf = data[0].cuf;
                    day_cuf = day_cuf.toFixed(3);
                    $("#today_date").empty();
                    $("#today_date").append(st+" - ");
                    $("#today_cuf").empty();
                    $("#today_cuf").append(day_cuf);    
                },
                error: function(data) {
                    console.log("error_streams_data");
                    data = null;
                },
            });

            // populate the data array and calculate the day_cuf
            for(var n= data.length-1; n >=0 ; n--) {
				var local_values = [];
				var ts = new Date(data[n].timestamp);

				local_values.push([ts, 0.0]);
                local_values.push([new Date(ts.setSeconds(ts.getSeconds() + 1)), parseFloat(data[n].cuf)]);
				arrayData.push({"values": local_values,
								"key": dateFormat(data[n].timestamp, 'yyyy-mm-dd HH:MM:ss').concat(" : ").concat(parseFloat(data[n].cuf).toString()),
								"color":"#4C85AB"});
            }

            // package the data
            /*var packagedData = [{
                "key": "cuf GENERATION ON DATE " + dateFormat(st, "yyyy-mm-dd") + " in kW",
                "values": arrayData,
                "color": "#4C85AB"
            }];*/
            // plot the chart
            day_line_cuf_chart(arrayData);
        },
        error: function(data) {
            console.log("error_streams_data");
            data = null;
        }
    });
}

function day_line_cuf_chart(data) {
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
              .axisLabel("cuf")
              .tickFormat(d3.format(",.2f"));
        
        live_chart.interactiveLayer.tooltip.headerFormatter(function (d) {
            return d3.time.format('%x %-I %p')(new Date(d));
        });
        d3.select('#day_cuf_chart svg')
                  .datum(data)
                  .call(live_chart);
        nv.utils.windowResize(live_chart.update);

        $(".nvd3-svg").css("float", "left");

        return live_chart;
    });
}

function week_cuf_data() {

    dates_cuf_week();

    var st = $('#week_start_date').attr('value');
    var e = $('#week_end_date').attr('value');
    
    $.ajax({
        type: "GET",
        url: "/api/solar/plants/".concat(plant_slug).concat('/CUF/'),
        data: {startTime: (st), endTime: (e), aggregator: "DAY"},
        success: function(data) {
            if(data == '') {
                $("#week_cuf_chart").empty();
                $("#week_cuf_no_data").empty();
                $("#week_cuf_no_data").append("<div class='alert alert-warning'>No data for the week</div>");
                return;
            } else {
                $("#week_cuf_chart").empty();
                $("#week_cuf_no_data").empty();
                $("#week_cuf_chart").append("<svg></svg>");
            }

            var y_date = new Date();
            var day_cuf = 0;
            var cumulative_cuf = 0;
            var arrayData = [];

            // populate the data array and calculate the day_cuf
            for(var n= data.length-1; n >=0 ; n--) {
                day_cuf = parseFloat(data[n].cuf);
                cumulative_cuf = cumulative_cuf + parseFloat(data[n].cuf);
                y_date = new Date(data[n].timestamp);
                y_date = dateFormat(y_date, "yyyy/mm/dd");
                arrayData.push({"label": y_date, "value": (day_cuf.toFixed(3))});
            }

            // package the data
            var packagedData = [{
                "key": "cuf generation of this week from" + dateFormat(st, "yyyy-mm-dd") + "to" + dateFormat(e, "yyyy-mm-dd") + day_cuf,
                "values": arrayData
            }];
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

        d3.select('#week_cuf_chart svg')
            .datum(packagedData)
            .call(chart);

        nv.utils.windowResize(chart.update);

        $(".nvd3-svg").css("float", "left");

        return chart;
    });
}