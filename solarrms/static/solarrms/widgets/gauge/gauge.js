$(document).ready(function() {
	gauge_widget();	
});

var opts = {};
var target = null;
var gauge = null;

function gauge_widget() {

	var inverters_status_info = inverters_status_function();

	$("#plant_capacity").empty();
	$("#plant_capacity").append(plant_capacity);
	$("#demo-gauge-text").empty();
	$("#demo-gauge-text").text((parseFloat(current_power)).toFixed(3).toString().concat(" kW"));

	if (plant_slug != 'uran' && plant_slug != 'rrkabel') {
	    opts = {
	        lines: 10, // The number of lines to draw
	        angle: 0, // The length of each line
	        lineWidth: 0.41, // The line thickness
	        pointer: {
	            length: 0.75, // The radius of the inner circle
	            strokeWidth: 0.035, // The rotation offset
	            color: '#769f48' // Fill color
	        },
	        limitMax: 'true', // If true, the pointer will not go past the end of the gauge
	        colorStart: '#fff', // Colors
	        colorStop: '#fff', // just experiment with them
	        strokeColor: '#8ab75a', // to see which ones work best for you
	        generateGradient: true
	    };

	    target = document.getElementById('current-power'); // your canvas element
	    gauge = new Gauge(target).setOptions(opts);
	    gauge.maxValue = plant_capacity; // set max gauge value
	    gauge.animationSpeed = 32; // set animation speed (32 is default value)
	    gauge.set(1);
	    gauge.set(0);
	    if( current_power > 0) {
	        gauge.set(current_power); // set actual value
	    } else {
	    }
	}

	if (plant_slug != 'uran' && plant_slug != 'rrkabel') {
        var current_power = inverters_status_info.current_power;
        if(current_power != undefined && current_power != "NA") {
            $("#demo-gauge-text").text((parseFloat(current_power)).toFixed(3).toString().concat(" kW"));
            gauge.set(current_power); // set actual value
        }
    }

}