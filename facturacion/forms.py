from django import forms
from django.core.exceptions import ValidationError
from django.forms import BaseInlineFormSet, inlineformset_factory

from .models import DetalleVenta, Marca, Producto, Venta                     # El modelo del que sale el formulario


class MarcaForm(forms.ModelForm):                # ModelForm: formulario construido desde un modelo

    class Meta:                                  # Configuración del formulario
        model = Marca                            # ¿De qué modelo sale? De Marca
        fields = ["nombre", "pais_origen", "activo"]   # ¿Qué campos muestra y en qué orden?
        labels = {                               # Cambia el texto de la etiqueta de un campo
            "nombre": "Nombre de la marca",
        }
        widgets = {                              # widgets: CÓMO se dibuja cada campo en HTML
            # TextInput = <input type="text">. attrs agrega atributos HTML: aquí la clase de Bootstrap
            "nombre": forms.TextInput(attrs={"class": "form-control", "placeholder": "Ej: Samsung"}),
            "pais_origen": forms.TextInput(attrs={"class": "form-control", "placeholder": "Ej: Corea del Sur"}),
            # CheckboxInput = <input type="checkbox">. form-check-input es la clase de Bootstrap para casillas
            "activo": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }
   
    def clean_nombre(self):                      # Validación propia del campo "nombre" (clean_ + nombre del campo)
        nombre = self.cleaned_data["nombre"].strip()   # cleaned_data: los datos ya revisados. strip quita espacios
        if len(nombre) < 2:                      # Si tiene menos de 2 letras...
            raise forms.ValidationError("El nombre debe tener al menos 2 letras.")  # ...error en rojo bajo el campo
        return nombre.title()  
    
                 # Si está bien, lo devolvemos con la Primera Letra Mayúscula """



class ProductoForm(forms.ModelForm):
    class Meta:
        model = Producto
        # user, fecha_creacion y fecha_modificacion NO van: los llena el sistema
        fields = ["nombre", "descripcion", "marca", "categorias", "precio", "stock", "imagen", "activo"]
        widgets = {
            "nombre": forms.TextInput(attrs={"class": "form-control", "placeholder": "Ej: Galaxy A55"}),
            "descripcion": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "marca": forms.Select(attrs={"class": "form-select"}),                         # 1:N → una opción
            "categorias": forms.CheckboxSelectMultiple(attrs={"class": "form-check-input"}),  # N:M → varias
            "precio": forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "min": "0"}),
            "stock": forms.NumberInput(attrs={"class": "form-control", "min": "0"}),
            # ClearableFileInput = <input type="file"> + casilla "Limpiar" para quitar la foto actual
            "imagen": forms.ClearableFileInput(attrs={"class": "form-control", "accept": "image/*"}),
            "activo": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["marca"].queryset = Marca.objects.filter(activo=True)   # solo marcas activas
        self.fields["marca"].empty_label = "— Elige una marca —"

    def clean_precio(self):
        precio = self.cleaned_data["precio"]
        if precio <= 0:
            raise forms.ValidationError("El precio debe ser mayor que 0.")
        return precio

# =====================================================================
# VENTA: cabecera (maestro)
# =====================================================================
class VentaForm(forms.ModelForm):
    class Meta:
        model = Venta
        fields = ["cliente", "fecha_hora", "tipo_pago"]   # subtotal, iva y total los calcula el sistema
        widgets = {
            "cliente": forms.Select(attrs={"class": "form-select"}),
            # type="datetime-local" → el navegador muestra un calendario con hora
            "fecha_hora": forms.DateTimeInput(attrs={"class": "form-control", "type": "datetime-local"},
                                              format="%Y-%m-%dT%H:%M"),
            "tipo_pago": forms.Select(attrs={"class": "form-select"}),   # las opciones salen de TipoPago
        }

# =====================================================================
# VENTA: filas del detalle
# =====================================================================
class ProductoConPrecioField(forms.ModelChoiceField):
    """Lista desplegable de productos que muestra también el precio y el stock."""
    def label_from_instance(self, obj):           # Django llama a este método para escribir cada <option>
        return f"{obj.nombre} · ${obj.precio} · stock: {obj.stock}"


class DetalleVentaForm(forms.ModelForm):
    producto = ProductoConPrecioField(
        queryset=Producto.objects.filter(activo=True),
        empty_label="— Elige un producto —",
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    class Meta:
        model = DetalleVenta
        fields = ["producto", "cantidad"]           # el precio NO: lo pone la vista con el precio actual
        widgets = {"cantidad": forms.NumberInput(attrs={"class": "form-control", "min": "1"})}

class BaseDetalleVentaFormSet(BaseInlineFormSet):
    """Validación de TODAS las filas juntas: ¿hay stock para lo que se pide?"""

    def clean(self):
        super().clean()                           # primero las validaciones normales de cada fila
        if any(self.errors):                      # si alguna fila ya tiene errores, no seguimos
            return

        pedido = {}                               # {producto: cantidad total pedida}
        for fila in self.forms:
            datos = fila.cleaned_data
            if not datos or datos.get("DELETE"):  # fila vacía o marcada para quitar → se ignora
                continue
            producto = datos["producto"]
            pedido[producto] = pedido.get(producto, 0) + datos["cantidad"]   # suma si el producto se repite

        anterior = {}                             # al EDITAR: lo que esta venta ya tenía reservado
        if self.instance.pk:
            for detalle in self.instance.detalles.all():
                anterior[detalle.producto_id] = anterior.get(detalle.producto_id, 0) + detalle.cantidad

        for producto, cantidad in pedido.items():
            disponible = producto.stock + anterior.get(producto.pk, 0)
            if cantidad > disponible:
                raise ValidationError(
                    f"Stock insuficiente de «{producto.nombre}»: pides {cantidad} y hay {disponible}."
                )

# inlineformset_factory crea una CLASE de formset: muchos DetalleVentaForm unidos a UNA Venta
DetalleVentaFormSet = inlineformset_factory(
    Venta,                                        # el maestro
    DetalleVenta,                                 # el detalle (tiene la ForeignKey venta)
    form=DetalleVentaForm,                        # el formulario de cada fila
    formset=BaseDetalleVentaFormSet,              # nuestra validación de stock
    extra=0,                                      # filas vacías extra (las agrega el botón con JavaScript)
    min_num=1,                                    # mínimo 1 fila...
    validate_min=True,                            # ...y se valida que exista
    can_delete=True,                              # cada fila tiene la casilla "Quitar"
)