from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.db.models import ProtectedError
from django.http import JsonResponse
from django.utils import timezone
import json
from .models import Proveedor, Compra, DetalleCompraMateriaPrima, DetalleCompraProducto
from inventario.models import MateriaPrima, Producto
from .forms import ProveedorForm, CompraForm, DetalleMateriaPrimaFormSet, DetalleProductoFormSet


# ------------------------------ GESTIÓN DE PROVEEDORES (CRUD) ------------------------------

@login_required
def lista_proveedores(request):
    """ Lista todos los proveedores ordenados por nombre - Solo ADMIN """
    if request.user.rol_fk_usuario.rol != 'ADMIN':
        messages.error(request, "Acceso denegado. No tienes permisos para gestionar proveedores.")
        return redirect('inicio')

    proveedores = Proveedor.objects.all().order_by('nombre_proveedor')
    return render(request, 'compras/proveedores/lista.html', {'proveedores': proveedores})


@login_required
def crear_proveedor(request):
    """ Crea un nuevo proveedor vinculándolo al usuario actual - Solo ADMIN """
    if request.user.rol_fk_usuario.rol != 'ADMIN':
        messages.error(request, "Acceso denegado. Solo administradores pueden crear proveedores.")
        return redirect('lista_proveedores')

    if request.method == 'POST':
        form = ProveedorForm(request.POST)
        if form.is_valid():
            nuevo_proveedor = form.save(commit=False)
            nuevo_proveedor.id_usuario_fk_proveedor = request.user
            nuevo_proveedor.estado_proveedor = True
            nuevo_proveedor.save()
            messages.success(request, f"Proveedor '{nuevo_proveedor.nombre_proveedor}' creado correctamente.")
            return redirect('lista_proveedores')
    else:
        form = ProveedorForm()

    return render(request, 'compras/proveedores/crear.html', {'form': form})


@login_required
def editar_proveedor(request, cedula_proveedor):
    """ Edita la información de un proveedor existente - Solo ADMIN """
    if request.user.rol_fk_usuario.rol != 'ADMIN':
        messages.error(request, "Acceso denegado.")
        return redirect('lista_proveedores')

    proveedor = get_object_or_404(Proveedor, cedula_proveedor=cedula_proveedor)

    if request.method == 'POST':
        form = ProveedorForm(request.POST, instance=proveedor)
        if form.is_valid():
            form.save()
            messages.success(request, f"Proveedor '{proveedor.nombre_proveedor}' actualizado.")
            return redirect('lista_proveedores')
    else:
        form = ProveedorForm(instance=proveedor)

    return render(request, 'compras/proveedores/editar.html', {'proveedor': proveedor, 'form': form})


@login_required
def eliminar_proveedor(request, cedula_proveedor):
    """ Elimina un proveedor si no tiene compras asociadas - Solo ADMIN """
    if request.user.rol_fk_usuario.rol != 'ADMIN':
        messages.error(request, "Acceso denegado para eliminar proveedores.")
        return redirect('lista_proveedores')

    proveedor = get_object_or_404(Proveedor, cedula_proveedor=cedula_proveedor)

    if request.method == 'POST':
        password_confirm = request.POST.get('password_confirm')
        if not request.user.check_password(password_confirm):
            messages.error(request, "Contraseña incorrecta. Acción cancelada.")
            return redirect('lista_proveedores')

        try:
            proveedor.delete()
            messages.success(request, "Proveedor eliminado definitivamente.")
        except ProtectedError:
            messages.error(request, "No se puede eliminar: tiene facturas asociadas.")

    return redirect('lista_proveedores')


# ------------------------------ SEGURIDAD AJAX ------------------------------

@login_required
def cambiar_estado_proveedor_ajax(request):
    if request.method == 'POST' and request.headers.get('x-requested-with') == 'XMLHttpRequest':
        if request.user.rol_fk_usuario.rol != 'ADMIN':
            return JsonResponse({'success': False, 'message': 'Acceso denegado.'})

        data = json.loads(request.body)
        if not request.user.check_password(data.get('password')):
            return JsonResponse({'success': False, 'message': 'Contraseña incorrecta.'})

        proveedor = get_object_or_404(Proveedor, cedula_proveedor=data.get('cedula_proveedor'))
        proveedor.estado_proveedor = data.get('nuevo_estado')
        proveedor.save()

        return JsonResponse({'success': True, 'message': 'Estado actualizado.'})

    return JsonResponse({'success': False}, status=400)


