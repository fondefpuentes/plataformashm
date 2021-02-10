function getValue(){
	var shownVal = document.getElementById("autocomplete").value;
	var value2send = document.querySelector("#estructuras" + " option[value='" + shownVal + "']").dataset.value;
	print(value2send);
}
function setMarkersOnMap(x){
    /*
    var mymap = L.map('map').setView([-36.906289,-72.398971],6);

    L.tileLayer('http://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}').addTo(mymap);
    L.tileLayer('https://api.maptiler.com/maps/basic/{z}/{x}/{y}.png?key=zZkrANgINoCERa0zI6td').addTo(mymap);

    var markers = L.markerClusterGroup()
    var puentes = x;
    for (var i=0; i < puentes.length; i++){
    markers.addLayer(L.marker([puentes[i][0], puentes[i][1]]).bindPopup('<a href=\"/estructura/'+puentes[i][3]+'\">'+puentes[i][2]+'</a>'));
    }
    mymap.addLayer(markers);
    */

    //mapa político
    var osmLayer = new L.TileLayer('https://api.maptiler.com/maps/basic/{z}/{x}/{y}.png?key=zZkrANgINoCERa0zI6td');
    //mapa físicobasic
    var ESRIWorldImageryLayer = new L.TileLayer('http://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}');

    var baseMaps = {
        'Político' : osmLayer,
        'Satelital': ESRIWorldImageryLayer
    };

    //se agregan imagenes satelitales al mapa
    var layerControl = new L.control.layers(baseMaps);
    //Se crea el mapa, se establece el foco y zoom iniciales
    var map = L.map('map').setView([-36.906289,-72.398971],6);
    map.addControl(layerControl);    
    //map.addLayer(ESRIWorldImageryLayer);
    map.addLayer(osmLayer);

    var markers = L.markerClusterGroup()
    var puentes = x;
    for (var i=0; i < puentes.length; i++){
    markers.addLayer(L.marker([puentes[i][0], puentes[i][1]]).bindPopup('<a href=\"/estructura/'+puentes[i][3]+'\">'+puentes[i][2]+'</a>'));
    }
    map.addLayer(markers);

}