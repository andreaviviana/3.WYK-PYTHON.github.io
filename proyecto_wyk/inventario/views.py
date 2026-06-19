from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import ProtectedError
from django.http import JsonResponse
from django.db import transaction
import json
import csv
import io

from .models import Producto, MateriaPrima, AjusteInventario, AjusteInventarioMatPrima
from .forms import ProductoForm, MateriaPrimaForm, AjusteInventarioForm, AjusteMatPrimaForm
from django.utils import timezone


# ------------------------------ PRODUCTOS ------------------------------

@login_required
def lista_productos(request):
    """ Permite que ADMIN, PASTELERO y PANADERO vean la lista de productos """
    if request.user.rol_fk_usuario.rol not in ['ADMIN', 'PASTELERO', 'PANADERO']:
        messages.error(request, "Acceso denegado. No tienes permisos para ver el inventario.")
        return redirect('inicio')

    productos = Producto.objects.all().order_by('id_producto')
    return render(request, 'inventario/producto/lista.html', {'productos': productos})


@login_required
def crear_producto(request):
    if request.user.rol_fk_usuario.rol != 'ADMIN':
        messages.error(request, "Acceso denegado.")
        return redirect('lista_productos')

    form = ProductoForm(request.POST or None, request.FILES or None)
    if request.method == 'POST':
        if form.is_valid():
            nuevo_producto = form.save(commit=False)
            nuevo_producto.id_usuario_fk_producto = request.user
            nuevo_producto.save()
            messages.success(request, f"Producto '{nuevo_producto.nombre_producto}' creado correctamente.")
            return redirect('lista_productos')
        else:
            for field in form:
                for error in field.errors:
                    messages.error(request, f"{field.label}: {error}")

    return render(request, 'inventario/producto/crear.html', {'form': form})


@login_required
def carga_masiva_productos(request):
    if request.user.rol_fk_usuario.rol != 'ADMIN':
        messages.error(request, "Acceso denegado.")
        return redirect('lista_productos')

    if request.method == 'POST':
        csv_file = request.FILES.get('archivo_csv')

        if not csv_file or not csv_file.name.endswith('.csv'):
            messages.error(request, 'Por favor, sube un archivo con extensión .csv')
            return redirect('lista_productos')

        try:
            data_set = csv_file.read().decode('UTF-8')
            io_string = io.StringIO(data_set)
            next(io_string)  # Omitir encabezado

            cont_creados = 0
            for row in csv.reader(io_string, delimiter=',', quotechar='"'):
                Producto.objects.create(
                    id_producto=row[0],
                    nombre_producto=row[1].upper(),
                    valor_unitario_product=row[2],
                    cant_exist_producto=row[3],
                    fecha_vencimiento_product=row[4],
                    tipo_producto=row[5].upper(),
                    descripcion_producto=row[6] if len(row) > 6 else '',
                    id_usuario_fk_producto=request.user,
                    estado_producto=True
                )
                cont_creados += 1

            messages.success(request, f'¡Éxito! Se cargaron {cont_creados} productos correctamente.')
        except Exception as e:
            messages.error(request, f'Error al procesar el archivo: {e}')

    return redirect('lista_productos')


@login_required
def editar_producto(request, id_producto):
    if request.user.rol_fk_usuario.rol != 'ADMIN':
        messages.error(request, "Acceso denegado.")
        return redirect('lista_productos')

    producto = get_object_or_404(Producto, id_producto=id_producto)
    form = ProductoForm(request.POST or None, request.FILES or None, instance=producto)

    if request.method == 'POST':
        if form.is_valid():
            producto_editado = form.save()
            messages.success(request, f"Producto '{producto_editado.nombre_producto}' actualizado correctamente.")
            return redirect('lista_productos')
        else:
            for field in form:
                for error in field.errors:
                    messages.error(request, f"{field.label}: {error}")

    return render(request, 'inventario/producto/editar.html', {
        'form': form,
        'producto': producto
    })


@login_required
def eliminar_producto(request, id_producto):
    if request.user.rol_fk_usuario.rol != 'ADMIN':
        messages.error(request, "Acceso denegado.")
        return redirect('lista_productos')

    producto = get_object_or_404(Producto, id_producto=id_producto)

    if request.method == 'POST':
        password_confirm = request.POST.get('password_confirm')
        if not request.user.check_password(password_confirm):
            messages.error(request, "Acceso denegado. Contraseña incorrecta.")
            return redirect('lista_productos')

        try:
            nombre_eliminado = producto.nombre_producto
            producto.delete()
            messages.success(request, f"Producto '{nombre_eliminado}' eliminado definitivamente.")
        except ProtectedError:
            messages.error(request,
                           f"No se puede eliminar '{producto.nombre_producto}' porque tiene registros asociados.")

    return redirect('lista_productos')