# ------------------------------ GESTIÓN DE COMPRAS (CRUD - SOLO ADMIN) ------------------------------

@login_required
def lista_compras(request):
    """ Lista historial de compras - Solo ADMIN """
    if request.user.rol_fk_usuario.rol != 'ADMIN':
        messages.error(request, "Acceso denegado. No tienes permisos para ver las compras.")
        return redirect('inicio')

    compras = Compra.objects.all().order_by('id_compra')
    return render(request, 'compras/compra/lista.html', {'compras': compras})


@login_required
def crear_compra(request):
    """ Registra una nueva compra - Solo ADMIN """
    if request.user.rol_fk_usuario.rol != 'ADMIN':
        messages.error(request, "Acceso denegado. No tienes permisos para registrar compras.")
        return redirect('inicio')

    proveedores = Proveedor.objects.filter(estado_proveedor=True)
    materias_primas = MateriaPrima.objects.filter(estado_materia_prima=True)

    # CORRECCIÓN AQUÍ: Se cambió 'categoria_producto' por 'tipo_producto'
    productos = Producto.objects.filter(
        estado_producto=True,
        tipo_producto__in=['REVENTA', 'ASEO']
    )

    form = CompraForm(request.POST or None)
    formset_mat = DetalleMateriaPrimaFormSet(request.POST or None, prefix='detallecompramateriaprima_set')
    formset_prod = DetalleProductoFormSet(request.POST or None, prefix='detallecompraproducto_set')

    if request.method == 'POST':
        tipo_compra = request.POST.get('tipo')

        if form.is_valid():
            try:
                with transaction.atomic():
                    nueva_compra = form.save(commit=False)
                    nueva_compra.id_usuario_fk_compra = request.user
                    nueva_compra.fecha_hora_compra = timezone.now()
                    nueva_compra.total_compra = 0
                    nueva_compra.save()

                    total_calculado = 0

                    if tipo_compra == 'MATERIA PRIMA':
                        formset_mat.instance = nueva_compra
                        if formset_mat.is_valid():
                            for d in formset_mat.save(commit=False):
                                d.estado_det_compra_mat_prima = True
                                d.save()
                                total_calculado += d.sub_total_mat_prima_comprada
                        else:
                            raise ValueError("Los detalles de la materia prima están incompletos o son inválidos.")

                    elif tipo_compra == 'PRODUCTO TERMINADO':
                        formset_prod.instance = nueva_compra
                        if formset_prod.is_valid():
                            for d in formset_prod.save(commit=False):
                                # CORRECCIÓN AQUÍ: Se cambió 'categoria_producto' por 'tipo_producto'
                                prod = d.id_prod_fk_det_compra_prod
                                if prod.tipo_producto not in ['REVENTA', 'ASEO']:
                                    raise ValueError(f"El producto '{prod.nombre_producto}' no es permitido para compra.")

                                d.estado_det_compra_prod = True
                                d.save()
                                total_calculado += d.sub_total_prod_comprado
                        else:
                            raise ValueError("Los detalles de los productos están incompletos o son inválidos.")

                    nueva_compra.total_compra = total_calculado
                    nueva_compra.save()

                    messages.success(request, f"Compra #{nueva_compra.id_compra} registrada correctamente.")
                    return redirect('lista_compras')

            except Exception as e:
                messages.error(request, f"Error: {str(e)}")
        else:
            messages.error(request, "Campos incompletos: Asegúrate de seleccionar un proveedor y el tipo de compra.")

    return render(request, 'compras/compra/crear.html', {
        'form': form,
        'formset_mat': formset_mat,
        'formset_prod': formset_prod,
        'proveedores': proveedores,
        'materias_primas': materias_primas,
        'productos': productos
    })


