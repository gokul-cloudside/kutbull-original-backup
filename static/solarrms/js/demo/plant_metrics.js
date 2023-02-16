$(document).ready(function() {
    
    $("#breadcrumb_page_path").empty();
    $("#breadcrumb_page_path").append('<li class="text-center text-bold" ><a href="#">Client</a></li><li class="text-center text-bold"><a href="#">Client Dashboard</a></li><li class="text-center text-bold"><a href="#">Plant Dashboard</a></li><li class="text-center text-bold"><a href="#">Plant Metrics</a></li>')

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

$(".plant_metric_parameter-list li a").click(function(){
    $("#plant_metric_parameter").html();
    $("#plant_metric_parameter").html($(this).text());

    plant_parameter = $(this).text();
});

var plant_parameter = "", aggregator_string = "";

$(".plant_metric_parameter_aggregator-list li a").click(function(){
    $("#plant_metric_parameter_aggregator").html();
    $("#plant_metric_parameter_aggregator").html($(this).text());

    aggregator_string = $(this).text();

    if(aggregator_string == "WEEK") {

        $("#datepicker_selected_plugin").empty();
        $("#datepicker_selected_plugin").append('<input type="text" class="form-control datepicker_start_days" id="datepicker_selected_picker" placeholder="Pick a Date" style="height: 31px;">');
        datepicker_start_day();

    } else if(aggregator_string == "MONTH") {

        $("#datepicker_selected_plugin").empty();
        $("#datepicker_selected_plugin").append('<input type="text" class="form-control datepicker_start_months" id="datepicker_selected_picker" placeholder="Pick a Month" style="height: 31px;">');
        datepicker_start_month();

    } else if(aggregator_string == "YEAR") {

        $("#datepicker_selected_plugin").empty();
        $("#datepicker_selected_plugin").append('<input type="text" class="form-control datepicker_start_years" id="datepicker_selected_picker" placeholder="Pick a Year" style="height: 31px;">');
        datepicker_start_year();

    }

    console.log(aggregator_string);
});

$("#plant_metrics-update").on('click', function() {
    var st = $("#datepicker_selected_picker").val();
    console.log(st);
    
    plant_parameter = $("#plant_metric_parameter").text();
    if(plant_parameter == "Select a Parameter") {
        noty_message("Please select a plant parameter!", 'error', 5000)
        return;
    }

    aggregator_string = $("#plant_metric_parameter_aggregator").text();
    if(aggregator_string == "Select an Aggregator") {
        noty_message("Please select an aggregator!", 'error', 5000)
        return;
    }

    if(st == "") {
        noty_message("Please select a Date!", 'error', 5000)
        return;
    }

    if(plant_parameter == "PR") {
        pr_chart(aggregator_string, st);
    } else if(plant_parameter == "CUF") {
        cuf_chart(aggregator_string, st);
    } else if(plant_parameter == "SPECIFIC YIELD") {
        specific_yield_chart(aggregator_string, st);
    }
})

function get_date(st) {

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

function pr_chart(aggregator_string, st) {

    var dates = get_date(st);

    st = dates[0];
    var et = dates[1];

    var aggregator_text = aggregator_string;

    if(aggregator_string == "WEEK" || aggregator_string == "MONTH") {
        aggregator_string = "DAY";
    } else if(aggregator_string == "YEAR") {
        aggregator_string = "MONTH";
    }

    $.ajax({
        type: "GET",
        url: "/api/solar/plants/".concat(plant_slug).concat('/performance/'),
        data: {startTime: (st), endTime: (et), aggregator: aggregator_string},
        success: function(data){
            if(data == "") {
                $('#performance_indicator_chart').remove(); // this is my <canvas> element
                $('#performance_indicator_chart_div').append('<canvas id="performance_indicator_chart"><canvas>');

                noty_message("No PR for the selected " + aggregator_text + "!", 'error', 5000)
                return;

            } else {

                console.log(data);

                var timestamp = [], pr_values = [], pvsyst_values_annotation = [], pvsyst_pr = [];

                var monitor_height = window.screen.availHeight;
                var monitor_width = window.screen.availWidth;
                console.log(monitor_height);
                console.log(monitor_width);

                var annotation_line = monitor_width/3.5;
                annotation_line = annotation_line/(data.length);

                for(var pr = data.length-1; pr >= 0; pr--) {
                    timestamp.push(new Date(data[pr].timestamp));
                    pr_values.push((data[pr].performance_ratio).toFixed(2));
                    if(data[pr].pvsyst_pr) {
                        pvsyst_pr.push({x: new Date(data[pr].timestamp), y: (parseFloat(data[pr].pvsyst_pr)).toFixed(2), r: 5});
                        /*pvsyst_values_annotation.push({
                            type: 'box',
                            xScaleID: 'x-axis-1',
                            yScaleID: 'y-axis-0',
                            // Left edge of the box. in units along the x axis
                            xMin: new Date(data[pr].timestamp).valueOf() + 100,
                            xMax: new Date(data[pr].timestamp).valueOf() + 100,
                            // Right edge of the box
                            // Top edge of the box in units along the y axis
                            yMax: data[pr].pvsyst_pr * 0.9999,

                            // Bottom edge of the box
                            yMin: data[pr].pvsyst_pr,

                            label: "Pvsyst PR",
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
                                $("#annotation_tooltip").append("Inverters Down at " + time);
                            },
                            onMouseleave: function(e) {
                                $("#annotation_tooltip").hide();
                            }
                        })*/
                    }
                }

                chart_plot(timestamp, pr_values, pvsyst_pr, "PR", "Performance Ratio", "Pvsyst PR", annotation_line);

            }
        },
        error: function(data){
            console.log("no data");

            noty_message("No data for the selected date!", 'error', 5000)
            return;
        }
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

function chart_plot(timestamp, values, pvsyst_values, plant_parameter, plant_parameter_label, pvsyst_parameter_label, annotation_line) {

    $("#performance_indicator_headings").empty();

    var chart_data, y_axes_values;

    if(!_.some(pvsyst_values)) {
        $("#performance_indicator_headings").append("<div class='col-lg-5 col-md-5 col-sm-5'></div><div class='col-lg-2 col-md-2 col-sm-2'><span class='label label-default' style='background-color: rgba(72, 137, 187, 1)'></span> <span>" + plant_parameter + "</span></div>");
        chart_data = {
            labels: timestamp,
            datasets: [
                {
                    label: plant_parameter_label,
                    backgroundColor: 'rgba(72, 137, 187, 1)',
                    borderColor: 'rgba(72,137,187,1)',
                    data: values,
                    pointBorderColor : 'rgba(0,0,0,0)',
                    pointBackgroundColor : 'rgba(0,0,0,0)'
                }
            ]
        };
    } else {

        $("#performance_indicator_headings").append("<div class='col-lg-4 col-md-4 col-sm-4'></div><div class='col-lg-2 col-md-2 col-sm-2'><span class='label label-default' style='background-color: rgba(38, 50, 56, 1)'></span> <span>" + pvsyst_parameter_label + "</span></div><div class='col-lg-2 col-md-2 col-sm-2'><span class='label label-default' style='background-color: rgba(72, 137, 187, 1)'></span> <span>" + plant_parameter + "</span></div>");
        chart_data = {
            labels: timestamp,
            datasets: [
                {
                    type: 'line',
                    label: pvsyst_parameter_label,
                    backgroundColor: 'rgba(0, 0, 0, 0)',
                    borderColor: 'rgba(0, 0, 0, 0)',
                    fillColor: 'rgba(0, 0, 0, 0)',
                    pointBackgroundColor: 'rgba(38, 50, 56, 1)',
                    pointBorderColor: 'rgba(38, 50, 56, 1)',
                    pointStyle: "line",
                    pointBorderWidth: 3,
                    pointRadius: annotation_line,
                    pointHoverRadius: annotation_line,
                    data: pvsyst_values
                },
                {
                    type: 'bar',
                    label: plant_parameter_label,
                    backgroundColor: 'rgba(72, 137, 187, 1)',
                    borderColor: 'rgba(72,137,187,1)',
                    data: values
                } 
            ]
        };
    }

    y_axes_values = [{
        gridLines: {
            display: true},
        position: 'left',
          scaleLabel: {
            display: true,
            labelString: plant_parameter_label
        },
        ticks: {
            beginAtZero: true
        }
    }];

    $('#performance_indicator_chart').remove(); // this is my <canvas> element
    $('#performance_indicator_chart_div').append('<canvas id="performance_indicator_chart"><canvas>');
    var ctx = document.getElementById("performance_indicator_chart");

    var myBarChart = new Chart(ctx, {
        type: 'bar',
        data: chart_data,
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
                            if(aggregator_string == "WEEK") {
                                return epoch_to_date(v)    
                            } else if(aggregator_string == "MONTH") {
                                return epoch_to_month(v)
                            } else if(aggregator_string == "YEAR") {
                                return epoch_to_year(v)
                            }
                        },
                        reverse: true
                    }
                }],
                yAxes: y_axes_values,
            }/*,
            annotation: {
                drawTime: "afterDraw",
                events: ['mouseover'],
                annotations: pvsyst_values_annotation
            }*/
        }
    });

}