@login_required
def cambiar_estado_producto_ajax(request):
    if request.method == 'POST' and request.headers.get('x-requested-with') == 'XMLHttpRequest':
        if request.user.rol_fk_usuario.rol != 'ADMIN':
            return JsonResponse({'success': False, 'message': 'Solo administradores.'})

        try:
            data = json.loads(request.body)
            id_prod = data.get('id_producto')
            nuevo_estado = data.get('nuevo_estado')
            password = data.get('password')

            if not request.user.check_password(password):
                return JsonResponse({'success': False, 'message': 'Contraseña incorrecta.'})

            producto = Producto.objects.get(id_producto=id_prod)
            producto.estado_producto = nuevo_estado
            producto.save()

            accion = "activado" if nuevo_estado else "inactivado"
            return JsonResponse({'success': True, 'message': f"Producto '{producto.nombre_producto}' {accion}."})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})

    return JsonResponse({'success': False, 'message': 'Acceso no autorizado.'}, status=400)


# ------------------------------ MATERIA PRIMA ------------------------------

@login_required
def lista_materia_prima(request):
    """ Permite que ADMIN, PASTELERO y PANADERO vean la lista de materia prima """
    if request.user.rol_fk_usuario.rol not in ['ADMIN', 'PASTELERO', 'PANADERO']:
        messages.error(request, "Acceso denegado.")
        return redirect('inicio')

    materias = MateriaPrima.objects.all().order_by('id_materia_prima')
    return render(request, 'inventario/materia_prima/lista.html', {'materias': materias})


@login_required
def crear_materia_prima(request):
    if request.user.rol_fk_usuario.rol != 'ADMIN':
        messages.error(request, "Acceso denegado.")
        return redirect('lista_materia_prima')

    form = MateriaPrimaForm(request.POST or None)
    if request.method == 'POST':
        if form.is_valid():
            nueva_mat = form.save(commit=False)
            nueva_mat.id_usuario_fk_mat_prima = request.user
            nueva_mat.save()
            messages.success(request, f"Materia prima '{nueva_mat.nombre_materia_prima}' registrada correctamente.")
            return redirect('lista_materia_prima')
        else:
            for field in form:
                for error in field.errors:
                    messages.error(request, f"{field.label}: {error}")

    return render(request, 'inventario/materia_prima/crear.html', {'form': form})


@login_required
def editar_materia_prima(request, id_materia_prima):
    if request.user.rol_fk_usuario.rol != 'ADMIN':
        messages.error(request, "Acceso denegado.")
        return redirect('lista_materia_prima')

    materia = get_object_or_404(MateriaPrima, id_materia_prima=id_materia_prima)
    form = MateriaPrimaForm(request.POST or None, instance=materia)
    if request.method == 'POST':
        if form.is_valid():
            form.save()
            messages.success(request, f"Materia prima '{materia.nombre_materia_prima}' actualizada.")
            return redirect('lista_materia_prima')
        else:
            for field in form:
                for error in field.errors:
                    messages.error(request, f"{field.label}: {error}")

    return render(request, 'inventario/materia_prima/editar.html', {'form': form, 'materia': materia})


@login_required
def eliminar_materia_prima(request, id_materia_prima):
    if request.user.rol_fk_usuario.rol != 'ADMIN':
        messages.error(request, "Acceso denegado.")
        return redirect('lista_materia_prima')

    materia = get_object_or_404(MateriaPrima, id_materia_prima=id_materia_prima)
    if request.method == 'POST':
        password_confirm = request.POST.get('password_confirm')
        if not request.user.check_password(password_confirm):
            messages.error(request, "Contraseña incorrecta.")
            return redirect('lista_materia_prima')

        try:
            materia.delete()
            messages.success(request, "Materia prima eliminada correctamente.")
        except ProtectedError:
            messages.error(request, "No se puede eliminar porque está siendo usada en producción o compras.")

    return redirect('lista_materia_prima')


@login_required
def cambiar_estado_materia_prima_ajax(request):
    if request.method == 'POST' and request.headers.get('x-requested-with') == 'XMLHttpRequest':
        if request.user.rol_fk_usuario.rol != 'ADMIN':
            return JsonResponse({'success': False, 'message': 'Acceso denegado.'})

        try:
            data = json.loads(request.body)
            materia = MateriaPrima.objects.get(id_materia_prima=data.get('id_materia_prima'))
            if not request.user.check_password(data.get('password')):
                return JsonResponse({'success': False, 'message': 'Contraseña incorrecta.'})

            materia.estado_materia_prima = data.get('nuevo_estado')
            materia.save()
            accion = "activada" if materia.estado_materia_prima else "inactivada"
            return JsonResponse({'success': True, 'message': f"Materia prima {accion}."})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})
    return JsonResponse({'success': False}, status=400)


