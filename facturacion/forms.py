from django import forms

from .models import Marca, Producto                     # El modelo del que sale el formulario


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