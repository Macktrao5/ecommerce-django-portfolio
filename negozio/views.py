from django.shortcuts import render, redirect, get_object_or_404
from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.urls import reverse
from .models import Prodotto, Ordine, VoceOrdine,Recensione
from .forms import ProdottoForm, OrdineForm
from .cart import Cart
import stripe
from .models import Prodotto
from django.shortcuts import redirect
from django.db.models import Q # Serve per cercare sia nel nome CHE nella descrizione dei prodotti nella barra di ricerca
import json
from django.contrib.auth.decorators import login_required
from .models import NewsletterIscritto
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import Ordine
from django.contrib.auth import logout
from django.contrib.auth.views import LoginView
from django.urls import reverse
from django.core.mail import send_mail
from .models import Prodotto, CarrelloItem
from django.utils import timezone
from .models import Coupon
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Sum
from .models import Ordine, Prodotto

# Configura la chiave segreta di Stripe
stripe.api_key = settings.STRIPE_SECRET_KEY


# 1. Vista per la Home Page / Lista Prodotti
def home(request):
    prodotti = Prodotto.objects.all()
    
    # Controlla se l'utente ha scelto un ordinamento
    ordinamento = request.GET.get('ordine')
    if ordinamento == 'prezzo_basso':
        prodotti = prodotti.order_by('prezzo')  # Dal meno caro al più caro
    elif ordinamento == 'prezzo_alto':
        prodotti = produt_ordinati = prodotti.order_by('-prezzo') # Dal più caro al meno caro
        # Oppure semplicemente:
        prodotti = prodotti.order_by('-prezzo')

    return render(request, 'negozio/home.html', {'prodotti': prodotti})
# 2. Vista per il Dettaglio del Prodotto
def prodotto_dettaglio(request, prodotto_id):
    # Prende il prodotto corrente
    prodotto = get_object_or_404(Prodotto, id=prodotto_id)
    
    # NOVITÀ: Prende altri 3 prodotti della STESSA categoria, 
    # escludendo (.exclude) il prodotto che stiamo già guardando
    prodotti_correlati = Prodotto.objects.filter(categoria=prodotto.categoria).exclude(id=prodotto.id)[:3]
    
    context = {
        'prodotto': prodotto,
        'prodotti_correlati': prodotti_correlati # Passiamo i correlati al template
    }
    return render(request, 'negozio/prodotto_dettaglio.html', context)

# 3. Vista per inserire un nuovo Prodotto tramite Form
def prodotto_nuovo(request):
    if request.method == "POST":
        form = ProdottoForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('home')
    else:
        form = ProdottoForm()
    return render(request, 'negozio/prodotto_nuovo.html', {'form': form})


# 4. Vista per visualizzare il Carrello
def cart_detail(request):
    cart = Cart(request)
    return render(request, 'negozio/carrello.html', {'cart': cart})


# 5. Vista per aggiungere un prodotto al Carrello
def cart_add(request, prodotto_id):
    cart = Cart(request)
    prodotto = get_object_or_404(Prodotto, id=prodotto_id)
    cart.add(prodotto=prodotto)
    return redirect(request.META.get('HTTP_REFERER', 'home'))


# 6. Vista per rimuovere un prodotto dal Carrello
def cart_remove(request, prodotto_id):
    cart = Cart(request)
    prodotto = get_object_or_404(Prodotto, id=prodotto_id)
    cart.remove(prodotto)
    return redirect('cart_detail')


