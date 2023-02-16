$(document).ready(function() {

    $("#breadcrumb_page_path").empty();
    $("#breadcrumb_page_path").append('<li class="text-center text-bold" ><a href="#">Client</a></li><li class="text-center text-bold"><a href="#">Client Dashboard</a></li><li class="text-center text-bold"><a href="#">Plant Dashboard</a></li><li class="text-center text-bold"><a href="#">Inverter Status</a></li>')

	/*inverter_status_data();*/
    inverters_status_chart();
});

var inverter_keys = [];
var inverters_status = {};
var inverters_orientation = {};
var list = $('#inverter_status');
var north_row = null;
var south_row = null;
var west_row = null;
var east_row = null;
var south_west_row = null;
var east_west_row = null;

function inverters_status_chart() {

    $.ajax({
        type: "GET",
        url: "/api/solar/plants/".concat(plant_slug).concat('/status/'),
        success: function (status_data) {
            for (var i = 0; i < status_data.inverters.length; i++) {
                var inverter_block = status_data.inverters[i];
                inverter_keys.push(inverter_block.key);
                inverters_status[inverter_block.name] = inverter_block.connected;
                inverters_orientation[inverter_block.name] = inverter_block.orientation;
            }
            inverters_data();
        },
        error: function (data) {
            console.log("error_streams_data");
            data = null;
        }
    });
}

function string_escape(myid) {

    return "#" + myid.replace( /(:|\.|\[|\]|,)/g, "\\$1" );

}

