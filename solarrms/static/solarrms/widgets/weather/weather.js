$(document).ready(function() {
    weather_widget();
});

function weather_widget() {

    $("#location").empty();
    $("#location").append(plant_location);

    // WEATHER UPDATE
    // =================================================================
    // OPENWEATHERMAP
    $.ajax({
        type: "GET",
        url: "https://api.worldweatheronline.com/premium/v1/weather.ashx".concat("?key=2bfdc03e0f1e4bab91f223144162105&q=").concat(plant_location).concat("&num_of_day=1").concat("&format=json"),
        success: function(weather_data) {
            var temp = weather_data.data.current_condition[0].temp_C;
            $('#temperature').text(Math.round(temp).toString().concat(String.fromCharCode(176)));
            var max_temp = weather_data.data.weather[0].maxtempC;
            var min_temp = weather_data.data.weather[0].mintempC;
            $('#minmax').text(Math.round(max_temp).toString().concat(String.fromCharCode(176)).concat("/").concat(Math.round(min_temp).toString().concat(String.fromCharCode(176))));
            var wind = weather_data.data.current_condition[0].windspeedMiles;
            $('#windspeed').text(Math.round(wind).toString().concat("mph"));
            var clouds_description = weather_data.data.current_condition[0].weatherDesc[0].value;
            $('#comments').text(clouds_description);
            var precipitation = weather_data.data.current_condition[0].precipMM;
            $('#precipitation').text((precipitation).toString());
        },
        error: function(weather_data){
            console.log("no data");
        }
    });

    var inverters_status_info = inverters_status_function();

    var irradiation = inverters_status_info.irradiation;
    if(irradiation != undefined && irradiation != "NA") {
        $('#irradiation').text(parseFloat(irradiation).toFixed(3).toString().concat(" kW/m").concat(String.fromCharCode(178)));
    } else {
        $('#irradiation').text("NA");
    }

    var module_temperature = inverters_status_info.module_temperature;
    if(module_temperature != undefined && module_temperature != "NA") {
        $('#module_temperature').text(Math.round(parseFloat(module_temperature)).toString().concat(String.fromCharCode(176)).concat("C"));
    } else {
        $('#module_temperature').text("NA");   
    }
}