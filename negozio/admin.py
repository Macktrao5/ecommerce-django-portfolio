from django.contrib import admin
from .models import Prodotto, Ordine, VoceOrdine, Recensione
from .models import Coupon
from .models import ProfiloUtente



# 1. Configurazione per i Prodotti
@admin.register(Prodotto)
class ProdottoAdmin(admin.ModelAdmin):
    # Colonne che compaiono nella lista dei prodotti nel pannello admin
    list_display = ('nome', 'prezzo', 'categoria', 'quantita_disponibile', 'stato_magazzino')
    search_fields = ('nome', 'descrizione')
    list_filter = ('categoria',)

    # Funzione personalizzata per colorare o evidenziare le scorte basse direttamente nell'Admin
    def stato_magazzino(self, obj):
        if obj.quantita_disponibile == 0:
            return "❌ Esaurito"
        elif obj.quantita_disponibile <= 3:
            return f"⚠️ Quasi esaurito ({obj.quantita_disponibile})"
        return f"✅ Disponibile ({obj.quantita_disponibile})"
    
    stato_magazzino.short_description = 'Stato Magazzino'

# Registriamo anche gli altri modelli se non lo erano già
admin.site.register(Ordine)
admin.site.register(VoceOrdine)
admin.site.register(Recensione)
admin.site.register(Coupon)
admin.site.register(ProfiloUtente)