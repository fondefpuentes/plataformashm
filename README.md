# Plataforma de Monitoreo de Salud Estructural de Puentes
Proyecto FONDEF IT18I0112

El proyecto consiste en el desarrollo de una plataforma web para el análisis y visualización de datos correspondientes a mediciones de sensores instalados en puentes. La plataforma implementa una estrategia de Monitoreo Directo de Salud Estructural (Structural Health Monitoring), permitiendo además la detección automática de anomalías en el puente, basada en los datos recibidos de forma remota. 

Además de información estructural y de localización de puentes gestionados por el Ministerio de Obras Públicas de Chile (MOP), la plataforma permite acceder a las siguientes funcionalidades:
- Exploración de la Estructura en 3D, que permite visualizar e interactuar con una representación en 3D del puente consultado y de los sensores instalados. 
- Mediciones y Alertas en Tiempo Real, que permite visualizar las mediciones que actualmente captan los distintos sensores instalados en el puente, mediante dashboards que se actualizan en tiempo real. Además, permite generar y consultar alertas de datos fuera de rango normal. 
- Análisis de Mediciones Recientes, que despliega un dashboards con análisis de datos capturados en el último día, semana en curso y 14 días antes. 
- Detección Temprana de Daños, que despliega gráficas y resultados de modelos autorregresivos aplicados a cada sensor de la infraestructura instalada en el puente consultado, detectando eventuales anomalías en comparación a su comportamiento normal.
- Consulta de Mediciones Históricas, que permite realizar consultas sobre datos significativos de las mediciones (mínimo, máximo, promedio) realizadas por los sensores instalados en el puente, entre rangos de fecha. 
- Descarga de Mediciones Históricas, que permite descargar los datos capturados por los sensores en un rango de fechas a elección, en un formato compatible con herramientas externas de análisis de datos. 

La plataforma provee, además, una interfaz de administración, que permite gestionar diferentes aspectos de la gestión de los datos de monitoreo y las predicciones a partir de éstos. 

### Pre-requisitos 📋

Antes de ejecutar:
  - Crear ambiente virtual con $ python3 -m venv venv
  - Instalar paquetes con $ pip3 install -r requirements.txt
  - Configurar por cuenta propia base de datos PostgreSQL, e instalar TimescaleDB
  - En caso de servir la aplicación usando gunicorn y nginx, seguir esto: https://www.digitalocean.com/community/tutorials/how-to-serve-flask-applications-with-gunicorn-and-nginx-on-ubuntu-18-04

Luego, ejecutar con 

### Instalación 🔧

_Una serie de ejemplos paso a paso que te dice lo que debes ejecutar para tener un entorno de desarrollo ejecutandose_


$ python3 app.py


_Finaliza con un ejemplo de cómo obtener datos del sistema o como usarlos para una pequeña demo_



## Construido con 🛠️

_Menciona las herramientas que utilizaste para crear tu proyecto_

* [Dropwizard](http://www.dropwizard.io/1.0.2/docs/) - El framework web usado
* [Maven](https://maven.apache.org/) - Manejador de dependencias
* [ROME](https://rometools.github.io/rome/) - Usado para generar RSS


## Autores ✒️

_Menciona a todos aquellos que ayudaron a levantar el proyecto desde sus inicios_

* **Gonzalo Rojas** - *Jefe de Proyecto, Análisis, Diseño, Testing y Documentación* 
* **Johann Llanos** - *Documentación*
* **Carlos Landero** - *Modelo de Datos, Desarrollo Web*
* **Carlos von Plessing**
* **Sergio Saavedra**
* **Diego Varas**
* **Angelo Zapata**


## Licencia 📄

Este proyecto está bajo la licencia (Tu Licencia) - mira el archivo [LICENSE.md](LICENSE.md) para detalles

---
⌨️ Gonzalo Rojas Durán, gonzalorojas@udec.cl
