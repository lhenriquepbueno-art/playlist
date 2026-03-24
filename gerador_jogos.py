#!/usr/bin/env python3
"""
gerador_jogos.py — Gera lista_jogos.m3u8 com jogos do dia
IPTV-M3Uandroid — Menu Jogos ⚽

Fonte: TheSportsDB (100% gratuita, chave "123" pública, sem cadastro)
Fallback: football-data.org (gratuita com cadastro simples)

Campeonatos:
  Brasileirão Série A  → ID 4351
  Premier League       → ID 4328
  La Liga              → ID 4335
  Champions League     → ID 4480
  Copa Libertadores    → ID 4501

Dependências: pip install requests pytz

Agendamento sugerido (crontab):
  0 6,12 * * * python3 /caminho/gerador_jogos.py >> /caminho/logs/jogos.log 2>&1
  */30 13-23 * * * python3 /caminho/gerador_jogos.py >> /caminho/logs/jogos.log 2>&1
"""

import requests, re, os, time, sys
from datetime import datetime
from collections import defaultdict
import pytz

# ── CONFIGURAÇÕES ─────────────────────────────────────────────────────────────
TSDB_BASE   = "https://www.thesportsdb.com/api/v1/json/123"
FDORG_KEY   = ""   # opcional — cadastro gratuito em football-data.org
FDORG_BASE  = "https://api.football-data.org/v4"
TIMEZONE    = pytz.timezone("America/Sao_Paulo")

BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
OUTPUT_FILE = os.path.join(BASE_DIR, "..", "listas", "lista_jogos.m3u8")

LOGO_FALLBACK = "https://www.thesportsdb.com/images/media/league/badge/ucj6gc1614973351.png"

# ── CAMPEONATOS ───────────────────────────────────────────────────────────────
CAMPEONATOS_TSDB = {
    "4351": {"nome": "Brasileirão Série A",  "bandeira": "🇧🇷", "canais": ["SporTV","CazeTV","Band Sports"]},
    "4328": {"nome": "Premier League",        "bandeira": "🏴󠁧󠁢󠁥󠁮󠁧󠁿", "canais": ["ESPN","CazeTV"]},
    "4335": {"nome": "La Liga",               "bandeira": "🇪🇸", "canais": ["ESPN 3"]},
    "4480": {"nome": "Champions League",      "bandeira": "🏆",  "canais": ["SporTV","CazeTV"]},
    "4501": {"nome": "Copa Libertadores",     "bandeira": "🌎",  "canais": ["SporTV","ESPN"]},
}

# ── STREAMS DOS CANAIS ────────────────────────────────────────────────────────
# Preencha com as URLs reais da lista_tv.m3u8 após gerá-la.
# Como encontrar: abra lista_tv.m3u8, procure o canal, copie a URL abaixo do #EXTINF.
STREAM_URLS = {
    "SporTV":      "",   # ← Cole a URL do SporTV aqui
    "SporTV 2":    "",
    "CazeTV":      "",   # ← Cole a URL do CazeTV aqui
    "CazeTV 2":    "",
    "ESPN":        "",   # ← Cole a URL do ESPN aqui
    "ESPN 2":      "",
    "ESPN 3":      "",
    "Band Sports":  "",
    "DAZN 1":      "",
}

# ── HELPERS ───────────────────────────────────────────────────────────────────
def hoje_brt(): return datetime.now(TIMEZONE)

def formatar_horario(s):
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        return dt.astimezone(TIMEZONE).strftime("%H:%M")
    except: return "--:--"

def is_hoje(s):
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        return dt.astimezone(TIMEZONE).date() == hoje_brt().date()
    except: return False

def safe_get(url, headers=None, params=None):
    try:
        r = requests.get(url, headers=headers or {}, params=params or {}, timeout=15)
        return r.json() if r.status_code == 200 else {}
    except Exception as e:
        print(f"  [ERRO] {url} — {e}"); return {}

# ── THESPORTSDB ───────────────────────────────────────────────────────────────
def tsdb_jogos(league_id):
    hoje = hoje_brt().strftime("%Y-%m-%d")
    data = safe_get(f"{TSDB_BASE}/eventsday.php", params={"d": hoje, "l": league_id})
    events = data.get("events") or []
    if not events:
        data2 = safe_get(f"{TSDB_BASE}/eventsnextleague.php", params={"id": league_id})
        all_ev = data2.get("events") or []
        events = [e for e in all_ev if is_hoje(e.get("strTimestamp", e.get("dateEvent","")))]
    return events

def tsdb_logo(team_name):
    data = safe_get(f"{TSDB_BASE}/searchteams.php", params={"t": team_name})
    teams = data.get("teams") or []
    if teams:
        badge = teams[0].get("strTeamBadge") or ""
        if badge: return badge + "/preview"
    return LOGO_FALLBACK

def tsdb_extinf(ev, camp, canal_nome, canal_url):
    home    = ev.get("strHomeTeam", "Time A")
    away    = ev.get("strAwayTeam", "Time B")
    status  = (ev.get("strStatus") or "").upper()
    ts      = ev.get("strTimestamp") or ev.get("dateEvent","") + "T" + (ev.get("strTime") or "00:00:00") + "Z"
    horario = formatar_horario(ts)
    logo    = ev.get("strHomeTeamBadge") or tsdb_logo(home)
    if not logo or logo == "null": logo = LOGO_FALLBACK
    prefix  = "🔴 AO VIVO" if status in ("LIVE","1H","2H","HT","ET") else ("✅ ENCERRADO" if status in ("FT","AET","PEN") else f"⏰ {horario}")
    display = f"{prefix} | {home} x {away}  [{canal_nome}]"
    group   = f"{camp['bandeira']} {camp['nome']}"
    return f'#EXTINF:-1 tvg-id="" tvg-name="{display}" tvg-logo="{logo}" group-title="{group}",{display}', canal_url