@login_required
def carga_masiva_materia_prima(request):
    if request.user.rol_fk_usuario.rol != 'ADMIN':
        messages.error(request, "Acceso denegado.")
        return redirect('lista_materia_prima')

    if request.method == 'POST':
        csv_file = request.FILES.get('archivo_csv')

        if not csv_file or not csv_file.name.endswith('.csv'):
            messages.error(request, 'Por favor, sube un archivo con extensión .csv')
            return redirect('lista_materia_prima')

        try:
            data_set = csv_file.read().decode('UTF-8')
            io_string = io.StringIO(data_set)
            next(io_string)  # Omitir encabezado

            cont_creados = 0
            for row in csv.reader(io_string, delimiter=',', quotechar='"'):
                MateriaPrima.objects.create(
                    nombre_materia_prima=row[0],
                    fecha_vencimiento_mat_prima=row[1],
                    cantidad_exist_mat_prima=row[2],
                    presentacion_mat_prima=row[3],
                    descripcion_mat_prima=row[4] if len(row) > 4 else '',
                    id_usuario_fk_mat_prima=request.user,
                    estado_materia_prima=True
                )
                cont_creados += 1

            messages.success(request, f'¡Éxito! Se cargaron {cont_creados} insumos correctamente.')
        except Exception as e:
            messages.error(request, f'Error al procesar el archivo: {e}')

    return redirect('lista_materia_prima')


# ------------------------------ AJUSTE PRODUCTO ------------------------------

@login_required
def lista_ajustes_producto(request):
    if request.user.rol_fk_usuario.rol != 'ADMIN':
        messages.error(request, "Acceso denegado.")
        return redirect('inicio')

    ajustes = AjusteInventario.objects.all().select_related(
        'id_prod_fk_ajuste',
        'id_usuario_fk_ajuste'
    ).order_by('id_ajuste')
    return render(request, 'inventario/ajuste_producto/lista.html', {'ajustes': ajustes})


@login_required
def crear_ajuste_producto(request):
    if request.user.rol_fk_usuario.rol != 'ADMIN':
        messages.error(request, "Acceso denegado.")
        return redirect('lista_ajustes_producto')

    if request.method == 'POST':
        id_prod = request.POST.get('producto')
        producto = get_object_or_404(Producto, id_producto=id_prod)

        form = AjusteInventarioForm(request.POST, producto=producto)

        if form.is_valid():
            try:
                with transaction.atomic():
                    nuevo_ajuste = form.save(commit=False)
                    nuevo_ajuste.id_prod_fk_ajuste = producto
                    nuevo_ajuste.id_usuario_fk_ajuste = request.user
                    nuevo_ajuste.fecha_ajuste = timezone.now()
                    nuevo_ajuste.save()

                    producto.cant_exist_producto -= nuevo_ajuste.cantidad_ajustada
                    producto.save()

                    messages.success(request, f"Ajuste registrado correctamente.")
                    return redirect('lista_ajustes_producto')
            except Exception as e:
                messages.error(request, f"Error en la base de datos: {e}")
        else:
            for error in form.errors.values():
                messages.error(error)
            return redirect('lista_ajustes_producto')

    productos = Producto.objects.filter(estado_producto=True)
    return render(request, 'inventario/ajuste_producto/crear.html', {'productos': productos})

@login_required
def eliminar_ajuste_producto(request, id_ajuste):
    if request.user.rol_fk_usuario.rol != 'ADMIN':
        messages.error(request, "Acceso denegado.")
        return redirect('lista_ajustes_producto')

    ajuste = get_object_or_404(AjusteInventario, id_ajuste=id_ajuste)

    if request.method == 'POST':
        password_confirm = request.POST.get('password_confirm')
        if not request.user.check_password(password_confirm):
            messages.error(request, "Acceso denegado. Contraseña incorrecta.")
            return redirect('lista_ajustes_producto')

        try:
            with transaction.atomic():
                producto = ajuste.id_prod_fk_ajuste
                producto.cant_exist_producto += ajuste.cantidad_ajustada
                producto.save()

                ajuste.delete()
                messages.success(request, f"Ajuste #{id_ajuste} eliminado e inventario restablecido.")
        except Exception as e:
            messages.error(request, f"Error al eliminar: {e}")

    return redirect('lista_ajustes_producto')


