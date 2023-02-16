$(document).ready(function() {

    $("#breadcrumb_page_path").empty();
    $("#breadcrumb_page_path").append('<li class="text-center text-bold" ><a href="#">Client</a></li><li class="text-center text-bold"><a href="#">Client Dashboard</a></li><li class="text-center text-bold"><a href="#">Plant Dashboard</a></li><li class="text-center text-bold"><a href="#">Power</a></li>')

    /*limit_plant_future_date();
    limit_plant_future_week_date();*/
});

var week_day_energy = [];

$('.datepicker_start_days').datepicker({
    autoclose: true,
    todayHighlight: true,
    startView: "days",
    minViewMode: "days",
    format: "dd-mm-yyyy"
});

$("#power_irradiation-li").on('click', function() {
    if($("#power_irradiation-li").hasClass("disabled") == false) {
        var st = $(".datepicker_start_days").val();

        if(st == "") {
            st = new Date();
        } else {
            st = st.split("-");
            st = st[2] + "-" + st[1] + "-" +st[0];
            st = new Date(st);    
        }
        st.setDate(st.getDate() - 1);
        st = dateFormat(st, "dd-mm-yyyy");

        $(".datepicker_start_days").val(st);
        power_irradiation_chart("chart");
    }
})

$("#power_irradiation-li-next").on('click', function() {
    if($("#power_irradiation-li-next").hasClass("disabled") == false) {
        var st = $(".datepicker_start_days").val();

        if(st == "") {
            st = new Date();
        } else {
            st = st.split("-");
            st = st[2] + "-" + st[1] + "-" +st[0];
            st = new Date(st);
        }
        st.setDate(st.getDate() + 1);
        st = dateFormat(st, "dd-mm-yyyy");

        $(".datepicker_start_days").val(st);
        power_irradiation_chart("chart");
    }
})

/*$(function() {
    $(".datetimepicker_start_week").datetimepicker({
        timepicker: false,
        format: 'd/m/Y',
        scrollMonth:false,
        scrollTime:false,
        scrollInput:false
    });
    $(".datetimepicker_start_week").on('change', function(ev) {
        $(this).datetimepicker('hide');
    });
});

$(function() {
    $(".datetimepicker_start_day").datetimepicker({
        timepicker: false,
        format: 'd/m/Y',
        scrollMonth:false,
        scrollTime:false,
        scrollInput:false
    });
    $(".datetimepicker_start_day").on('change', function(ev) {
        $(this).datetimepicker('hide');
    });
});

function limit_plant_future_week_date() {
    $(function(){
        $('#start_week').datetimepicker({
            onShow:function( ct ){
                this.setOptions({
                    maxDate: new Date()
                })
            }
        });
    });
  }

  function limit_plant_future_date() {
    $(function(){
        $('#start_day').datetimepicker({
            onShow:function( ct ){
                this.setOptions({
                    maxDate: new Date()
                })
            }
        });
    });
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
}*/

function redraw_window() {
    $('a[data-toggle="tab"]').on('shown.bs.tab', function (e) {
        window.dispatchEvent(new Event('resize'));
    });
  }

