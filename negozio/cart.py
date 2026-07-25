from decimal import Decimal
from django.conf import settings
from .models import Prodotto, CarrelloItem, Coupon

class Cart:
    def __init__(self, request):
        """
        Inizializza il carrello (supporta database per utenti loggati e sessione per ospiti).
        """
        self.request = request
        self.session = request.session
        self.user = request.user
        
        if not self.user.is_authenticated:
            cart = self.session.get('cart')
            if not cart:
                cart = self.session['cart'] = {}
            self.cart = cart
        else:
            self.cart = None
            
        # Recupera il coupon dalla sessione
        self.coupon_id = self.session.get('coupon_id')

    @property
    def coupon(self):
        if self.coupon_id:
            try:
                return Coupon.objects.get(id=self.coupon_id)
            except Coupon.DoesNotExist:
                pass
        return None

    def get_total_price_base(self):
        """Calcola il prezzo totale del carrello senza applicare alcuno sconto."""
        if self.user.is_authenticated:
            return sum(item.prodotto.prezzo * item.quantita for item in CarrelloItem.objects.filter(user=self.user))
        else:
            return sum(Decimal(item['prezzo']) * item['quantita'] for item in self.cart.values())

    def get_discount(self):
        if self.coupon:
            totale = self.get_total_price_base()
            return (Decimal(self.coupon.sconto) / Decimal('100')) * totale
        return Decimal('0')

    def get_total_price(self):
        totale_base = self.get_total_price_base()
        if self.coupon:
            sconto = self.get_discount()
            return max(Decimal('0'), totale_base - sconto)
        return totale_base
    def add(self, prodotto, quantita=1, override_quantita=False):
        """
        Aggiunge un prodotto al carrello o ne aggiorna la quantità.
        """
        if self.user.is_authenticated:
            item, creato = CarrelloItem.objects.get_or_create(
                user=self.user,
                prodotto=prodotto,
                defaults={'quantita': 0 if override_quantita else quantita}
            )
            if not creato:
                if override_quantita:
                    item.quantita = quantita
                else:
                    item.quantita += quantita
                item.save()
            else:
                if override_quantita:
                    item.quantita = quantita
                    item.save()
        else:
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
        if not self.user.is_authenticated:
            self.session.modified = True

    def remove(self, prodotto):
        """
        Rimuove un prodotto dal carrello.
        """
        if self.user.is_authenticated:
            CarrelloItem.objects.filter(user=self.user, prodotto=prodotto).delete()
        else:
            prodotto_id = str(prodotto.id)
            if prodotto_id in self.cart:
                del self.cart[prodotto_id]
                self.save()

    def __iter__(self):
        """
        Itera sui prodotti nel carrello (da database o sessione).
        """
        if self.user.is_authenticated:
            items = CarrelloItem.objects.filter(user=self.user)
            for item in items:
                yield {
                    'prodotto': item.prodotto,
                    'quantita': item.quantita,
                    'prezzo': item.prodotto.prezzo,
                    'prezzo_totale': item.prodotto.prezzo * item.quantita
                }
        else:
            prodotto_ids = self.cart.keys()
            prodotti = Prodotto.objects.filter(id__in=prodotto_ids)
            prodotti_db = {str(p.id): p for p in prodotti}
            
            for prodotto_id, item in self.cart.items():
                prodotto_obj = prodotti_db.get(prodotto_id)
                if prodotto_obj:
                    item_completo = item.copy()
                    item_completo['prodotto'] = prodotto_obj
                    item_completo['prezzo'] = Decimal(item['prezzo'])
                    item_completo['prezzo_totale'] = item_completo['prezzo'] * item_completo['quantita']
                    yield item_completo

    def __len__(self):
        """
        Conta il numero totale di articoli nel carrello.
        """
        if self.user.is_authenticated:
            return sum(item.quantita for item in CarrelloItem.objects.filter(user=self.user))
        else:
            return sum(item['quantita'] for item in self.cart.values())

    def get_total_price(self):
        """
        Calcola il costo totale del carrello.
        """
        if self.user.is_authenticated:
            return sum(item.prodotto.prezzo * item.quantita for item in CarrelloItem.objects.filter(user=self.user))
        else:
            return sum(Decimal(item['prezzo']) * item['quantita'] for item in self.cart.values())

    def clear(self):
        """
        Svuota il carrello.
        """
        if self.user.is_authenticated:
            CarrelloItem.objects.filter(user=self.user).delete()
        else:
            if 'cart' in self.session:
                del self.session['cart']
                self.save()