function cuf_chart(aggregator_string, st) {

    var dates = get_date(st);

    st = dates[0];
    var et = dates[1];

    var aggregator_text = aggregator_string;

    if(aggregator_string == "WEEK" || aggregator_string == "MONTH") {
        aggregator_string = "DAY";
    } else if(aggregator_string == "YEAR") {
        aggregator_string = "MONTH";
    }

    $.ajax({
        type: "GET",
        url: "/api/solar/plants/".concat(plant_slug).concat('/CUF/'),
        data: {startTime: (st), endTime: (et), aggregator: aggregator_string},
        success: function(data){
            if(data == "") {

                $('#performance_indicator_chart').remove(); // this is my <canvas> element
                $('#performance_indicator_chart_div').append('<canvas id="performance_indicator_chart"><canvas>');

                noty_message("No CUF for the selected " + aggregator_text + "!", 'error', 5000)
                return;

            } else {

                console.log(data);

                var timestamp = [], cuf_values = [];

                for(var cuf = data.length-1; cuf >= 0; cuf--) {
                    timestamp.push(new Date(data[cuf].timestamp));
                    cuf_values.push((data[cuf].cuf).toFixed(2));
                }

                chart_plot(timestamp, cuf_values, [], "CUF", "CUF", "CUF", "");                

            }
        },
        error: function(data){
            console.log("no data");

            noty_message("No data for the selected date!", 'error', 5000)
            return;
        }
    });

}

