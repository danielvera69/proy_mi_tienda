from django.contrib import messages                          # mensajes verdes / rojos
from django.contrib.auth.mixins import LoginRequiredMixin   # exige sesión (el @login_required de las clases)
from django.contrib.messages.views import SuccessMessageMixin   # mensaje de éxito automático
from django.db import transaction                            # transaction.atomic(): todo o nada
from django.db.models import ProtectedError, Q
from django.http import HttpResponseRedirect
from django.shortcuts import redirect, render
from django.urls import reverse, reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DetailView, DeleteView

from .forms import MarcaForm, ProductoForm, VentaForm, DetalleVentaFormSet
from .mixins import UsuarioRegistroMixin
from .models import Marca, Producto, Venta, TipoPago, IVA_TARIFA                             # Nuestro modelo


# =====================================================================
# MARCAS · Vistas Basadas en Funciones (VBF)
# =====================================================================

def marca_lista(request):                                  # READ: muestra todas las marcas
    q = request.GET.get("q", "") #                         # 1. Leemos el buscador: /facturacion/marcas/?q=sam (si no hay, queda "")
    marcas = Marca.objects.all()                          # 2. Pedimos todas las marcas a la base de datos

    if q:                                                  # 3. Si el usuario escribió algo en el buscador...
        marcas = marcas.filter(nombre__icontains=q)        #    ...dejamos solo las que contienen ese texto

    contexto = {                                           # 4. Datos que enviamos al template
        "titulo": "Marcas",                                #    → {{ titulo }}
        "marcas": marcas,                                  #    → {% for marca in marcas %}
        "q": q,                                            #    → para que el buscador no se borre
    }
    return render(request, "facturacion/marca_lista.html", contexto)   # 5. Mostramos la página

def marca_crear(request):                                  # CREATE: crear una marca nueva

    if request.method == "POST":                           # ¿El usuario presionó "Guardar"? (llegó por POST)
        form = MarcaForm(request.POST)                     # 1. Llenamos el formulario con lo que escribió
        if form.is_valid():                                # 2. ¿Los datos están bien? (obligatorios, únicos, clean_nombre)
            marca = form.save()                            # 3. Guardamos en la base de datos (save devuelve la marca)
            messages.success(request, f"Marca «{marca.nombre}» creada correctamente.")   # 4. Mensaje verde
            return redirect("facturacion:marca_lista")     # 5. Vamos a la lista. Así, si recarga, no se guarda dos veces
        # Si NO es válido, no entra al if: baja hasta el render y muestra el formulario CON errores

    else:                                                  # Si llegó por GET (solo abrió la página)...
        form = MarcaForm()                                 # ...creamos un formulario vacío

    contexto = {                                           # Datos para el template
        "titulo": "Nueva marca",                           # Título de la página
        "form": form,                                      # El formulario (vacío o con errores)
        "boton": "Guardar",                                # Texto del botón
    }
    return render(request, "facturacion/marca_form.html", contexto)



def marca_editar(request, pk):                             # UPDATE. pk llega desde la URL: /marcas/editar/3/ → pk=3
    marca = get_object_or_404(Marca, pk=pk)   
    #marca = Marca.objects.get(id=pk)             # 1. Buscamos la marca. Si no existe → página 404

    if request.method == "POST":                           # 2. ¿Presionó "Actualizar"?
        form = MarcaForm(request.POST, instance=marca)     #    Datos nuevos + la marca que vamos a cambiar
        if form.is_valid():                                #    ¿Están bien?
            form.save()                                    #    Actualiza (UPDATE), no crea una nueva
            messages.success(request, f"Marca «{marca.nombre}» actualizada.")
            return redirect("facturacion:marca_lista")     #    Volvemos a la lista
    else:                                                  # 3. Llegó por GET...
        form = MarcaForm(instance=marca)                   #    ...formulario lleno con los datos actuales

    contexto = {
        "titulo": f"Editar marca: {marca.nombre}",
        "form": form,
        "boton": "Actualizar",
    }
    return render(request, "facturacion/marca_form.html", contexto)   # ¡El mismo template de crear!



def marca_eliminar(request, pk):                           # DELETE
    marca = get_object_or_404(Marca, pk=pk)                # Buscamos la marca o mostramos 404

    if request.method == "POST":                           # ¿Presionó "Sí, eliminar"?
        try:                                               # Intentamos borrar...
            nombre = marca.nombre                          # Guardamos el nombre para el mensaje
            marca.delete()                                 # DELETE en la base de datos
            messages.success(request, f"Marca «{nombre}» eliminada.")
        except ProtectedError:                             # ...si tiene productos, PROTECT no deja borrarla
            messages.error(request, f"No se puede eliminar «{marca.nombre}» porque tiene productos. Desactívala en su lugar.")
        return redirect("facturacion:marca_lista")         # En los dos casos volvemos a la lista

    # Si llegó por GET: mostramos la pregunta "¿Seguro?"
    contexto = {"titulo": "Eliminar marca", "marca": marca}
    return render(request, "facturacion/marca_eliminar.html", contexto)

