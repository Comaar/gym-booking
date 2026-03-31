# Gym Booking Automation - OndeChiare

Sistema autonomo per prenotare **automaticamente** lezioni in palestra su **inforyou.teamsystem.com/ondechiare**.

## 🎯 Caratteristiche

- ✅ **Esecuzione automatica giornaliera** tramite launchd (macOS)
- ✅ Autenticazione automatica con gestione token
- ✅ Pianificazione settimanale personalizzabile
- ✅ Timezone-aware (Europe/Rome)
- ✅ Skip automatico weekend/giorni configurati
- ✅ Retry automatico in caso di errori temporanei
- ✅ Token app-token valido **1 anno**
- ✅ Token auth-token rigenerato automaticamente
- ✅ Logging completo di tutte le operazioni

## 📋 Requisiti

- macOS (per launchd)
- Python 3.9+
- Connessione internet attiva alle 00:01 ogni giorno

## 🚀 Setup Completo

### 1. Installa dipendenze

```bash
cd /Users/Marco/Documents/GitHub_Projects/n8n_booking
pip install -r requirements.txt
```

### 2. Configura le credenziali

Assicurati che `.env` contenga:

```env
# Credenziali TeamSystem
TS_BASE_URL=https://inforyou.teamsystem.com/ondechiare
TS_COMPANY_ID=2
TS_LOGIN=tuo_username
TS_PASSWORD=tua_password

# CRITICO: URL base del tenant
TS_IYESURL=http://app.ondechiare.it:65432/

# Token app (vedi sotto come ottenerlo)
TS_APP_TOKEN=your_app_token_here
```

### 3. Ottieni l'app-token dal browser

**L'app-token è necessario per l'autenticazione e dura 1 anno.**

1. Apri Chrome e vai su: https://inforyou.teamsystem.com/ondechiare/planning/2
2. Fai login con le tue credenziali
3. Apri DevTools (F12) → **Application** → **Cookies** → `inforyou.teamsystem.com`
4. Trova il cookie `app-token` e copia il suo **Value**
5. Incolla il valore in `.env` come `TS_APP_TOKEN=...`

### 4. Configura il tuo piano settimanale

Modifica in `app.py` la sezione `WEEKLY_PLAN`:

```python
WEEKLY_PLAN = {
    0: {"IDLesson": 11414, "start": "19:40", "end": "20:30", "BookingID": 2598},  # Lunedì
    1: {"IDLesson": 11406, "start": "18:50", "end": "19:40", "BookingID": 80},    # Martedì
    2: {"IDLesson": 11407, "start": "18:50", "end": "19:40", "BookingID": 80},    # Mercoledì
    3: {"IDLesson": 11415, "start": "19:40", "end": "20:30", "BookingID": 2598},  # Giovedì
}
SKIP_WEEKDAYS = {4, 5, 6}  # Venerdì, Sabato, Domenica
```

**Come trovare IDLesson e BookingID:**
- Vai sul sito e prenota manualmente una lezione
- Apri DevTools → Network → Filtra "book"
- Guarda il payload JSON della richiesta
- Copia `IDLesson` e `BookingID` dalla richiesta

### 5. Installa il servizio automatico (launchd)

```bash
# Copia il file di configurazione
cp com.marco.gymbooking.plist ~/Library/LaunchAgents/

# Carica il servizio
launchctl load ~/Library/LaunchAgents/com.marco.gymbooking.plist

# Verifica che sia attivo
launchctl list | grep gymbooking
```

Se vedi una riga come `- 0 com.marco.gymbooking`, il servizio è attivo! ✅

## 🤖 Funzionamento Automatico

### Come funziona

1. **Ogni giorno alle 00:01** il sistema si attiva automaticamente
2. Verifica il giorno della settimana
3. Se c'è una lezione configurata, prenota per la **settimana successiva** (+7 giorni)
4. Salva tutto nel log `gym_booking.log`
5. Si spegne automaticamente

### Esempio timeline

- **Lunedì 4 Feb ore 00:01** → Prenota per Lunedì 11 Feb
- **Martedì 5 Feb ore 00:01** → Prenota per Martedì 12 Feb
- **Venerdì-Domenica** → Non fa nulla (configurato in SKIP_WEEKDAYS)

### Controllo stato servizio

