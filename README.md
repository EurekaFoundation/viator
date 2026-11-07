# Viator

**Viator** (in latino "viaggiatore") è un browser web libero e open source, leggero e rispettoso della privacy, scritto in Python con PySide6 e Qt WebEngine.

> Versione 0.3.0 — prototipo in sviluppo.

## Funzioni

- Interfaccia moderna con schede in alto, tema **chiaro e scuro** (automatico, segue il sistema)
- Pagina "nuova scheda" con ricerca, **siti fissati** e siti più visitati
- **Permessi dei siti** (fotocamera, microfono, schermo, posizione, notifiche) con «Consenti / Blocca», ricordati per ogni sito
- Videochiamate con condivisione dello schermo
- **Ripristino delle schede** all'avvio (si caricano solo quando le apri)
- **Visualizzatore PDF** integrato, salvataggio delle pagine come PDF e stampa
- **Menu del tasto destro** completo in italiano, con «Ispeziona» per gli strumenti da sviluppatore
- Scudo nella barra che mostra quanti tracker sono stati bloccati nella pagina
- Schede multiple (spostabili, chiudibili, apertura dei link in nuove schede)
- Barra degli indirizzi unica per indirizzi e ricerche, con suggerimenti da segnalibri e cronologia
- Motore di ricerca a scelta (DuckDuckGo predefinito, Startpage, Ecosia, Qwant, Google, Bing)
- Segnalibri e cronologia salvati **solo sul tuo computer** (database SQLite)
- Gestore dei download
- Finestra di navigazione privata: nessun dato salvato
- Blocco integrato di tracker e pubblicità, ampliabile con liste esterne
- Trova nella pagina, zoom, schermo intero (anche per i video)
- Eliminazione di cookie e cache dalle impostazioni

## Installazione

Gli installatori pronti si trovano nella pagina **Releases** del progetto su GitHub:

- **Windows**: `Viator-x.y.z-Windows-setup.exe` — doppio clic e avanti. Dopo l'installazione Viator compare anche in *Impostazioni → App → App predefinite*, se vuoi usarlo come browser principale.
- **macOS**: `Viator-x.y.z-macOS-….dmg` — trascina Viator in Applicazioni. Al primo avvio: clic destro sull'app → **Apri** (l'app non è firmata con un certificato Apple).
- **Linux**: `Viator-x.y.z-Linux-x86_64.AppImage` — rendilo eseguibile (clic destro → Proprietà → Permessi) e fai doppio clic.

## Avvio (per sviluppatori)

Serve Python 3.9 o superiore.

```bash
python -m pip install -r requirements.txt
python main.py
```

Si può anche aprire direttamente un indirizzo: `python main.py https://www.wikipedia.org`

## Creare gli installatori

**In automatico su GitHub (consigliato).** Il file `.github/workflows/build.yml` crea gli installatori per Windows, macOS (Intel e Apple) e Linux. Basta pubblicare un tag di versione:

```bash
git tag v0.3.0
git push origin v0.3.0
```

Dopo qualche minuto gli installatori compaiono nella pagina *Releases*. Si può avviare anche a mano dalla scheda **Actions**.

**Sul proprio computer.**

| Sistema | Comando | Requisiti |
|---|---|---|
| Windows | doppio clic su `packaging\windows\build_windows.bat` | Python e [Inno Setup 6](https://jrsoftware.org/isdl.php) |
| macOS | `bash packaging/macos/build_macos.sh` | Python (solo su un Mac) |
| Linux | `bash packaging/linux/build_linux.sh` | Python |

Gli installatori finiscono nella cartella `dist/installer`. Le icone in `assets/` si rigenerano con `python tools/make_icons.py`.

## Scorciatoie da tastiera

| Azione | Tasti |
|---|---|
| Nuova scheda / chiudi scheda | Ctrl+T / Ctrl+W |
| Nuova finestra / finestra privata | Ctrl+N / Ctrl+Shift+P |
| Barra degli indirizzi | Ctrl+L, F6 |
| Ricarica | F5, Ctrl+R |
| Indietro / avanti | Alt+← / Alt+→ |
| Aggiungi segnalibro | Ctrl+D |
| Segnalibri / cronologia / download | Ctrl+Shift+O / Ctrl+H / Ctrl+J |
| Trova nella pagina | Ctrl+F |
| Salva come PDF / stampa | Ctrl+Shift+S / Ctrl+P |
| Zoom | Ctrl+ + / Ctrl+ - / Ctrl+0 |
| Schermo intero | F11 |
| Cambia scheda | Ctrl+Tab / Ctrl+Shift+Tab |
| Chiudi scheda | clic con la rotella sulla scheda |
| Nuova scheda | doppio clic nello spazio vuoto della barra schede |

## Blocco tracker

Oltre alla lista integrata, Viator legge il file `blocklist.txt` nella sua cartella dati (si apre dalle Impostazioni con «Apri cartella dei dati»). Il file accetta un dominio per riga oppure il formato hosts (`0.0.0.0 dominio.com`), quindi funziona con le liste pubbliche più diffuse. Dopo averlo modificato, riavvia Viator.

## Struttura del codice

```
main.py              avvio
viator/app.py        applicazione e stato condiviso tra le finestre
viator/window.py     finestra principale, schede, barra indirizzi, menu
viator/dialogs.py    segnalibri, cronologia, impostazioni
viator/downloads.py  gestore dei download
viator/adblock.py    blocco di tracker e pubblicità
viator/storage.py    database di segnalibri e cronologia
viator/config.py     impostazioni e percorsi
viator/theme.py      colori, icone e foglio di stile (chiaro/scuro)
viator/startpage.py  pagina "nuova scheda" (viator://home) e siti fissati
viator/permissions.py permessi dei siti e condivisione schermo
viator/contextmenu.py menu del tasto destro
assets/              icone dell'applicazione
packaging/           script per gli installatori (windows, macos, linux)
tools/               icone e dati di versione per gli installatori
```

## Prossimi passi

- Modalità lettura e tema scuro forzato per i siti
- Barra dei segnalibri e importazione da Firefox/Chrome
- Assistente IA locale (riassunto e domande sulla pagina)
- Una sola istanza aperta: i link da altri programmi si aprono come nuova scheda
- Aggiornamento automatico delle liste di blocco

## Licenza

GPL-3.0 (da confermare: aggiungere il file `LICENSE` con il testo ufficiale).
