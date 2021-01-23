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


function estimate_size(dt1, dt2,n_axis,n_sensor,type) {

	var map_hours = [2,3,4,5, 7,8,9,10, 13,14,15,16, 18,19,20,21]; //Bloques de horarios
	var low_size = 0.0;
	var high_size = 0.0;
	
	//Check invalid values
	if(n_sensor == 0 || n_axis == 0 || isNaN(dt1) || isNaN(dt2) || dt2.getTime() <= dt1.getTime()){
		return 0;
	}

	if(type == "todo_entre_las_fechas"){

		while(dt1.getTime() < dt2.getTime()){
			if(map_hours.includes(dt1.getHours())){
				low_size += 0.7;
				high_size += 1.3;
			}
			dt1.setHours(dt1.getHours() + 1);
		}

	}

	if(type == "horas_por_dia"){

		var diff =(dt2.getTime() - dt1.getTime()) / 1000;
		diff /= (60 * 60);
		var days = Math.abs(Math.round(diff));

		while(dt1.getHours() < dt2.getHours()){
			if(map_hours.includes(dt1.getHours())){
				low_size += 0.7;
				high_size += 1.3;
			}
			dt1.setHours(dt1.getHours() + 1);
		}
		low_size *= days;
		high_size *= days;
	}

	low_size = low_size * n_axis * n_sensor;
	high_size = high_size * n_axis * n_sensor;

	var estimate = "[" + low_size.toFixed(1) + " - " + high_size.toFixed(1) + "]";

	return estimate;
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
    
    //3,4MB por sensor y eje
    var number_axis = consultas_ejes.length; // numero de sensores involucrados
    var number_sensor = lista_sensores.length;


    // Texto consulta a realizar
    if (destino_consulta == "almacenamiento_programado"){
    	if (rango_consulta == "todo_entre_las_fechas"){
    		//Todo entre [Fecha inicio a las Hora inicio] y [Fecha fin a las Hora fin]
    		$('#texto_rango').text("Todo entre [" + fecha_inicial + " a las " + hora_inicial + "] y [" + fecha_final + " a las " + hora_final + "]");
    		$('#texto_sensores').text("Sensores: " + lista_sensores);
    		$('#texto_ejes').text("Ejes: " + consultas_ejes);
    		$('#texto_consulta').text("Tamaño estimado \u2245 "  + estimate_size(date_inicial,date_final,number_axis,number_sensor,"todo_entre_las_fechas") + " MB");
    	}
    	else if (rango_consulta == "horas_por_dia"){
    		//Desde el [Fecha inicio] hasta [Fecha fin] entre los horarios [Hora inicial] y [Hora fin]
    		$('#texto_rango').text("Desde el [" + fecha_inicial + "] hasta [" + fecha_final + "] entre los horarios [" + hora_inicial + "] y [" + hora_final + "]");
    		$('#texto_sensores').text("Sensores: " + lista_sensores);
    		$('#texto_ejes').text("Ejes: " + consultas_ejes);
    		$('#texto_consulta').text("Tamaño estimado:\u2245 "  + estimate_size(date_inicial,date_final,number_axis,number_sensor,"horas_por_dia") + " MB" );
    	}
    }
    else if (destino_consulta == "evento_inesperado"){
        //Todo entre [Fecha inicio a las Hora inicio] y [Fecha fin a las Hora fin]
	    $('#texto_rango').text("Todo evento inesperado entre [" + fecha_inicial + " a las " + hora_inicial + "] y [" + fecha_final + " a las " + hora_final + "]");
		$('#texto_sensores').text("Sensores: " + lista_sensores);
		$('#texto_ejes').text("Ejes: " + consultas_ejes);
		$('#texto_consulta').text("Tamaño estimado \u2245 "  + estimate_size(date_inicial,date_final,number_axis,number_sensor,"todo_entre_las_fechas") + " MB");
    }
});
