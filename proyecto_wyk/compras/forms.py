from django import forms
from django.forms import inlineformset_factory, BaseInlineFormSet
from .models import Proveedor, Compra, DetalleCompraMateriaPrima, DetalleCompraProducto


# --------------------------------- VALIDACIÓN DE DUPLICADOS ---------------------------------
class BaseDetalleCompraFormSet(BaseInlineFormSet):
    def clean(self):
        """ Valida que no haya productos duplicados en el FormSet """
        super().clean()
        if any(self.errors):
            return

        items = []
        for form in self.forms:
            # Si el formulario está marcado para borrado, lo ignoramos
            if self.can_delete and form.cleaned_data.get('DELETE'):
                continue

            # Obtenemos el ID del producto o materia prima según el formset
            item = form.cleaned_data.get('id_mat_prima_fk_det_compra_mat_prima') or \
                   form.cleaned_data.get('id_prod_fk_det_compra_prod')

            if item:
                if item in items:
                    raise forms.ValidationError(
                        "No puedes agregar el mismo producto o insumo dos veces en la misma compra.")
                items.append(item)


# --------------------------------- FORMULARIO PROVEEDOR ---------------------------------
class ProveedorForm(forms.ModelForm):
    lugar_expedicion = forms.CharField(
        widget=forms.Select(attrs={
            'class': 'input-wyk',
            'id': 'id_lugar_expedicion',
            'required': True
        }),
        label="Lugar de Expedición"
    )

    class Meta:
        model = Proveedor
        fields = [
            'cedula_proveedor',
            'lugar_expedicion',
            'nombre_proveedor',
            'marca',
            'tel_proveedor',
            'email_proveedor'
        ]
        widgets = {
            'cedula_proveedor': forms.NumberInput(attrs={
                'placeholder': 'Ej: 10203040',
                'class': 'input-wyk',
                'required': True
            }),
            'nombre_proveedor': forms.TextInput(attrs={
                'placeholder': 'Nombre o Razón Social',
                'class': 'input-wyk input-uppercase',
                'required': True
            }),
            'marca': forms.TextInput(attrs={
                'placeholder': 'Nombre Comercial / Marca',
                'class': 'input-wyk input-uppercase',
                'required': True
            }),
            'tel_proveedor': forms.NumberInput(attrs={
                'placeholder': '3101234567',
                'class': 'input-wyk',
                'required': True
            }),
            'email_proveedor': forms.EmailInput(attrs={
                'placeholder': 'proveedor@ejemplo.com',
                'class': 'input-wyk',
                'required': True
            }),
        }

    def __init__(self, *args, **kwargs):
        super(ProveedorForm, self).__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields['lugar_expedicion'].initial = self.instance.lugar_expedicion

    def clean_cedula_proveedor(self):
        cedula = self.cleaned_data.get('cedula_proveedor')
        if Proveedor.objects.filter(cedula_proveedor=cedula).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError(f"La cédula/NIT '{cedula}' ya está registrado con otro proveedor.")
        return cedula

    def clean_nombre_proveedor(self):
        nombre = self.cleaned_data.get('nombre_proveedor').strip().upper()
        if Proveedor.objects.filter(nombre_proveedor=nombre).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError(f"El proveedor '{nombre}' ya existe en el sistema.")
        return nombre

    def clean_tel_proveedor(self):
        telefono = self.cleaned_data.get('tel_proveedor')
        if Proveedor.objects.filter(tel_proveedor=telefono).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError(f"El teléfono '{telefono}' ya pertenece a otro proveedor.")
        return telefono

    def clean_email_proveedor(self):
        email = self.cleaned_data.get('email_proveedor').strip().lower()
        if Proveedor.objects.filter(email_proveedor=email).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError(f"El correo '{email}' ya está registrado.")
        return email


# --------------------------------- FORMULARIO COMPRA ---------------------------------
class CompraForm(forms.ModelForm):
    class Meta:
        model = Compra
        fields = [
            'id_proveedor_fk_compra',
            'tipo',
            'estado_factura_compra',
            'descripcion_compra'
        ]
        widgets = {
            'id_proveedor_fk_compra': forms.Select(attrs={'class': 'input-wyk', 'required': True}),
            'tipo': forms.Select(attrs={'class': 'input-wyk', 'id': 'id_tipo_compra', 'required': True}),
            'estado_factura_compra': forms.Select(attrs={'class': 'input-wyk', 'id': 'id_estado_factura'}),
            'descripcion_compra': forms.Textarea(attrs={
                'class': 'input-wyk',
                'rows': 2,
                'placeholder': 'Opcional: Detalles adicionales de la factura...'
            }),
        }


# --------------------------------- FORMSETS DE DETALLE ---------------------------------

# Detalle para Materia Prima
DetalleMateriaPrimaFormSet = inlineformset_factory(
    Compra,
    DetalleCompraMateriaPrima,
    formset=BaseDetalleCompraFormSet,
    fields=[
        'id_mat_prima_fk_det_compra_mat_prima',
        'cantidad_mat_prima_comprada',
        'sub_total_mat_prima_comprada'
    ],
    widgets={
        'id_mat_prima_fk_det_compra_mat_prima': forms.Select(
            attrs={'class': 'input-wyk select-item', 'required': True}),
        'cantidad_mat_prima_comprada': forms.NumberInput(attrs={
            'class': 'input-wyk cantidad-input',
            'step': '0.001',
            'min': '0.001',
            'required': True
        }),
        'sub_total_mat_prima_comprada': forms.NumberInput(attrs={
            'class': 'input-wyk subtotal-input',
            'readonly': 'readonly',
            'required': True
        }),
    },
    extra=0,
    can_delete=True
)

# Detalle para Producto Terminado
DetalleProductoFormSet = inlineformset_factory(
    Compra,
    DetalleCompraProducto,
    formset=BaseDetalleCompraFormSet,
    fields=[
        'id_prod_fk_det_compra_prod',
        'cantidad_prod_comprado',
        'sub_total_prod_comprado'
    ],
    widgets={
        'id_prod_fk_det_compra_prod': forms.Select(attrs={'class': 'input-wyk select-item', 'required': True}),
        'cantidad_prod_comprado': forms.NumberInput(attrs={
            'class': 'input-wyk cantidad-input',
            'step': '1',
            'min': '1',
            'required': True
        }),
        'sub_total_prod_comprado': forms.NumberInput(attrs={
            'class': 'input-wyk subtotal-input',
            'readonly': 'readonly',
            'required': True
        }),
    },
    extra=0,
    can_delete=True
)