```bash
# Verifica se è carico
launchctl list | grep gymbooking

# Vedi configurazione completa
launchctl print gui/$(id -u)/com.marco.gymbooking

# Ricarica se necessario
launchctl unload ~/Library/LaunchAgents/com.marco.gymbooking.plist
launchctl load ~/Library/LaunchAgents/com.marco.gymbooking.plist
```

## 🎮 Utilizzo Manuale (opzionale)

Se vuoi eseguire manualmente lo script (es. per recuperare un giorno perso):

```bash
cd /Users/Marco/Documents/GitHub_Projects/n8n_booking
python3 run_booking.py
```

Lo script:
- Controlla che oggi sia un giorno con lezione configurata
- Prenota per la settimana successiva
- Logga tutto in `gym_booking.log`

### Verifica pianificazione

Per vedere quale lezione sarà prenotata domani:

```bash
python3 check_schedule.py
```

Output esempio:
```
Today: Wednesday 2026-02-04 (weekday 2)
Tomorrow: Thursday 2026-02-05 (weekday 3)

Weekly Schedule:
  Mon: Lesson 11414 at 19:40 (BookingID: 2598)
  Tue: Lesson 11406 at 18:50 (BookingID: 80)
  Wed: Lesson 11407 at 18:50 (BookingID: 80)
  Thu: Lesson 11415 at 19:40 (BookingID: 2598)

Skipped days: Fri, Sat, Sun

✅ Tomorrow at 00:01 will book: Lesson 11415 for 2026-02-12 at 19:40
```

## 📁 Struttura File

```
n8n_booking/
├── app.py                          # Core: logica booking e autenticazione
├── run_booking.py                  # Script eseguito da launchd ogni giorno
├── check_schedule.py               # Utility: verifica pianificazione
├── com.marco.gymbooking.plist      # Configurazione launchd (da installare)
├── requirements.txt                # Dipendenze Python
├── .env                           # Configurazione credenziali (NON committare!)
├── .env.example                   # Template configurazione
├── session_cookies.json           # Cookies di sessione (generato automaticamente)
├── gym_booking.log                # Log di tutte le esecuzioni
├── .gitignore                     # File da ignorare in git
└── README.md                      # Questa documentazione
```

## 📊 Log e Monitoraggio

### Visualizza log in tempo reale

```bash
tail -f /Users/Marco/Documents/GitHub_Projects/n8n_booking/gym_booking.log
```

### Esempio log di successo

```
2026-02-04 00:01:00,123 [INFO] ============================================================
2026-02-04 00:01:00,124 [INFO] 🚀 SCRIPT STARTED - 2026-02-04 00:01:00 CET
2026-02-04 00:01:00,124 [INFO] ============================================================
2026-02-04 00:01:00,125 [INFO] 📅 Weekday: Wednesday (2)
2026-02-04 00:01:00,125 [INFO] 📍 Working directory: /Users/Marco/Documents/GitHub_Projects/n8n_booking
2026-02-04 00:01:00,125 [INFO] 🔧 Python: /Library/Developer/CommandLineTools/usr/bin/python3
2026-02-04 00:01:00,125 [INFO] ⏰ Execution time: 00:01:00
2026-02-04 00:01:00,126 [INFO] 🆔 Process ID: 12345
2026-02-04 00:01:00,126 [INFO] 
2026-02-04 00:01:00,126 [INFO] [STEP 1] Building booking payload...
2026-02-04 00:01:00,127 [INFO] ✓ Payload created
2026-02-04 00:01:00,127 [INFO] 📋 Target booking: 2026-02-11T18:50:00 - 2026-02-11T19:40:00
2026-02-04 00:01:00,127 [INFO]    IDLesson: 11407, BookingID: 80
2026-02-04 00:01:00,128 [INFO] 
2026-02-04 00:01:00,128 [INFO] [STEP 2] Authenticating...
2026-02-04 00:01:00,129 [INFO] Loaded 6 cookies
2026-02-04 00:01:00,129 [INFO] ✓ Authentication successful
2026-02-04 00:01:00,129 [INFO] 
2026-02-04 00:01:00,130 [INFO] [STEP 3] Executing booking...
2026-02-04 00:01:00,131 [INFO] Loaded 6 cookies
2026-02-04 00:01:00,131 [INFO] Booking: 11407 at 2026-02-11T18:50:00
2026-02-04 00:01:02,456 [INFO] ✅ Booking successful! (attempt 1)
2026-02-04 00:01:02,456 [INFO] ============================================================
```

