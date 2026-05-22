from django.urls import path
from . import views

urlpatterns = [
    # --- RUTAS DE RECETAS (GESTIÓN CRUD) ---
    # dominio.com/recetas/lista/
    path('lista/', views.lista_recetas, name='lista_recetas'),

    # dominio.com/recetas/crear/
    path('crear/', views.crear_receta, name='crear_receta'),

    # dominio.com/recetas/editar/1/
    path('editar/<int:id_receta>/', views.editar_receta, name='editar_receta'),

    # dominio.com/recetas/detalle/1/
    path('detalle/<int:id_receta>/', views.detalle_receta, name='detalle_receta'),

    # --- ACCIONES AJAX Y CONSULTAS ---
    # Ruta para cambiar el estado de la receta con validación de contraseña
    path('cambiar-estado-ajax/', views.cambiar_estado_receta_ajax, name='cambiar_estado_receta_ajax'),

    # Ruta crítica: Obtiene los insumos de una receta según el producto (Uso en Producción)
    # dominio.com/recetas/api/obtener-por-producto/1/
    path('api/obtener-por-producto/<int:id_producto>/',
         views.obtener_receta_por_producto_ajax,
         name='obtener_receta_por_producto_ajax'),
]