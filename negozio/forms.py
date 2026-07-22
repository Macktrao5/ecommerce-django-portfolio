# from django import forms
# from .models import Prodotto
# from .models import Ordine

# class ProdottoForm(forms.ModelForm):
#     class Meta:
#         model = Prodotto
#         # I campi del database che l'utente deve compilare nel modulo
#         fields = ['nome', 'descrizione', 'prezzo']
        
#         # Aggiungiamo un po' di stile Bootstrap ai campi del form
#         widgets = {
#             'nome': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nome del prodotto'}),
#             'descrizione': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Inserisci una descrizione...'}),
#             'prezzo': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '0.00', 'step': '0.01'}),
#         }   
# class OrdineForm(forms.ModelForm):
#     class Meta:
#         model = Ordine
#         # Chiediamo solo i dati di spedizione; lo stato dell'ordine sarà gestito dall'admin
#         fields = ['nome', 'cognome', 'email', 'indirizzo', 'citta', 'cap']
#         widgets = {
#             'nome': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nome'}),
#             'cognome': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Cognome'}),
#             'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'La tua email'}),
#             'indirizzo': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Via/Piazza e Numero Civico'}),
#             'citta': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Città'}),
#             'cap': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'CAP'}),
#         }


from django import forms
from .models import Ordine, Prodotto

# Form per la creazione dell'Ordine con i dati reali del cliente
class OrdineForm(forms.ModelForm):
    class Meta:
        model = Ordine
        fields = ['nome', 'cognome', 'email', 'indirizzo', 'citta', 'cap']
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Inserisci il tuo nome'}),
            'cognome': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Inserisci il tuo cognome'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'esempio@email.com'}),
            'indirizzo': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Via/Piazza e Numero Civico'}),
            'citta': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Es. Barletta'}),
            'cap': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Es. 76123'}),
        }

# Form per la creazione del Prodotto (quello che avevi già)
class ProdottoForm(forms.ModelForm):
    class Meta:
        model = Prodotto
        fields = ['nome', 'descrizione', 'prezzo', 'immagine']