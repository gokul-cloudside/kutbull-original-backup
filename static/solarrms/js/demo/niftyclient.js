$(document).ready(function() {
	var bounds = new google.maps.LatLngBounds();
	var infowindow = new google.maps.InfoWindow(); /* SINGLE */
	var dashboard_map = new google.maps.Map(document.getElementById('dashboard-geocoding-map'), {
	  zoom: 5,
	  center: new google.maps.LatLng(19.9705, 79.3015),
	  scrollwheel: false
	});

	function placeMarker( plant ) {
		var latLng = new google.maps.LatLng(plant['lat'], plant['lng']);
		var dashboard_marker = new google.maps.Marker({
			position : latLng,
			animation: google.maps.Animation.DROP,
			icon: 'https://maps.google.com/mapfiles/ms/micons/sunny.png',
			map : dashboard_map
		});
		bounds.extend(dashboard_marker.position);
		google.maps.event.addListener(dashboard_marker, 'click', function(){
			infowindow.close(); // Close previously opened infowindow
			var url = "/solar/plant/".concat(plant.slug);
			infowindow.setContent( '<h3 style="color: blue"> <a href=' + url.toString() + '/>' +
					plant.name + '</h3> <h5>' +
					plant.location + ' </h5> <h6> Generation Today : ' +
					plant.today_generation + 'kWh </h5> <h6> Devices Connected : ' +
					plant.stable + '</h6> <h6> Devices Disconnected : ' +
					plant.errors + '</a></h6>');
			infowindow.open(dashboard_map, dashboard_marker);
		});
	}
	for(var i=0; i<plants_info.length; i++) {
		placeMarker( plants_info[i] );
	}
	dashboard_map.fitBounds(bounds);

	dashboard_data();

});

var todays_generation = 0;
var total_capacity = 0;
var co2_emission = 0;

function dashboard_data() {

	$("#pr_table_div").append("<thead><tr><th>Sites</th><th class='text-center'>Performance Ratio</th></tr></thead>")
	$("#pr_table_div").append("<tbody id='pr_tbody'></tbody>");

	$("#cuf_table_div").append("<thead><tr><th>Sites</th><th>CUF</th></tr></thead>")
	$("#cuf_table_div").append("<tbody id='cuf_tbody'></tbody>");

	$("#warnings_and_alarms_table_div").append("<thead><tr><th>Sites</th><th class='text-center'>Unacknowledged</th><th class='text-center'>Open</th><th class='text-center'>Closed</th></tr></thead>")
	$("#warnings_and_alarms_table_div").append("<tbody id='warnings_and_alarms_tbody'></tbody>");

	$("#details_table_div").append("<thead><tr><th>Sites</th><th>Location</th><th>Capacity (kW)</th><th>Active Power (kW)</th><th>Today Generation</th><th>Specific Production (kWh)</th><th>Insolation (kWh/m^2)</th></tr></thead>")
	$("#details_table_div").append("<tbody id='details_tbody'></tbody>");

	$("#weather_table_div").append("<thead><tr><th>Sites</th><th>Temperature (C)</th><th>Rainfall (mm)</th><th>Ambient Temperature (C)</th><th>Humidity (%)</th><th>Module Temperature (C)</th><th>Wind (km/hr)</th></tr></thead>")
	$("#weather_table_div").append("<tbody id='weather_tbody'></tbody>");


	$.ajax({
		type: "GET",
		async: true,
		url : "/api/solar/summary/",
		success: function(summary_info){
			$("#total_generation").text(summary_info.total_energy);
			$("#todays_generation").text(summary_info.energy_today);
			$("#total_capacity").text(summary_info.total_capacity);
			$("#co2_conversion").text(summary_info.total_co2);
			summary_info.plants.forEach(function(plant_information, index){
				var pr = plant_information.performance_ratio * 100;
				pr = parseInt(pr);
	        	$("#pr_tbody").append("<tr><td>" + plant_information.plant_name + "</td><td class='text-center'>" + pr + " %</td></tr>");
	        	$("#cuf_tbody").append("<tr><td>" + plant_information.plant_name + "</td><td>" + parseInt(plant_information.cuf*100) + " %</td></tr>");
	        	$("#warnings_and_alarms_tbody").append("<tr><td>" + plant_information.plant_name + "</td><td class='text-center'>" + plant_information.unacknowledged_tickets + "</td><td class='text-center'>" + plant_information.open_tickets + "</td><td class='text-center'>" + plant_information.closed_tickets + "</td></tr>")
	        	$("#details_tbody").append("<tr><td>" + plant_information.plant_name + "</td><td class='text-center'>" + plant_information.plant_location + "</td><td class='text-center'>" + plant_information.plant_capacity + "</td><td class='text-center'>" + plant_information.current_power.toFixed(2) + "</td><td class='text-center'>" + plant_information.plant_generation_today + "</td><td class='text-center'>NA</td><td class='text-center'>" + plant_information.irradiation.toFixed(2) + "</td></tr>")
				$.ajax({
					type: "GET",
					async: true,
					url: "https://api.worldweatheronline.com/premium/v1/weather.ashx".concat("?key=7ec3bc2ef94e4bfa8b0101346172001&q=").concat(plant_information.plant_location).concat("&num_of_day=1").concat("&format=json"),
					success: function(weather_data) {
						$("#weather_tbody").append("<tr><td>" + plant_information.plant_name + "</td><td class='text-center'>" + plant_information.ambient_temperature.toFixed(2) + "</td><td class='text-center'>" + weather_data.data.current_condition[0].precipMM + "</td><td class='text-center'>" + weather_data.data.current_condition[0].FeelsLikeC + "</td><td class='text-center'>" + weather_data.data.current_condition[0].humidity + "</td><td class='text-center'>" + plant_information.module_temperature.toFixed(2) + "</td><td class='text-center'>" + weather_data.data.current_condition[0].windspeedKmph + "</td></tr>")
					},
					error: function(weather_data){
						console.log("no data");
					}
				});
			});
		}
	});
}