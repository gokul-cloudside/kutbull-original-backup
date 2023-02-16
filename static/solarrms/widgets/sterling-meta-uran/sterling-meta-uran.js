$(document).ready(function() {
    sterling_meta_widget();
});

function sterling_meta_widget() {
    
    var inverters_status_info = inverters_status_function();
    
    var performance_ratio = inverters_status_info.performance_ratio;
    if(performance_ratio != undefined && performance_ratio != "NA") {
        performance_ratio = performance_ratio.toFixed(2);
        $('#performance_ratio_uran').text((parseFloat(performance_ratio)).toString());
    } else {
        $('#performance_ratio_uran').text("NA");   
    }

    var plant_generation_today = inverters_status_info.plant_generation_today;
    if(plant_generation_today != undefined && plant_generation_today != "NA") {
        $("#generation_today_uran").text((parseFloat(plant_generation_today)).toFixed(2).toString().concat(" kWh"));
    }
}