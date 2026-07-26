from django.shortcuts import render, redirect, get_object_or_404
from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.urls import reverse
from .models import Prodotto, Ordine, VoceOrdine, Recensione, NewsletterIscritto, CarrelloItem, Coupon, ProfiloUtente
from .forms import ProdottoForm, OrdineForm
from .cart import Cart
import stripe
from django.db.models import Q, Sum
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.views import LoginView
from django.utils import timezone
from django.contrib.admin.views.decorators import staff_member_required
from django.core.mail import send_mail

# Configura la chiave segreta di Stripe
stripe.api_key = settings.STRIPE_SECRET_KEY


# 1. Vista per la Home Page / Lista Prodotti
def home(request):
    prodotti = Prodotto.objects.all()
    
    # Controlla se l'utente ha scelto un ordinamento
    ordinamento = request.GET.get('ordine')
    if ordinamento == 'prezzo_basso':
        prodotti = prodotti.order_by('prezzo')
    elif ordinamento == 'prezzo_alto':
        prodotti = prodotti.order_by('-prezzo')

    return render(request, 'negozio/home.html', {'prodotti': prodotti})


# 2. Vista per il Dettaglio del Prodotto
def prodotto_dettaglio(request, prodotto_id):
    prodotto = get_object_or_404(Prodotto, id=prodotto_id)
    # 1. Recupera tutte le recensioni di questo prodotto
    recensioni = prodotto.recensioni.all().order_by('-data')
    
    # 2. Gestione dell'invio di una nuova recensione
    if request.method == 'POST':
        if not request.user.is_authenticated:
            messages.error(request, "Devi effettuare il login per lasciare una recensione.")
            return redirect('login')
            
        voto = request.POST.get('voto')
        testo = request.POST.get('testo')
        immagine = request.FILES.get('immagine') # Cattura la foto caricata
        
        Recensione.objects.create(
            prodotto=prodotto,
            utente=request.user,
            voto=voto,
            testo=testo,
            immagine=immagine
        )
        messages.success(request, "Recensione pubblicata con successo!")
        return redirect('prodotto_dettaglio', pk=prodotto.id)
    
    # (Facoltativo) Prodotti correlati se li usi
    prodotti_correlati = Prodotto.objects.exclude(id=prodotto.id)[:3]

    context = {
        'prodotto': prodotto,
        'recensioni': recensioni, # <-- Fondamentale per mostrarle in HTML!
        'prodotti_correlati': prodotti_correlati,
    }
    return render(request, 'negozio/prodotto_dettaglio.html', context)

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


# 7. Vista Checkout unificata con Stripe
@login_required
def checkout(request):
    carrello_elementi = CarrelloItem.objects.filter(user=request.user)

    if not carrello_elementi.exists():
        return redirect('cart_detail')

    if request.method == 'POST':
        form = OrdineForm(request.POST)
        if form.is_valid():
            ordine = form.save(commit=False)
            ordine.stato = 'PAGATO'
            ordine.utente = request.user
            
            # Calcolo del totale dal database
            totale_ordine = sum(item.totale_articolo for item in carrello_elementi)
            ordine.totale = totale_ordine  
            ordine.save()
            
            # Salvataggio dati di spedizione in sessione per recuperarli dopo il pagamento
            request.session['dati_spedizione'] = {
                'nome': ordine.nome,
                'cognome': ordine.cognome,
                'email': ordine.email,
                'indirizzo': ordine.indirizzo,
                'citta': ordine.citta,
                'cap': ordine.cap,
            }
            
            # Prepariamo la lista articoli per Stripe
            line_items = []
            for item in carrello_elementi:
                line_items.append({
                    'price_data': {
                        'currency': 'eur',
                        'product_data': {
                            'name': item.prodotto.nome,
                        },
                        'unit_amount': int(item.prodotto.prezzo * 100),
                    },
                    'quantity': item.quantita,
                })
                
            success_url = request.build_absolute_uri(reverse('pagamento_successo')) + "?session_id={CHECKOUT_SESSION_ID}"
            cancel_url = request.build_absolute_uri(reverse('home'))
            
            try:
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
                return redirect(checkout_session.url, code=303)
                
            except Exception as e:
                return render(request, 'negozio/checkout.html', {'form': form, 'errore': str(e)})
    else:
        form = OrdineForm()
        
    return render(request, 'negozio/checkout.html', {'form': form})


