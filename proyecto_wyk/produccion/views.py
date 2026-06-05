from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.utils import timezone
from django.http import JsonResponse
import json

from .models import Produccion, DetalleProduccion
from inventario.models import MateriaPrima, Producto
from .forms import ProduccionForm, InsumosProduccionFormSet
from recetas.models import Receta


# ------------------------------ GESTIÓN DE PRODUCCIÓN (CRUD) ------------------------------

@login_required
def lista_produccion(request):
    """ Lista las órdenes de producción filtradas según el rol del usuario """
    rol_usuario = request.user.rol_fk_usuario.rol

    if rol_usuario not in ['ADMIN', 'PASTELERO', 'PANADERO']:
        messages.error(request, "Acceso denegado. No tienes permisos para ver producción.")
        return redirect('inicio')

    # Base de la consulta
    queryset = Produccion.objects.all().order_by('-fecha_hora_produccion')

    # Aplicar filtros según el rol
    if rol_usuario == 'PANADERO':
        # Filtra solo categoría Panadería
        producciones = queryset.filter(categoria_produccion='PANADERIA')
    elif rol_usuario == 'PASTELERO':
        # Filtra solo categoría Pastelería
        producciones = queryset.filter(categoria_produccion='PASTELERIA')
    else:
        # El ADMIN ve todos los registros
        producciones = queryset

    return render(request, 'produccion/lista.html', {'producciones': producciones})


@login_required
def crear_produccion(request):
    """ Registra una nueva orden de producción con sus insumos y categoría fija según rol """
    rol_usuario = request.user.rol_fk_usuario.rol

    if rol_usuario not in ['ADMIN', 'PASTELERO', 'PANADERO']:
        messages.error(request, "Acceso denegado. No tienes permisos para registrar producción.")
        return redirect('lista_produccion')

    productos = Producto.objects.filter(estado_producto=True)
    materias_primas = MateriaPrima.objects.filter(estado_materia_prima=True)

    if request.method == 'POST':
        form = ProduccionForm(request.POST)
        formset = InsumosProduccionFormSet(request.POST, prefix='insumos_set')

        if form.is_valid() and formset.is_valid():
            try:
                with transaction.atomic():
                    # 1. Guardar Cabecera
                    nueva_produccion = form.save(commit=False)
                    nueva_produccion.id_usuario_fk_produccion = request.user
                    nueva_produccion.fecha_hora_produccion = timezone.now()
                    nueva_produccion.estado_produccion = 'PENDIENTE'

                    # ASIGNACIÓN FIJA DE CATEGORÍA SEGÚN ROL
                    if rol_usuario == 'PANADERO':
                        nueva_produccion.categoria_produccion = 'PANADERIA'
                    elif rol_usuario == 'PASTELERO':
                        nueva_produccion.categoria_produccion = 'PASTELERIA'
                    # Si es ADMIN, toma el valor seleccionado en el formulario

                    nueva_produccion.save()

                    # 2. Guardar Detalle
                    formset.instance = nueva_produccion
                    formset.save()

                    messages.success(request,
                                     f"Producción '{nueva_produccion.nombre_produccion}' registrada exitosamente.")
                    return redirect('lista_produccion')
            except Exception as e:
                messages.error(request, f"Error en base de datos: {str(e)}")
        else:
            # Captura de errores detallada para depuración
            for error in form.non_field_errors(): messages.error(request, error)
            for field in form:
                for error in field.errors: messages.error(request, f"{field.label}: {error}")
            for dict_error in formset.errors:
                for field, error in dict_error.items(): messages.error(request, f"Insumo: {error}")
    else:
        form = ProduccionForm()

        # Establecer valor inicial en el formulario según el rol (útil para el frontend)
        if rol_usuario == 'PANADERO':
            form.fields['categoria_produccion'].initial = 'PANADERIA'
        elif rol_usuario == 'PASTELERO':
            form.fields['categoria_produccion'].initial = 'PASTELERIA'

        formset = InsumosProduccionFormSet(prefix='insumos_set')

    return render(request, 'produccion/crear.html', {
        'form': form,
        'formset': formset,
        'productos': productos,
        'materias_primas': materias_primas,
        'rol_usuario': rol_usuario
    })


@login_required
def detalle_produccion(request, id_produccion):
    """ Muestra la información completa de una producción y sus insumos consumidos """
    rol_usuario = request.user.rol_fk_usuario.rol

    if rol_usuario not in ['ADMIN', 'PASTELERO', 'PANADERO']:
        messages.error(request, "Acceso denegado.")
        return redirect('lista_produccion')

    produccion = get_object_or_404(Produccion, id_produccion=id_produccion)

    # Seguridad adicional: Validar que el usuario no acceda por ID a una categoría ajena
    if rol_usuario == 'PANADERO' and produccion.categoria_produccion != 'PANADERIA':
        messages.error(request, "No tienes permiso para ver registros de otras categorías.")
        return redirect('lista_produccion')

    if rol_usuario == 'PASTELERO' and produccion.categoria_produccion != 'PASTELERIA':
        messages.error(request, "No tienes permiso para ver registros de otras categorías.")
        return redirect('lista_produccion')

    insumos = produccion.insumos.all()

    return render(request, 'produccion/detalle.html', {
        'produccion': produccion,
        'insumos': insumos
    })