### Sistema di retry automatico

Se la prenotazione fallisce (es. problemi di rete temporanei), il sistema:
1. Riprova automaticamente fino a **3 volte**
2. Aspetta 2 secondi tra un tentativo e l'altro
3. Se l'errore è "prenotazione doppia", non riprova (è già prenotato)

## 🔧 Manutenzione

### Token app-token scaduto?

L'app-token dura **1 anno**. Quando scade (gennaio 2027):

1. Apri browser → DevTools → Cookies
2. Copia nuovo valore di `app-token`
3. Aggiorna `TS_APP_TOKEN` in `.env`
4. **Non serve riavviare nulla**, verrà usato automaticamente

### Aggiungere una nuova classe

1. Vai sul sito e ispeziona la richiesta di prenotazione
2. Copia `IDLesson` e `BookingID`
3. Aggiungi in `WEEKLY_PLAN` dentro `app.py`:
   ```python
   4: {"IDLesson": 12345, "start": "12:00", "end": "12:50", "BookingID": 9999},  # Venerdì
   ```
4. Rimuovi `4` da `SKIP_WEEKDAYS` se presente

### Disattivare temporaneamente il sistema

```bash
# Disattiva
launchctl unload ~/Library/LaunchAgents/com.marco.gymbooking.plist

# Riattiva
launchctl load ~/Library/LaunchAgents/com.marco.gymbooking.plist
```

### Rimuovere completamente il sistema

```bash
# Disattiva servizio
launchctl unload ~/Library/LaunchAgents/com.marco.gymbooking.plist

# Rimuovi file di configurazione
rm ~/Library/LaunchAgents/com.marco.gymbooking.plist

# (Opzionale) Rimuovi cartella progetto
rm -rf /Users/Marco/Documents/GitHub_Projects/n8n_booking
```

## 🔧 Manutenzione

### Token app-token scaduto?

L'app-token dura **1 anno**. Quando scade (gennaio 2027):

1. Apri browser → DevTools → Cookies
2. Copia nuovo valore di `app-token`
3. Aggiorna `TS_APP_TOKEN` in `.env`
4. Riavvia il server

### Aggiungere una nuova classe

1. Vai sul sito e ispeziona la richiesta di prenotazione
2. Copia `IDLesson` e `BookingID`
3. Aggiungi in `WEEKLY_PLAN`:
   ```python
   2: {"IDLesson": 12345, "start": "12:00", "end": "12:50", "BookingID": 9999},
   ```
4. Riavvia il server

## 🐛 Troubleshooting

### Il sistema non si è attivato alle 00:01

```bash
# 1. Verifica che il servizio sia caricato
launchctl list | grep gymbooking

# 2. Controlla exit code (deve essere 0 o -)
launchctl print gui/$(id -u)/com.marco.gymbooking | grep "last exit code"

# 3. Se exit code è 78 o altro errore, ricarica:
launchctl unload ~/Library/LaunchAgents/com.marco.gymbooking.plist
cp /Users/Marco/Documents/GitHub_Projects/n8n_booking/com.marco.gymbooking.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.marco.gymbooking.plist

# 4. Esegui manualmente per recuperare:
python3 /Users/Marco/Documents/GitHub_Projects/n8n_booking/run_booking.py
```

### "TS_APP_TOKEN must be set"
Hai dimenticato di aggiungere l'app-token in `.env`. Vedi sezione "Ottieni l'app-token dal browser".

### "Login failed: 401 Unauthorized"
L'app-token è scaduto o non valido. Ottieni un nuovo token dal browser.

### "Prenotazione non consentita"
- La classe potrebbe non essere ancora prenotabile (troppo presto)
- Hai già una prenotazione per quella fascia oraria
- La classe è al completo

### "Prenotazione doppia"
Hai già prenotato questa lezione. Non è un errore critico.

### Il log non si aggiorna
```bash
# Verifica permessi
ls -la /Users/Marco/Documents/GitHub_Projects/n8n_booking/gym_booking.log

# Se necessario, ricrea il file
rm gym_booking.log
touch gym_booking.log
```

## 📊 Variabili Ambiente (.env)

