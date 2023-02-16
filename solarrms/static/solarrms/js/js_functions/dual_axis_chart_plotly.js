
function dual_axis_chart_plotly(x_array1, y_array1, x_array2, y_array2, y_axis1_text, y_axis2_text, name1, name2, title_dual_axis_chart, div_name, page, scatter_chart, l_m, r_m, b_m, t_m) {

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

	if(scatter_chart == 0) {
		var y_axis1 = {
			x: x_array1,
			y: y_array1,
			text: y_axis1_text,
			name: name1,
			marker: {
				color: color_past
			},
			hoverinfo: 'text',
			type: 'scatter'
		};

		var y_axis2 = {
			x: x_array2,
			y: y_array2,
			text: y_axis2_text,
			name: name2,
			yaxis: 'y2',
			hoverinfo: 'text',
			type: 'scatter',
			marker: {
				color: color_today
			}
		};
	} else {
		var y_axis1 = {
			x: x_array1,
			y: y_array1,
			text: y_axis1_text,
			name: name1,
			marker: {
				color: color_past
			},
			hoverinfo: 'text',
			type: 'bar'
		};

		var y_axis2 = {
			x: x_array2,
			y: y_array2,
			text: y_axis2_text,
			name: name2,
			yaxis: 'y2',
			type: 'scatter',
			/*mode: 'markers',*/
			hoverinfo: 'text',
			marker: {
				color: color_today
			}
		};
	}

	var data = [y_axis1, y_axis2];

	var layout = {
		/*title: "<b>" + title_dual_axis_chart + "</b>",
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
			x: 0.3,
			y: 1.2,
			orientation: "h"
		},
		xaxis: {
		showgrid: false,
		ticklen: 7,
		dtick: 11
		},
      	yaxis: {title: name1},
      	yaxis2: {
	        title: name2,
	        overlaying: 'y',
	        side: 'right'
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