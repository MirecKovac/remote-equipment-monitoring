# Remote Equipment Monitoring Dashboard

Webový dashboard na sledovanie a vzdialené riadenie výrobných liniek (simulácia ABB robota/pneumatiky) v reálnom čase.

## Čo to robí
- číta dáta zo zariadenia cez WebSocket (teplota, tlak, počet cyklov)
- automaticky loguje poruchy
- umožňuje vzdialený reštart/kvitovanie poruchy priamo z prehliadača
- ukladá históriu do SQLite
- pripravené na nasadenie cez Docker

## Novšie funkcie
- podpora viacerých liniek naraz (prepínanie cez taby)
- štart/stop ovládanie linky, nie len reštart pri poruche
- nastaviteľné cieľové hodnoty (teplota, tlak) — linka sa k nim reálne približuje
- export histórie do CSV

## Prečo som to robil
Pracujem s priemyselnou automatizáciou (ABB roboty, RAPID, IPTE FrameWorX) a chcel som si vyskúšať, ako by vyzeral vzdialený monitoring reálnej linky, keby som k nej nemal fyzický prístup.

## Architektúra
- `app/simulator.py` — generuje dáta zariadenia (v produkcii by sa nahradilo Modbus/OPC UA klientom)
- `app/database.py` — SQLite log histórie a alarmov
- `app/main.py` — FastAPI server, REST API + WebSocket
- `static/` — frontend dashboardu

## Spustenie lokálne
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
Otvor `http://localhost:8000`.

## Spustenie cez Docker
```bash
docker build -t remote-monitoring .
docker run -p 8000:8000 remote-monitoring
```

## Čo by som pridal ďalej
1. **Napojenie na reálne dáta** — ak mám prístup k Arduino/Raspberry Pi so senzorom, nahradiť `simulator.py` reálnym čítaním.
2. **Nasadenie na Azure** — `az containerapp up` alebo Azure App Service pre kontajnery, plus Azure Monitor na alerting namiesto lokálnej SQLite.
3. **Autentifikácia** — jednoduché prihlásenie (napr. FastAPI + OAuth2/JWT), aby dashboard nebol verejne prístupný.
4. **Alerting mimo dashboardu** — pri poruche poslať notifikáciu na Slack/Discord/e-mail.

## Novšie funkcie
- podpora viacerých liniek naraz (prepínanie cez taby)
- štart/stop ovládanie linky, nie len reštart pri poruche
- nastaviteľné cieľové hodnoty (teplota, tlak) — linka sa k nim reálne približuje
- export histórie do CSV