class ProductoListView(LoginRequiredMixin, ListView):     # LISTAR
    model = Producto                                       # ¿qué tabla?
    template_name = "facturacion/producto_lista.html"      # ¿qué HTML?
    context_object_name = "productos"                      # nombre de la lista en el HTML
    paginate_by = 5                                        # 5 por página → envía page_obj
    extra_context = {"titulo": "Productos"} 
    
    def get_queryset(self):                                # ¿QUÉ registros se muestran?
        productos = super().get_queryset()                 # lo normal: Producto.objects.all()
        productos = productos.select_related("marca").prefetch_related("categorias")   # menos consultas
        q = self.request.GET.get("q", "")                  # buscador: ?q=galaxy
        if q:
            productos = productos.filter(nombre__icontains=q)
        return productos

    def get_context_data(self, **kwargs):                  # ¿qué datos EXTRA recibe el HTML?
        contexto = super().get_context_data(**kwargs) 
        # lo que ListView ya armó
        contexto["q"] = self.request.GET.get("q", "")      # + lo buscado
        return contexto


class ProductoCreateView(LoginRequiredMixin, UsuarioRegistroMixin, SuccessMessageMixin, CreateView):   # CREAR
    model = Producto
    form_class = ProductoForm                              # nuestro formulario
    template_name = "facturacion/producto_form.html"
    success_url = reverse_lazy("facturacion:producto_lista")   # a dónde ir al guardar
    success_message = "Producto «%(nombre)s» creado."      # %(nombre)s = el campo nombre del formulario
    extra_context = {"titulo": "Nuevo producto", "boton": "Guardar"}

   
class ProductoUpdateView(LoginRequiredMixin, UsuarioRegistroMixin, SuccessMessageMixin, UpdateView):   # EDITAR
    model = Producto
    form_class = ProductoForm
    template_name = "facturacion/producto_form.html"       # el mismo template de crear
    success_url = reverse_lazy("facturacion:producto_lista")
    success_message = "Producto «%(nombre)s» actualizado."
    extra_context = {"titulo": "Editar producto", "boton": "Actualizar"}

    def form_invalid(self, form):                          # cuando hay errores (POST inválido)
        messages.error(self.request, "Revisa los campos marcados en rojo.")
        return super().form_invalid(form)                  # vuelve a mostrar el formulario

class ProductoDetailView(LoginRequiredMixin, DetailView):  # VER UNO
    model = Producto
    template_name = "facturacion/producto_detalle.html"
    context_object_name = "producto"

class ProductoDeleteView(LoginRequiredMixin, DeleteView):  # ELIMINAR
    model = Producto
    template_name = "facturacion/producto_eliminar.html"
    context_object_name = "producto"
    success_url = reverse_lazy("facturacion:producto_lista")

    def form_valid(self, form):                            # se ejecuta al confirmar (POST)
        nombre = self.object.nombre                        # self.object = el producto a eliminar
        try:
            respuesta = super().form_valid(form)           # DELETE + redirect
        except ProtectedError:                             # ya está en una venta o compra (PROTECT)
            messages.error(self.request, f"No se puede eliminar «{nombre}»: ya tiene ventas o compras. Desactívalo.")
            return redirect("facturacion:producto_lista")
        messages.success(self.request, f"Producto «{nombre}» eliminado.")
        return respuesta

