// Ocultar radio button
$(document).ready(function() { 
    $('input[type="radio"]').click(function() { 
        var inputValue = $(this).attr("value"); 
			var targetBox = $(".hidediv"); 

        if (inputValue == "almacenamiento_programado"){
        	$(targetBox).show();
        }
        else if (inputValue == "evento_inesperado"){
        	$(targetBox).hide();
        }


    }); 
}); 

// Seleccionar todos - ninguno
$('#selectall').click( function() {
	if($('#sensor_list option').prop('selected') == true){
		$('#sensor_list option').prop('selected', false);
	}
	else
		$('#sensor_list option').prop('selected', true);

});

// Desactivar Enter Key
$("#idform").keypress(function(e) {
  if (e.which == 13) {
    event.preventDefault();
  }
});


function diff_hours(dt2, dt1) {

	var diff =(dt2.getTime() - dt1.getTime()) / 1000;
	diff /= (60 * 60);
	return Math.abs(Math.round(diff));

}

//////////////////////////////////////////
///////// Validando Form submit/////////
//////////////////////////////////////////
$('#submitBtn').click(function() {

    var destino_consulta = $('input[name="destino_consulta"]:checked').val();
    var rango_consulta = $('input[name="rango_consulta"]:checked').val();
    var fecha_inicial = $('input[name="fecha_inicial"]').val();
    var hora_inicial = $('input[name="hora_inicial"]').val();
    var fecha_final = $('input[name="fecha_final"]').val();
    var hora_final = $('input[name="hora_final"]').val();
    var lista_sensores = $('#sensor_list').val();
    var consultas_ejes = []
    $("input:checkbox[name=consultas_ejes]:checked").each(function(){
	    consultas_ejes.push($(this).val());
	});

	// Validando checkboxes
	axis_query=document.getElementsByName("consultas_ejes");

    var atLeastOneChecked=false;
    for (i=0; i<axis_query.length; i++) {
        if (axis_query[i].checked === true) {
            atLeastOneChecked=true;
        }
    }
    if (atLeastOneChecked === true) {
        for (i=0; i<axis_query.length; i++) {
            axis_query[i].required = false;
        }
    } else {
        for (i=0; i<axis_query.length; i++) {
            axis_query[i].required = true;
        }
    }

    

    //Validacion Rango de consulta
	if (rango_consulta == "todo_entre_las_fechas"){
		var date_inicial = new Date( fecha_inicial + " " + hora_inicial);
		var date_final = new Date( fecha_final + " " + hora_final);
		if (date_final.getTime() - date_inicial.getTime() <= 0){
			document.getElementsByName("hora_inicial")[0].setCustomValidity("Rango invalido");
			document.getElementsByName("hora_final")[0].setCustomValidity("Rango invalido");
		}
		else{
			document.getElementsByName("hora_inicial")[0].setCustomValidity("");
			document.getElementsByName("hora_final")[0].setCustomValidity("");
		}
	}

	else if (rango_consulta == "horas_por_dia"){
		var date_inicial = new Date( "1970-01-01 " + hora_inicial);
		var date_final = new Date( "1970-01-01 " + hora_final);
		if (date_final.getTime() - date_inicial.getTime() <= 0){
			document.getElementsByName("hora_inicial")[0].setCustomValidity("Rango invalido");
			document.getElementsByName("hora_final")[0].setCustomValidity("Rango invalido");

		} 
		else{
			document.getElementsByName("hora_inicial")[0].setCustomValidity("");
			document.getElementsByName("hora_final")[0].setCustomValidity("");
		}
	}

	// Validacion de bootstrap
	var forms = document.getElementsByClassName('needs-validation');
		var validation = Array.prototype.filter.call(forms, function(form) {

				if (form.checkValidity() === false) {
					event.preventDefault();
					event.stopPropagation();
				}
				form.classList.add('was-validated');

		});


    var h_i_int = hora_inicial.split(":",1);
    var h_f_int = hora_final.split(":",1);
	date_inicial = new Date( fecha_inicial + " " + hora_inicial);
	date_final = new Date( fecha_final + " " + hora_final);
    var lower_bound = 0.2; // 1 solo sensor
    var upper_bound = 18; // todos los sensores
    var number_axis = consultas_ejes.lenght; // numero de sensores involucrados

    // Texto consulta a realizar
    if (destino_consulta == "almacenamiento_programado"){
    	if (rango_consulta == "todo_entre_las_fechas"){
    		//Todo entre [Fecha inicio a las Hora inicio] y [Fecha fin a las Hora fin]
    		var query_hours = diff_hours(date_inicial, date_final); 
    		lower_bound = Math.round(lower_bound * query_hours * number_axis);
    		upper_bound = Math.round(upper_bound * query_hours * number_axis);
    		$('#texto_rango').text("Todo entre [" + fecha_inicial + " a las " + hora_inicial + "] y [" + fecha_final + " a las " + hora_final + "]");
    		$('#texto_sensores').text("Sensores: " + lista_sensores);
    		$('#texto_ejes').text("Ejes: " + consultas_ejes);
    		if(upper_bound != 0)
    			$('#texto_consulta').text("Tamaño estimado \u2245 < 12 MB");
    		else 
    			$('#texto_consulta').text("Tamaño estimado \u2245 [" + lower_bound + " - " + upper_bound + "] MB");
    	}
    	else if (rango_consulta == "horas_por_dia"){
    		//Desde el [Fecha inicio] hasta [Fecha fin] entre los horarios [Hora inicial] y [Hora fin]
    		var query_days = date_final.getTime() - date_inicial.getTime();
    		query_days = query_days / (1000*3600*24);
    		lower_bound =  Math.round(lower_bound * (h_f_int - h_i_int) * query_days);
    		upper_bound =  Math.round(upper_bound * (h_f_int - h_i_int) * query_days);
    		$('#texto_rango').text("Desde el [" + fecha_inicial + "] hasta [" + fecha_final + "] entre los horarios [" + hora_inicial + "] y [" + hora_final + "]");
    		$('#texto_sensores').text("Sensores: " + lista_sensores);
    		$('#texto_ejes').text("Ejes: " + consultas_ejes);
    		$('#texto_consulta').text("Tamaño estimado:\u2245 [" + lower_bound + " - " + upper_bound + "] MB" );
    	}
    }
    else if (destino_consulta == "evento_inesperado"){
        //Todo entre [Fecha inicio a las Hora inicio] y [Fecha fin a las Hora fin]
		var query_hours = diff_hours(date_inicial, date_final); 
		upper_bound = Math.round(upper_bound * query_hours);
	    $('#texto_rango').text("Todo evento inesperado entre [" + fecha_inicial + " a las " + hora_inicial + "] y [" + fecha_final + " a las " + hora_final + "]");
		$('#texto_sensores').text("Sensores: " + lista_sensores);
		$('#texto_ejes').text("Ejes: " + consultas_ejes);
		$('#texto_consulta').text("Tamaño estimado \u2245 [0 - " + upper_bound + "] MB");
    }
});
