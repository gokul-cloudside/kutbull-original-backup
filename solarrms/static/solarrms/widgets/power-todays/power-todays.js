$(document).ready(function() {
    var dates = get_dates();
	var st = dates[0];
	var et = dates[1];

	power_data(plant_slug, st, et, '#power_chart svg');
});

function get_dates(){
    
    // get the start date
    var st = new Date();
    // prepare an end date
    var e = new Date(st.getTime());
    e = new Date(e.setDate(st.getDate() + 1));
    // convert them into strings

    st = dateFormat(st, "yyyy-mm-dd");
    e = dateFormat(e, "yyyy-mm-dd");

    return [st, e];
}