$(document).ready(function() {
    
    $("#breadcrumb_page_path").empty();
    $("#breadcrumb_page_path").append('<li class="text-center text-bold" ><a href="#">Client</a></li><li class="text-center text-bold"><a href="#">Client Dashboard</a></li><li class="text-center text-bold"><a href="#">Plant Dashboard</a></li><li class="text-center text-bold"><a href="#">Inverter Residuals</a></li>')

    inverter_residuals();

});

function inverter_residuals() {

    $.ajax({
        type: "GET",
        url: "/api/solar/plants/".concat(plant_slug).concat('/residual/'),
        success: function(data){
            if(data == "") {
                $("#residual_message").empty();
                $("#residual_message").append("<div class='alert alert-warning' id='alert'>No data for Inverter Residuals for last 1 week.</div>");

            } else { 
                $("#inverter_residual").append("<div class='row' id='residual_row'></div>");

                var inverters = [];
                var residual_data = [];

                for(var inverter in data) {
                    if((data).hasOwnProperty(inverter)) {
                        inverters.push(inverter);
                        residual_data.push(data[inverter]);
                    }
                }

                var inverter_timestamps = [];
                var inverter_values = [];
                var colors = [];

                for(var i = 0; i < residual_data.length; i++) {
                    inverter_timestamps = [], inverter_values = [], colors = [];
                    for(var date in residual_data[i]) {
                        if((residual_data[i]).hasOwnProperty(date)) {
                            var inverter_date = new Date(date);
                            inverter_date = dateFormat(inverter_date, "yyyy-mm-dd");
                            inverter_timestamps.push(inverter_date);
                            inverter_values.push(parseFloat(residual_data[i][date]));
                        }
                    }
                    for(var k = 0; k < inverter_values.length; k++) {
                        if(inverter_values[k] < 0) {
                            colors.push('#f76549');
                        } else {
                            colors.push('#46bbdc');
                        }
                    }
                    var y_axis_title = "kWh";
                    var chart_title = '';
                    var div_name = inverters[i];
                    $("#residual_row").append("<div class='col-lg-4 col-md-4'><h4 class='text-center'>" + inverters[i] + "</h4><div id='"+div_name+"' style='height: 30vh;'></div></div>");
                    var l_m = 40, r_m = 20, b_m = 30, t_m = 5;
                    var page = 1;

                    basic_bar_chart_plotly(inverter_timestamps, inverter_values, y_axis_title, colors, chart_title, div_name, l_m, r_m, page, b_m, t_m);
                }

                $("#residual_message").hide();

            }
        },
        error: function(data){
            console.log("no data");
            
            $("#residual_message").empty();
            $("#residual_message").append("<div class='alert alert-warning' id='alert'>Error. We will check what is happening.</div>");
        }
    });
}