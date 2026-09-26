# Remote Equipment Monitoring Dashboard

Vzdialený monitoring a riadenie priemyselnej výrobnej bunky (simulovaný ABB
robot / pneumatická stanica) cez webový dashboard v reálnom čase.

## Prečo tento projekt

Firmy, ktoré zvažujú, či dať juniorovi/kontraktorovi **plný home office**,
riešia jednu vec: *dá sa touto osobou riadiť a diagnostikovať proces bez jej
fyzickej prítomnosti?* Tento projekt je priama odpoveď — ukazuje, že viem:

- čítať dáta zo zariadenia na diaľku v reálnom čase (WebSocket),
- detegovať a logovať poruchy automaticky,
- bezpečne zasiahnuť do procesu z prehliadača (vzdialený reštart/kvitovanie),
- postaviť to ako nasaditeľnú aplikáciu (Docker, pripravené na Azure),
- zdokumentovať to tak, aby to niekto cudzí pochopil bez toho, aby sa ma
  musel niečo pýtať naživo.

Spája to moju prax s priemyselnou automatizáciou (ABB roboty, RAPID,
pneumatické systémy, IPTE FrameWorX) s programovaním a cloudom.

## Architektúra

```
Zariadenie (PLC/robot)  →  simulator.py  →  main.py (FastAPI)  →  SQLite
                                                 │
                                                 ├── REST API (/api/*)
                                                 └── WebSocket (/ws) ──► dashboard v prehliadači
```

- **`app/simulator.py`** — generuje realistické dáta (teplota, tlak, počet
  cyklov, stav, náhodné poruchy). V produkcii sa metóda `read()` nahradí
  reálnym čítaním cez [`pymodbus`](https://pypi.org/project/pymodbus/)
  (Modbus TCP) alebo [`opcua-asyncio`](https://pypi.org/project/asyncua/)
  (OPC UA) — zvyšok aplikácie sa nemení.
- **`app/database.py`** — SQLite log histórie a alarmov (prežije reštart
  servera).
- **`app/main.py`** — FastAPI server: REST endpointy + WebSocket, ktorý
  posiela nové dáta všetkým pripojeným klientom naraz (viac ľudí môže
  sledovať to isté zariadenie súčasne — presne ako pri remote tíme).
- **`static/`** — samotný dashboard (HTML/CSS/JS + Chart.js).

## Spustenie lokálne

```bash
python -m venv venv
source venv/bin/activate        # na Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Otvor `http://localhost:8000`. Hodnoty sa aktualizujú každé 2 sekundy,
občas nastane simulovaná porucha (tlak mimo rozsah) — vtedy sa rozsvieti
červený stav a v logu alarmov pribudne záznam. Tlačidlo **"Vzdialený
reštart"** poruchu kvituje presne tak, ako by to spravil operátor na diaľku.

## Spustenie cez Docker

```bash
docker build -t remote-monitoring .
docker run -p 8000:8000 remote-monitoring
```

## Ako to rozšíriť ďalej (odporúčané kroky pre portfólio)

1. **Napojenie na reálne dáta** — ak máš doma prístup k Arduino/Raspberry
   Pi so senzorom, nahraď `simulator.py` reálnym čítaním — to je najsilnejší
   možný upgrade pre pohovor ("toto naozaj beží na fyzickom zariadení").
2. **Nasadenie na Azure** (nadväzuje na tvoj AZ-104/Terraform plán) —
   `az containerapp up` alebo Azure App Service pre kontajnery, plus Azure
   Monitor na alerting namiesto lokálnej SQLite.
3. **Autentifikácia** — pridaj jednoduché prihlásenie (napr. FastAPI +
   OAuth2/JWT), aby dashboard nebol verejne prístupný — ukazuje povedomie
   o bezpečnosti vzdialeného prístupu k výrobe.
4. **Alerting mimo dashboardu** — pri poruche pošli notifikáciu na
   Slack/Discord/e-mail (podobne ako si to plánoval pri CI/CD projekte).

## Ako to prezentovať firmám

V README na GitHube (a v LinkedIn/Malt/Upwork profile) opíš toto ako:

> "Postavil som webový dashboard na vzdialený monitoring a riadenie
> priemyselnej výrobnej bunky (simulácia ABB robotickej stanice) — reálny
> čas dát cez WebSocket, automatická detekcia porúch, vzdialený zásah do
> procesu. Architektúra pripravená na napojenie na skutočný PLC cez Modbus/
> OPC UA a nasadenie na Azure."

To je presne veta, ktorá spája tvoju výrobnú prax s cloudom a dokazuje
remote-ready mentalitu.