# ------------------------------ ACCIONES AJAX (ESTADOS Y STOCK) ------------------------------

@login_required
def obtener_receta_por_producto(request):
    """ Busca la receta activa vinculada a un producto para cargar los insumos automáticamente """
    id_producto = request.GET.get('id_producto')
    receta = Receta.objects.filter(id_producto_fk_receta=id_producto, estado_receta=True).first()

    if not receta:
        return JsonResponse({'success': False, 'message': 'No se encontró una receta activa para este producto.'})

    # Usamos el related_name 'insumos_receta' definido en el modelo DetalleReceta
    detalles = receta.insumos_receta.all()
    insumos = [
        {
            'id_materia': d.id_materia_prima_fk_det_rec.id_materia_prima,
            'nombre': d.id_materia_prima_fk_det_rec.nombre_materia_prima,
            'cantidad': float(d.cantidad_insumo_base),
            'stock': float(d.id_materia_prima_fk_det_rec.cantidad_exist_mat_prima)
        }
        for d in detalles
    ]

    return JsonResponse({
        'success': True,
        'id_receta': receta.id_receta,
        'cantidad_base_receta': float(receta.cantidad_base),
        'insumos': insumos
    })


@login_required
def finalizar_produccion_ajax(request):
    """ Procesa la finalización: Suma stock al Producto y resta a Materia Prima """
    if request.method == 'POST' and request.headers.get('x-requested-with') == 'XMLHttpRequest':
        try:
            data = json.loads(request.body)
            password = data.get('password')
            id_prod = data.get('id_produccion')

            if not request.user.check_password(password):
                return JsonResponse({'success': False, 'message': 'Contraseña incorrecta.'})

            with transaction.atomic():
                produccion = get_object_or_404(Produccion, id_produccion=id_prod)

                if produccion.estado_produccion != 'PENDIENTE':
                    return JsonResponse({'success': False, 'message': 'Esta orden ya fue procesada o cancelada.'})

                # 1. Validar y Restar stock de Materia Prima
                detalles = produccion.insumos.all()
                for item in detalles:
                    insumo = item.id_materia_prima_fk_det_produc
                    if insumo.cantidad_exist_mat_prima < item.cantidad_requerida:
                        return JsonResponse({
                            'success': False,
                            'message': f"Insumo insuficiente: {insumo.nombre_materia_prima}. Disponible: {insumo.cantidad_exist_mat_prima} {insumo.presentacion_mat_prima}"
                        })

                    insumo.cantidad_exist_mat_prima -= item.cantidad_requerida
                    insumo.save()

                # 2. Sumar stock al Producto Terminado
                producto_final = produccion.id_producto_fk_produccion
                producto_final.cant_exist_producto += produccion.cant_produccion
                producto_final.save()

                # 3. Actualizar estado
                produccion.estado_produccion = 'FINALIZADA'
                produccion.fecha_cambio_estado = timezone.now()
                produccion.save()

            return JsonResponse({'success': True, 'message': '¡Producción finalizada! Inventarios actualizados.'})

        except Exception as e:
            return JsonResponse({'success': False, 'message': f"Error técnico: {str(e)}"})

    return JsonResponse({'success': False, 'message': 'Petición no válida.'}, status=400)


@login_required
def cancelar_produccion_ajax(request):
    """ Cancela la producción y revierte el stock si ya estaba finalizada """
    if request.method == 'POST' and request.headers.get('x-requested-with') == 'XMLHttpRequest':
        try:
            data = json.loads(request.body)
            if not request.user.check_password(data.get('password')):
                return JsonResponse({'success': False, 'message': 'Contraseña incorrecta.'})

            produccion = get_object_or_404(Produccion, id_produccion=data.get('id_produccion'))

            if produccion.estado_produccion == 'CANCELADA':
                return JsonResponse({'success': False, 'message': 'Esta orden ya está cancelada.'})

            with transaction.atomic():
                # SI ESTABA FINALIZADA, REVERTIMOS EL STOCK
                if produccion.estado_produccion == 'FINALIZADA':
                    # 1. Restar stock del Producto Terminado
                    producto_final = produccion.id_producto_fk_produccion
                    if producto_final.cant_exist_producto < produccion.cant_produccion:
                        return JsonResponse({
                            'success': False,
                            'message': f"No se puede revertir: El stock de {producto_final.nombre_producto} es menor a lo producido (posible venta ya realizada)."
                        })

                    producto_final.cant_exist_producto -= produccion.cant_produccion
                    producto_final.save()

                    # 2. Devolver stock a Materias Primas
                    detalles = produccion.insumos.all()
                    for item in detalles:
                        insumo = item.id_materia_prima_fk_det_produc
                        insumo.cantidad_exist_mat_prima += item.cantidad_requerida
                        insumo.save()

                # 3. Actualizar estado a CANCELADA
                produccion.estado_produccion = 'CANCELADA'
                produccion.fecha_cambio_estado = timezone.now()
                produccion.save()

            return JsonResponse({'success': True, 'message': 'Orden cancelada y stock revertido correctamente.'})
        except Exception as e:
            return JsonResponse({'success': False, 'message': f"Error al cancelar: {str(e)}"})

    return JsonResponse({'success': False}, status=400)