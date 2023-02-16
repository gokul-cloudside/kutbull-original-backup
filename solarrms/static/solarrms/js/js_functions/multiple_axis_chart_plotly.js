function multiple_axis_chart_plotly(all_x_arrays, all_y_arrays, all_y_array_names, all_y_axis_number, title_multiple_axis_chart, div_name, l_m, r_m, page, b_m, t_m) {

	/*x_array1 - Array having the data to be plotted on x-axis
	y_array1 - Array having the data to be plotted on y-axis1
	x_array2 - Array having the data to be plotted on x-axis
	y_array2 - Array having the data to be plotted on y-axis2
	name1 - Title of y_axis1(String)
	name2 - Title of y_axis1(String)
	title_dual_axis_chart - The title for the chart
	div_name - Name of the div. HTML Element
	width - Integer which defines the width of the chart
	height - Integer which defines the height of the chart*/

	/*NOTE - x_array1 and x_array2 could be same*/

	var data = [];

	for(var i = 0; i < all_x_arrays.length; i++) {
		data.push({
			x: all_x_arrays[i],
			y: all_y_arrays[i],
			name: all_y_array_names[i],
			yaxis: all_y_axis_number[i],
			/*marker: {
				color: color_row[i]
			},*/
			type: 'scatter'
		});
	}

	console.log(data);

	var layout = {
		title: "<b>" + title_multiple_axis_chart + "</b>",
		titlefont: {
	   		family: 'Helvetica',
	    	size: 16,
	    	color: "#2b425b"
	    },
		margin: {
			l: l_m,
			r: r_m,
			b: b_m,
			t: t_m,
			pad: 0
		},
		showlegend: false,
		legend: {
			x: 0.3,
			y: 1.2,
			orientation: "h"
		},
      	yaxis: {
      		title: all_y_array_names[0] + ' & ' + all_y_array_names[1],
      	},
		yaxis2: {
	        title: all_y_array_names[2],
	        overlaying: 'y',
	        side: 'right',
	        anchor: 'x'
		},
		font: {
			family: 'Helvetica',
			size: 11,
			weight: 'normal',
			color: "#000000"
		}
    };

    if(page == 1) {
    	Plotly.newPlot(div_name, data, layout, {displaylogo: false, modeBarButtonsToRemove: ['sendDataToCloud', 'lasso2d', 'select2d', , 'zoom2d', 'pan2d', 'zoomIn2d', 'zoomOut2d', 'autoScale2d', 'resetScale2d', 'hoverClosestCartesian', 'hoverCompareCartesian']});
    } else {
    	Plotly.newPlot(div_name, data, layout, {displaylogo: false, modeBarButtonsToRemove: ['sendDataToCloud', 'lasso2d', 'select2d']});
    }

}