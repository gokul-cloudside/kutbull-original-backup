function inverters_csv_parse_data(st, et, inverter_keys, stream_name) {
    
    if(inverter_keys[0] == "") {
    	inverter_keys.shift();
    }
    
    var startDate = st;
    var endDate = et;

    var power_data = null;
    // now make the data call
    $.ajax({
        type: "GET",
        async: false,
        url: "/solar/plant/".concat(plant_slug).concat("/data/file/?inverters=").concat(inverter_keys.join()).concat("&startTime=").concat(startDate).concat("&endTime=").concat(endDate).concat("&streamNames="+stream_name),
        success: function(data) {
        	power_data = Papa.parse(data);
/*
            for (var i=0; i < power_data.data.length; i++){
                for (var j=0; j < power_data.data[i].length; j++) {
                    if (power_data.data[i][j].length == 0) {
                        power_data.data[i][j] = null;
                    }
                }
            }
*/
        },
      	error: function(data){
        	console.log("no data");
  		}
    });
    return power_data;
}