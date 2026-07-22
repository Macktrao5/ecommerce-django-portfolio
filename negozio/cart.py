from decimal import Decimal
from django.conf import settings
from .models import Prodotto

class Cart:
    def __init__(self, request):
        """
        Inizializza il carrello usando la sessione di Django.
        """
        self.session = request.session
        cart = self.session.get('cart')
        if not cart:
            # Se il carrello non esiste nella sessione, ne creiamo uno vuoto
            cart = self.session['cart'] = {}
        self.cart = cart

    def add(self, prodotto, quantita=1, override_quantita=False):
        """
        Aggiunge un prodotto al carrello o ne aggiorna la quantità.
        """
        prodotto_id = str(prodotto.id)
        if prodotto_id not in self.cart:
            self.cart[prodotto_id] = {
                'quantita': 0,
                'prezzo': str(prodotto.prezzo)
            }
        
        if override_quantita:
            self.cart[prodotto_id]['quantita'] = quantita
        else:
            self.cart[prodotto_id]['quantita'] += quantita
        
        self.save()

    def save(self):
        # Segnala a Django che la sessione è stata modificata e va salvata nel database
        self.session.modified = True

    def remove(self, prodotto):
        """
        Rimuove un prodotto dal carrello.
        """
        prodotto_id = str(prodotto.id)
        if prodotto_id in self.cart:
            del self.cart[prodotto_id]
            self.save()

    def __iter__(self):
        """
        Itera sui prodotti nel carrello e recupera gli oggetti Prodotto dal database.
        """
        prodotto_ids = self.cart.keys()
        prodotti = Prodotto.objects.filter(id__in=prodotto_ids)
        
        # Creiamo un dizionario per mappare rapidamente gli ID agli oggetti Prodotto
        prodotti_db = {str(p.id): p for p in prodotti}
        
        # Cicliamo sulle chiavi del carrello reale
        for prodotto_id, item in self.cart.items():
            prodotto_obj = prodotti_db.get(prodotto_id)
            if prodotto_obj:
                # Creiamo un nuovo dizionario separato per non toccare la sessione originale
                item_completo = item.copy()
                item_completo['prodotto'] = prodotto_obj
                item_completo['prezzo'] = Decimal(item['prezzo'])
                item_completo['prezzo_totale'] = item_completo['prezzo'] * item_completo['quantita']
                yield item_completo

    def __len__(self):
        """
        Conta il numero totale di articoli nel carrello.
        """
        return sum(item['quantita'] for item in self.cart.values())

    def get_total_price(self):
        """
        Calcola il costo totale del carrello.
        """
        return sum(Decimal(item['prezzo']) * item['quantita'] for item in self.cart.values())

    def clear(self):
        """
        Svuota il carrello.
        """
        del self.session['cart']
        self.save()