# 7. Vista Checkout (Pagina con il Form per i dati reali e reindirizzamento Stripe)
# 7. Vista Checkout CORRETTA (Aggiunge il prodotto al volo e reindirizza a Stripe)
# 7. Vista Checkout CORRETTA (Calcola il totale prima del salvataggio)
# 7. Vista Checkout CORRETTA (Calcola sempre il totale e gestisce ospiti e utenti loggati)
def checkout(request):
    cart = Cart(request)

    # Se il carrello è completamente vuoto, blocchiamo il checkout
    if len(cart) == 0:
        return redirect('cart_detail')

    if request.method == 'POST':
        form = OrdineForm(request.POST)
        if form.is_valid():
            ordine = form.save(commit=False)
            ordine.stato = 'IN_ATTESA'
            
            # Se l'utente è loggato, colleghiamo l'account all'ordine
            if request.user.is_authenticated:
                ordine.utente = request.user
            
            # CALCOLO DEL TOTALE: Adesso è fuori dal blocco, così funziona per tutti!
            totale_ordine = sum(item['prodotto'].prezzo * item['quantita'] for item in cart)
            ordine.totale = totale_ordine  
            
            ordine.save()
            
            # Colleghiamo i prodotti reali del carrello a questo ordine e aggiorniamo il magazzino
            for item in cart:
                prodotto = item['prodotto']
                quantita_acquistata = item['quantita']
                
                VoceOrdine.objects.create(
                    ordine=ordine,
                    prodotto=prodotto,
                    quantita=quantita_acquistata,
                    prezzo=prodotto.prezzo
                )
                
                # Sottraiamo i pezzi dal magazzino
                prodotto.quantita_disponibile -= quantita_acquistata
                prodotto.save()
                
            # Prepariamo la lista articoli per Stripe
            line_items = []
            for item in cart:
                line_items.append({
                    'price_data': {
                        'currency': 'eur',
                        'product_data': {
                            'name': item['prodotto'].nome,
                        },
                        'unit_amount': int(item['prodotto'].prezzo * 100),
                    },
                    'quantity': item['quantita'],
                })
                
            success_url = request.build_absolute_uri(reverse('payment_success')) + f"?ordine_id={ordine.id}"
            cancel_url = request.build_absolute_uri(reverse('home'))
            
            try:
                # Creazione sessione Stripe
                checkout_session = stripe.checkout.Session.create(
                    payment_method_types=['card'],
                    line_items=line_items,
                    mode='payment',
                    success_url=success_url,
                    cancel_url=cancel_url,
                    customer_email=ordine.email,
                    metadata={
                        'ordine_id': str(ordine.id)
                    }
                )
                
                # Svuotiamo il carrello dopo aver creato la sessione con successo
                cart.clear()
                
                # Reindirizzamento alla schermata di pagamento di Stripe
                return redirect(checkout_session.url, code=303)
                
            except Exception as e:
                return render(request, 'negozio/checkout.html', {'form': form, 'cart': cart, 'errore': str(e)})
    else:
        form = OrdineForm()
        
    return render(request, 'negozio/checkout.html', {'form': form, 'cart': cart})
# 8. Vista per la pagina di successo (dopo il pagamento)
def payment_success(request):
    stripe.api_key = settings.STRIPE_SECRET_KEY
    session_id = request.GET.get('session_id')
    ordine = None
    
    # 1. Recupero ordine tramite Stripe session_id
    if session_id:
        try:
            session = stripe.checkout.Session.retrieve(session_id)
            ordine_id = session.metadata.get('ordine_id')
            if ordine_id:
                ordine = get_object_or_404(Ordine, id=ordine_id)
                ordine.stato = 'PAGATO'
                ordine.save()
        except Exception as e:
            print(f"Errore Stripe: {e}")

    # 2. Fallback tramite parametro GET nell'URL
    if not ordine:
        ordine_id = request.GET.get('ordine_id')
        if ordine_id:
            ordine = get_object_or_404(Ordine, id=ordine_id)
            ordine.stato = 'PAGATO'
            ordine.save()

    # 3. Invio dell'email di conferma al cliente
    if ordine and ordine.email:
        subject = f'Conferma Ordine #{ordine.id} - Pagamento Ricevuto'
        message = (
            f"Ciao {ordine.nome},\n\n"
            f"Grazie mille per il tuo acquisto!\n"
            f"Il pagamento per l'ordine #{ordine.id} è andato a buon fine.\n\n"
            f"Totale pagato: €{ordine.totale}\n"
            f"Indirizzo di spedizione: {ordine.indirizzo}, {ordine.citta} ({ordine.cap})\n\n"
            f"Ti avviseremo non appena il pacco sarà spedito.\n\n"
            f"A presto!"
        )
        try:
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [ordine.email],
                fail_silently=False,
            )
        except Exception as e:
            print(f"Errore nell'invio dell'email: {e}")
            
    return render(request, 'negozio/successo.html', {'ordine': ordine})
    # Vista per la pagina con tutti i prodotti (Articoli)
