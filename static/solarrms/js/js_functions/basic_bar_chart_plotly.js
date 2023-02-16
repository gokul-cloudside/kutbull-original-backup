var color_past = '#B5E3F2';
var color_today = '#00ABD9';
var color_arr = [];

/*rgb(86,86,86)*/
/*rgb(239,83,73)*/

function basic_bar_chart_plotly(x_array, y_array, y_axis_title, color_array, chart_title, div_name, l_m, r_m, page, b_m, t_m) {

	/*x_array - Array having the data to be plotted on x-axis
	y_array - Array having the data to be plotted on y-axis
	color_array - Array defining the color the bars
	chart_title - The title for the chart
	div_name - Name of the div. HTML Element*/

	var d3 = Plotly.d3;
	var img_jpg= d3.select('#jpg-export');

	color_arr = [];

	if(x_array.length == 7) {
		for (var i = 0; i < x_array.length - 1; i++) {
			color_arr.push(color_past);
		}
		color_arr.push(color_today);	
	} else {
		for (var i = 0; i <= x_array.length - 1; i++) {
			color_arr.push(color_past);
		}
	}
	

	var bar_chart_data = {
		x: x_array,
		y: y_array,
		name: y_axis_title,
		marker: {
			color: color_array
		},
		type: 'bar'
	};

	var data = [bar_chart_data];

	var layout = {
		title: "<b>" + chart_title + "</b>",
		titlefont: {
	   		family: 'Helvetica',
	    	size: 16,
	    	color: "#2b425b"
	    },
	    image: 'jpg',
		xaxis: {
			showgrid: false/*,
			ticklen: 7,
			dtick: 3,
			tickangle: 0*/
		},
		yaxis: {
			showgrid: true,
			title: y_axis_title,
		},
		margin: {
			l: l_m,
			r: r_m,
			b: b_m,
			t: t_m,
			pad: 0
		},
		font: {
			family: 'Helvetica',
			size: 11,
			weight: 'normal',
			color: "#000000"
		},
		barmode: 'stack'
  		/*#5a2a6b*/
  		/*#8b5898*/
  		/*#441958*/
  		/*#ffffcc*/
  		/*#996633*/
  		/*#996699*/
	};

	if(page == 1) {
		Plotly.newPlot(div_name, data, layout, {displaylogo: false, modeBarButtonsToRemove: ['sendDataToCloud', 'zoom2d', 'pan2d', 'zoomIn2d', 'zoomOut2d', 'autoScale2d', 'resetScale2d', 'hoverClosestCartesian', 'hoverCompareCartesian']})
		.then( function(gd)
		    {
				Plotly.toImage(gd,{height:300,width:300})
		   			.then(
		        		function(url)
		        	{
		            	img_jpg.attr("src", url);
		           		return Plotly.toImage(gd,{format:'jpeg',height:400,width:400});
		         	}
		        )
		    });
	} else if(page == 2) {		
		Plotly.newPlot(div_name, data, layout, {displaylogo: false, modeBarButtonsToRemove: ['sendDataToCloud', 'zoom2d', 'pan2d', 'zoomIn2d', 'zoomOut2d', 'autoScale2d', 'resetScale2d', 'hoverClosestCartesian', 'hoverCompareCartesian']});
	} else {
		Plotly.newPlot(div_name, data, layout, {displaylogo: false, modeBarButtonsToRemove: ['sendDataToCloud']});
	}

}