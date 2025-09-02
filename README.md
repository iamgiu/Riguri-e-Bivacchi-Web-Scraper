# 🏔️ Rifugi e Bivacchi Scraper

**Estrattore di rifugi e bivacchi italiani da escursionismo.it**

Web scraper Python che raccoglie automaticamente informazioni dettagliate su rifugi e bivacchi di montagna dalle regioni italiane, con l'obiettivo di ottenere un dataset completo e strutturato per ogni regione.

## 📋 Dati Estratti

Per ogni rifugio/bivacco viene raccolto:

### Informazioni Base
- **Nome** e **Tipo** (Rifugio/Bivacco)
- **Quota altitudine** e **Ubicazione geografica**
- **Regione**, **Valle**, **Area montuosa**
- **URL della pagina** e **Immagine principale**

### Informazioni Operative
- **Periodo di apertura**
- **Numero posti letto**
- **Proprietà** e **Gestore**
- **Servizi disponibili** (riscaldamento, docce, ristorante, ecc.)

### Contatti e Accesso
- **Telefono**, **Email**, **Sito web**
- **Coordinate GPS** (latitudine/longitudine)
- **Informazioni di accesso** (percorso, difficoltà, tempo)

### Servizi Tracciati
- 🔥 Riscaldamento
- 🚽 WC
- 🚿 Docce
- 🍽️ Ristorante
- 👨‍🍳 Possibilità di cucinare
- 💡 Luce elettrica
- 💳 Carte di credito
- 🎒 Sconti associati CAI

### Configurazione Parametri
```python
# Nel file main(), modifica questi parametri:
MAX_RIFUGI = 300        # Limite totale rifugi
DELAY_SECONDS = 2       # Pausa tra richieste (rispetta il server!)
MAX_RIFUGI_PER_REGIONE = 30  # Rifugi per regione
```

### Esempio Output Console
```
🚀 AVVIO SCRAPING RIFUGI - VERSIONE COMPLETA
============================================================
🎯 Obiettivo: 30 rifugi per ogni regione italiana
📊 Limite totale: 300 rifugi
⏱️ Pausa tra richieste: 2 secondi
🌐 Fonte: https://www.escursionismo.it

📊 STATISTICHE CORRENTI:
   Piemonte             [████████░░] 25/30 (83%)
   Valle D'Aosta        [██████████] 30/30 (100%)
   Lombardia            [█████░░░░░] 15/30 (50%)
   ...
```

## Output Files

### `Rifugi_bivacchi.json`
File principale con struttura:
```json
{
  "metadata": {
    "generated_at": "2024-01-15 14:30:00",
    "total_rifugi": 285,
    "total_regioni": 15,
    "regioni_statistiche": {
      "piemonte": 30,
      "valle d'aosta": 30,
      "lombardia": 28
    },
    "source": "escursionismo.it",
    "scraper_version": "2.0"
  },
  "rifugi": [
    {
      "url": "https://www.escursionismo.it/rifugi-bivacchi/rifugio-esempio/",
      "nome": "Rifugio Esempio",
      "quota_altitudine": "2450m",
      "luogo": "Val d'Esempio, Alpi Graie, Piemonte, Italia",
      "tipo": "Rifugio",
      "proprietà": "CAI",
      "nazione": "Italia",
      "regione": "Piemonte",
      "valle": "Val d'Esempio",
      "area_montuosa": "Alpi Graie",
      "periodo_apertura": "Giugno - Settembre",
      "posti_letto": "45",
      "coordinate_lat": "45.123456",
      "coordinate_lon": "7.654321",
      "servizi": [
        "🔥 Riscaldamento",
        "🚿 Docce",
        "🍽️ Ristorante"
      ],
      "accesso": {
        "localita_partenza": "Piano del Nivolet",
        "dislivello": "350m",
        "tempo_percorrenza": "2h 30min",
        "difficolta": "E",
        "descrizione": "Sentiero ben segnato..."
      },
      "telefono": "+39 0123 456789",
      "email": "info@rifugioesempio.it",
      "sito_web": "https://www.rifugioesempio.it",
      "immagine_url": "https://www.escursionismo.it/images/rifugio-esempio.jpg",
      "gestore": "Mario Rossi",
      "altre_dotazioni": "Biblioteca, Sala conferenze"
    }
  ]
}
```

## 🗺️ Regioni Supportate

Il scraper riconosce e categorizza automaticamente rifugi da tutte le regioni italiane:

**Nord**: Piemonte, Valle d'Aosta, Lombardia, Trentino-Alto Adige, Veneto, Friuli-Venezia Giulia, Liguria, Emilia-Romagna

**Centro**: Toscana, Umbria, Marche, Lazio

**Sud e Isole**: Abruzzo, Molise, Campania, Puglia, Basilicata, Calabria, Sicilia, Sardegna

## 📊 Statistiche di Esempio

```
🎯 STATISTICHE FINALI:
============================================================
📊 TOTALI:
   • Rifugi raccolti: 285
   • Regioni coperte: 15
   • Media per regione: 19.0

🗺️ DETTAGLIO PER REGIONE:
   Piemonte             30/30 rifugi (100%) ✅ COMPLETO
   Valle D'Aosta        30/30 rifugi (100%) ✅ COMPLETO
   Lombardia            28/30 rifugi (93%)  ⏳ In corso
   Trentino-Alto Adige  30/30 rifugi (100%) ✅ COMPLETO
   ...

🏔️ TIPOLOGIE:
   Rifugio         245 (86.0%)
   Bivacco          35 (12.3%)
   Non specificato   5 (1.7%)

📋 COMPLETEZZA DATI:
   Con servizi:    267/285 (93.7%)
   Con telefono:   198/285 (69.5%)
   Con email:      156/285 (54.7%)
   Con coordinate: 234/285 (82.1%)
```

## ⚙️ Personalizzazione

### Modifica Target per Regione
```python
self.MAX_RIFUGI_PER_REGIONE = 50  # Aumenta a 50 per regione
```

### Aggiungere Nuovi Servizi
```python
self.servizi_mapping = {
    'wifi': '📶 WiFi',
    'parking': '🅿️ Parcheggio',
    # Aggiungi i tuoi servizi...
}
```

### Filtri Personalizzati
```python
def custom_filter(self, rifugio_info):
    # Esempio: solo rifugi sopra i 2000m
    quota = rifugio_info.quota_altitudine
    if quota and 'm' in quota:
        altitude = int(re.findall(r'\d+', quota)[0])
        return altitude >= 2000
    return True
```

### Risoluzione Problemi

**Errore "Nessun URL trovato":**
```bash
# Verifica connessione
curl -I https://www.escursionismo.it/rifugi-bivacchi/
```

**Timeout frequenti:**
```python
# Aumenta il delay
DELAY_SECONDS = 5
```

**Dati incompleti:**
```python
# Verifica i selettori CSS nel codice
# Potrebbero essere cambiati nel sito
```