def articoli(request):
    prodotti = Prodotto.objects.all()
    return render(request, 'negozio/articoli.html', {'prodotti': prodotti})

# Vista per la storia del Brand (A proposito)
def a_proposito(request):
    return render(request, 'negozio/a_proposito.html')

# Vista per la pagina dei Contatti
def contatti(request):
    return render(request, 'negozio/contatti.html')

        # Vista per la pagina della Collezione (Filtra per categoria)
def vedi_collezione(request, nome_categoria):
    # 1. Prende tutti i prodotti della categoria selezionata
    prodotti_filtrati = Prodotto.objects.filter(categoria=nome_categoria)
    
    # 2. Prende l'opzione di ordinamento scelta dall'utente (se esiste)
    ordinamento = request.GET.get('ordine')
    
    if ordinamento == 'prezzo_crescente':
        prodotti_filtrati = prodotti_filtrati.order_by('prezzo') # Dal più economico al più caro
    elif ordinamento == 'prezzo_decrescente':
        prodotti_filtrati = prodotti_filtrati.order_by('-prezzo') # Dal più caro al più economico
        
    titolo_categoria = nome_categoria.capitalize()
    
    context = {
        'prodotti': prodotti_filtrati,
        'titolo': titolo_categoria,
        'ordinamento_attuale': ordinamento # Ci serve per tenere selezionata l'opzione nel menu
    }
    return render(request, 'negozio/collezione.html', context)


# Vista per la barra di ricerca dei prodotti
def cerca_prodotti(request):
    query = request.GET.get('q')
    risultati = Prodotto.objects.all()
    
    if query:
        risultati = risultati.filter(Q(nome__icontains=query) | Q(descrizione__icontains=query))
    
    context = {
        'prodotti': risultati,
        'query': query
    }
    return render(request, 'negozio/ricerca.html', context)

# Vista per l'Area Personale del cliente
@login_required(login_url='/admin/login/') # Se non sei loggato, ti manda al login
def area_personale(request):
    # Recupera tutti gli ordini collegati all'utente che ha fatto l'accesso, dal più recente
    ordini_utente = Ordine.objects.filter(utente=request.user).order_by('-data_creazione')
    
    context = {
        'ordini': ordini_utente
    }
    return render(request, 'negozio/area_personale.html', context)


@login_required
def aggiungi_recensione(request, prodotto_id):
    prodotto = get_object_or_404(Prodotto, id=prodotto_id)
    if request.method == 'POST':
        voto = request.POST.get('voto')
        commento = request.POST.get('commento')
        Recensione.objects.create(prodotto=prodotto, utente=request.user, voto=voto, commento=commento)
    return redirect('prodotto_dettaglio', prodotto_id=prodotto_id)

    # Vista per iscriversi alla newsletter
