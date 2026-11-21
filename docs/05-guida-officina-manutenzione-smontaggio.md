# ScooterLab — Guida Officina, Verifica di Fabbrica & Smontaggio Scocche

**Veicolo Target:** SYM Symphony ST 200i ABS Euro 4 (2019 — codice modello `XB20E2-EU`)  
**Fonti Verificate:** `[TUO]` Scheda Tecnica SYM Italia + Libretto Uso & Manutenzione Symphony ST 200 ABS E4; `[XB20]` Service Manual & EFI Manual Fiddle III 200i (stesso motore 169 cc); `[FAM]` Service Manual Jet 14 (ABS Bosch) & Maxsym (sensore ABS `44870-L4C-000`); Esplosi OEM `EasyParts.it` / `Bike-Parts-SYM`.

> **Avvertenza di sicurezza:** Prima di scollegare la batteria stacca **sempre prima il negativo (-)** e poi il positivo (+). **MAI scollegare il connettore della centralina ABS con la chiave su ON** (`Maxsym pag. 14-15`), pena il danneggiamento della centralina. Lavora a motore freddo (`< 35 °C`) per valvole, olio e candela.

---

## 1. Copertura Documentale: Cosa Abbiamo in Locale (`manuals/`)

In locale (cartella `manuals/`, esclusa da Git per copyright/dimensioni) sono archiviati e verificati **8 documenti ufficiali SYM**:

| File locale (`manuals/`) | Copertura | Livello fonte |
| :--- | :--- | :--- |
| `symphony_st_200_abs_scheda_it.pdf` | Specifiche esatte SYM Italia (`XB20E2-EU`), olio, valvole, candela, pressioni, lampade, fusibili | **`[TUO]`** |
| `symphony_st_200_abs_e4_owners_tr.pdf` | Libretto d'uso esatto Euro 4 ABS: intervalli tagliandi, batteria/fusibili sotto cestello, freno, ABS | **`[TUO]`** |
| `fiddle3_200i_service_manual.pdf` | Manuale officina completo stesso motore 169 cc: valvole, compressione, coppie, ricarica/statore/bobina | **`[XB20]`** |
| `fiddle3_200i_efi_maintenance.pdf` | Diagnostica iniezione EFI, codici lampeggio, pompa benzina, TPS, pinout ECU | **`[XB20]`** |
| `fiddle3_200i_electrical_diagram.pdf` | Schema elettrico impianto motore `XB20` | **`[XB20]`** |
| `jet14_service_manual.pdf` | Capitolo ABS Bosch (anelli fonici **50 fori**, codici `C1042–C1055`) e procedure carenature SYM | **`[FAM]`** |
| `jet14_electrical_diagram.pdf` | Schema elettrico versione con ABS + OBD CAN + segnali cruscotto | **`[FAM]`** |
| `maxsym_abs_service_manual.pdf` | Capitolo ABS dedicato allo stesso sensore OEM `44870-L4C-000` | **`[FAM]`** |