function get_dates(){
    // get the start date
    var st = $(".datepicker_start_days").val();
    console.log(st)

    /*var st = new Date();*/
    st = st.split("-");
    st = st[2] + "-" + st[1] + "-" + st[0];

    /*var st = new Date();*/
    if (st == '') {
        noty_message("Please select a date!", 'error', 5000)
        return;
    } else {
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

function power_data() {

    var id = "#start_day";

    var dates = get_dates(id);
    var st = dates[0];
    var e = dates[1];

    $.ajax({
        type: "GET",
        url: "/api/solar/plants/".concat(plant_slug).concat('/power/'),
        data: {startTime: st, endTime: e},
        success: function(data) {
            if(data == '') {
                /*$("#legend-badge-row").empty();
                $("#legend-badge-row").append("<div class='col-md-4'></div><span class='badge' style='margin-top: 10px;' id='badge-row-day-energy'></span>");
                $("#badge-row-day-energy").empty();
                $("#badge-row-day-energy").append("<div class='pull-left'>The energy for&nbsp;</div>")
                $("#badge-row-day-energy").append("<div id='today_date' class='pull-left'></div>");
                $("#badge-row-day-energy").append("<div id='today_energy' class='pull-left' style='margin-left: 7px;margin-right: 7px;'></div>");
                
                $("#today_date").empty();
                $("#today_date").append(st+" - ");
                $("#today_energy").empty();
                $("#today_energy").append("No energy for this date.");*/
                $("#power_chart").empty();
                $("#power_chart_no_data").empty();
                $("#power_chart_no_data").append("<div class='alert alert-warning'> No data for the date </div>");

                $(".plant-power-generation h2").empty();
                return;
            } else {
                $("#power_chart_no_data").empty();
                $("#power_chart").empty();
                $("#power_chart").append("<div class='col-lg-2'></div><div class='col-lg-12'><h3 class='days_energy text-center'>Energy Generation for " + dateFormat(st, "dd-mm-yyyy") +" : </h3></div>");
                $("#power_chart").append("<svg></svg>");
            }

            var arrayData = [];

            $.ajax({
                type: "GET",
                url: "/api/solar/plants/".concat(plant_slug).concat('/energy/'),
                data: {startTime: st, endTime: e, aggregator: "DAY"},
                success: function(data) {
                    /*$("#legend-badge-row").empty();
                    $("#legend-badge-row").append("<div class='col-md-4'></div><span class='badge' style='margin-top: 10px;' id='badge-row-day-energy'></span>");
                    $("#badge-row-day-energy").empty();
                    $("#badge-row-day-energy").append("<div class='pull-left'>The energy for&nbsp;</div>")
                    $("#badge-row-day-energy").append("<div id='today_date' class='pull-left'></div>");
                    $("#badge-row-day-energy").append("<div id='today_energy' class='pull-left' style='margin-left: 7px;margin-right: 7px;'></div>");*/

                    var day_energy = data[0].energy;
                    day_energy = day_energy/1000;
                    day_energy = day_energy.toFixed(2);
                    /*$("#today_date").empty();
                    $("#today_date").append(st+" - ");
                    $("#today_energy").empty();
                    $("#today_energy").append(day_energy + " MWh");*/

                    $(".days_energy").append(day_energy+" MWh");
                },
                error: function(data) {
                    console.log("error_streams_data");
                    data = null;
                },
            });

            // populate the data array and calculate the day_energy
            for(var n= data.length-1; n >=0 ; n--) {
                if(data[n].power > 0) {
                    var local_values = [];
                    var ts = new Date(data[n].timestamp);

                    local_values.push([ts, 0.0]);
                    local_values.push([new Date(ts.setSeconds(ts.getSeconds() + 1)), parseFloat(data[n].power)]);
                    arrayData.push({"values": local_values,
                                    "key": dateFormat(data[n].timestamp, 'yyyy-mm-dd HH:MM:ss').concat(" : ").concat(parseFloat(data[n].power).toString()),
                                    "color":"#4C85AB"});
                }
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
                        return '<p>' + key.point[0].format("dd/mm/yyyy HH:MM") + " : " + key.point[1].toFixed(2) + ' kW' + '</p>' ;
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
            d3.select('#power_chart svg')
                      .datum(data)
                      .call(live_chart);
            nv.utils.windowResize(live_chart.update);

            $(".nvd3-svg").css("float", "left");

            return live_chart;
        });

        /*d3.select('#power_chart svg').empty();
        d3.select('#power_chart svg')
              .datum(data)
              .call(live_chart);
        nv.utils.windowResize(live_chart.update);*/
    }

function week_power_data() {
    var dates = get_dates_week();
    var st = dates[0];
    var et = dates[1];

    /*var daysOfWeek = [];
    for (var d = new Date(st); d <= new Date(et); d.setDate(d.getDate() + 1)) {
        daysOfWeek.push([new Date(d), 0]);
    }

    console.log(daysOfWeek);*/

    /*var oneDay = 24*60*60*1000;
    var firstDate = new Date(st);
    var secondDate = new Date(et);
    var diffDays = Math.round(Math.abs((firstDate.getTime() - secondDate.getTime())/(oneDay)));*/

    var ew = et.split("-");
    ew[2] = "0"+(parseInt(ew[2]) - 1);
    ew = ew[0] + "-" + ew[1] + "-" + ew[2];

    $("#week_power_range_start").empty();
    $("#week_power_range_start").append(st);
    $("#week_power_range_end").empty();
    $("#week_power_range_end").append(ew);
    $("#power_week_range_to").empty();
    $("#power_week_range_to").append("to");

    $.ajax({
        type: "GET",
        async: false,
        url: "/api/solar/plants/".concat(plant_slug).concat('/power/'),
        data: {startTime: (st), endTime: (et)},
        success: function(data) {
            if(data == '') {
                $("#row-power-day").empty();
                $("#week_power_chart").empty();
                $("#week_power_chart_no_data").empty();
                $("#week_power_chart_no_data").append("<div class='alert alert-warning'>No data for the week</div>");
                return;
            } else {
                $("#week_power_chart").empty();
                $("#week_power_chart_no_data").empty();
                $("#week_power_chart").append("<svg></svg>");
            }

            $.ajax({
                type: "GET",
                async: false,
                url: "/api/solar/plants/".concat(plant_slug).concat('/energy/'),
                data: {startTime: st, endTime: et, aggregator: "DAY"},
                success: function(data) {
                    $("#row-power-day").empty();
                    /*$("#row-power-day").append("<span class='badge' style='margin-top: 10px;'>The energy for</span>");*/
                    /*var data_packaged_array = [];
                    var t = 0;
                    for(var j = data.length - 1; j >= 0; j--) {
                        for(var k = 0; k < daysOfWeek.length - 2; k++) {
                            var date = new Date(data[j].timestamp);
                            date = dateFormat(date, "yyyy-mm-dd");
                            var k_date = dateFormat(daysOfWeek[k][0], "yyyy-mm-dd");
                            if(date == k_date) {
                                t = 1;
                            } else {
                                t = 0;
                            }
                        }
                        if(t == 1) {
                            data_packaged_array.push((data[j].energy).toFixed(2));
                        } else {
                            data_packaged_array.push("0");
                        }
                    }
                    console.log(data_packaged_array);*/
                    for(var i = data.length - 1; i >= 0; i--) {
                        var day_energy = data[i].energy;
                        day_energy = day_energy/1000;
                        day_energy = day_energy.toFixed(2);
                        var that_date = dateFormat(data[i].timestamp, 'dd/mm/yyyy');
                        week_day_energy.push([that_date, day_energy]);
                        $("#row-power-day").append("<span class='badge' style='margin-top: 10px;'> " + that_date + " - " +day_energy+ " MWh"+"</span>");
                    }
                },
                error: function(data) {
                    console.log("error_streams_data");
                    data = null;
                },
            });

            var week_power = 0;
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

            // populate the data array and calculate the day_energy
            /*for(var n= data.length-1; n >=0 ; n--) {
                arrayData.push([new Date(data[n].timestamp), parseFloat(data[n].power)]);
            }
            week_power = week_power.toFixed(2);*/

            // package the data
            /*var packagedData = [{
                "key": "PLANT GENERATION FROM " + dateFormat(st, "yyyy-mm-dd") + " TO " + dateFormat(et, "yyyy-mm-dd") + " in kW",
                "values": arrayData,
                "color": "#4C85AB"
            }];*/
            // plot the chart
            plant_week_power_generation_chart(arrayData);
        },
        error: function(data) {
            console.log("error_streams_data");
            data = null;
        }
    });
}

function plant_week_power_generation_chart(data) {
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
                    return '<p>' + key.point[0].format("dd/mm/yyyy HH:MM") + " : " + key.point[1].toFixed(2) + ' kW' + '</p>' ;
                }
            });

        live_chart.interactiveLayer.tooltip
              .headerFormatter(function(d, i) {
                return nv.models.axis().tickFormat()(d, i);
        });
        live_chart.xAxis
              .axisLabel("")
              .tickFormat(function (d) {
                return d3.time.format('%d/%m')(new Date(d))
            });
        live_chart.yAxis
              .axisLabel("Power (kW)")
              .tickFormat(d3.format(",.2f"));
        
        live_chart.interactiveLayer.tooltip.headerFormatter(function (d) {
            return d3.time.format('%x %-I %p')(new Date(d));
        });
        d3.select('#week_power_chart svg')
                  .datum(data)
                  .call(live_chart);
        nv.utils.windowResize(live_chart.update);
        return live_chart;
    });
}