# ── FOOTBALL-DATA.ORG (FALLBACK) ──────────────────────────────────────────────
FDORG_CODES = {"4351":"BSA","4328":"PL","4335":"PD","4480":"CL"}

def fdorg_jogos(league_id):
    if not FDORG_KEY: return []
    code = FDORG_CODES.get(league_id)
    if not code: return []
    hoje = hoje_brt().strftime("%Y-%m-%d")
    data = safe_get(f"{FDORG_BASE}/competitions/{code}/matches",
                    headers={"X-Auth-Token": FDORG_KEY},
                    params={"dateFrom": hoje, "dateTo": hoje})
    return data.get("matches") or []

def fdorg_extinf(match, camp, canal_nome, canal_url):
    home    = match.get("homeTeam",{}).get("shortName") or match.get("homeTeam",{}).get("name","Time A")
    away    = match.get("awayTeam",{}).get("shortName") or match.get("awayTeam",{}).get("name","Time B")
    status  = match.get("status","SCHEDULED")
    horario = formatar_horario(match.get("utcDate",""))
    logo    = match.get("homeTeam",{}).get("crest") or LOGO_FALLBACK
    prefix  = "🔴 AO VIVO" if status in ("IN_PLAY","PAUSED","LIVE") else ("✅ ENCERRADO" if status=="FINISHED" else f"⏰ {horario}")
    display = f"{prefix} | {home} x {away}  [{canal_nome}]"
    group   = f"{camp['bandeira']} {camp['nome']}"
    return f'#EXTINF:-1 tvg-id="" tvg-name="{display}" tvg-logo="{logo}" group-title="{group}",{display}', canal_url

def sem_jogos_extinf(camp):
    group = f"{camp['bandeira']} {camp['nome']}"
    display = f"📭 Sem jogos hoje — {camp['nome']}"
    return f'#EXTINF:-1 tvg-id="" tvg-name="{display}" tvg-logo="{LOGO_FALLBACK}" group-title="{group}",{display}', "http://0.0.0.0"

# ── GERADOR PRINCIPAL ─────────────────────────────────────────────────────────
def gerar_m3u():
    hoje_str = hoje_brt().strftime("%d/%m/%Y")
    hora_str = hoje_brt().strftime("%H:%M")
    print(f"\n⚽  Gerando lista_jogos.m3u8 — {hoje_str} {hora_str} BRT")
    print("=" * 55)

    linhas = ["#EXTM3U", f"#PLAYLIST:Jogos do Dia — {hoje_str}", ""]
    total = 0

    for lid, camp in CAMPEONATOS_TSDB.items():
        print(f"\n{camp['bandeira']}  {camp['nome']}")
        eventos = tsdb_jogos(lid)

        if not eventos and FDORG_KEY:
            matches = fdorg_jogos(lid)
            if matches:
                for m in matches:
                    for cn in camp.get("canais",[]):
                        cu = STREAM_URLS.get(cn,"")
                        if not cu: continue
                        extinf, url = fdorg_extinf(m, camp, cn, cu)
                        linhas += [extinf, url]; total += 1
                        print(f"   ✓ {formatar_horario(m.get('utcDate',''))} | {m.get('homeTeam',{}).get('shortName','?')} x {m.get('awayTeam',{}).get('shortName','?')} [{cn}]")
                continue

        if not eventos:
            print(f"   → Sem jogos hoje")
            extinf, url = sem_jogos_extinf(camp)
            linhas += [extinf, url]; continue

        print(f"   → {len(eventos)} jogo(s)")
        for ev in eventos:
            home = ev.get("strHomeTeam","?"); away = ev.get("strAwayTeam","?")
            ts   = ev.get("strTimestamp",""); h = formatar_horario(ts) if ts else "--:--"
            canais = camp.get("canais",[])
            adicionado = False
            for cn in canais:
                cu = STREAM_URLS.get(cn,"")
                if not cu: continue
                extinf, url = tsdb_extinf(ev, camp, cn, cu)
                linhas += [extinf, url]; total += 1; adicionado = True
                print(f"   ✓ {h} | {home} x {away} [{cn}]")
            if not adicionado:
                group = f"{camp['bandeira']} {camp['nome']}"
                logo  = ev.get("strHomeTeamBadge") or LOGO_FALLBACK
                display = f"⏰ {h} | {home} x {away}"
                extinf = f'#EXTINF:-1 tvg-id="" tvg-name="{display}" tvg-logo="{logo}" group-title="{group}",{display}'
                linhas += [extinf, "http://0.0.0.0"]; total += 1
                print(f"   ⚠ {h} | {home} x {away} [sem URL de canal]")
        time.sleep(1)

    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(linhas) + "\n")

    print(f"\n{'='*55}")
    print(f"✅  {total} entradas → {OUTPUT_FILE}")
    print(f"{'='*55}\n")

if __name__ == "__main__":
    gerar_m3u()
