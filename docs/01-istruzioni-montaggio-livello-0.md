# ScooterLab — Istruzioni di Montaggio (Livello 0)

```text
SCOOTERLAB — ISTRUZIONI DI MONTAGGIO

SYM Symphony ST 200i 2019 — Livello 0

============================================================


Livello 0: centralina, IMU e GPS. Nessuna carenatura smontata.

Alla fine di queste istruzioni esci a fare un giro e trovi il report

ad aspettarti.


FASI

  A   Banco             \~2 ore   software e primo assemblaggio

  B   Rilievo del vano  \~30 min  misure e foto sul TUO mezzo

  C   Alimentazione     \~1 ora   buck tarato, positivo sottochiave

  C2  Montaggio         \~1 ora   scatola, IMU, GPS, prova su strada

  D   Primo giro        \~40 min  calibrazione, registrazione, report


SERVE: ESP32 DevKit, modulo microSD + scheda 32 GB, MPU-6050, modulo GPS,

convertitore buck 12->5 V, fusibile 1 A con portafusibile, scatola IP65,

cavo, fascette, multimetro.

Tempo totale circa 5 ore, spezzabili in due serate (fine fase A e un

punto di arresto naturale).



============================================================

FASE A — BANCO  (\~2 ore)

============================================================


--- 1. Installa gli strumenti sul PC ---

Arduino IDE, poi File > Preferenze > URL aggiuntive Gestore schede:

  https://espressif.github.io/arduino-esp32/package\_esp32\_index.json

Poi Strumenti > Scheda > Gestore schede > cerca "esp32" > installa.

Da Gestore librerie installa: OneWire, DallasTemperature.

Python sul PC:

  pip install numpy pandas scipy matplotlib


VERIFICA: in Strumenti > Scheda compare "ESP32 Dev Module".



--- 2. Prova la pipeline prima di avere l'hardware ---

Serve a sapere che il software funziona: cosi se dopo qualcosa non va,

sai che il problema e nel cablaggio.

  cd tools

  python make\_test\_session.py --level0

  python analyze.py sessions/sess00002.slab --label "prova"


VERIFICA: si apre tools/reports/sess00002.html con velocita, angolo di

piega, comfort e il tempo 0-50. I riquadri di rpm e sospensioni mostrano

un trattino: e corretto, a questo livello non sono misurati.



--- 3. Cabla ESP32, microSD, IMU e GPS su breadboard ---

  MPU-6050 VCC  ->  3V3

  MPU-6050 GND  ->  GND

  MPU-6050 SDA  ->  GPIO21

  MPU-6050 SCL  ->  GPIO22

  MPU-6050 AD0  ->  GND          (indirizzo 0x68)

  microSD  VCC  ->  5V (VIN)     NON 3V3: in scrittura assorbe troppo

  microSD  GND  ->  GND

  microSD  CS   ->  GPIO5

  microSD  SCK  ->  GPIO18

  microSD  MISO ->  GPIO19

  microSD  MOSI ->  GPIO23

  GPS      VCC  ->  3V3          (alcuni moduli vogliono 5 V: verifica)

  GPS      GND  ->  GND

  GPS      TX   ->  GPIO16

  GPS      RX   ->  GPIO17


Cavi SPI della SD corti, sotto i 10 cm.


ATTENZIONE: TX del GPS va su RX dell'ESP32 e viceversa. E l'errore numero

uno: se il GPS non risponde, prima di tutto inverti questi due.



--- 4. Configura e carica il firmware ---

Apri firmware/scooterlab\_logger/scooterlab\_logger.ino e modifica solo

queste righe in testa:

  \#define BUILD\_LEVEL 0            // gia cosi: livello 0

  HOME\_SSID  = "il-tuo-wifi";

  HOME\_PASS  = "la-tua-password";

  INGEST\_URL = "http://192.168.1.50:8500/upload";   // IP del tuo PC


L'IP del PC: ipconfig (Windows) o ip addr (Mac/Linux). FISSALO NEL ROUTER

(DHCP reservation), altrimenti un giorno cambia e gli upload si fermano.

Scheda: ESP32 Dev Module. Carica.


VERIFICA: Monitor Seriale a 115200 baud, devi leggere in ordine:

  IMU1:1 IMU2:0

  Livello di montaggio: 0

  Calibrazione gyro: NON muovere...

  Sessione /sess00001 aperta

IMU1:1 conferma che l'IMU risponde. IMU2:0 e corretto: la seconda non c'e.


SE LEGGI "ERRORE SD": alimentazione del modulo (deve stare sul 5 V), cavi

troppo lunghi, o scheda non formattata FAT32.



--- 5. Collaudo completo sulla scrivania ---

Con l'ESP32 alimentato via USB e LONTANO dal Wi-Fi di casa, lascialo

registrare 2 minuti muovendo e inclinando la breadboard a mano. Poi porta

il GPS vicino a una finestra e aspetta il fix.

Sul PC:  cd tools && python ingest\_server.py

Ora riavvia l'ESP32 vicino al router: aggancia il Wi-Fi, carica le

sessioni e lancia l'analisi da solo.


VERIFICA: il terminale stampa "\[ingest\] ricevuto sess00001.slab" e in

tools/reports/ compare il report. SE L'ANGOLO DI PIEGA SEGUE LE

INCLINAZIONI CHE HAI FATTO A MANO, L'INTERA CATENA FUNZIONA.


>> PUNTO DI ARRESTO. Da qui il sistema e provato: il resto e solo meccanica.



============================================================

FASE B — RILIEVO DEL VANO  (\~30 min)

============================================================


Perche esiste questa fase: non conosco il vano sottosella del TUO mezzo.

Quanto e profondo, dove passa il fascio cavi, se hai la presa accessoria.

Nessun manuale lo dice con la precisione che serve. Il rilievo si fa una

volta, e da li in poi ogni scelta e informata invece che tentata.


--- 6. Apri, fotografa, misura ---

Solleva la sella e svuota il vano. Col telefono:

  1. Foto dall'alto del vano vuoto, tutto inquadrato

  2. Foto del fondo e delle pareti: cerca passacavi in gomma, fori

     preesistenti, fascette del costruttore, connettori liberi

  3. Foto sotto la sella aperta verso la cerniera: di solito li passa il

     fascio cavi del fanale posteriore


Tre misure da scrivere:

  - Lunghezza x larghezza del fondo -> ci sta la scatola distesa?

  - ALTEZZA LIBERA CON IL CASCO DENTRO -> il vincolo vero

  - Distanza dal punto piu vicino al motore -> zona calda


ATTENZIONE — IL VANO SI SCALDA. Il libretto del tuo mezzo avverte di non

riporre oggetti sensibili al calore: il motore irradia da sotto. Metti la

scatola nella parte ANTERIORE del vano, la piu lontana dal motore, e usa

PETG per la piastra (mai PLA). Carico massimo del vano: 10 kg.


VERIFICA: hai un posto dove la scatola sta distesa e ferma, il piu avanti

possibile, il casco entra ancora, e c'e un passaggio cavi verso il telaio.



--- 7. Batteria e fusibili ---

Sono TUTTI E DUE DENTRO IL VANO SOTTOSELLA, SOTTO IL CESTELLO. Il libretto

lo dice: "rimuovi il vano portaoggetti e accanto alla batteria vedrai la

scatola fusibili". Nessuna carenatura da smontare.

Il tuo mezzo monta 10 A x2, 15 A x1, 20 A x1. Fotografa la scatola aperta.


VERIFICA: hai il cestello fuori, vedi batteria e fusibili, hai fotografato

entrambe. Rimetti il cestello prima di proseguire.



============================================================

FASE C — ALIMENTAZIONE  (\~1 ora)

============================================================


>> PRIMA DI TOCCARE QUALUNQUE CAVO: STACCA IL MORSETTO NEGATIVO DELLA

   BATTERIA. Lo ricolleghi solo al passo 10.


--- 8. Tara il buck a 5,0 V — a banco, ESP32 SCOLLEGATO ---

Un convertitore nuovo esce regolato a caso: se lo colleghi cosi com'e, con

ogni probabilita manda 12 V nel pin da 5 e l'ESP32 muore in un secondo.

  1. Alimenta SOLO il buck con 12 V

  2. Multimetro su tensione continua, portata 20 V, sull'uscita

  3. Gira il trimmer un quarto di giro alla volta fino a 5,0 V (4,9-5,1)

  4. Togli alimentazione, rimisura a vuoto

  5. SOLO ORA collega l'uscita a VIN e GND dell'ESP32


VERIFICA: ridai i 12 V, il LED si accende, e l'uscita resta a 5,0 V SOTTO

CARICO. Se crolla sotto 4,7 V il buck e sottodimensionato o mal regolato.



--- 9. Cerca il positivo sottochiave ---

Serve un filo che porti 12 V SOLO A QUADRO ACCESO. Col positivo diretto

dalla batteria, la centralina resta accesa a mezzo spento e in una

settimana hai la batteria a terra.


Preparazione: ricollega temporaneamente il negativo, multimetro in continua

20 V, puntale nero su una vite del telaio SENZA VERNICE.


Candidati in ordine di preferenza:

  1. Presa accessoria / USB nel vano interno (gia sottochiave e protetta)

  2. Circuito luci di posizione

  3. Alimentazione del cruscotto


Il test, su ogni candidato:

  1. Quadro SPENTO   -> 0 V.  Se legge 12 V e un positivo diretto: scarta

  2. Quadro ACCESO   -> 12-12,8 V

  3. Motore ACCESO   -> 13,5-14,5 V  (conferma che sei a valle del

                        regolatore, sul ramo giusto)

  4. Muovi il manubrio da fermo a fermo: la tensione non deve saltare.

     Se salta, quel filo passa dove si flette e prima o poi si spezza.


NON TOCCARE MAI: cavi dell'accensione (bobina, candela), iniezione, pompa

benzina, e qualunque filo del circuito ABS.


VERIFICA: hai un filo che supera tutti e quattro i test. Segnalo con

nastro colorato.



--- 10. Collega, nell'ordine esatto ---

Stacca di nuovo il negativo. L'ordine non e casuale: il fusibile va

inserito per ULTIMO, cosi finche non hai finito il circuito e aperto.

  1. MASSA: capocorda ad occhiello sul negativo del buck -> vite del

     telaio senza vernice (raschiala se serve). Una massa su vernice e la

     causa numero uno dei dati sporchi negli ADC.

  2. POSITIVO: connettore a derivazione rapida di qualita (Posi-Tap) sul

     filo identificato -> portafusibile -> ingresso positivo del buck.

     Il portafusibile IL PIU VICINO POSSIBILE al punto di prelievo.

  3. ANSA DI SCARICO: 10-15 cm di cavo in piu con una curva verso il basso

     prima di entrare nella scatola. L'acqua gocciola invece di entrare.

  4. GUAINA su tutto il tratto lungo il telaio, fascette ogni 15 cm,

     lontano da parti mobili e dallo scarico.

  5. ORA inserisci il fusibile da 1 A e ricollega il negativo.


VERIFICA in tre tempi:

  - Quadro spento -> ESP32 spento, nessun LED

  - Quadro acceso -> LED acceso entro 3 secondi

  - Spegni e riaccendi TRE VOLTE: identico ogni volta. Se e incostante,

    il contatto sulla derivazione e incerto.



============================================================

FASE C2 — MONTAGGIO  (\~1 ora)

============================================================


--- 11. Chiudi l'elettronica nella scatola ---

Tutto cio che era a innesto va reso definitivo: SALDATO o su connettori

JST. I cavetti dupont saltano con le vibrazioni in una settimana, e ti

ritrovi a cercare un guasto che non e un guasto.

Se hai stampato 05\_piastra\_centralina: avvita ESP32 e modulo SD sulle

colonnine, poi fissa la piastra con biadesivo strutturale.

Fori dei cavi SUL LATO BASSO, sigillati con pressacavo o silicone neutro.


VERIFICA: scuoti la scatola chiusa. Non deve sentirsi niente muoversi.



--- 12. Orienta la IMU e verificalo sul serio ---

La IMU dev'essere SOLIDALE alla scatola (avvitata o biadesivo strutturale,

mai appoggiata) e la scatola solidale al telaio. Ogni gioco diventa un

segnale che leggerai come se fosse la strada.


Orientamento nominale, guardando il mezzo da seduto:

  X -> avanti (ruota anteriore)

  Y -> sinistra

  Z -> alto


Verifica empirica, mezzo sul cavalletto centrale, Monitor Seriale aperto:

  1. Fermo e dritto: roll e pitch entro +-2 gradi. Se leggi valori grandi

     la scatola e storta: RADDRIZZALA, non correggere via software.

  2. Inclina a sinistra di una decina di gradi: il roll si muove netto e

     TORNA A ZERO quando rilasci.

  3. SEGNO: annota se inclinando a sinistra il roll va positivo o negativo.

  4. Premi sulla sella di scatto: il pitch reagisce e torna a zero.


VERIFICA: tutti e quattro passano. Se il roll non torna a zero, la

calibrazione dei giroscopi e andata male: spegni e riaccendi il quadro

senza toccare il mezzo.



--- 13. Antenna GPS, e la prova che ha davvero il fix ---

Faccia ceramica RIVOLTA AL CIELO, sotto plastica ma MAI sotto metallo.

Se sopra il vano c'e una piastra portapacchi metallica, sposta l'antenna

nel vano interno anteriore.


La prova seria (non fidarti del LED lampeggiante):

  1. Mezzo all'aperto, quadro acceso, aspetta 2-3 minuti

  2. Spegni, prendi la microSD, aprila sul PC

  3. Apri il .gps.csv: lat e lon devono contenere coordinate PLAUSIBILI,

     non zeri. Incollale su una mappa: devono cadere sul tuo indirizzo.


VERIFICA: le coordinate cadono dove sei davvero. Se sono a zero, antenna

schermata o TX/RX invertiti.



--- 14. Prova su strada PRIMA di fissare definitivamente ---

Questo passo si salta sempre, ed e quello che fa risparmiare un pomeriggio.

  1. Scatola nel vano APPOGGIATA, con due fascette provvisorie

  2. Giro breve, 10 minuti, in zona che conosci

  3. Torna, scarica, guarda il report


Se qualcosa non va — roll che deriva, GPS assente, sessione che si chiude —

lo scopri con tutto ancora smontabile in due minuti.


VERIFICA: il report contiene una traccia di velocita che riconosci e un

angolo di piega che si muove quando curvi. SOLO ORA fissa in via definitiva.



============================================================

FASE D — PRIMO GIRO  (\~40 min)

============================================================


--- 15. Accensione e calibrazione ---

Ogni volta che accendi il quadro il firmware calibra i giroscopi nei primi

2 secondi.


>> IL MEZZO DEVE RESTARE FERMO E DRITTO SUL CAVALLETTO CENTRALE PER I PRIMI

   2 SECONDI DOPO IL QUADRO. Se lo muovi, l'angolo di piega derivera per

   tutta la sessione.


Accendi il quadro, conta fino a cinque, poi sali e parti.



--- 16. Il giro di riferimento ---

Scegli un anello di 5-10 km vicino casa che contenga: un rettilineo

pianeggiante, un tratto di curve, un tratto sconnesso. Sara sempre lo

stesso, sempre nello stesso verso, per tutte le sessioni future.


La prima volta, prima di partire:

  - Pressioni gomme misurate A FREDDO e annotate

  - Zaino/abbigliamento che userai sempre nei test

  - Asfalto asciutto


Sul rettilineo: tre accelerazioni piene da fermo fino a 60 km/h e tre

frenate decise. Sono i tuoi tempi di riferimento.

Per il resto guida normalmente: il sistema registra e basta.



--- 17. Torna a casa e prendi il report ---

Sul PC, prima di rientrare in garage:

  cd tools && python ingest\_server.py

Parcheggia vicino a casa e lascia il quadro acceso: la centralina aggancia

il Wi-Fi, carica le sessioni e lancia l'analisi.

Se non hai copertura in garage, porta la microSD al PC:

  python analyze.py sessions/sess00001.slab --label "baseline di fabbrica"


VERIFICA FINALE: apri tools/reports/sess00001.html. Devi trovare la traccia

di velocita che riconosci, l'istogramma delle tue pieghe, il tempo 0-50 e

l'indice di comfort. DA QUESTO MOMENTO HAI UNA BASELINE MISURATA DEL TUO

SCOOTER.



--- 18. Ripeti tre volte ---

Una sessione sola non e una baseline: e un campione. Fai TRE giri in giorni

diversi con la stessa configurazione. La mediana dei tre e il valore di

riferimento; la loro dispersione ti dice quanto deve cambiare un KPI perche

la differenza sia reale e non rumore.

Da qui in poi ogni modifica va confrontata con questi tre giri secondo il

protocollo A/B.



============================================================

SE QUALCOSA NON VA

============================================================

ERRORE SD all'avvio

  Modulo alimentato a 3V3 invece che 5 V; cavi SPI lunghi; non FAT32


IMU1:0

  SDA/SCL invertiti, o AD0 non a massa. Controlla la continuita


Nessun dato GPS nel .csv

  TX e RX invertiti (il caso piu frequente), antenna sotto metallo, o

  baud rate diverso: prova GPS.begin(9600, ...)


Roll che deriva durante il giro

  Il mezzo si e mosso durante i 2 secondi di calibrazione. Rifai il giro


Velocita sempre a zero nel report

  Il GPS non aveva il fix: guarda il .gps.csv, se e vuoto e quello


La sessione si chiude da sola mentre guidi

  Non dovrebbe (il firmware rileva il movimento da GPS e vibrazione).

  Se succede, alza IDLE\_STOP\_MS


L'upload a casa non parte

  IP del PC cambiato: fissalo nel router e aggiorna INGEST\_URL.

  Verifica che il firewall non blocchi la porta 8500



Per i livelli 1 e 2 (contagiri, gas, ruote, sospensioni) si cambia

\#define BUILD\_LEVEL nel firmware e i nuovi KPI compaiono da soli nel report.


ScooterLab — istruzioni livello 0 — agosto 2026
```