$("#power_irradiation-update").on('click', function() {
    power_irradiation_chart();
})

function power_irradiation_chart() {

    var st = $(".datepicker_start_days").val();
    if (st == '') {
        noty_message("Please select a date!", 'error', 5000)
        return;
    }

    var dates = get_dates();

    var st = dates[0];
    var et = dates[1];

    $.ajax({
        type: "GET",
        url: "/api/solar/plants/".concat(plant_slug).concat('/irradiation-power/'),
        data: {startTime: (st), endTime: (et)},
        success: function(power_irradiation) {
            var power_data = [], irradiation_data = [], timestamps = [], inverters_down = [], modbus_error = [], annotation_array = [];

            if(power_irradiation) {
                for(var j = 0; j < power_irradiation.length; j++) {
                    power_data.push(power_irradiation[j].power);
                    irradiation_data.push(parseFloat(power_irradiation[j].irradiation).toFixed(2));
                    timestamps.push(new Date(power_irradiation[j].timestamp).valueOf());
                }

                var power_max_value = Math.max.apply(null, power_data);
                console.log(power_max_value);

                for(var m = 0; m < power_irradiation.length; m++) {
                    if(m < power_irradiation.length-1) {
                        if(power_irradiation[m].Inverters_down > 0) {
                            annotation_array.push({
                                type: 'box',
                                xScaleID: 'x-axis-0',
                                yScaleID: 'y-axis-1',
                                // Left edge of the box. in units along the x axis
                                xMin: new Date(power_irradiation[m].timestamp).valueOf(),
                                xMax: new Date(power_irradiation[m+1].timestamp).valueOf(),
                                // Right edge of the box
                                // Top edge of the box in units along the y axis
                                yMax: power_max_value * 1.11,

                                // Bottom edge of the box
                                yMin: power_max_value * 1.10,

                                label: "Inverters Down",
                                backgroundColor: 'rgba(101, 33, 171, 0.5)',
                                borderColor: 'rgb(101, 33, 171)',
                                borderWidth: 1,
                                onMouseover: function(e) {
                                    console.log(e);
                                    console.log('Box', e.type, this);

                                    $("#annotation_tooltip").show();

                                    var time = new Date(this._model.ranges["x-axis-0"].min);
                                    time = dateFormat(time, "HH:MM:ss");
                                    $("#annotation_tooltip").empty();
                                    $("#annotation_tooltip").append("Inverters Down at " + time);
                                },
                                onMouseleave: function(e) {
                                    $("#annotation_tooltip").hide();
                                }
                            })
                        }
                        if(power_irradiation[m].modbus_read_error == true) {
                            annotation_array.push({
                                type: 'box',
                                xScaleID: 'x-axis-0',
                                yScaleID: 'y-axis-1',
                                // Left edge of the box. in units along the x axis
                                xMin: new Date(power_irradiation[m].timestamp).valueOf(),
                                xMax: new Date(power_irradiation[m+1].timestamp).valueOf(),
                                // Right edge of the box
                                // Top edge of the box in units along the y axis
                                yMax: power_max_value * 1.13,

                                // Bottom edge of the box
                                yMin: power_max_value * 1.12,

                                backgroundColor: 'red',
                                borderColor: 'green',
                                borderWidth: 1,
                                label: "Read Error",
                                onMouseover: function(e) {
                                    console.log(e);
                                    console.log('Box', e.type, this);

                                    $("#annotation_tooltip").show();
                                    
                                    var time = new Date(this._model.ranges["x-axis-0"].min);
                                    time = dateFormat(time, "HH:MM:ss");
                                    $("#annotation_tooltip").empty();
                                    $("#annotation_tooltip").append("Read Error at " + time);
                                },
                                onMouseleave: function(e) {
                                    $("#annotation_tooltip").hide();
                                }
                            })
                        }
                    }
                }

                power_irradiation_data(power_data, irradiation_data, timestamps, []);
            } else {
                $("#power_irradiation-li").addClass("disabled");
                $("#power_irradiation-li-next").addClass("disabled");

                noty_message("No data for the selected dates!", 'error', 5000)
                return;
            }

        },
        error: function(data) {
            console.log("error_streams_data");
            
            noty_message("No data for the selected dates!", 'error', 5000)
            return;
        }
    });

}

