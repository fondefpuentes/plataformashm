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

//Cambio de texto, consultas por rango

$(document).ready(function() { 
    $('input[type="radio"]').click(function() { 
        var inputValue = $(this).attr("value"); 
        var targetBox1 = document.getElementById("range_text1");
        var targetBox2 = document.getElementById("range_text2");

        if (inputValue == "todo_entre_las_fechas"){
            $(targetBox1).text("a las:");
            $(targetBox2).text("a las:");
        }
        else if (inputValue == "horas_por_dia"){
            $(targetBox1).text("Hora inicio:");
            $(targetBox2).text("Hora fin:");
        }


    }); 
}); 

// Desactivar Enter Key
$("#idform").keypress(function(e) {
  if (e.which == 13) {
    event.preventDefault();
  }
});

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
    var lista_sensores = []
    $("input:checkbox[name=sensor_selected]:checked").each(function(){
        lista_sensores.push($(this).val());
        console.log(lista_sensores)
    });
    var consultas_ejes = []
    $("input:checkbox[name=consultas_ejes]:checked").each(function(){
        consultas_ejes.push($(this).val());
    });
    var consultas_sensor = []
    $("input:checkbox[name=consultas_sensor]:checked").each(function(){
        consultas_sensor.push($(this).val());
    });


	// Validando checkboxes
	sensor_query=document.getElementsByName("consultas_sensor");

    var atLeastOneChecked=false;
    for (i=0; i<sensor_query.length; i++){
        if (sensor_query[i].checked === true){
            atLeastOneChecked=true;
        }
    }
    if (atLeastOneChecked === true){
        for (i=0; i<sensor_query.length; i++){
            sensor_query[i].required = false;
        }
    } 
    else{
        for (i=0; i<sensor_query.length; i++){
            sensor_query[i].required = true;
        }
    }

    sensor_query=document.getElementsByName("sensor_selected");
    var atLeastOneChecked_sensor=false;
    for (i=0; i<sensor_query.length; i++) {
        if (sensor_query[i].checked === true) {
            atLeastOneChecked_sensor=true;
        }
    }
    if (atLeastOneChecked_sensor === true) {
        $('#validate_sensor_list').removeClass('d-block')
    } else {
        $('#validate_sensor_list').addClass('d-block');
    }

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

				if (form.checkValidity() === false || atLeastOneChecked_sensor === false) {
					event.preventDefault();
					event.stopPropagation();
				}
				form.classList.add('was-validated');

		});



    // Texto consulta a realizar
    if (destino_consulta == "almacenamiento_programado"){
    	if (rango_consulta == "todo_entre_las_fechas"){
    		//Todo entre [Fecha inicio a las Hora inicio] y [Fecha fin a las Hora fin]
    		$('#texto_rango').text("Todo entre [" + fecha_inicial + " a las " + hora_inicial + "] y [" + fecha_final + " a las " + hora_final + "]");
    		$('#texto_sensores').text("Sensores: " + lista_sensores);
    		$('#texto_ejes').text("Ejes: " + consultas_ejes);
    		$('#texto_consulta').text("Consultas: " + consultas_sensor);
    	}
    	else if (rango_consulta == "horas_por_dia"){
    		//Desde el [Fecha inicio] hasta [Fecha fin] entre los horarios [Hora inicial] y [Hora fin]
    		$('#texto_rango').text("Desde el [" + fecha_inicial + "] hasta [" + fecha_final + "] entre los horarios [" + hora_inicial + "] y [" + hora_final + "]");
    		$('#texto_sensores').text("Sensores: " + lista_sensores);
    		$('#texto_ejes').text("Ejes: " + consultas_ejes);
    		$('#texto_consulta').text("Consultas: " + consultas_sensor);
    	}
    }
    else if (destino_consulta == "evento_inesperado"){
        //Todo entre [Fecha inicio a las Hora inicio] y [Fecha fin a las Hora fin]
	    $('#texto_rango').text("Todo evento inesperado entre [" + fecha_inicial + " a las " + hora_inicial + "] y [" + fecha_final + " a las " + hora_final + "]");
		$('#texto_sensores').text("Sensores: " + lista_sensores);
		$('#texto_ejes').text("Ejes: " + consultas_ejes);
		$('#texto_consulta').text("Consultas: " + consultas_sensor);
    }  
});