function specific_yield_chart(aggregator_string, st) {

    var dates = get_date(st);

    st = dates[0];
    var et = dates[1];

    var aggregator_text = aggregator_string;

    if(aggregator_string == "WEEK" || aggregator_string == "MONTH") {
        aggregator_string = "DAY";
    } else if(aggregator_string == "YEAR") {
        aggregator_string = "MONTH";
    }

    $.ajax({
        type: "GET",
        url: "/api/solar/plants/".concat(plant_slug).concat('/specific_yield/'),
        data: {startTime: (st), endTime: (et), aggregator: aggregator_string},
        success: function(data){
            if(data == "") {
                $('#performance_indicator_chart').remove(); // this is my <canvas> element
                $('#performance_indicator_chart_div').append('<canvas id="performance_indicator_chart"><canvas>');

                noty_message("No Specific Yield for the selected " + aggregator_text + "!", 'error', 5000)
                return;

            } else { 
                
                console.log(data);

                var timestamp = [], specific_yield_values = [], pvsyst_values_annotation = [], pvsyst_specific_yield = [];

                var monitor_height = window.screen.availHeight;
                var monitor_width = window.screen.availWidth;

                var annotation_line = monitor_width/3.5;
                annotation_line = annotation_line/(data.length);

                for(var yield = data.length-1; yield >= 0; yield--) {
                    timestamp.push(new Date(data[yield].timestamp));
                    specific_yield_values.push((data[yield].specific_yield).toFixed(2));
                    if(data[yield].pvsyst_specific_yield) {
                        pvsyst_specific_yield.push({x: new Date(data[yield].timestamp), y: (parseFloat(data[yield].specific_yield)).toFixed(2), r: 5});
                        /*pvsyst_values_annotation.push({
                            type: 'box',
                            xScaleID: 'x-axis-1',
                            yScaleID: 'y-axis-0',
                            // Left edge of the box. in units along the x axis
                            xMin: new Date(data[yield].timestamp).valueOf() + 100,
                            xMax: new Date(data[yield].timestamp).valueOf() + 100,
                            // Right edge of the box
                            // Top edge of the box in units along the y axis
                            yMax: data[yield].pvsyst_specific_yield * 0.9999,

                            // Bottom edge of the box
                            yMin: data[yield].pvsyst_specific_yield,

                            label: "Pvsyst Specific Yield",
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
                                $("#annotation_tooltip").append("Inverters Down at " + time);
                            },
                            onMouseleave: function(e) {
                                $("#annotation_tooltip").hide();
                            }
                        })*/
                    }
                }

                chart_plot(timestamp, specific_yield_values, pvsyst_specific_yield, "Specific Yield (kWh/kWp)", "Specific Yield (kWh/kWp)", "Pvsyst Yield (kWh/kWp)", annotation_line);

            }
        },
        error: function(data){
            console.log("no data");

            noty_message("No data for the selected date!", 'error', 5000)
            return;
        }
    });

}