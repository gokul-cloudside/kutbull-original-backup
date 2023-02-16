function bubble_chart_plotly(x_arrays, all_y_arrays, all_text, marker_circle, chart_title, div_name, l_m, r_m, page, b_m, t_m) {

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

	var color_row = ['#B5E3F2', '#00ABD9', '#BED73E'];

	var data = [];

	var c = 2;

	for(var i = 0; i < x_arrays.length; i++) {
		data.push({
			x: x_arrays[i],
			y: all_y_arrays[i],
			text: all_text[i],
			mode: 'markers',
			marker: {
				sizeref: c,
				size: marker_circle[i],
				sizemode: 'area'
			}
		});
	}

	var layout = {
		title: "<b>" + chart_title + "</b>",
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
		xaxis: {
			showgrid: true
		},
		yaxis: {
			showgrid: true,
			showticklabels: false
		},
		font: {
			family: 'Helvetica',
			size: 11,
			weight: 'normal',
			color: "#000000"
		}

	};

	if(page == 1 || page == 2) {
		Plotly.newPlot(div_name, data, layout, {displaylogo: false, modeBarButtonsToRemove: ['sendDataToCloud', 'zoom2d', 'pan2d', 'zoomIn2d', 'zoomOut2d', 'autoScale2d', 'resetScale2d', 'hoverClosestCartesian', 'hoverCompareCartesian', 'select2d', 'lasso2d']});
	} else {
		Plotly.newPlot(div_name, data, layout, {displaylogo: false, modeBarButtonsToRemove: ['sendDataToCloud']});
	}

	/*myPlot.on('plotly_hover', function(data){
		console.log(data);
	    var infotext = data.points.map(function(d){
	    	console.log(d);
	    	return (d.data.name+': x= '+d.x+', y= '+d.y.toPrecision(3));
	    });

	    hoverInfo.innerHTML = infotext.join('
	');
	})
	 .on('plotly_unhover', function(data){
	    hoverInfo.innerHTML = '';
	});*/

}