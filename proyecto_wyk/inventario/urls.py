from django.urls import path
from . import views

urlpatterns = [
    # --- RUTAS DE PRODUCTOS ---
    path('productos/', views.lista_productos, name='lista_productos'),
    path('productos/crear/', views.crear_producto, name='crear_producto'),
    path('productos/editar/<int:id_producto>/', views.editar_producto, name='editar_producto'),
    path('productos/eliminar/<int:id_producto>/', views.eliminar_producto, name='eliminar_producto'),
    path('productos/cambiar-estado-ajax/', views.cambiar_estado_producto_ajax, name='cambiar_estado_producto_ajax'),
    path('productos/carga-masiva/', views.carga_masiva_productos, name='carga_masiva_productos'),

    # --- RUTAS DE MATERIA PRIMA ---
    path('materia-prima/', views.lista_materia_prima, name='lista_materia_prima'),
    path('materia-prima/crear/', views.crear_materia_prima, name='crear_materia_prima'),
    path('materia-prima/editar/<int:id_materia_prima>/', views.editar_materia_prima, name='editar_materia_prima'),
    path('materia-prima/eliminar/<int:id_materia_prima>/', views.eliminar_materia_prima, name='eliminar_materia_prima'),
    path('materia-prima/cambiar-estado-ajax/', views.cambiar_estado_materia_prima_ajax, name='cambiar_estado_materia_prima_ajax'),
    path('materia-prima/carga-masiva/', views.carga_masiva_materia_prima, name='carga_masiva_materia_prima'),

    # --- RUTAS DE AJUSTES DE INVENTARIO (PRODUCTOS) ---
    path('ajustes/productos/', views.lista_ajustes_producto, name='lista_ajustes_producto'),
    path('ajustes/productos/crear/', views.crear_ajuste_producto, name='crear_ajuste_producto'),
    path('ajustes/productos/eliminar/<int:id_ajuste>/', views.eliminar_ajuste_producto, name='eliminar_ajuste_producto'),

    # proyecto_wyk/inventario/urls.py

    # --- RUTAS DE AJUSTES DE INVENTARIO (MATERIA PRIMA) ---
    path('ajustes/materia-prima/', views.lista_ajustes_mat_prima, name='lista_ajustes_mat_prima'),
    path('ajustes/materia-prima/crear/', views.crear_ajuste_mat_prima, name='crear_ajuste_mat_prima'),
    path('ajustes/materia-prima/editar/<int:id_ajust_mat>/', views.editar_ajuste_mat_prima,name='editar_ajuste_mat_prima'),
    path('ajustes/materia-prima/eliminar/<int:id_ajust_mat>/', views.eliminar_ajuste_mat_prima,name='eliminar_ajuste_mat_prima'),
]