# 8. Vista per la pagina di successo del pagamento
@login_required
def pagamento_successo(request):
    session_id = request.GET.get('session_id')
    ordine = None
    
    if session_id:
        try:
            session = stripe.checkout.Session.retrieve(session_id)
            if session.payment_status == 'paid':
                carrello_elementi = CarrelloItem.objects.filter(user=request.user)
                
                if carrello_elementi.exists():
                    totale_ordine = sum(item.totale_articolo for item in carrello_elementi)
                    dati_spedizione = request.session.get('dati_spedizione', {})
                    
                    # Crea l'ordine ufficiale
                    ordine = Ordine.objects.create(
                        utente=request.user,
                        nome=dati_spedizione.get('nome', request.user.first_name or 'Cliente'),
                        cognome=dati_spedizione.get('cognome', request.user.last_name or ''),
                        email=dati_spedizione.get('email', request.user.email),
                        indirizzo=dati_spedizione.get('indirizzo', 'Indirizzo non specificato'),
                        citta=dati_spedizione.get('citta', ''),
                        cap=dati_spedizione.get('cap', ''),
                        totale=totale_ordine,
                        stato='PAGATO'
                    )
                    
                    # Crea le voci d'ordine e scala il magazzino
                    for item in carrello_elementi:
                        VoceOrdine.objects.create(
                            ordine=ordine,
                            prodotto=item.prodotto,
                            quantita=item.quantita,
                            prezzo=item.prodotto.prezzo
                        )
                        item.prodotto.quantita_disponibile -= item.quantita
                        item.prodotto.save()
                    
                    # Pulisci carrello e sessione
                    carrello_elementi.delete()
                    if 'dati_spedizione' in request.session:
                        del request.session['dati_spedizione']
                        
                    messages.success(request, f"Pagamento completato con successo! Il tuo ordine #{ordine.id} è stato registrato.")
        except Exception as e:
            print(f"Errore Stripe in successo: {e}")

    return render(request, 'negozio/successo.html', {'ordine': ordine})


# Viste di supporto (Articoli, A proposito, Contatti, Collezione, Ricerca, ecc.)
def articoli(request):
    prodotti = Prodotto.objects.all()
    return render(request, 'negozio/articoli.html', {'prodotti': prodotti})


def a_proposito(request):
    return render(request, 'negozio/a_proposito.html')


def contatti(request):
    return render(request, 'negozio/contatti.html')


def vedi_collezione(request, nome_categoria):
    prodotti_filtrati = Prodotto.objects.filter(categoria=nome_categoria)
    ordinamento = request.GET.get('ordine')
    
    if ordinamento == 'prezzo_crescente':
        prodotti_filtrati = prodotti_filtrati.order_by('prezzo')
    elif ordinamento == 'prezzo_decrescente':
        prodotti_filtrati = prodotti_filtrati.order_by('-prezzo')
        
    context = {
        'prodotti': prodotti_filtrati,
        'titolo': nome_categoria.capitalize(),
        'ordinamento_attuale': ordinamento
    }
    return render(request, 'negozio/collezione.html', context)


def cerca_prodotti(request):
    query = request.GET.get('q')
    risultati = Prodotto.objects.all()
    if query:
        risultati = risultati.filter(Q(nome__icontains=query) | Q(descrizione__icontains=query))
    return render(request, 'negozio/ricerca.html', {'prodotti': risultati, 'query': query})


@login_required
def area_personale(request):
    ordini_utente = Ordine.objects.filter(utente=request.user).order_by('-data_creazione')
    return render(request, 'negozio/area_personale.html', {'ordini': ordini_utente})


