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


### Instalación 🔧

Cumplidos los pre-requisitos, se debe ejecutar el siguiente comando

$ python3 app.py

## Manual de Uso y Administración 📖

Disponible [aquí] (https://github.com/fondefpuentes/plataformashm/blob/master/Ejecuci%C3%B3n%20y%20Gesti%C3%B3n%20Plataforma%20de%20Monitoreo%20Estructural.pdf) (PDF, 4.42MB)


## Construido con 🛠️

Las herramientas que se utilizaron para el desarrollo y la ejecución de este proyecto son:

* [Flask](https://flask.palletsprojects.com/) - El framework web usado
* [Thingsboard](https://thingsboard.io/) - Servidor y cliente de transmisión de datos y visualizador de mediciones en tiempo real
* [Plotly](https://plotly.com/) - Framework para desarrollo y despliegue de dashboards
* [Unity](https://store.unity.com/es/products/unity-pro) - Entorno de desarrollo y ejecución de visualizador 3D 


## Autores ✒️


* **Fernando Cerda** - *Director del Proyecto Proyecto FONDEF IT18I0112*
* **Gonzalo Rojas** - *Director Alterno Proyecto Proyecto FONDEF IT18I0112. Jefe de Proyecto de Desarrollo. Análisis, Diseño, Testing y Documentación* 
* **Johann Llanos** - *Líder de Equipo de Desarrollo, Arquitectura del sistema*
* **Carlos Landero** - *Modelo de Datos, Desarrollo Web*
* **Carlos von Plessing** - *Arquitectura de subsistema de transmisión y gestión de datos en tiempo real*
* **Sergio Saavedra** - *Modelado 3D, gestión de modelos BIM, panel de administración*
* **Diego Varas** - *Dashboard de datos recientes*
* **Sergio Navarrete** - *Consulta y descarga de datos históricos*
* **Angelo Zapata** - *Implementación de modelos autorregresivos para detección de anomalías*


## Licencia 📄

Este proyecto está bajo licencia GNU GPL - mira el archivo [LICENSE.md](LICENSE.md) para detalles

---
⌨️ Gonzalo Rojas Durán, [gonzalorojas@udec.cl] (mailto:gonzalorojas@udec.cl)