# ------------------------------ AJUSTE MATERIA PRIMA ------------------------------

@login_required
def lista_ajustes_mat_prima(request):
    if request.user.rol_fk_usuario.rol != 'ADMIN':
        messages.error(request, "Acceso denegado.")
        return redirect('inicio')

    ajustes = AjusteInventarioMatPrima.objects.all().select_related(
        'id_mat_fk_ajuste_mat',
        'id_usuario_fk_ajuste_mat'
    ).order_by('id_ajust_mat')
    return render(request, 'inventario/ajuste_mat/lista.html', {'ajustes': ajustes})


@login_required
def crear_ajuste_mat_prima(request):
    if request.user.rol_fk_usuario.rol != 'ADMIN':
        messages.error(request, "Acceso denegado.")
        return redirect('lista_ajustes_mat_prima')

    if request.method == 'POST':
        id_mat = request.POST.get('materia_prima')
        materia = get_object_or_404(MateriaPrima, id_materia_prima=id_mat)

        form = AjusteMatPrimaForm(request.POST, materia=materia)

        if form.is_valid():
            try:
                with transaction.atomic():
                    nuevo_ajuste = form.save(commit=False)
                    nuevo_ajuste.id_mat_fk_ajuste_mat = materia
                    nuevo_ajuste.id_usuario_fk_ajuste_mat = request.user
                    nuevo_ajuste.fecha_ajust_mat = timezone.now()
                    nuevo_ajuste.save()

                    materia.cantidad_exist_mat_prima -= nuevo_ajuste.cantidad_ajustada_mat
                    materia.save()

                    messages.success(request, f"Ajuste de materia prima registrado correctamente.")
                    return redirect('lista_ajustes_mat_prima')
            except Exception as e:
                messages.error(request, f"Error en la base de datos: {e}")
        else:
            for error in form.errors.values():
                messages.error(error)
            return redirect('lista_ajustes_mat_prima')

    materias = MateriaPrima.objects.filter(estado_materia_prima=True)
    return render(request, 'inventario/ajuste_mat/crear.html', {'materias': materias})


@login_required
def editar_ajuste_mat_prima(request, id_ajust_mat):
    if request.user.rol_fk_usuario.rol != 'ADMIN':
        messages.error(request, "Acceso denegado.")
        return redirect('lista_ajustes_mat_prima')

    ajuste = get_object_or_404(AjusteInventarioMatPrima, id_ajust_mat=id_ajust_mat)
    materia = ajuste.id_mat_fk_ajuste_mat

    form = AjusteMatPrimaForm(request.POST or None, instance=ajuste, materia=materia)

    if request.method == 'POST':
        if form.is_valid():
            try:
                with transaction.atomic():
                    ajuste_editado = form.save(commit=False)
                    valor_anterior = AjusteInventarioMatPrima.objects.get(pk=id_ajust_mat).cantidad_ajustada_mat
                    materia.cantidad_exist_mat_prima += valor_anterior
                    materia.cantidad_exist_mat_prima -= ajuste_editado.cantidad_ajustada_mat
                    materia.save()

                    ajuste_editado.save()
                    messages.success(request, "Ajuste de materia actualizado y stock recalculado.")
                    return redirect('lista_ajustes_mat_prima')
            except Exception as e:
                messages.error(request, f"Error al editar: {e}")
        else:
            for error in form.errors.values():
                messages.error(error)

    return render(request, 'inventario/ajuste_mat/editar.html', {'ajuste': ajuste, 'form': form})


@login_required
def eliminar_ajuste_mat_prima(request, id_ajust_mat):
    if request.user.rol_fk_usuario.rol != 'ADMIN':
        messages.error(request, "Acceso denegado.")
        return redirect('lista_ajustes_mat_prima')

    ajuste = get_object_or_404(AjusteInventarioMatPrima, id_ajust_mat=id_ajust_mat)

    if request.method == 'POST':
        password_confirm = request.POST.get('password_confirm')
        if not request.user.check_password(password_confirm):
            messages.error(request, "Acceso denegado. Contraseña incorrecta.")
            return redirect('lista_ajustes_mat_prima')

        try:
            with transaction.atomic():
                materia = ajuste.id_mat_fk_ajuste_mat
                materia.cantidad_exist_mat_prima += ajuste.cantidad_ajustada_mat
                materia.save()

                ajuste.delete()
                messages.success(request, f"Ajuste de insumo #{id_ajust_mat} eliminado.")
        except Exception as e:
            messages.error(request, f"Error al eliminar: {e}")

    return redirect('lista_ajustes_mat_prima')