**Esplosi ufficiali microfiche carrozzeria & ricambi (per viti/clip di ogni singola scocca del tuo modello esatto):**
- [EasyParts.it — SYM Symphony 200i ST 4T E4 (2018–2020)](https://www.easyparts.it/Disegni-esplosi/1685/28747/Sym-Symphony-200I-ST-4T-E4-2018-2020-(EU).html)

---

## 2. Attrezzi & Ricambi per Check-up + Tagliando 30.000 km

### Attrezzi indispensabili
- **Chiavi a bussola:** 8, 10, 12, 14, 17, 19, 24 mm + cricchetto e prolunghe.
- **Chiave candela:** 16 mm snodata (per `NGK CR7HSA`).
- **Cacciaviti & Brugole:** croce **PH1** e **PH2**, brugola **5 mm**, leva in plastica per clip carenature (evita di graffiare o rompere i ganci).
- **Strumenti di misura:**
  - **Chiave dinamometrica** (range ~10–130 Nm; per carter, candela, tappo olio, variatore, ruote).
  - **Spessimetro a lamelle** (0,10 / 0,12 / 0,15 mm) per gioco valvole.
  - **Calibro ventesimale/digitale** (per cinghia, rulli su 2 assi, dischi freno, ferodo).
  - **Multimetro digitale** (tensione DC, resistenza Ω, frequenza Hz per segnali RPM/SPEED).
  - **Manometro gomme** affidabile (controllo a freddo).
- **Per aprire il CVT:** blocca-variatore universale (o chiave a fascia/puleggia) — **mai** bloccare solo la ruota posteriore col freno per svitare il dado frizione/variatore (`Fiddle III pag. 6-4`), si danneggiano gli ingranaggi del riduttore!

### Kit Ricambi OEM & Equivalenti (Tagliando 30.000 km)
| Ricambio | Intervallo `[TUO]` | Codice OEM SYM / Specifica | Equivalente verificato |
| :--- | :--- | :--- | :--- |
| **Olio motore** | Ogni **3.000 km** | **0,70 L** al cambio (`SAE 10W-30 API SH/CD`, `5W-40` sotto 0 °C) | Motul / Castrol / Bardahl 4T 10W-30 o 10W-40 JASO MB |
| **Olio trasmissione** | Ogni **6.000 km** | **170 cc** al cambio (`SAE 85W-140 hypoid`) | Olio ingranaggi 85W-140 GL-5 |
| **Filtro aria (carta)** | Ogni **6.000 km** | `17211-ADB-000` | HifloFiltro `HFA5101` |
| **Filtro pompa benzina** | Ogni **10.000 km** | Elemento su gruppo pompa serbatoio | OEM SYM |
| **Candela** | Ogni **12.000 km** | **NGK `CR7HSA`** — gap **0,6–0,7 mm** (serraggio `10–12 Nm`) | NGK CR7HSA / CR7HIX |
| **Cinghia CVT** | Ogni **12.000 km** | `1B01XMA02` (`860 × 19,7 × 9,0 mm`, 28°) | **Bando `S08-023`** (stesso fornitore OEM) |
| **Rulli variatore** | Controllo/usura | `22121-GY6-920-A` (**18 × 14 mm — 13,0 g — 6 pz**) | Dr.Pulley 18×14 |
| **Pastiglie freno** | A usura | `45105-APA-000-A` (verificare pinza ant/post prima dell'ordine) | Brembo CC / EBC / Ferodo |
| **Batteria** | Al bisogno | **12V 6Ah sigillata** (`YTX7A-BS`) | Yuasa `YTX7A-BS` |
| **Viteria di scorta** | Sempre utile | Dadi a molla da **4 mm e 5 mm** (cadono facilmente nel telaio) | Kit clip/dadi a molla scooter |

---

## 3. Protocollo "Verifica Conformità di Fabbrica" (5 Step)

Esegui questi 5 controlli in ordine per certificare che il tuo scooter sia meccanicamente ed elettricamente in specifica di fabbrica prima di registrare la baseline ScooterLab.

### Step 1 — Impianto Elettrico & Ricarica (Multimetro)
1. **Batteria a riposo (quadro OFF):** `12,6–12,8 V` (sotto `12,3 V` è scarica o solfatata).
2. **Dispersione parassita (quadro OFF, amperometro in serie al negativo):** `< 1 mA` (`[XB20]`).
3. **Tensione in avviamento:** non deve scendere sotto `~10,0 V`.
4. **Ricarica regolatore (motore acceso a ~2.000 rpm, fari accesi):** **`14,0–14,8 V`** (specifica `[XB20]`: `14,5 +0,5 V`). Se supera `15,0 V` il regolatore è guasto; se resta sotto `13,2 V` controllare statore (`0,2–1,2 Ω` tra i fili gialli `Y–Y` a connettore scollegato).

### Step 2 — Diagnostica EFI & ABS (Senza Strumenti)
1. **Spia EFI (quadro ON senza avviare):** deve accendersi e poi spegnersi; se lampeggia, conta i lampeggi (lungo `1 s` = decine, corto `0,5 s` = unità) e incrocia la tabella codici in [`docs/02-dati-tecnici-verificati.md`](./02-dati-tecnici-verificati.md) (sez. 8).
2. **Spia ABS:** si accende a quadro ON e deve **spegnersi** superando ~5–10 km/h. Se resta accesa, verificare integrità visiva dei cavi sensori ruota e pulizia dei due anelli fonici a **50 fori**.

### Step 3 — Motore, Candela & Gioco Valvole (a Motore Freddo `< 35 °C`)
1. **Candela (`NGK CR7HSA`):** colore nocciola chiaro = carburazione corretta; nera fuligginosa = miscela grassa/filtro aria sporco; bianca = miscela magra. Verifica gap **`0,6–0,7 mm`** e serra a **`10–12 Nm`** (prima avvita a mano!).
2. **Gioco valvole (`[TUO]`):**
   - Togli tappo ispezione fasatura sul carter ventola lato destro e coperchio punterie.
   - Ruota l'albero motore **SOLO IN SENSO ORARIO** (`[XB20]` pag. 2-7) fino ad allineare la tacca **`T`** sul volano col riferimento carter e verificare che il foro singolo sull'ingranaggio albero a camme punti in alto (PMS in fase di compressione, bilancieri entrambi liberi).
   - Misura con spessimetro: **Aspirazione (IN) = `0,12 ± 0,02 mm`**, **Scarico (EX) = `0,12 ± 0,02 mm`**.
   - Se fuori tolleranza: allenta controdado, regola registro, riserra e **rimisura**.
3. **Compressione cilindro (opzionale se hai il manometro):** a motore caldo, candela smontata, gas tutto aperto → **`10,2 ± 0,2 kg/cm²`** (`[XB20]`).

### Step 4 — Ispezione Trasmissione CVT (Carter Sinistro)
> **Attenzione al mismatch dei manuali SYM:** I service manual Fiddle III 200i e Jet 14 riportano in tabella i limiti dei rulli da 16 mm (`15,40 mm`) e campana da 125 mm. Sul Symphony ST 200i i rulli OEM sono **18 × 14 mm**: verifica col calibro cosa monta realmente il tuo variatore e applica le tolleranze ufficiali SYM qui sotto.
- **Cinghia:** misura la larghezza col calibro → nominale `19,7 mm`, **limite usura `17,5 mm`** (sostituire comunque ogni `12.000 km` o se presenta crepe tra i denti).
- **Rulli:** misura il diametro in **due direzioni a 90°**:
  - Se diametro `< 17,5 mm` (per rulli da 18 mm) → sostituire.
  - Se differenza tra i due assi `> 0,2–0,3 mm` (spiattellamento/ovalizzazione) → sostituire comunque.
- **Frizione & Campana:** spessore ferodo masse `≥ 2,0–2,5 mm` (mai a metallo); superficie interna campana senza solchi o bluastri da surriscaldamento.
- **Pulizia:** soffia polvere di ferodo e gomma; pulegge e cinghia devono essere **100% prive di grasso/olio**.
- **Coppie di serraggio (`[XB20]`):** dado variatore **`49–59 Nm`**, dado campana frizione **`54–59 Nm`**, 7×M8 carter trasmissione **`25–29 Nm`**.

### Step 5 — Ciclistica, Freni & Pneumatici
- **Pressioni gomme a freddo (`110/70-16`):** Anteriore **`2,00 kg/cm²`**, Posteriore **`2,00 kg/cm²`** (1 persona) / **`2,25 kg/cm²`** (2 persone).
- **Gioco leve freno:** **`10–20 mm`** (non spugnose).
- **Pastiglie e dischi:** controlla visivamente lo spessore residuo delle pastiglie (sostituire prima di `1,5–2,0 mm` o quando scompare la tacca di usura) e assenza di scalini profondi sui dischi (`Ø 260 mm` ant. / `Ø 240 mm` post.).
- **Oli:** scarica olio motore a caldo (`tappo scarico 34–44 Nm`, riempi **`0,70 L`**) e olio trasmissione (`170 cc`).

---

## 4. Guida Smontaggio Scocche & Carenature (Per Obiettivo)

> **Regola d'oro plastiche SYM (`Jet 14 pag. 12-2`):** Le carenature SYM usano **viti + ganci stampati ad incastro**. Se hai tolto tutte le viti e il pannello non viene via, **non tirare mai di forza**: guarda il verso di scorrimento del gancio e aiutati con una leva in plastica. Tieni una vaschetta magnetica separata per ogni pannello e fotografa ogni passaggio!

### Livello A — Vano Sottosella, Batteria, Fusibili, Candela & ScooterLab Livello 0
*Non richiede di smontare nessuna carenatura esterna.*
1. Apri la sella e svuota il vano.
2. Svita i **bulloni flangiati con chiave a bussola da 10 mm** sul fondo del cestello portaoggetti (e le eventuali viti anteriori vicino alla cerniera/serbatoio).
3. Solleva verticalmente il **cestello sottosella** (fai attenzione all'eventuale cavo luce vano o presa USB se presente: scollega il connettore prima di estrarlo del tutto).
4. **Ora hai accesso diretto a:**
   - **Batteria `12V 6Ah`** e **Scatola Fusibili** (`10A×2, 15A×1, 20A×1`) affiancati (`[TUO]`).
   - **Parte superiore motore** (coperchio valvole, pipetta candela, corpo farfallato, iniettore).
   - **Passaggio cavi verso il telaio** per installare ScooterLab Livello 0 nella parte anteriore del vano (lontano dal calore motore).

### Livello B — Filtro Aria & Carter Trasmissione CVT (Lato Sinistro)
*Non richiede di smontare le carenature laterali superiori.*
1. **Filtro aria:** svita le viti perimetrali (croce PH2) del coperchio nero dell'airbox sopra il carter sinistro, estrai l'elemento in carta `17211-ADB-000` e pulisci l'interno scatola.
2. **Carter CVT:** rimuovi il convogliatore/presa aria in plastica anteriore del carter (viti PH2/bussola 8), poi svita i **7 bulloni M8** (bussola 8/10) lungo il perimetro del carter alluminio lavorando a croce. Sfila il carter tenendolo dritto (attenzione alle 2 boccole di centraggio e alla guarnizione).

### Livello C — Coprimanubrio, Scudo Anteriore & Cruscotto (Solo per Livello 1/2: segnali IGN/RPM/SPEED/OBD)
*Segui l'ordine esatto (Stadi 1 e 2):*
1. **Specchietti:** svitali (attenzione a eventuale filetto sinistrorso sul lato destro).
2. **Coprimanubrio anteriore → posteriore:** rimuovi le viti autofilettanti (`4×12` / `4,8×16`, croce PH1–PH2) sul lato interno del retroscudo manubrio, poi sgancia delicatamente le clip perimetrali lungo la giunzione anteriore/posteriore. Ora accedi al **connettore del cruscotto** (dove arrivano `IGN(+)`, `RPM`, `SPEED`, spia `ABS` — sempre da verificare col multimetro prima di derivare in parallelo!).
3. **Scudo anteriore / Vano retroscudo (se serve accedere a connettore OBD, centralina ABS anteriore o fascio cavi):**
   - Rimuovi le viti nel retroscudo e le viti inferiori sotto il parafango/faro.
   - Fai scorrere lo scudo verso l'avanti/basso liberando i ganci laterali; scollega i connettori frecce/faro prima di appoggiarlo su un panno morbido.

### Livello D — Fianchetti Posteriori & Codone (Solo per manutenzione profonda / cablaggio fanale posteriore)
1. Rimuovi il **cestello sottosella** (Livello A).
2. Svita i bulloni del **portapacchi posteriore** (bussola 10/12).
3. Rimuovi la **copertura centrale** sopra il tunnel/serbatoio, poi le viti dei **fianchetti laterali dx/sx** (sotto la pedana, lungo il bordo sella e dietro al fanale).
4. Sfila i fianchetti facendoli scorrere all'indietro per liberare i ganci anteriori senza romperli.

---

## 5. Checklist Rapida per la Prima Sessione in Garage

Prima di richiudere il cestello sottosella (Livello A), sfrutta l'apertura per raccogliere i dati mancanti del tuo mezzo in [`docs/02-dati-tecnici-verificati.md`](./02-dati-tecnici-verificati.md):
- [ ] **Foto dall'alto** del vano sottosella vuoto + misura **altezza libera con casco dentro** (Fase B ScooterLab).
- [ ] **Foto scatola fusibili aperta** e batteria.
- [ ] **Misura circonferenza rotolamento reale** ruota anteriore (`110/70-16`): segno a terra, 1 giro completo, metro (oggi calcolata `1,716 m`).
- [ ] **Test multimetro sul filo sottochiave candidato** (0 V quadro OFF, ~12,5 V quadro ON, ~14,2 V motore acceso, stabile ruotando il manubrio).
- [ ] **Test tensione batteria e ricarica** (Step 1) + controllo visivo pastiglie freno e anello fonico 50 fori.