function epoch_to_hh_mm_ss(epoch) {
    var date = new Date(epoch);
    date = dateFormat(date, "HH:MM");
    return date;
}

function power_irradiation_data(power, irradiation, timestamps, annotations_array) {
    console.log(irradiation);
    console.log(!_.some(irradiation));
    var newpowerdata = [];
    var newirrdata = [];
    for (var i = 0; i < timestamps.length; i++) {
        newpowerdata.push({x: timestamps[i], y: power[i]});
        newirrdata.push({x: timestamps[i], y: irradiation[i]});
    }
    if (!_.some(irradiation)) {
        var scatterChartData = {
            labels: timestamps,
            datasets: [{
                label: "Power",
                data: newpowerdata,
                yAxisID: 'y-axis-1',
                borderColor : 'rgba(0, 144, 217, 0)',
                backgroundColor : 'rgba(0, 144, 217, 0.409804)',
                pointBorderColor : 'rgba(0,0,0,0)',
                pointBackgroundColor : 'rgba(0,0,0,0)'
            }]
        };

        var y_axes_values = [{
                        gridLines: {
                            display: true},
                        position: 'left',
                        id: 'y-axis-1',
                          scaleLabel: {
                            display: true,
                            labelString: 'Power (kW)'
                          }
                    }];
    } else {
        var scatterChartData = {
            labels: timestamps,
            datasets: [{
                label: "Power",
                data: newpowerdata,
                yAxisID: 'y-axis-1',
                borderColor : 'rgba(0, 144, 217, 0)',
                backgroundColor : 'rgba(0, 144, 217, 0.409804)',
                pointBorderColor : 'rgba(0,0,0,0)',
                pointBackgroundColor : 'rgba(0,0,0,0)'
            }, {
                label: "Irradiation",
                data: newirrdata,
                yAxisID: 'y-axis-2',
                borderDash: [6,0],
                borderColor : '#bcbfc0',
                backgroundColor : '#eceff1',
                pointBorderColor : 'rgba(0,0,0,0)',
                pointBackgroundColor : 'rgba(0,0,0,0)'
            }]
        };

        var y_axes_values = [{
            gridLines: {
                display: true
            },
            position: 'left',
            id: 'y-axis-1',
            scaleLabel: {
                display: true,
                labelString: 'Power (kW)'
            },
            ticks: {
                beginAtZero: true
            }
        },
        {
            gridLines: {
                display: false
            },
            position: 'right',
            id: 'y-axis-2',
            scaleLabel: {
                display: true,
                labelString: 'Irradiance (kW/m2)'
            },
            ticks: {
                beginAtZero: true
            }
        }];
    };
    $('#performance_irradiation_chart').remove(); // this is my <canvas> element
    $('#graph-container').append('<canvas id="performance_irradiation_chart"><canvas>');
    ctx = document.getElementById("performance_irradiation_chart");
    var myChart = new Chart(ctx, {
        type: "line",
        responsive: true,
        data: scatterChartData,
        annotateDisplay: true,
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
                        maxTicksLimit: 8,
                        maxRotation: 0,
                        userCallback: function(v) {
                            return epoch_to_hh_mm_ss(v)
                        },
                        reverse: true
                    }
                }],
                yAxes: y_axes_values,
            },
            annotation: {
                drawTime: "afterDraw",
                events: ['mouseover'],
                annotations: annotations_array
            }
        }
    });

    $("#power_irradiation-li").removeClass("disabled");
    $("#power_irradiation-li-next").removeClass("disabled");
}