function inverters_data() {
    var startDate = new Date();
    var endDate = new Date();
    endDate = new Date(endDate.setDate(endDate.getDate() + 1));
    // now make the data call
    $.ajax({
        type: "GET",
        url: "/solar/plant/".concat(plant_slug).concat("/data/file/?inverters=").concat(inverter_keys.join()).concat("&startTime=").concat(dateFormat(startDate, "yyyy-mm-dd")).concat("&endTime=").concat(dateFormat(endDate, "yyyy-mm-dd")).concat("&streamNames=ACTIVE_POWER"),
        success: function(data) {
            var inverters_index = {};
            var power_data = Papa.parse(data);
            if (power_data.data.length < 3) {
                var no_data = $("<div class='row' style='margin-top: 20px;' disabled>" +
                    "<div class='row' style='text-align: center;'><strong style='font-size:20px;font-weight:900;'>There is no generation data for today, please check later</strong>" +
                    "</div>" +
                    "<div class='row' id='error'></div>" +
                    "</div>");
                list.append(no_data);
                return;
            }
            var inverters_data = {};
            for (var col = 1; col < power_data.data[0].length; col++) {
                inverters_data[power_data.data[0][col]] = [];
                inverters_index[col] = power_data.data[0][col];
            }
            for (var row = 1; row < power_data.data.length-2; row++) {
                for (col = 1; col < power_data.data[row].length; col++) {
                    var data_val = parseFloat(power_data.data[row][col]);
                    if (isNaN(data_val)) {
                        data_val = null;
                    }
                    inverters_data[inverters_index[col]].push( {
                        "date": power_data.data[row][0] ,
                        "value":data_val});
                    }
            }

            console.log(inverters_data);

            for (var inverter_name in inverters_data){
                if (inverters_data.hasOwnProperty(inverter_name)) {
                    var orientation = inverters_orientation[inverter_name];
                    var connection_status = inverters_status[inverter_name];
                    var column = $("<div class='col-lg-3' id=" + inverter_name + "></div>");
                    if (orientation == "NORTH"){
                        if (north_row == null) {
                            // add north section and create a global row
                            north_row = $("<div class='row' style='margin-top: 20px;' disabled>" +
                                "<div class='row' style='text-align: center;'><strong style='font-size:20px;font-weight:900;'>NORTH</strong>" +
                                "</div>" +
                                "<div class='row' id='north'></div>" +
                                "</div>");
                            list.append(north_row);
                        }
                        // add a new 3 col
                        $('#north').append(column);
                    }

                    else if (orientation == "SOUTH"){
                        if (south_row == null) {
                            // add north section and create a global row
                            south_row = $("<div class='row' style='margin-top: 20px;' disabled>" +
                                "<div class='row' style='text-align: center;'><strong style='font-size:20px;font-weight:900;'>SOUTH</strong>" +
                                "</div>" +
                                "<div class='row' id='south'></div>" +
                                "</div>");
                            list.append(south_row);
                        }
                        // add a new 3 col
                        $('#south').append(column);
                    }

                    else if (orientation == "EAST"){
                        if (east_row == null) {
                            // add north section and create a global row
                            east_row = $("<div class='row' style='margin-top: 20px;' disabled>" +
                                "<div class='row' style='text-align: center;'><strong style='font-size:20px;font-weight:900;'>EAST</strong>" +
                                "</div>" +
                                "<div class='row' id='east'></div>" +
                                "</div>");
                            list.append(east_row);
                        }
                        // add a new 3 col
                        $('#east').append(column);
                    }

                    else if (orientation == "WEST"){
                        if (west_row == null) {
                            // add north section and create a global row
                            west_row = $("<div class='row' style='margin-top: 20px;' disabled>" +
                                "<div class='row' style='text-align: center;'><strong style='font-size:20px;font-weight:900;'>WEST</strong>" +
                                "</div>" +
                                "<div class='row' id='west'></div>" +
                                "</div>");
                            list.append(west_row);
                        }
                        // add a new 3 col
                        $('#west').append(column);
                    }

                    else if (orientation == "SOUTH-WEST"){
                        console.log(orientation);
                        console.log(inverter_name);
                        if (south_west_row == null) {
                            // add north section and create a global row
                            south_west_row = $("<div class='row' style='margin-top: 20px;' disabled>" +
                                "<div class='row' style='text-align: center;'><strong style='font-size:20px;font-weight:900;'>SOUTH WEST</strong>" +
                                "</div>" +
                                "<div class='row' id='south_west'></div>" +
                                "</div>");
                            list.append(south_west_row);
                        }
                        // add a new 3 col
                        $('#south_west').append(column);
                    }

                    else if (orientation == "EAST-WEST"){
                        console.log(orientation);
                        console.log(inverter_name);
                        if (east_west_row == null) {
                            // add north section and create a global row
                            east_west_row = $("<div class='row' style='margin-top: 20px;' disabled>" +
                                "<div class='row' style='text-align: center;'><strong style='font-size:20px;font-weight:900;'>EAST WEST</strong>" +
                                "</div>" +
                                "<div class='row' id='east_west'></div>" +
                                "</div>");
                            list.append(east_west_row);
                        }
                        // add a new 3 col
                        $('#east_west').append(column);
                    }

                    metric_chart(inverter_name, inverters_data[inverter_name], inverter_name, connection_status);
                }
            }

        },
        error: function(data){
            console.log("no data");
        }
    });
}

