from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from negozio import views  # Importa le viste dell'app negozio
from django.contrib.auth.views import LogoutView
from negozio import views


admin.site.site_header = "Amministrazione Traostore" 
admin.site.site_title = "Pannello Admin"
admin.site.index_title = "Benvenuto nel Pannello di Controllo"
admin.site.site_url = '/'
urlpatterns = [
    # 1. Pannello di Amministrazione
    path('admin/', admin.site.urls),

    # 2. Viste principali del negozio
    path('', views.home, name='home'),
    path('prodotto/<int:prodotto_id>/', views.prodotto_dettaglio, name='prodotto_dettaglio'),
    
    # 3. Gestione del Carrello
    path('carrello/', views.cart_detail, name='cart_detail'),
    path('carrello/aggiungi/<int:prodotto_id>/', views.cart_add, name='cart_add'),
    path('carrello/rimuovi/<int:prodotto_id>/', views.cart_remove, name='cart_remove'),
    
    # 4. Processo di Checkout e Stripe
    path('checkout-stripe/', views.checkout, name='checkout_stripe'),
    path('pagamento-successo/', views.payment_success, name='payment_success'),
    path('webhook/', views.stripe_webhook, name='stripe_webhook'),
    # 5. Pagine statiche aggiuntive
    path('articoli/', views.articoli, name='articoli'),
    path('a-proposito/', views.a_proposito, name='a_proposito'),
    path('contatti/', views.contatti, name='contatti'),
    # NUOVO URL DINAMICO: <str:nome_categoria> cattura il nome della collezione
    path('collezione/<str:nome_categoria>/', views.vedi_collezione, name='collezione_dettaglio'),
    # NUOVO URL PER LA RICERCA DEI PRODOTTI NELLA BARRA DI RICERCA
    path('cerca/', views.cerca_prodotti, name='cerca_prodotti'),
    # NUOVO URL PER L'AREA PERSONALE DEGLI UTENTI REGISTRATI
    path('area-personale/', views.area_personale, name='area_personale'),
    # NUOVO URL PER LA GESTIONE DELLE RECENSIONI DEI PRODOTTI
    path('prodotto/<int:prodotto_id>/recensione/', views.aggiungi_recensione, name='aggiungi_recensione'),
    # NUOVO URL PER LA GESTIONE DELLE NEWSLETTER
    path('newsletter/iscriviti/', views.iscrivi_newsletter, name='iscrivi_newsletter'),
    # NUOVO URL PER LA VISUALIZZAZIONE DELLO STORICO DEGLI ORDINI DELL'UTENTE
    path('i-miei-ordini/', views.storico_ordini, name='storico_ordini'),
    # URL PER IL LOGOUT DELL'UTENTE
    path('logout/', views.custom_logout, name='logout'),

    # URL PER IL LOGIN DELL'UTENTE (SOSTITUITO CON LA VISTA PERSONALIZZATA)
    path('login/', views.ClienteLoginView.as_view(), name='login'),
    # URL PER LA REGISTRAZIONE DELL'UTENTE (SOSTITUITO CON LA VISTA PERSONALIZZATA)
    path('admin/', admin.site.urls),
    #stripe webhook endpoint
    path('webhook/stripe/', views.stripe_webhook, name='stripe_webhook'),
]


# 5. Gestione delle immagini (MEDIA) durante lo sviluppo
# Controlliamo che l'impostazione MEDIA_URL sia effettivamente configurata
if settings.DEBUG and settings.MEDIA_URL:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)