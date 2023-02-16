$(document).ready(function() {
    plant_parameters();
    inverter_names();
});

$(function() {
    $(".datetimepicker_start_compare_plant_table_day").datetimepicker({
        timepicker: false,
        format: 'd/m/Y',
        scrollMonth:false,
        scrollTime:false,
        scrollInput:false
    });
    $(".datetimepicker_start_compare_plant_table_day").on('change', function(ev) {
        $(this).datetimepicker('hide');
    });
});

function get_dates(){
    // get the start date
    var st = $("#start_compare_parameters_day").val();
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

var plant_parameters_array = "";

var plant_inverters_parameters_array = "";

function plant_parameters() {

	var param_arr = [];
	var params_all = [];

	plant_parameters_array = source_key.toString() + "=";

	$('#plant_parameters').empty();
    $.ajax({
		type: "GET",
		url: "/api/sources/".concat(source_key).concat('/streams/'),
		success: function(streams){
			$('#plant_parameters').html('');
			if (streams.length == 0) {
			  $('#plant_parameters').append("<option>Parameters not present! </option>");
			} else {
			  for (var i = 0 ; i < streams.length ; i++) {
			    /*$('#plant_parameters').append("<option value=" + streams[i].name + ">" + streams[i].name + "</option>");*/
			    $('#plant_parameters').append("<div class='checkbox'><label><input type='checkbox' id='" + streams[i].name + "' value='" + streams[i].name + "'>"+ streams[i].name + "</label></div>");

			    $("#"+streams[i].name).change(function() {
			    	if(plant_parameters_array == "") {
						plant_parameters_array = source_key.toString() + "=";
					}
			    	param_arr = [];
					var checkbox_plant_param = this.id;
					if(document.getElementById(checkbox_plant_param.toString()).checked) {
						param_arr.push(checkbox_plant_param);
						params_all.push(checkbox_plant_param);
					} else {
						for(var k = 0; k < params_all.length; k++) {
							if(params_all[k] == checkbox_plant_param) {
								var index = params_all.indexOf(params_all[k]);
								params_all.splice(index, 1);
							}
						}
						param_arr = params_all;
						plant_parameters_array = source_key.toString() + "=";
					}
					var array = "";
					for(var k = 0; k < param_arr.length; k++) {
						array = array + param_arr[k] + ",";
					}
					if(array != null) {
						plant_parameters_array = plant_parameters_array + array;
					}
					if(plant_parameters_array == source_key.toString() + "=" || plant_parameters_array == source_key.toString()) {
						plant_parameters_array = "";
					}
				});
			  } 
			}
      	},
      	error: function(data){
			console.log("no data");
      	}
    });

}

function inverter_names() {

	var array = null;

	var plant_inverters_param_array = "";

	var inverter_name = "";

	var invereter_sourcekey = "";

	$('#inverter_names').empty();
    $.ajax({
        type: "GET",
        async: false,
        url: "/api/solar/plants/".concat(plant_slug).concat('/inverters/'),
        success: function(inverters) {
        	var inverters_array = inverters;
        	for (var i = 0 ; i < inverters.length ; i++) {
            	/*$('#inverter_names').append("<div class='checkbox'><label><input type='checkbox' value='" + inverters[i].sourceKey + "' sourceKey='" + inverters[i].sourceKey + "'>" + inverters[i].name + "</label></div>");*/
				$('#inverter_names').append("<li id='" + inverters[i].name + "' source='" + inverters[i].sourceKey + "'><a class='collapsed' role='button' data-toggle='collapse' data-parent='#accordion' href='#collapse" + inverters[i].name + "' aria-expanded='false' aria-controls='collapse" + inverters[i].name + "' style='font-size: 15px;font-weight: 600;'>" + inverters[i].name + "</a></li>");
				$('#inverter_names').append("<div id='collapse" + inverters[i].name + "' class='panel-collapse collapse' role='tabpanel' aria-labelledby='heading" + inverters[i].name + "'><div class='panel-body' id='panel-" + inverters[i].name + "' source='" + inverters[i].sourceKey + "'> </div></div>");

				$.ajax({
					type: "GET",
					async: false,
					url: "/api/sources/".concat(inverters_array[0].sourceKey).concat('/streams/'),
					success: function(streams){
						$("#panel-"+inverters_array[i].name).html('');
						if (streams.length == 0) {
							$("#panel-"+inverters_array[i].name).append("<option>No Streams are present! </option>");
						} else {
							for (var m = 0 ; m <= streams.length-1 ; m++) {
								$("#panel-"+inverters_array[i].name).append("<div class='checkbox'><label><input type='checkbox' id='" + inverters_array[i].sourceKey + "-" + streams[m].name + "' name='" + inverters_array[i].name + "' value='" + streams[m].name + "'>"+ streams[m].name + "</label></div>");

								$('#'+inverters_array[i].sourceKey+"-"+streams[m].name).change(function() {
									var checkbox_inverter_param = this.id;
									var inverter_params = checkbox_inverter_param.split("-");
									if(document.getElementById(checkbox_inverter_param.toString()).checked) {
										
										if(array == null) {
											array = "&" + inverter_params[0] + "=" + inverter_params[1];
										} else {
											var no_need = 0;
											for(var z = 0; z < array.length; z++) {
												if(array[z] == "=") {
													var index = z;
													var ar1 = array.substring(index-15, index);
													var ar2	= array.substring(index+1, array.length);
													var ar3 = array.substring(0, index-15);
													if(inverter_params[0] == ar1) {
														no_need = 1;
														array =  ar3 + ar1 + "=" + ar2 + "," + inverter_params[1];
														continue;
													}
												}
											}
											if(no_need == 0) {
												array = array + "&" + inverter_params[0] + "=" + inverter_params[1];	
											}
										}
									} else {
										var un_check = inverter_params[0]+"="+inverter_params[1];

										var count_array = 0;
										var count_source_no_need = 0;

										var arr1 = [];
										var arr2 = [];

										var arr1_string = "";
										var arr2_string = "";

										un_check = un_check.split("=");

										for(var z = 0; z < array.length; z++) {
											if(array[z] == "&") {
												count_array++;
											}
										}

										if(count_array > 1) {
											arr1 = array.split("&");
											var ar1 = arr1.shift();

											for(var z = 0; z < arr1.length; z++) {
												arr1[z] = arr1[z].split("=");
											}

											for(c = 0; c < arr1.length; c++) {
												if(arr1[c][0] == un_check[0]) {
													arr1[c][1] = arr1[c][1].split(",");
													for(c1 = 0; c1 < arr1[c][1].length; c1++) {
														var index = arr1[c][1].indexOf(arr1[c][1][c1]);
														arr1[c][1].splice(index, 1);
													}
													for(c1 = 0; c1 < arr1[c][1].length; c1++) {
														if(arr1_string == null) {
															arr1_string = arr1[c][1][c1];
														} else {
															arr1_string = arr1_string + "," + arr1[c][1][c1];
														}
													}
													arr1[c][1] = arr1_string;
												}
											}

											for(var l = 0; l < arr1.length; l++) {
												if(arr1[l][1] == null) {
													var index = arr1.indexOf(arr1[l]);
													arr1.splice(index, 1);
												}
											}

											arr1_string = "";

											for(r = 0; r < arr1.length; r++) {
												arr1_string = arr1_string + "&" + arr1[r][0] + "=" + arr1[r][1];
											}

											array = arr1_string;

										} else {
											arr2 = array.split("=");

											arr2[1] = arr2[1].split(",");

											if(arr2[1].length == 1) {
												count_source_no_need = 1;
											}

											for(var w = 0; w < arr2[1].length; w++) {
												if(arr2[1][w] == un_check[1]){
													var index = arr2[1].indexOf(arr2[1][w]);
													arr2[1].splice(index, 1);
												}
											}

											if(count_source_no_need == 0) {
												arr2_string = arr2[0] + "=" + arr2[1];	
												array = arr2_string;
											} else {
												array = "";
											}
										}

										/*var new_array = null;

										var par_remove = un_check[1].length;

										for(var z = 0; z < array.length; z++) {
											var array1 = array.split("=");
											var array2 = array.split(",");
											if(array[z] == "=") {
												var index = z;
												var ar1 = array.substring(index-15, index+1);
												var ar2	= array.substring(index+1, array.length);
												var new_index = null;
												for(var p = 0; p < ar2.length; p++) {
													if(ar2[p] == "&" || ar2[p].indexOf(ar2[p]) == ar2.length-1) {
														new_index = p;
													}
												}
												var ar3 = ar2.substring(0, new_index+1);
												var ar4 = array.substring(0, index-15);
												var ar5 = ar2.substring(new_index+1, ar2.length);
												var array2 = null;
												
												ar3.replace(un_check[1], '');

												array =  ar4 + ar1 + ar2 + ar3 + ar5;
											}
										}*/

										/*for(var k = 0; k < uncheck_delete.length; k++) {
											if(uncheck_delete[k] == un_check) {
												var index = uncheck_delete.indexOf(uncheck_delete[k]);
												uncheck_delete.splice(index, 1);
											}
										}

										var index = uncheck_delete.indexOf(uncheck_delete[0]);
										uncheck_delete.splice(index, 1);

										array = null;
										for(var t = 0; t < uncheck_delete.length; t++) {
											if(array == null) {
												array = "&" + uncheck_delete[t];	
											} else {
												array = array + "&" + uncheck_delete[t];	
											}
										}*/
									}
									plant_inverters_parameters_array = array;
								});
							}
						}
					},
					error: function(data){
						console.log("no data");
					}
				});

				/*$('#'+inverters[i].name).click(function() {
					inverter_name = this.id;
					invereter_sourcekey = $(this).attr("source");
				});*/
        	}
    	},
        error: function(data) {
            console.log("error_streams_data");
            data = null;
        }
	});
}

function inverter_parameters() {

	var dates = get_dates();
	var st = dates[0];
	var et = dates[1];

	var api = null;

	if(plant_parameters_array[plant_parameters_array.length-1] == ",") {
		plant_parameters_array = plant_parameters_array.substring(0, plant_parameters_array.length-1);
	}

	if(plant_parameters_array != (source_key.toString()+"=") && plant_inverters_parameters_array != "") {
		api = "/api/msources/data/?start=".concat(st).concat('&end=').concat(et).concat("&"+plant_parameters_array).concat(plant_inverters_parameters_array);
	} else if(plant_parameters_array == (source_key.toString()+"=") && plant_inverters_parameters_array != "") {
		api = "/api/msources/data/?start=".concat(st).concat('&end=').concat(et).concat(plant_inverters_parameters_array);
	} else if(plant_parameters_array != (source_key.toString()+"=") && plant_inverters_parameters_array == "") {
		api = "/api/msources/data/?start=".concat(st).concat('&end=').concat(et).concat("&"+plant_parameters_array);
	} else {
		api = "/api/msources/data/?start=".concat(st).concat('&end=').concat(et);
	}

	$.ajax({
		type: "GET",
		url: api,
		success: function(data){
			if(data == "") {
				$("#parameters_selected").empty();
		        $("#parameters_selected").append("<div class='alert alert-warning' id='alert'>No parameter selected.</div>");

			} else {
				$("#parameters_selected").empty();

				var parsed_data = Papa.parse(data);

				$("#table_plant_parameters").empty();
				$("#table_plant_parameters").append("<div class='row'><div class='col-sm-12'><div class='panel'><div class='panel-body'><div class='table-responsive'><table class='table table-bordered'><thead><tr id='table_headers'></tr></thead><tbody id='table_body'></tbody></table></div></div></div></div></div>");

				for(var j = 0; j < parsed_data.data[0].length; j++) {
					$("#table_headers").append("<th class='text-center'>"+parsed_data.data[0][j]+"</th>");
				}
				for(var j = 1; j < parsed_data.data.length-1; j++) {
					$("#table_body").append("<tr id='new_row"+j+"'></tr>")
					for(var k = 0; k < parsed_data.data[j].length; k++) {
						$("#new_row"+j).append("<td class='text-center'>"+ parsed_data.data[j][k] +"</td>");
					}
				}
			}
      	},
      	error: function(data){
			console.log("no data");

			$("#parameters_selected").empty();
		    $("#parameters_selected").append("<div class='alert alert-warning' id='alert'>No parameter selected.</div>");
      	}
    });

}