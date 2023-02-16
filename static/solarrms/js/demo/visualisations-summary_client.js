$(document).ready(function() {
	
    $("#breadcrumb_page_path").empty();
    $("#breadcrumb_page_path").append('<li class="text-center text-bold" ><a href="#">Client</a></li><li class="text-center text-bold"><a href="#">Client Dashboard</a></li><li class="text-center text-bold"><a href="#">Plant Dashboard</a></li><li class="text-center text-bold"><a href="#">Client Summary</a></li>')

	limit_plant_future_date();
	summary_client_date();

});

$(function() {
    $(".datetimepicker_start").datetimepicker({
        timepicker: false,
        format: 'd/m/Y',
        scrollMonth:false,
        scrollTime:false,
        scrollInput:false
    });
    $(".datetimepicker_start").on('change', function(ev) {
        $(this).datetimepicker('hide');
    });
});

function limit_plant_future_date() {
    $(function(){
        $('#start').datetimepicker({
            onShow:function( ct ){
                this.setOptions({
                    maxDate: new Date()
                })
            }
        });
    });
}

function get_dates(id){
    // get the start date
    var st = $("#"+id).val();
    /*var st = new Date();*/
    if (st == '') {
        st = new Date();
    } else {
        var date = [];
        date = st.split('/');
        st = date[2] + "/" + date[1] + "/" + date[0];
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

var todays_generation = 0;
var total_capacity = 0;
var co2_emission = 0;

function summary_client_date() {

	var id = "start";

	var dates = get_dates(id);
    var st = dates[0];
    var et = dates[1];

    $("#pr_table_div").empty();
    $("#pr_table_div").append("<thead><tr><th>Sites</th><th class='text-center'>Performance Ratio</th></tr></thead>")
	$("#pr_table_div").append("<tbody id='pr_tbody'></tbody>");

	$("#cuf_table_div").empty();
	$("#cuf_table_div").append("<thead><tr><th>Sites</th><th>CUF</th></tr></thead>")
	$("#cuf_table_div").append("<tbody id='cuf_tbody'></tbody>");

	$("#warnings_and_alarms_table_div").empty();
	$("#warnings_and_alarms_table_div").append("<thead><tr><th>Sites</th><th class='text-center'>Unacknowledged</th><th class='text-center'>Open</th><th class='text-center'>Closed</th></tr></thead>")
	$("#warnings_and_alarms_table_div").append("<tbody id='warnings_and_alarms_tbody'></tbody>");

	$("#details_table_div").empty();
	$("#details_table_div").append("<thead><tr><th>Sites</th><th>Location</th><th>Capacity (kW)</th><th>Today Generation (kWh)</th><th>Specific Production (kWh)</th></tr></thead>")
	$("#details_table_div").append("<tbody id='details_tbody'></tbody>");

	$("#weather_table_div").empty();
	$("#weather_table_div").append("<thead><tr><th>Sites</th><th>Temperature (C)</th><th>Rainfall (mm)</th><th>Ambient Temperature (C)</th><th>Humidity (%)</th><th>Module Temperature (C)</th><th>Wind (km/hr)</th></tr></thead>")
	$("#weather_table_div").append("<tbody id='weather_tbody'></tbody>");

	$.ajax({
        type: "GET",
        url: "/api/solar/summary/",
        data: {date: (st)},
        success: function(summary_client_data) {
            if(summary_client_data == '') {
                $("#no_client_summary_data").empty();
                $("#no_client_summary_data").append("<div>No data of solar plants for this client.</div>");
                return;
            } else {

            	$("#total_generation").empty();
	            $("#total_generation").text(((summary_client_data.total_energy)));
	            $("#todays_generation").empty();
				$("#todays_generation").text(((summary_client_data.energy_today)));
				$("#total_capacity").empty();
				$("#total_capacity").text((parseFloat(summary_client_data.total_capacity)).toFixed(2).toString().concat(" kW"));
				$("#co2_conversion").empty();
				$("#co2_conversion").text(((summary_client_data.total_co2)));
				summary_client_data.plants.forEach(function(plant_information, index){
		        	$("#pr_tbody").append("<tr><td>" + plant_information.plant_name + "</td><td class='text-center'>" + ((plant_information.performance_ratio) *100).toFixed(2) + " %</td></tr>")
		        	$("#cuf_tbody").append("<tr><td>" + plant_information.plant_name + "</td><td>" + plant_information.cuf + " %</td></tr>")
		        	$("#warnings_and_alarms_tbody").append("<tr><td>" + plant_information.plant_name + "</td><td class='text-center'>" + plant_information.unacknowledged_tickets + "</td><td class='text-center'>" + plant_information.open_tickets + "</td><td class='text-center'>" + plant_information.closed_tickets + "</td></tr>")
		        	$("#details_tbody").append("<tr><td>" + plant_information.plant_name + "</td><td class='text-center'>" + plant_information.plant_location + "</td><td class='text-center'>" + plant_information.plant_capacity + " kW</td><td class='text-center'>" + plant_information.plant_generation_today + "</td><td class='text-center'>NA</td></tr>");
				});

            }

        },
        error: function(data) {
            console.log("error_streams_data");
            data = null;
        }
    });

}