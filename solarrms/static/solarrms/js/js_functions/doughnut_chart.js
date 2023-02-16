function doughnut_chart(chart_data, color_for_entity, ctx, doughnut_title) {
	
	var data = {
	    labels: chart_labels,
	    datasets: [
	        {
	            data: chart_data,
	            backgroundColor: [
	                "#ef5349",
	                "#36a2eb"
	            ],
	            hoverBackgroundColor: [
	                "#ef5349",
	                "#36a2eb"
	            ]
	        }]
	};

	var myDoughnutChart = new Chart(ctx, {
	    type: 'doughnut',
	    data: data,
	    options: {
	    	title: {
	    		display: false,
	    		text: 'Tickets'
	    	}
	    }
	});

}