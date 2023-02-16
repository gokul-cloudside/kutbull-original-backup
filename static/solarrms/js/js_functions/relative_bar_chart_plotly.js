function relative_bar_chart_plotly(x_arrays, all_y_arrays, color_row, all_y_array_names, chart_title, div_name, barmode_type, l_m, r_m, page, b_m, t_m) {

	/*x_array - Array having the data to be plotted on x-axis
	number_of_stack_bars - Number of bars to be present in stack bar
	all_y_arrays - Array of arrays where each array has the data to plot that source
	all_y_array_names - Array of string where each source name is defined
	div_name - Name of the div. HTML Element*/

	/*color_arr = [];
	for (var i = 0; i < x_arrays.length - 1; i++) {
		color_arr.push(color_past);
	}
	color_arr.push(color_today);*/

	var data = [];

	for(var i = 0; i < x_arrays.length; i++) {
		data.push({
			x: x_arrays[i],
			y: all_y_arrays[i],
			name: all_y_array_names[i],
			marker: {
				color: color_row[i]
			},
			type: 'bar'
		});
	}

	var layout = {
		/*title: "<b>" + chart_title + "</b>",
		titlefont: {
	   		family: 'Helvetica',
	    	size: 16,
	    	color: "#2b425b"
	    },*/
		margin: {
			l: l_m,
			r: r_m,
			b: b_m,
			t: t_m,
			pad: 0
		},
		showlegend: true,
		legend: {
			x: 0.1,
			y: 1.3,
			orientation: "h"
		},
		xaxis: {
			showgrid: true,
			ticklen: 7,
			dtick: 2,
			tickangle: 0
		},
		yaxis: {
			showgrid: true
		},
		font: {
			family: 'Helvetica',
			size: 11,
			weight: 'normal',
			color: "#000000"
		},
		barmode: barmode_type

	};

	if(page == 1 || page == 2) {
		Plotly.newPlot(div_name, data, layout, {displaylogo: false, modeBarButtonsToRemove: ['sendDataToCloud', 'zoom2d', 'pan2d', 'zoomIn2d', 'zoomOut2d', 'autoScale2d', 'resetScale2d', 'hoverClosestCartesian', 'hoverCompareCartesian']});
	} else {
		Plotly.newPlot(div_name, data, layout, {displaylogo: false, modeBarButtonsToRemove: ['sendDataToCloud']});
	}

}