# ================= Ventas ===================
class VentaDetallesMixin:
    """Lo que COMPARTEN crear y editar una venta: cabecera (form) + filas (formset)."""
    model = Venta
    form_class = VentaForm
    template_name = "facturacion/venta_form.html"

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)      # trae "form" (la cabecera)
        if "detalles" not in contexto:                     # en GET el formset todavía no existe...
            contexto["detalles"] = DetalleVentaFormSet(instance=self.object)   # ...lo creamos (vacío o lleno)
        return contexto

    def post(self, request, *args, **kwargs):              # REEMPLAZA el post() normal de la vista
        form = self.get_form()                             # 1. cabecera con request.POST
        detalles = DetalleVentaFormSet(request.POST, instance=self.object)   # 2. filas con request.POST
        if form.is_valid() and detalles.is_valid():        # 3. ¿las DOS partes están bien?
            return self.form_valid(form, detalles)
        return self.form_invalid(form, detalles)

    def form_valid(self, form, detalles):
        with transaction.atomic(): 
           # TODO o NADA: si algo falla, se deshace todo
            if self.object:                                # al EDITAR: devolver lo que la venta tenía
                self.object.devolver_stock()
            form.instance.user = self.request.user
            self.object = form.save()                      # INSERT o UPDATE de la cabecera
            self.guardar_detalles(detalles)                # INSERT / UPDATE / DELETE de las filas
            self.object.descontar_stock()                  # saca de bodega lo vendido
            self.object.calcular_totales()                 # subtotal, IVA y total
        messages.success(self.request, f"{self.object} guardada. Total: ${self.object.total}")
        return HttpResponseRedirect(self.get_success_url())

    def guardar_detalles(self, detalles):
        detalles.instance = self.object                    # las filas pertenecen a ESTA venta
        filas = detalles.save(commit=False)                # objetos nuevos o cambiados, SIN guardar todavía
        for fila in detalles.deleted_objects:              # filas con la casilla "Quitar"
            fila.delete()
        cambio_producto = {obj.pk for obj, campos in detalles.changed_objects if "producto" in campos}
        for fila in filas:
            if fila.pk is None or fila.pk in cambio_producto:   # fila nueva o con otro producto...
                fila.precio = fila.producto.precio              # ...toma el precio ACTUAL del producto
            fila.user = self.request.user
            fila.save()

    def form_invalid(self, form, detalles):
        messages.error(self.request, "Revisa los datos de la venta.")
        # volvemos a dibujar la página con la cabecera Y las filas, con sus errores
        return self.render_to_response(self.get_context_data(form=form, detalles=detalles))

    def get_success_url(self):
        return reverse("facturacion:venta_detalle", kwargs={"pk": self.object.pk})   # a la factura
class VentaListView(LoginRequiredMixin, ListView):
    model = Venta
    template_name = "facturacion/venta_lista.html"
    context_object_name = "ventas"
    paginate_by = 10
    extra_context = {"titulo": "Ventas", "tipos_pago": TipoPago.choices}   # opciones para el filtro

    def get_queryset(self):
        ventas = super().get_queryset().select_related("cliente")   # trae el cliente en el mismo JOIN
        q = self.request.GET.get("q", "")
        tipo = self.request.GET.get("tipo_pago", "")
        if q:   # Q(...) | Q(...) = condición con OR: por apellido O por cédula
            ventas = ventas.filter(Q(cliente__apellidos__icontains=q) | Q(cliente__cedula__icontains=q))
        if tipo:
            ventas = ventas.filter(tipo_pago=tipo)
        return ventas

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto["q"] = self.request.GET.get("q", "")
        contexto["tipo_pago"] = self.request.GET.get("tipo_pago", "")
        return contexto

class VentaCreateView(LoginRequiredMixin, VentaDetallesMixin, CreateView):   # CREAR
    extra_context = {"titulo": "Nueva venta", "boton": "Guardar venta"}

    def post(self, request, *args, **kwargs):
        self.object = None                                 # CreateView: aún no hay venta
        return super().post(request, *args, **kwargs)      # sigue al post() del mixin
class VentaUpdateView(LoginRequiredMixin, VentaDetallesMixin, UpdateView):   # EDITAR
    extra_context = {"titulo": "Editar venta", "boton": "Actualizar venta"}

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()                    # UpdateView: la venta del <int:pk>
        return super().post(request, *args, **kwargs)
class VentaDetailView(LoginRequiredMixin, DetailView):     # VER (la factura)
    model = Venta
    template_name = "facturacion/venta_detalle.html"
    context_object_name = "venta"

    def get_queryset(self):
        return super().get_queryset().select_related("cliente", "user").prefetch_related("detalles__producto")

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto["iva_porcentaje"] = IVA_TARIFA * 100      # 15
        return contexto
    
class VentaDeleteView(LoginRequiredMixin, DeleteView):     # ELIMINAR
    model = Venta
    template_name = "facturacion/venta_eliminar.html"
    context_object_name = "venta"
    success_url = reverse_lazy("facturacion:venta_lista")

    def form_valid(self, form):
        with transaction.atomic():
            self.object.devolver_stock()                   # 1. los productos regresan a la bodega
            respuesta = super().form_valid(form)           # 2. DELETE de la venta (CASCADE borra sus detalles)
        messages.success(self.request, "Venta eliminada y stock devuelto.")
        return respuesta

