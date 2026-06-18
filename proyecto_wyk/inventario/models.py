from django.db import models
# Create your models here.
"""CONTROL DE INVENTARIOS (MATERIA_PRIMA, PRODUCTO, AJUSTE_INVENTARIO_MATERIA_PRIMA, AJUSTE_INVENTARIO_PRODUCTO)."""


# ---------------------------------MODELO PRODUCTO---------------------------------
class Producto(models.Model):
    # Mapeo del CREATE TYPE tipo_producto
    class TipoProducto(models.TextChoices):
        PANADERIA = 'PANADERIA', 'Panadería'
        PASTELERIA = 'PASTELERIA', 'Pastelería'
        ASEO = 'ASEO', 'Aseo'
        REVENTA = 'REVENTA', 'Reventa'

    id_producto = models.BigIntegerField(primary_key=True, db_column='id_producto')
    nombre_producto = models.CharField(max_length=50, unique=True, db_column='nombre_producto')

    # NUEVO CAMPO PARA IMAGEN
    imagen_producto = models.ImageField(upload_to='productos/', null=True, blank=True, db_column='imagen_producto')

    valor_unitario_product = models.BigIntegerField(db_column='valor_unitario_producto')
    cant_exist_producto = models.BigIntegerField(db_column='cant_exist_producto')
    fecha_vencimiento_product = models.DateField(db_column='fecha_vencimiento_producto')

    # Campo con ENUM
    tipo_producto = models.CharField(max_length=20, choices=TipoProducto.choices, db_column='tipo_producto')

    # NUEVO CAMPO DESCRIPCIÓN (Agregado para coincidir con SQL)
    descripcion_producto = models.CharField(max_length=200, null=True, blank=True, db_column='descripcion_producto')

    # Llave foranea con con otra app
    id_usuario_fk_producto = models.ForeignKey('usuarios.Usuario', on_delete=models.PROTECT,
                                               db_column='id_usuario_fk_producto')

    estado_producto = models.BooleanField(db_column='estado_producto')

    class Meta:
        managed = False
        db_table = 'producto'

    def __str__(self):
        return self.nombre_producto


# ---------------------------------MODELO MATERIA PRIMA---------------------------------
class MateriaPrima(models.Model):
    # Mapeo del CREATE TYPE presentacion_mat
    class PresentacionMat(models.TextChoices):
        KG = 'KG', 'Kilogramos'
        LT = 'LT', 'Litros'
        UN = 'UN', 'Unidades'

    id_materia_prima = models.BigAutoField(primary_key=True, db_column='id_materia_prima')
    nombre_materia_prima = models.CharField(max_length=50, db_column='nombre_materia_prima')

    fecha_vencimiento_mat_prima = models.DateField(db_column='fecha_vencimiento_materia_prima')

    # CAMBIO A DECIMAL(10,3) para Gramos y Mililitros
    cantidad_exist_mat_prima = models.DecimalField(max_digits=10, decimal_places=3,
                                                   db_column='cantidad_exist_materia_prima')

    # CAMBIO A CHOICES PARA ENUM
    presentacion_mat_prima = models.CharField(max_length=20, choices=PresentacionMat.choices,
                                              db_column='presentacion_materia_prima')

    # Ajustado a null=True, blank=True para coincidir con el SQL (opcional)
    descripcion_mat_prima = models.CharField(max_length=200, null=True, blank=True, db_column='descripcion_materia_prima')

    # Llave foranea con otra app
    id_usuario_fk_mat_prima = models.ForeignKey('usuarios.Usuario', on_delete=models.PROTECT,
                                                db_column='id_usuario_fk_materia_prima')
    estado_materia_prima = models.BooleanField(db_column='estado_materia_prima')

    class Meta:
        managed = False
        db_table = 'materia_prima'

    def __str__(self):
        return self.nombre_materia_prima


# ---------------------------------MODELO AJUSTE INVENTARIO---------------------------------
class AjusteInventario(models.Model):
    # Mapeo del CREATE TYPE tipo_ajuste
    class TipoAjuste(models.TextChoices):
        DANADO = 'DAÑADO', 'Dañado'
        ROBO = 'ROBO', 'Robo'
        PERDIDA = 'PERDIDA', 'Pérdida'
        CADUCADO = 'CADUCADO', 'Caducado'
        MUESTRA = 'MUESTRA', 'Muestra'

    id_ajuste = models.AutoField(primary_key=True, db_column='id_ajuste')
    fecha_ajuste = models.DateTimeField(db_column='fecha_ajuste')

    # Campo con ENUM
    tipo_ajuste = models.CharField(max_length=20, choices=TipoAjuste.choices, db_column='tipo_ajuste')

    cantidad_ajustada = models.IntegerField(db_column='cantidad_ajustada')
    descripcion = models.CharField(max_length=200, blank=True, null=True, db_column='descripcion')
    id_prod_fk_ajuste = models.ForeignKey(Producto, on_delete=models.PROTECT, db_column='id_prod_fk_ajuste_inventario')

    # Llave forane con otra app
    id_usuario_fk_ajuste = models.ForeignKey('usuarios.Usuario', on_delete=models.PROTECT,
                                             db_column='id_usuario_fk_ajuste_inventario')

    class Meta:
        managed = False
        db_table = 'ajuste_inventario'


# ---------------------------------MODELO AJUSTE INVENTARIO MATERIA PRIMA---------------------------------
class AjusteInventarioMatPrima(models.Model):  # Corregido nombre (Inventario)
    class TipoAjustMat(models.TextChoices):
        DANADO = 'DAÑADO', 'Dañado'
        ROBO = 'ROBO', 'Robo'
        PERDIDA = 'PERDIDA', 'Pérdida'
        CADUCADO = 'CADUCADO', 'Caducado'
        # Nota: No incluye MUESTRA según el script SQL (tipo_ajuste_mat)

    id_ajust_mat = models.AutoField(primary_key=True, db_column='id_ajus_mat')
    fecha_ajust_mat = models.DateTimeField(db_column='fecha_ajus_mat')
    tipo_ajust_mat = models.CharField(max_length=20, choices=TipoAjustMat.choices, db_column='tipo_ajus_mat')

    # DECIMAL(10,3) coincide con el SQL
    cantidad_ajustada_mat = models.DecimalField(max_digits=10, decimal_places=3, db_column='cantidad_ajustada_mat')

    # CORRECCIÓN: El db_column debe ser descripcion_ajust_mat según tu SQL
    descripcion = models.CharField(
        max_length=200,
        null=True,
        blank=True,
        db_column='descripcion_ajust_mat'
    )

    id_mat_fk_ajuste_mat = models.ForeignKey(
        MateriaPrima,
        on_delete=models.PROTECT,
        db_column='id_mat_fk_ajuste_mat'
    )
    id_usuario_fk_ajuste_mat = models.ForeignKey(
        'usuarios.Usuario',
        on_delete=models.PROTECT,
        db_column='id_usuario_fk_ajuste_mat'
    )

    @property
    def cantidad_convertida(self):
        """
        Multiplica por 1000 si el valor es menor a 1 (para g/ml).
        Mantiene la lógica de seguridad de tu filtro custom_filters.py.
        """
        try:
            valor = float(self.cantidad_ajustada_mat)
            if valor < 1:
                return valor * 1000
            return valor
        except (ValueError, TypeError):
            return 0

    class Meta:
        managed = False
        db_table = 'ajuste_materia_prima'