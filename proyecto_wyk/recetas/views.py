from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.http import JsonResponse
from django.db.models import Exists, OuterRef
import json

from .models import Receta, DetalleReceta
from inventario.models import Producto, MateriaPrima
from .forms import RecetaForm, DetalleRecetaFormSet


# ------------------------------ GESTIÓN DE RECETAS (CRUD) ------------------------------

@login_required
def lista_recetas(request):
    """ Lista las recetas maestras registradas en el sistema """
    if request.user.rol_fk_usuario.rol not in ['ADMIN', 'PASTELERO', 'PANADERO']:
        messages.error(request, "Acceso denegado. No tienes permisos para ver recetas.")
        return redirect('inicio')

    recetas = Receta.objects.all().select_related('id_producto_fk_receta', 'id_usuario_fk_receta').order_by(
        'nombre_receta')

    return render(request, 'recetas/lista.html', {'recetas': recetas})


@login_required
def crear_receta(request):
    """ Registra una nueva receta con su detalle de insumos (Maestro-Detalle) """
    if request.user.rol_fk_usuario.rol != 'ADMIN':
        messages.error(request, "Acceso denegado. Solo el administrador puede crear recetas.")
        return redirect('lista_recetas')

    # Anotación eficiente usando subconsultas de Django para detectar recetas previas
    productos = Producto.objects.filter(estado_producto=True).annotate(
        tiene_receta=Exists(
            Receta.objects.filter(id_producto_fk_receta=OuterRef('pk'))
        )
    )
    materias_primas = MateriaPrima.objects.filter(estado_materia_prima=True)

    if request.method == 'POST':
        form = RecetaForm(request.POST)
        formset = DetalleRecetaFormSet(request.POST, prefix='insumos_receta')

        if form.is_valid() and formset.is_valid():
            try:
                with transaction.atomic():
                    # 1. Guardar Cabecera (Maestro)
                    nueva_receta = form.save(commit=False)
                    nueva_receta.id_usuario_fk_receta = request.user
                    nueva_receta.estado_receta = True
                    nueva_receta.save()

                    # 2. Guardar Detalle (Insumos)
                    formset.instance = nueva_receta
                    formset.save()

                    messages.success(request, f"Receta '{nueva_receta.nombre_receta}' creada exitosamente.")
                    return redirect('lista_recetas')
            except Exception as e:
                messages.error(request, f"Error en base de datos: {str(e)}")
        else:
            # Captura de errores detallada (siguiendo tu estilo de producción)
            for error in form.non_field_errors(): messages.error(request, error)
            for field in form:
                for error in field.errors: messages.error(request, f"{field.label}: {error}")
            for dict_error in formset.errors:
                for field, error in dict_error.items(): messages.error(request, f"Detalle: {error}")
    else:
        form = RecetaForm()
        formset = DetalleRecetaFormSet(prefix='insumos_receta')

    return render(request, 'recetas/crear.html', {
        'form': form,
        'formset': formset,
        'productos': productos,
        'materias_primas': materias_primas
    })


@login_required
def editar_receta(request, id_receta):
    """ Edita una receta existente y sus insumos asociados """
    if request.user.rol_fk_usuario.rol != 'ADMIN':
        messages.error(request, "Acceso denegado.")
        return redirect('lista_recetas')

    receta = get_object_or_404(Receta, id_receta=id_receta)

    if request.method == 'POST':
        form = RecetaForm(request.POST, instance=receta)
        formset = DetalleRecetaFormSet(request.POST, instance=receta, prefix='insumos_receta')

        if form.is_valid() and formset.is_valid():
            try:
                with transaction.atomic():
                    form.save()
                    formset.save()
                    messages.success(request, f"Receta '{receta.nombre_receta}' actualizada correctamente.")
                    return redirect('lista_recetas')
            except Exception as e:
                messages.error(request, f"Error al actualizar: {str(e)}")
    else:
        form = RecetaForm(instance=receta)
        formset = DetalleRecetaFormSet(instance=receta, prefix='insumos_receta')

    return render(request, 'recetas/editar.html', {
        'form': form,
        'formset': formset,
        'receta': receta
    })


@login_required
def detalle_receta(request, id_receta):
    """ Detalle de una receta específica (Insumos vinculados) - Estilo Compras """
    if request.user.rol_fk_usuario.rol not in ['ADMIN', 'PASTELERO', 'PANADERO']:
        messages.error(request, "Acceso denegado. No tienes permisos para ver esta sección.")
        return redirect('inicio')

    receta = get_object_or_404(Receta, id_receta=id_receta)
    insumos = DetalleReceta.objects.filter(id_receta_fk_det_rec=receta).select_related('id_materia_prima_fk_det_rec')

    return render(request, 'recetas/detalle.html', {
        'receta': receta,
        'insumos': insumos
    })


# ------------------------------ SEGURIDAD AJAX (ESTILO COMPRAS) ------------------------------

@login_required
def cambiar_estado_receta_ajax(request):
    """ Alterna el estado (Activa/Inactiva) de una receta de forma lógica mediante contraseña """
    if request.method == 'POST' and request.headers.get('x-requested-with') == 'XMLHttpRequest':
        if request.user.rol_fk_usuario.rol != 'ADMIN':
            return JsonResponse({'success': False, 'message': 'Acceso denegado.'})

        try:
            data = json.loads(request.body)
            password = data.get('password')
            id_rec = data.get('id_receta')
            nuevo_estado = data.get('nuevo_estado')

            if not request.user.check_password(password):
                return JsonResponse({'success': False, 'message': 'Contraseña incorrecta.'})

            receta = get_object_or_404(Receta, id_receta=id_rec)
            receta.estado_receta = nuevo_estado
            receta.save()

            estado_str = "activada" if nuevo_estado else "inactivada"
            return JsonResponse({'success': True, 'message': f"La receta '{receta.nombre_receta}' fue {estado_str} correctamente."})
        except Exception as e:
            return JsonResponse({'success': False, 'message': f"Error: {str(e)}"})

    return JsonResponse({'success': False}, status=400)


# ------------------------------ UTILIDADES AJAX (PARA PRODUCCIÓN) ------------------------------

@login_required
def obtener_receta_por_producto_ajax(request, id_producto):
    """
    Endpoint para que Producción jale automáticamente los insumos
    cuando se selecciona un producto.
    """
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        try:
            # Buscamos la receta única del producto
            receta = Receta.objects.get(id_producto_fk_receta_id=id_producto, estado_receta=True)
            insumos = receta.insumos_receta.all()

            data = {
                'id_receta': receta.id_receta,
                'nombre_receta': receta.nombre_receta,
                'cantidad_base': receta.cantidad_base,
                'insumos': [
                    {
                        'id_materia_prima': item.id_materia_prima_fk_det_rec.id_materia_prima,
                        'nombre_materia_prima': item.id_materia_prima_fk_det_rec.nombre_materia_prima,
                        'cantidad_insumo_base': float(item.cantidad_insumo_base),
                    } for item in insumos
                ]
            }
            return JsonResponse({'success': True, 'receta': data})
        except Receta.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'El producto seleccionado no tiene una receta asignada.'})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})

    return JsonResponse({'success': False}, status=400)