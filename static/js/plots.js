
$('#first_cat').on('change',function(){

    $.ajax({
        url: "/bar",
        type: "GET",
        contentType: 'application/json;charset=UTF-8',
        data: {
            'selected': document.getElementById('first_cat').value

        },
        dataType:"json",
        success: function (data) {
			Plotly.newPlot('lineplot', data);
        }
    });
    $.ajax({
        url: "/bar2",
        type: "GET",
        contentType: 'application/json;charset=UTF-8',
        data: {
            'selected': document.getElementById('first_cat').value

        },
        dataType:"json",
        success: function (data) {
			Plotly.newPlot('barplot', data);
        }
    });
})
