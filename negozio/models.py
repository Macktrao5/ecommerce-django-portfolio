from django.db import models
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth.models import User

class Prodotto(models.Model):

     # Categorie disponibili
    CATEGORIE_CHOICES = [
        ('donna', 'Donna'),
        ('uomini', 'Uomini'),
        ('bambini', 'Bambini'),
        ('accessori', 'Accessori'),
    ]

    nome = models.CharField(max_length=200)
    prezzo = models.DecimalField(max_digits=10, decimal_places=2)
    descrizione = models.TextField()
    immagine = models.ImageField(upload_to='prodotti/', null=True, blank=True)
    
    # AGGIUNGI QUESTO CAMPO:
    categoria = models.CharField(
        max_length=20, 
        choices=CATEGORIE_CHOICES, 
        default='donna'
    )
    # 🔥 NUOVO CAMPO: Gestione Magazzino
    quantita_disponibile = models.IntegerField(default=10, help_text="Quanti pezzi hai fisicamente in magazzino?")

    def __str__(self):
        return self.nome
    
    # NUOVI CAMPI AGGIUNTI:
    immagine2 = models.ImageField(upload_to='prodotti/', blank=True, null=True) # Seconda foto
    immagine3 = models.ImageField(upload_to='prodotti/', blank=True, null=True) # Terza foto
    colori = models.CharField(max_length=200, blank=True, null=True, help_text="Separa i colori con una virgola (es: Rosso, Blu, Nero)")

    data_creazione = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Prodotto"
        verbose_name_plural = "Prodotti"

    def __str__(self):
        return self.nome

class Ordine(models.Model):
    STATO_ORDINE = [
        ('PAGATO', 'Pagato'),
        ('in_elaborazione', 'In Elaborazione ⏳'),
        ('spedito', 'Spedito 📦'),
        ('consegnato', 'Consegnato ✅'),
    ]
    
    stato = models.CharField(max_length=20, choices=STATO_ORDINE, default='IN_ATTESA')
    # NUOVO CAMPO: Collega l'ordine a un utente registrato (può essere vuoto se l'utente compra come ospite)
    utente = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='ordini')
    # Dati completi del cliente e della spedizione
    nome = models.CharField(max_length=100)
    cognome = models.CharField(max_length=100, default="")
    email = models.EmailField()
    indirizzo = models.CharField(max_length=255)
    citta = models.CharField(max_length=100, default="")
    cap = models.CharField(max_length=10, default="")
    
    # Dati economici e di tracciamento
    totale = models.DecimalField(max_digits=10, decimal_places=2)
    data_creazione = models.DateTimeField(auto_now_add=True)
    
    # Stato dell'ordine manipolabile dall'admin
    stato = models.CharField(max_length=20, choices=STATO_ORDINE, default='in_elaborazione')
    codice_tracciamento = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return f"Ordine #{self.id} - {self.nome} {self.cognome}"

   # 🔥 FUNZIONE AGGIORNATA: Include il codice di tracciamento nell'email se presente
    def save(self, *args, **kwargs):
        if self.pk:
            vecchio_ordine = Ordine.objects.get(pk=self.pk)
            if vecchio_ordine.stato != 'spedito' and self.stato == 'spedito':
                print(f"\n📧 [EMAIL] Invio notifica di spedizione a: {self.email}...")
                
                # 1. Controlliamo se è stato inserito un codice di tracciamento
                if self.codice_tracciamento:
                    info_tracking = f"\nPuoi tracciare il tuo pacco utilizzando il seguente codice di spedizione:\n👉 {self.codice_tracciamento}"
                else:
                    info_tracking = "\nIl tuo pacco sarà tracciabile nelle prossime ore."

                # 2. Componiamo il testo dell'e-mail includendo il tracking
                soggetto = f"Il tuo ordine #{self.id} è in viaggio! 📦"
                messaggio = (
                    f"Ciao {self.nome},\n\n"
                    f"Grandi notizie! Il tuo ordine #{self.id} è stato spedito e sta arrivando a {self.citta}.\n"
                    f"{info_tracking}\n\n"
                    f"Grazie per aver acquistato da noi!"
                )
                
                email_mittente = settings.DEFAULT_FROM_EMAIL if hasattr(settings, 'DEFAULT_FROM_EMAIL') else 'noreply@negozio.com'
                
                # 3. Invia l'e-mail
                send_mail(
                    soggetto,
                    messaggio,
                    email_mittente,
                    [self.email],
                    fail_silently=False,
                )
                print("📧 [EMAIL] Notifica inviata con successo!\n")

        super().save(*args, **kwargs)
class VoceOrdine(models.Model):
    ordine = models.ForeignKey(Ordine, related_name='voci', on_delete=models.CASCADE)
    prodotto = models.ForeignKey(Prodotto, on_delete=models.CASCADE)
    quantita = models.IntegerField(default=1)
    prezzo = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        verbose_name = "Voce d'Ordine"
        verbose_name_plural = "Voci d'Ordine"

    def __str__(self):
        return f"{self.quantita} x {self.prodotto.nome} (Ordine {self.ordine.id})"
    
#Recensione del prodotto definita come modello Django, collegata al prodotto e all'utente che l'ha scritta. Include voto, commento e data di creazione. 
class Recensione(models.Model):
    prodotto = models.ForeignKey(Prodotto, on_delete=models.CASCADE, related_name='recensioni')
    utente = models.ForeignKey(User, on_delete=models.CASCADE)
    voto = models.IntegerField(choices=[(1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5')])
    commento = models.TextField()
    data = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Recensione di {self.utente.username} su {self.prodotto.nome}"
    
class NewsletterIscritto(models.Model):
    email = models.EmailField(unique=True)
    data_iscrizione = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.email
    


   