from .cart import Cart

# def cart(request):
#     return {'cart': Cart(request)}

def cart_counter(request):
    # Restituisce l'istanza del carrello così possiamo leggerne la lunghezza in qualsiasi pagina
    return {'cart': Cart(request)}