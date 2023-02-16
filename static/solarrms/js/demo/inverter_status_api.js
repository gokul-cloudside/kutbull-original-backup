var inverter_status_data = null;

function inverters_status_function() {
    
    $.ajax({
        type: "GET",
        async: false,
        url: "/api/solar/plants/".concat(plant_slug).concat('/status/'),
        success: function(data) {
            inverter_status_data = data;
        },
        error: function(data) {
            console.log("error_streams_data");
            data = null;
        }
    });
    return inverter_status_data;
}