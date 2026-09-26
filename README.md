# Remote Equipment Monitoring Dashboard

Webový dashboard na sledovanie a vzdialené riadenie výrobnej bunky (simulácia ABB robota/pneumatiky) v reálnom čase.

## Čo to robí
- číta dáta zo zariadenia cez WebSocket (teplota, tlak, počet cyklov)
- automaticky loguje poruchy
- umožňuje vzdialený reštart/kvitovanie poruchy priamo z prehliadača
- ukladá históriu do SQLite
- pripravené na nasadenie cez Docker

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
- napojenie na reálny Modbus/OPC UA namiesto simulátora
- nasadenie na Azure (Container Apps)
- autentifikácia pred prístupom k dashboardu