@login_required
def aggiungi_recensione(request, prodotto_id):
    prodotto = get_object_or_404(Prodotto, id=prodotto_id)
    if request.method == 'POST':
        voto = request.POST.get('voto')
        commento = request.POST.get('commento')
        immagine = request.FILES.get('immagine')
        Recensione.objects.create(prodotto=prodotto, utente=request.user, voto=voto, commento=commento)
        immagine=immagine
    return redirect('prodotto_dettaglio', prodotto_id=prodotto_id)


def iscrivi_newsletter(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        if email:
            if NewsletterIscritto.objects.filter(email=email).exists():
                messages.warning(request, "Questa email è già iscritta alla newsletter!")
            else:
                NewsletterIscritto.objects.create(email=email)
                messages.success(request, "Iscrizione alla newsletter avvenuta con successo! 🎉")
    return redirect(request.META.get('HTTP_REFERER', 'home'))
    

@login_required
def storico_ordini(request):
    ordini = Ordine.objects.filter(utente=request.user).order_by('-id')
    return render(request, 'negozio/storico_ordini.html', {'ordini': ordini})


def custom_logout(request):
    logout(request)
    return redirect('home')


class ClienteLoginView(LoginView):
    template_name = 'negozio/login.html'
    redirect_authenticated_user = True


@csrf_exempt
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except Exception:
        return HttpResponse(status=400)

    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        ordine_id = session.get('metadata', {}).get('ordine_id')
        if ordine_id:
            try:
                ordine = Ordine.objects.get(id=ordine_id)
                ordine.stato = 'PAGATO'
                ordine.save()
            except Ordine.DoesNotExist:
                pass

    return HttpResponse(status=200)


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


@staff_member_required
def admin_dashboard(request):
    totale_ordini = Ordine.objects.count()
    fatturato_totale = Ordine.objects.filter(stato='PAGATO').aggregate(totale_somma=Sum('totale'))['totale_somma'] or 0
    totale_prodotti = Prodotto.objects.count()
    ultimi_ordini = Ordine.objects.order_by('-id')[:5]
    
    context = {
        'totale_ordini': totale_ordini,
        'fatturato_totale': fatturato_totale,
        'totale_prodotti': totale_prodotti,
        'ultimi_ordini': ultimi_ordini,
    }
    return render(request, 'negozio/admin_dashboard.html', context)


@login_required
def elimina_ordini_selezionati(request):
    if request.method == 'POST':
        ids_selezionati = request.POST.getlist('ordini_selezionati')
        if ids_selezionati:
            ordini = Ordine.objects.filter(id__in=ids_selezionati, utente=request.user)
            conteggio = ordini.count()
            ordini.delete()
            messages.success(request, f"Eliminati con successo {conteggio} ordini dal tuo storico.")
        else:
            messages.warning(request, "Non hai selezionato nessun ordine da eliminare.")
    return redirect('storico_ordini')

#
def pagamento_annullato(request):
    messages.warning(request, "Il processo di pagamento è stato annullato.")
    return redirect('cart_detail')



@login_required
def profilo_utente(request):
    # Recupera o crea automaticamente il profilo per l'utente loggato
    profilo, created = ProfiloUtente.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        # Aggiorna i dati anagrafici standard dell'utente
        request.user.first_name = request.POST.get('first_name', '')
        request.user.last_name = request.POST.get('last_name', '')
        request.user.email = request.POST.get('email', '')
        request.user.save()
        
        # Aggiorna i dati del profilo/spedizione
        profilo.indirizzo = request.POST.get('indirizzo', '')
        profilo.citta = request.POST.get('citta', '')
        profilo.cap = request.POST.get('cap', '')
        profilo.telefono = request.POST.get('telefono', '')
        profilo.save()
        
        messages.success(request, "I tuoi dati personali e di spedizione sono stati aggiornati con successo! 🚀")
        return redirect('profilo_utente')
        
    return render(request, 'negozio/profilo.html', {'profilo': profilo})