def iscrivi_newsletter(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        if email:
            # Controlla se è già iscritto per evitare doppioni
            if NewsletterIscritto.objects.filter(email=email).exists():
                messages.warning(request, "Questa email è già iscritta alla newsletter!")
            else:
                NewsletterIscritto.objects.create(email=email)
                messages.success(request, "Iscrizione alla newsletter avvenuta con successo! 🎉")
    return redirect(request.META.get('HTTP_REFERER', 'home'))
    
 # Vista per visualizzare lo storico degli ordini dell'utente loggato
@login_required
def storico_ordini(request):
    # Ordinamento crescente: dal più vecchio in alto al più recente in basso
    ordini = Ordine.objects.filter(utente=request.user).order_by('id')
    return render(request, 'negozio/storico_ordini.html', {'ordini': ordini})


def custom_logout(request):
    logout(request)
    return redirect('home')

# Vista personalizzata per il login degli utenti
class ClienteLoginView(LoginView):
    template_name = 'negozio/login.html'
    redirect_authenticated_user = True


# Disabilitiamo il CSRF per questa vista, altrimenti Django blocca la chiamata di Stripe!
@csrf_exempt
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    event = None

    try:
        # Verifica che il messaggio arrivi davvero da Stripe
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError as e:
        # Errore nel caricamento dei dati
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError as e:
        # Errore nella firma di sicurezza
        return HttpResponse(status=400)

    # Se l'evento è "Pagamento completato con successo"
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        
        # Recuperiamo l'ordine in modo sicuro leggendo direttamente l'attributo Stripe
        ordine_id = None
        if session.metadata:
            ordine_id = getattr(session.metadata, 'ordine_id', None)
        
        if ordine_id:
            try:
                # Troviamo l'ordine nel database
                ordine = Ordine.objects.get(id=ordine_id)
                # Cambiamo lo stato in PAGATO! (Assicurati che 'PAGATO' sia una delle opzioni del tuo modello)
                ordine.stato = 'PAGATO'
                ordine.save()
                print(f"BINGO! L'ordine {ordine_id} è stato pagato con successo.")
            except Ordine.DoesNotExist:
                print("Errore: Ordine non trovato.")

    # Rispondiamo a Stripe con un 200 OK per dirgli "Messaggio ricevuto!"
    return HttpResponse(status=200)

# Vista per applicare un coupon al carrello

def applica_coupon(request):
    if request.method == 'POST':
        codice = request.POST.get('codice_coupon')
        now = timezone.now()
        try:
            coupon = Coupon.objects.get(codice__iexact=codice, valido_da__lte=now, valido_a__gte=now, attivo=True)
            request.session['coupon_id'] = coupon.id
        except Coupon.DoesNotExist:
            request.session['coupon_id'] = None
    return redirect('visualizza_carrello')

#staff dashboard view
@staff_member_required
def admin_dashboard(request):
    # Calcoliamo le metriche principali
    totale_ordini = Ordine.objects.count()
    
    # Somma il totale degli ordini pagati (o di tutti gli ordini, a seconda delle tue preferenze)
    fatturato_totale = Ordine.objects.filter(stato='PAGATO').aggregate(totale_somma=Sum('totale'))['totale_somma'] or 0
    
    totale_prodotti = Prodotto.objects.count()
    
    # Recuperiamo gli ultimi 5 ordini effettuati
    ultimi_ordini = Ordine.objects.order_by('-id')[:5]
    
    context = {
        'totale_ordini': totale_ordini,
        'fatturato_totale': fatturato_totale,
        'totale_prodotti': totale_prodotti,
        'ultimi_ordini': ultimi_ordini,
    }
    return render(request, 'negozio/admin_dashboard.html', context)

# Vista per eliminare un ordine dallo storico personale dell'utente
@login_required
def elimina_ordini_selezionati(request):
    if request.method == 'POST':
        # Prende tutti gli ID degli ordini spuntati dall'utente
        ids_selezionati = request.POST.getlist('ordini_selezionati')
        
        if ids_selezionati:
            # Filtra solo gli ordini che appartengono effettivamente all'utente loggato per sicurezza
            ordini = Ordine.objects.filter(id__in=ids_selezionati, utente=request.user)
            conteggio = ordini.count()
            ordini.delete()
            messages.success(request, f"Eliminati con successo {conteggio} ordini dal tuo storico.")
        else:
            messages.warning(request, "Non hai selezionato nessun ordine da eliminare.")
            
    return redirect('storico_ordini') # Assicurati che corrisponda al nome della tua rotta nel urls.py