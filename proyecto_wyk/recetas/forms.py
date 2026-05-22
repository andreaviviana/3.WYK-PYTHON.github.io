from django import forms
from django.forms import inlineformset_factory
from django.core.exceptions import ValidationError
from .models import Receta, DetalleReceta


# --------------------------------- FORMULARIO RECETA (MAESTRO) ---------------------------------
class RecetaForm(forms.ModelForm):
    class Meta:
        model = Receta
        fields = [
            'nombre_receta',
            'id_producto_fk_receta',
            'cantidad_base',
            'descripcion_receta',
            'estado_receta'
        ]
        widgets = {
            'nombre_receta': forms.TextInput(attrs={
                'placeholder': 'Ej: Receta Pan Blandito Tradicional',
                'class': 'input-wyk input-uppercase',
                'maxlength': '100',
                'required': True
            }),
            'id_producto_fk_receta': forms.Select(attrs={
                'class': 'input-wyk select-item',
                'required': True
            }),
            'cantidad_base': forms.NumberInput(attrs={
                'placeholder': 'Cantidad entera (ej: 10)',
                'class': 'input-wyk',
                'step': '1',    # Solo permite números enteros
                'min': '1',     # Mínimo 1 para asegurar valor positivo
                'required': True
            }),
            'descripcion_receta': forms.Textarea(attrs={
                'class': 'input-wyk',
                'rows': 2,
                'maxlength': '255',
                'placeholder': 'Pasos clave o descripción de la receta...'
            }),
            'estado_receta': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }

    def clean_nombre_receta(self):
        nombre = self.cleaned_data.get('nombre_receta').strip().upper()
        return nombre


# --------------------------------- CLASE DE VALIDACIÓN PARA FORMSET ---------------------------------

class BaseDetalleRecetaFormSet(forms.BaseInlineFormSet):
    def clean(self):
        """ Valida que no se repita una misma materia prima en el listado de insumos """
        super().clean()

        # Si ya existen errores individuales en los campos de los formularios, detenemos la validación grupal
        if any(self.errors):
            return

        ingredientes = []
        for form in self.forms:
            # Ignoramos formularios que están vacíos o marcados para eliminación (clic en el bote de basura)
            if self.can_delete and self._should_delete_form(form):
                continue
            if not form.cleaned_data:
                continue

            materia_prima = form.cleaned_data.get('id_materia_prima_fk_det_rec')

            if materia_prima:
                if materia_prima.id_materia_prima in ingredientes:
                    raise ValidationError(
                        f"El ingrediente '{materia_prima.nombre_materia_prima}' ya fue agregado. No puedes ponerlo más de una vez."
                    )
                ingredientes.append(materia_prima.id_materia_prima)


# --------------------------------- FORMSET DE INSUMOS (DETALLE) ---------------------------------

# Este FormSet permite agregar múltiples materias primas a una sola receta
DetalleRecetaFormSet = inlineformset_factory(
    Receta,
    DetalleReceta,
    formset=BaseDetalleRecetaFormSet,  # Inyección de nuestra clase de validación personalizada
    fields=[
        'id_materia_prima_fk_det_rec',
        'cantidad_insumo_base'
    ],
    widgets={
        'id_materia_prima_fk_det_rec': forms.Select(attrs={
            'class': 'input-wyk select-item',
            'required': True
        }),
        'cantidad_insumo_base': forms.NumberInput(attrs={
            'class': 'input-wyk cantidad-input',
            'step': 'any',  # Los insumos SÍ mantienen decimales
            'min': '0.001',
            'placeholder': 'Cant. Base',
            'required': True
        }),
    },
    extra=0,  # Igual que en producción, se maneja dinámicamente con JS
    can_delete=True,
    fk_name='id_receta_fk_det_rec'
)