function metric_chart(title_name, data, target, status){
    var color = "green";
    if (status == "disconnected") {
        color = "red";
    } else if (status == "unknown") {
        color = "blue";
    }

    target = string_escape(target);

    console.log(data);

    var linked_form = '%Y-%m-%d-%H-%M-%S';
    data = MG.convert.date(data, 'date', '%Y-%m-%dT%H:%M:%S');
    console.log(data);
    MG.data_graphic({
        title: title_name,
        data: data,
        missing_is_hidden: true,
        color: color,
        linked: true,
        interpolate: 'basis',
        linked_format: linked_form,
        width: 250,
        height: 250,
        right: 5,
        xax_count: 4,
        mouseover: function(d, i) {
            var prefix = d3.formatPrefix(d.value);
            d3.select(target.concat(' svg .mg-active-datapoint'))
                .text("Time: " + dateFormat(d.date,"HH:MM") + ' Power: ' + prefix.scale(d.value).toFixed(2) + 'kW')
                      .style("font-size","14px");

        },
        point_size:4,
        x_sort:true,
        x_accessor: 'date',
        y_accessor: 'value',
        target: target
    });
}
/*
function plot_labels(data){
    var list = $('#inverter_status');
    var north_elements = 0, south_elements = 0, east_elements = 0, west_elements = 0, row_count = -1, d = 0;
    var north_row_count = 0, south_row_count = 0, east_row_count = 0, west_row_count = 0;
    var d_north = 0, d_south = 0, d_east = 0, d_west = 0;
    list.innerHTML = "";
    list.empty();
    var north = $("<div class='row' id='north' style='margin-top: 20px;' disabled><div class='row' style='text-align: center;'><strong style='font-size:20px;font-weight:900;'>NORTH</strong></div></div>");
    var south = $("<div class='row' id='south' style='margin-top: 20px;' disabled><div class='row' style='text-align: center;'><strong style='font-size:20px;font-weight:900;'>SOUTH</strong></div></div>");
    var east = $("<div class='row' id='east' style='margin-top: 20px;' disabled><div class='row' style='text-align: center;'><strong style='font-size:20px;font-weight:900;'>EAST</strong></div></div>");
    var west = $("<div class='row' id='west' style='margin-top: 20px;' disabled><div class='row' style='text-align: center;'><strong style='font-size:20px;font-weight:900;'>WEST</strong></div></div>");
    list.append(north);
    list.append(south);
    list.append(east);
    list.append(west);
    for(var i = 0; i < data.inverters.length; i++) {
        if(data.inverters[i].orientation == 'NORTH') {
            if(north_elements % 5 == 0) {
                north_row_count++;
                $("#north").append('<div class="row" id="north-row'+north_row_count+'"></div>');
                d_north = 0;
            }
            var generation = data.inverters[i].generation;
            if (data.inverters[i].connected == "connected") {
                var success = $('<div class="col-lg-2 pad-all" id="div'+d_north+'" style="text-align:center;"> ' +
                    '<div class="row"> ' + '<div class="col-lg-1"></div>' + '<strong>' + data.inverters[i].name + '</strong>' + ' </div> ' +
                    '<button class="btn btn-lg btn-success mar-lft" id="inverter_button_value" style="width: 150px;">' +
                    '<div class="row"> ' + '<div class="col-lg-1"></div>' + '<strong>' + data.inverters[i].name + '</strong>' + ' </div> ' + generation.toFixed(1) +
                    ' KWH </button>' + '<div class="row"> ' + '<div class="col-lg-1"></div>' + '<strong> Power : ' + data.inverters[i].power + '</strong>' + ' </div> ' + '</div>');
                $("#north-row"+north_row_count).append(success);
            } else if (data.inverters[i].connected == "unknown") {
                var success = $('<div class="col-lg-2 pad-all" id="div'+d_north+'" style="text-align:center;"> ' +
                    '<div class="row"> ' + '<div class="col-lg-1"></div>' + '<strong>' + data.inverters[i].name + '</strong>' + ' </div> ' +
                    '<button class="btn btn-lg btn-danger mar-lft" id="inverter_button_value" style="width: 150px;">' + generation.toFixed(1) +
                    ' KWH </button>' + '<div class="row"> ' + '<div class="col-lg-1"></div>' + '<strong> Power : ' + data.inverters[i].power + '</strong>' + ' </div> ' + '</div>');
                $("#north-row"+north_row_count).append(success);
            }
            else {
                var label = $('<div class="col-lg-2 pad-all" id="div'+d_north+'" style="text-align:center;"> ' +
                    '<div class="row"> ' + '<div class="col-lg-1"></div>' + '<strong>' + data.inverters[i].name + '</strong>' + ' </div> ' +
                    '<button class="btn btn-lg btn-info mar-lft" id="inverter_button_value" style="width: 150px;">' + generation.toFixed(1) +
                    ' KWH </button>' + '<div class="row"> ' + '<div class="col-lg-1"></div>' + '<strong> Power : ' + data.inverters[i].power + '</strong>' + ' </div> ' + ' </div>');
                $("#north-row"+north_row_count).append(label);
            }
            north_elements++;
            d_north++;
        } else if(data.inverters[i].orientation == 'SOUTH') {
            if(south_elements % 5 == 0) {
                south_row_count++;
                $("#south").append('<div class="row" id="south-row'+south_row_count+'"></div>');
                d_south = 0;
            }
            var generation = data.inverters[i].generation;
            if (data.inverters[i].connected == "connected") {
                var success = $('<div class="col-lg-2 pad-all" id="div'+d_south+'" style="text-align:center;"> ' +
                    '<div class="row"> ' + '<div class="col-lg-1"></div>' + '<strong>' + data.inverters[i].name + '</strong>' + ' </div> ' +
                    '<button class="btn btn-lg btn-success mar-lft" id="inverter_button_value" style="width: 150px;">'+ generation.toFixed(1) +
                    ' KWH </button>' + '<div class="row"> ' + '<div class="col-lg-1"></div>' + '<strong> Power : ' + data.inverters[i].power + '</strong>' + ' </div> ' + '</div>');
                $("#south-row"+south_row_count).append(success);
            } else if (data.inverters[i].connected == "unknown") {
                var success = $('<div class="col-lg-2 pad-all" id="div'+d_south+'" style="text-align:center;"> ' +
                    '<div class="row"> ' + '<div class="col-lg-1"></div>' + '<strong>' + data.inverters[i].name + '</strong>' + ' </div> ' +
                    '<button class="btn btn-lg btn-danger mar-lft" id="inverter_button_value" style="width: 150px;">'+ generation.toFixed(1) +
                    ' KWH </button>' + '<div class="row"> ' + '<div class="col-lg-1"></div>' + '<strong> Power : ' + data.inverters[i].power + '</strong>' + ' </div> ' + '</div>');
                $("#south-row"+south_row_count).append(success);
            }
            else {
                var label = $('<div class="col-lg-2 pad-all" id="div'+d_south+'" style="text-align:center;"> ' +
                    '<div class="row"> ' + '<div class="col-lg-1"></div>' + '<strong>' + data.inverters[i].name + '</strong>' + ' </div> ' +
                    '<button class="btn btn-lg btn-info mar-lft" id="inverter_button_value" style="width: 150px;">' + generation.toFixed(1) +
                    ' KWH </button>' + '<div class="row"> ' + '<div class="col-lg-1"></div>' + '<strong> Power : ' + data.inverters[i].power + '</strong>' + ' </div> ' + '</div>');
                $("#south-row"+south_row_count).append(label);
            }
            south_elements++;
            d_south++;
        } else if(data.inverters[i].orientation == 'EAST') {
            if(east_elements % 5 == 0) {
                east_row_count++;
                $("#east").append('<div class="row" id="east_row'+east_row_count+'"></div>');
                d_east = 0;
            }
            var generation = data.inverters[i].generation;
            if (data.inverters[i].connected == "connected") {
                var success = $('<div class="col-lg-2 pad-all" id="div'+d_east+'" style="text-align:center;"> ' +
                    '<div class="row"> ' + '<div class="col-lg-1"></div>' + '<strong>' + data.inverters[i].name + '</strong>' + ' </div> ' +
                    '<button class="btn btn-lg btn-success mar-lft" id="inverter_button_value" style="width: 150px;">'+ generation.toFixed(1) +
                    ' KWH </button>' + '<div class="row"> ' + '<div class="col-lg-1"></div>' + '<strong> Power : ' + data.inverters[i].power + '</strong>' + ' </div> ' + '</div>');
                $("#east_row"+east_row_count).append(success);
            } else if (data.inverters[i].connected == "unknown") {
                var success = $('<div class="col-lg-2 pad-all" id="div'+d_east+'" style="text-align:center;"> ' +
                    '<div class="row"> ' + '<div class="col-lg-1"></div>' + '<strong>' + data.inverters[i].name + '</strong>' + ' </div> ' +
                    '<button class="btn btn-lg btn-danger mar-lft" id="inverter_button_value" style="width: 150px;">'+ generation.toFixed(1) +
                    ' KWH </button>' + '<div class="row"> ' + '<div class="col-lg-1"></div>' + '<strong> Power : ' + data.inverters[i].power + '</strong>' + ' </div> ' + '</div>');
                $("#east_row"+east_row_count).append(success);
            }
            else {
                var label = $('<div class="col-lg-2 pad-all" id="div'+d_east+'" style="text-align:center;"> ' +
                    '<div class="row"> ' + '<div class="col-lg-1"></div>' + '<strong>' + data.inverters[i].name + '</strong>' + ' </div> ' +
                    '<button class="btn btn-lg btn-info mar-lft" id="inverter_button_value" style="width: 150px;">' + generation.toFixed(1) +
                    ' KWH </button>' + '<div class="row"> ' + '<div class="col-lg-1"></div>' + '<strong> Power : ' + data.inverters[i].power + '</strong>' + ' </div> ' + '</div>');
                $("#east_row"+east_row_count).append(label);
            }
            east_elements++;
            d_east++;
        } else if(data.inverters[i].orientation == 'WEST') {
            if(west_elements % 5 == 0) {
                west_row_count++;
                $("#west").append('<div class="row" id="west_row'+west_row_count+'"></div>');
                d_west = 0;
            }
            var generation = data.inverters[i].generation;
            if (data.inverters[i].connected == "connected") {
                var success = $('<div class="col-lg-2 pad-all" id="div'+d_west+'" style="text-align:center;"> ' +
                    '<div class="row"> ' + '<div class="col-lg-1"></div>' + '<strong>' + data.inverters[i].name + '</strong>' + ' </div> ' +
                    '<button class="btn btn-lg btn-success mar-lft" id="inverter_button_value" style="width: 150px;">'+ generation.toFixed(1) +
                    ' KWH </button>' + '<div class="row"> ' + '<div class="col-lg-1"></div>' + '<strong> Power : ' + data.inverters[i].power + '</strong>' + ' </div> ' + '</div>');
                $("#west_row"+west_row_count).append(success);
            } else if (data.inverters[i].connected == "unknown") {
                var success = $('<div class="col-lg-2 pad-all" id="div'+d_west+'" style="text-align:center;"> ' +
                    '<div class="row"> ' + '<div class="col-lg-1"></div>' + '<strong>' + data.inverters[i].name + '</strong>' + ' </div> ' +
                    '<button class="btn btn-lg btn-danger mar-lft" id="inverter_button_value" style="width: 150px;">'+ generation.toFixed(1) +
                    ' KWH </button>' + '<div class="row"> ' + '<div class="col-lg-1"></div>' + '<strong> Power : ' + data.inverters[i].power + '</strong>' + ' </div> ' + '</div>');
                $("#west_row"+west_row_count).append(success);
            }
            else {
                var label = $('<div class="col-lg-2 pad-all" id="div'+d_west+'" style="text-align:center;"> ' +
                    '<div class="row"> ' + '<div class="col-lg-1"></div>' + '<strong>' + data.inverters[i].name + '</strong>' + ' </div> ' +
                    '<button class="btn btn-lg btn-info mar-lft" id="inverter_button_value" style="width: 150px;">' + generation.toFixed(1) +
                    ' KWH </button>' + '<div class="row"> ' + '<div class="col-lg-1"></div>' + '<strong> Power : ' + data.inverters[i].power + '</strong>' + ' </div> ' + '</div>');
                $("#west_row"+west_row_count).append(label);
            }
            west_elements++;
            d_west++;
        }
    }
    /!*for (var inverter_name in data.inverters) {
        if (data.inverters.hasOwnProperty(inverter_name)) {

        }
    }*!/
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
}*/