| Variabile | Descrizione | Richiesto |
|-----------|-------------|-----------|
| `TS_BASE_URL` | URL base TeamSystem | ✅ |
| `TS_COMPANY_ID` | ID della tua palestra | ✅ |
| `TS_LOGIN` | Username | ✅ |
| `TS_PASSWORD` | Password | ✅ |
| `TS_IYESURL` | URL tenant (fisso) | ✅ |
| `TS_APP_TOKEN` | Token dal browser (valido 1 anno) | ✅ |
| `APP_TIMEZONE` | Timezone (default: Europe/Rome) | ❌ |
| `HTTP_TIMEOUT_SECONDS` | Timeout richieste (default: 15) | ❌ |
| `COOKIE_FILE` | File cookies (default: ./session_cookies.json) | ❌ |
| `LOG_LEVEL` | Livello log (default: INFO) | ❌ |

## 🔒 Sicurezza

- **NON committare mai `.env`** con le tue credenziali
- L'app-token è sensibile quanto una password
- I cookies di sessione sono salvati localmente in `session_cookies.json`
- Il Mac deve essere sveglio alle 00:01 per l'esecuzione (o usa pmset per impedire lo sleep)

## 💡 Tips & Best Practices

- **Backup token**: Salva una copia dell'app-token in un posto sicuro (scade tra 1 anno)
- **Monitoring**: Controlla il log ogni tanto per verificare che tutto funzioni
- **Test manuale**: Usa `python3 run_booking.py` per testare prima dell'attivazione automatica
- **Verifica pianificazione**: Usa `python3 check_schedule.py` per vedere cosa prenoterà domani
- **Mac sempre acceso**: Il Mac deve essere acceso e sveglio alle 00:01 (considera Energy Saver settings)

## ❓ FAQ

**Q: Il Mac deve rimanere sempre acceso?**  
A: Il Mac deve essere acceso e sveglio alle 00:01 ogni giorno. Puoi configurarlo per accendersi automaticamente o impedire lo sleep notturno.

**Q: Cosa succede se il Mac è spento alle 00:01?**  
A: La prenotazione per quel giorno viene saltata. Puoi eseguirla manualmente con `python3 run_booking.py`.

**Q: Posso cambiare l'orario di esecuzione?**  
A: Sì, modifica `<integer>0</integer>` e `<integer>1</integer>` nel file `com.marco.gymbooking.plist` (Hour e Minute), poi ricarica il servizio.

**Q: Il sistema funziona senza browser aperto?**  
A: Sì, è completamente autonomo dopo aver ottenuto l'app-token iniziale.

**Q: Posso prenotare più lezioni lo stesso giorno?**  
A: No, il sistema prenota una sola lezione per giorno come configurato in `WEEKLY_PLAN`.

**Q: Cosa succede se la prenotazione fallisce?**  
A: Il sistema riprova automaticamente fino a 3 volte. Se continua a fallire, controlla il log.

## 🎯 Funzionamento Dettagliato

### Flusso completo

1. **00:01** - launchd avvia `run_booking.py`
2. **Verifica giorno** - Controlla se è configurato in `WEEKLY_PLAN`
3. **Skip check** - Se è in `SKIP_WEEKDAYS`, esce
4. **Build payload** - Crea richiesta per lezione della settimana prossima
5. **Autenticazione** - Carica cookies o fa login
6. **Booking** - Invia richiesta di prenotazione (max 3 tentativi)
7. **Log** - Salva risultato in `gym_booking.log`
8. **Exit** - Processo termina pulitamente

### Gestione errori avanzata

- **Retry automatico**: 3 tentativi con pausa di 2 secondi
- **Smart skip**: Non riprova se "prenotazione doppia" (già fatto)
- **Clean exit**: Processo termina sempre correttamente (exit code 0)
- **Cookie persistence**: Mantiene sessione tra esecuzioni

## 🔄 Aggiornamenti Sistema

### Aggiornare il codice

```bash
cd /Users/Marco/Documents/GitHub_Projects/n8n_booking
# Modifica i file che vuoi...
# Poi ricarica il servizio:
launchctl unload ~/Library/LaunchAgents/com.marco.gymbooking.plist
launchctl load ~/Library/LaunchAgents/com.marco.gymbooking.plist
```

### Modificare configurazione launchd

1. Modifica `com.marco.gymbooking.plist`
2. Copia in `~/Library/LaunchAgents/`
3. Ricarica servizio come sopra

## 📄 Licenza

Uso personale. Non per scopi commerciali.

---

**✅ Sistema completamente automatico! Zero manutenzione per 1 anno! 🎉**