@login_required
def detalle_compra(request, id_compra):
    """ Detalle de una compra específica - Solo ADMIN """
    if request.user.rol_fk_usuario.rol != 'ADMIN':
        messages.error(request, "Acceso denegado.")
        return redirect('inicio')

    compra = get_object_or_404(Compra, id_compra=id_compra)
    detalles_mat = DetalleCompraMateriaPrima.objects.filter(
        id_compra_fk_det_compra_mat_prima=compra) if compra.tipo == 'MATERIA PRIMA' else None
    detalles_prod = DetalleCompraProducto.objects.filter(
        id_compra_fk_det_compra_prod=compra) if compra.tipo == 'PRODUCTO TERMINADO' else None

    return render(request, 'compras/compra/detalle.html', {
        'compra': compra,
        'detalles_mat': detalles_mat,
        'detalles_prod': detalles_prod
    })


@login_required
def pagar_compra_ajax(request):
    if request.method == 'POST' and request.headers.get('x-requested-with') == 'XMLHttpRequest':
        if request.user.rol_fk_usuario.rol != 'ADMIN':
            return JsonResponse({'success': False, 'message': 'Solo administradores.'})

        data = json.loads(request.body)
        if not request.user.check_password(data.get('password')):
            return JsonResponse({'success': False, 'message': 'Contraseña incorrecta.'})

        try:
            with transaction.atomic():
                compra = get_object_or_404(Compra, id_compra=data.get('id_compra'))
                if compra.estado_factura_compra != 'PENDIENTE':
                    return JsonResponse({'success': False, 'message': 'Estado inválido.'})

                if compra.tipo == 'MATERIA PRIMA':
                    for d in DetalleCompraMateriaPrima.objects.filter(id_compra_fk_det_compra_mat_prima=compra):
                        insumo = d.id_mat_prima_fk_det_compra_mat_prima
                        insumo.cantidad_exist_mat_prima += d.cantidad_mat_prima_comprada
                        insumo.save()
                else:
                    for d in DetalleCompraProducto.objects.filter(id_compra_fk_det_compra_prod=compra):
                        prod = d.id_prod_fk_det_compra_prod
                        prod.cant_exist_producto += d.cantidad_prod_comprado
                        prod.save()

                compra.estado_factura_compra = 'PAGADA'
                compra.fecha_cambio_estado = timezone.now()
                compra.save()

            return JsonResponse({'success': True, 'message': 'Pago confirmado y stock actualizado.'})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})

    return JsonResponse({'success': False}, status=400)


@login_required
def cancelar_compra_ajax(request):
    if request.method == 'POST' and request.headers.get('x-requested-with') == 'XMLHttpRequest':
        if request.user.rol_fk_usuario.rol != 'ADMIN':
            return JsonResponse({'success': False, 'message': 'Solo administradores.'})

        data = json.loads(request.body)
        if not request.user.check_password(data.get('password')):
            return JsonResponse({'success': False, 'message': 'Contraseña incorrecta.'})

        try:
            with transaction.atomic():
                compra = get_object_or_404(Compra, id_compra=data.get('id_compra'))

                if compra.estado_factura_compra == 'PAGADA':
                    if compra.tipo == 'MATERIA PRIMA':
                        for d in DetalleCompraMateriaPrima.objects.filter(id_compra_fk_det_compra_mat_prima=compra):
                            insumo = d.id_mat_prima_fk_det_compra_mat_prima
                            insumo.cantidad_exist_mat_prima -= d.cantidad_mat_prima_comprada
                            insumo.save()
                    else:
                        for d in DetalleCompraProducto.objects.filter(id_compra_fk_det_compra_prod=compra):
                            prod = d.id_prod_fk_det_compra_prod
                            prod.cant_exist_producto -= d.cantidad_prod_comprado
                            prod.save()

                compra.estado_factura_compra = 'CANCELADA'
                compra.fecha_cambio_estado = timezone.now()
                compra.save()

            return JsonResponse({'success': True, 'message': 'Compra anulada y stock revertido.'})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})

    return JsonResponse({'success': False}, status=400)