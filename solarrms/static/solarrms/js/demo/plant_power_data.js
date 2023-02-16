/*Power Data for a day*/

function power_data(plantslug, st, e, svg) {
    
    $.ajax({
        type: "GET",
        url: "/api/solar/plants/".concat(plantslug).concat('/power/'),
        data: {startTime: st, endTime: e},
        success: function(data) {
            if(data == '') {
                $("#no_data_power_value").empty();
                $("#"+svg).empty();
                $("#"+svg).append("<div class='alert alert-warning'> No power for the date </div>");

                $(".plant-power-generation h2").empty();
                return;
            } else {
                $("#"+svg).empty();
                $("#"+svg).append("<svg></svg>");
            }

            var arrayData = [];

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

            /*if(irradiation_data != 0 && irradiation_data.data.length > 2) {
                for(var n= power.length-1; n >=0 ; n--) {
                    if(power[n].power > 0) {
                        var power_ts = new Date(power[n].timestamp);
                        power_ts.setMilliseconds(000);
                        power_ts = power_ts.getTime();
                        var local_values = [];
                        var ts = new Date(power[n].timestamp);
                        local_values.push([ts, 0.0]);
                        local_values.push([new Date(ts.setSeconds(ts.getSeconds() + 1)), parseFloat(power[n].power)]);
                        for(var m = 1; m <= irradiation_data.data.length-1; m++) {
                            var irradiation_ts = new Date(irradiation_data.data[m][1]);
                            irradiation_ts.setMilliseconds(000);
                            irradiation_ts = irradiation_ts.getTime();
                            if(power_ts == irradiation_ts) {
                                irradiation_value = 1;
                            } else {
                                irradiation_value = 0;
                            }
                        }
                        if(irradiation_value == 1) {
                            arrayData.push({"values": local_values,
                                    "key": dateFormat(power[n].timestamp, 'yyyy-mm-dd HH:MM:ss').concat(", ").concat(parseFloat(irradiation_data.data[m][1]).toString()),
                                    "color":"#4C85AB"});    
                        } else {
                            arrayData.push({"values": local_values,
                                    "key": dateFormat(power[n].timestamp, 'yyyy-mm-dd HH:MM:ss').concat(", ").concat(("NA").toString()),
                                    "color":"#4C85AB"});    
                        }
                    }
                }
            }

            console.log(arrayData);*/

            if(arrayData.length == 0) {

                $("#no_data_power_value").empty();
                $("#"+svg).empty();
                $("#"+svg).append("<div class='alert alert-warning'>No data for the date to be plotted.</div>");

                $(".plant-power-generation h2").empty();
                return;

            }

            // package the data
            //var packagedData = [{
            //    "key": "PLANT GENERATION ON DATE " + dateFormat(st, "yyyy-mm-dd") + " in kW",
            //    "values": arrayData,
            //    "color": "#4C85AB"
            //}];
            // plot the chart
            plant_power_generation_chart(st, arrayData, svg);
            /*#B4D3E5*/
        },
        error: function(data) {
            console.log("error_streams_data");
            data = null;
        },
    });
    return 1;
}

function plant_power_generation_chart(st, data, svg) {
    console.log(svg);
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
            d3.select("#"+svg+" svg")
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
