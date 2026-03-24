#!/usr/bin/env python3
"""
gerar_lista_curada.py — Gerador de listas IPTV curadas
IPTV-M3Uandroid v4

Gera 6 arquivos M3U8 na pasta ../listas/:
  lista_tv.m3u8      → canais ao vivo (inclui Kids canais como aba interna)
  lista_filmes.m3u8  → filmes VOD
  lista_series.m3u8  → séries separadas por título
  lista_kids.m3u8    → conteúdo kids VOD
  lista_animes.m3u8  → animes
  lista_adultos.m3u8 → adultos (protegido por senha)

USO:
  python gerar_lista_curada.py

ATENÇÃO: Ajuste INPUT_FILES com os caminhos reais das suas listas M3U no servidor.
"""

import re, os
from collections import defaultdict

# ── CAMINHOS ─────────────────────────────────────────────────────────────────
# Ajuste para o caminho real das suas listas no servidor
BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
LISTAS_DIR = os.path.join(BASE_DIR, "..", "listas")

# Pasta fontes/ no servidor (se existir) ou pasta pai com os originais
_FONTES = os.path.join(BASE_DIR, "..", "fontes")
_ORIGINAIS = r"C:\Users\luizb\Iptv-Brasil-2026"
_BASE = _FONTES if os.path.isdir(_FONTES) and os.listdir(_FONTES) else _ORIGINAIS

INPUT_FILES = [
    os.path.join(_BASE, "CanaisIPTV.m3u"),
    os.path.join(_BASE, "CanaisBR01.m3u8"),
    os.path.join(_BASE, "novalista.m3u8"),
    os.path.join(_BASE, "Lista Mundial03.m3u"),
    os.path.join(_BASE, "Lista Mundial04.m3u"),
    os.path.join(_BASE, "Lista Mundial06.m3u8"),
    os.path.join(_BASE, "Lista Mundial02.m3u8"),
    os.path.join(_BASE, "Lista Mundial05.m3u8"),
    os.path.join(_BASE, "Jumper.m3u8"),
]

OUTPUT_TV      = os.path.join(LISTAS_DIR, "lista_tv.m3u8")
OUTPUT_FILMES  = os.path.join(LISTAS_DIR, "lista_filmes.m3u8")
OUTPUT_SERIES  = os.path.join(LISTAS_DIR, "lista_series.m3u8")
OUTPUT_KIDS    = os.path.join(LISTAS_DIR, "lista_kids.m3u8")
OUTPUT_ANIMES  = os.path.join(LISTAS_DIR, "lista_animes.m3u8")
OUTPUT_ADULTOS = os.path.join(LISTAS_DIR, "lista_adultos.m3u8")

# ── GRUPOS DE CANAIS AO VIVO ─────────────────────────────────────────────────
GRUPOS_TV = {
    "ABERTOS","BAND","SBT","RECORD","GLOBO SUDESTE",
    "BBB 26","BBB 2026","Canais | BBB","♦️Canais | BBB 26",
    "ESPN","ESPORTES","ESPORTES PPV","HORA DO JOGO","PREMIERE",
    "NOTÍCIAS","DISCOVERY","DOCUMENTÁRIOS","VARIEDADES",
    "INFANTIS","DESENHOS 24H","ESPECIAIS 24H",
}
GRUPOS_TV_MUNDIAIS = {"BRAZIL","BRAZIL ","24/7 CHANNELS","24/7 CHANNELS "}
GRUPOS_CINEMA = {
    "HBO ","HBO","MAX","TELECINE","CINE SKY","FILMES & SERIES",
    "DISNEY+","PRIME VIDEO","PARAMOUNT+","LEGENDADOS",
}

# ── NOTÍCIAS INTERNACIONAIS ───────────────────────────────────────────────────
NOTICIAS_INTL = [
    "us cnn","us fox news","us msnbc","uk: bbc news","uk: sky news",
    "euronews","france 24","cnn internacional","cnn international",
    "bbc world news","rai news",
]

# ── ESPORTES ─────────────────────────────────────────────────────────────────
ESPORTES_KW = [
    "sportv","band sports","bandsports","combate","dazn",
    "cazétv","cazetv","caze tv","cazé tv","cazé",
    "nsports","onefootball","ge tv","redbull","xsports","zapping","fifa+",
    "canal goat","uol play","fla tv","flamengo tv","furacão","sporty net",
    "apple tv+","bjj stars","flograppling","mr. olympia","tv coxa",
]

# ── DISCOVERY / NATGEO / HISTORY ─────────────────────────────────────────────
DISC_KW = [
    "discovery channel","discovery home","discovery science","discovery theater",
    "discovery turbo","discovery world","investigation discovery",
    "national geographic","nat geo","natgeo","history","h2 ","h2,",
    "hgtv","animal planet",
]

# ── VARIEDADES ────────────────────────────────────────────────────────────────
VAR_KW = [
    "gnt","multishow","bis","off ","off,","tlc","lifetime","e!","arte 1",
    "curta","woohoo","travel box","modo viagem","food network",
    "globoplay novelas","prime box brasil","music box","urban tv","nhk","a&e",
]

# ── KIDS CANAIS AO VIVO (ficam no menu TV) ────────────────────────────────────
KIDS_CANAIS_TV = [
    "cartoon network","cartoonito","discovery kids","gloob","gloobinho",
    "tv ra tim bum","tooncast","disney channel","nickelodeon","nick jr",
    "baby tv","boomerang","zoomoo",
]

# ── GLOBO: SP E RJ APENAS ────────────────────────────────────────────────────
GLOBO_PERMITIDOS       = ["globo sp","globo rj","globo rio","globo são paulo","globo sao paulo"]
GLOBO_EXCLUIR_EXPLICIT = ["globo mogi"]
REGIONAIS_EXCLUIR = [
    "globo mg","globo minas","globo nordeste","globo norte","globo sul",
    "globo bahia","globo ceará","globo pará","globo belem","globo recife",
    "globo fortaleza","globo manaus","globo rbs","globo rpc","globo sc",
    "globo brasília","globo brasilia","globo goiás","globo curitiba",
    "globo londrina","globo maringa","globo foz","globo acre",
    "globo amapá","globo roraima","globo tocantins","globo ms","globo mt",
    "globo mogi",
]

# ── ADULTOS E ANIMES ─────────────────────────────────────────────────────────
ADULTO_KW = [
    "adulto","adult","xxx","18+","porno","porn","sexy"," sex ",
    "erótico","erotico","hot channel","playboy","penthouse","hustler",
    "brazzers","bangbros",
]
ANIME_KW = [
    "anime","animê","dragon ball","naruto","one piece","attack on titan",
    "sword art","demon slayer","my hero academia","death note","bleach",
    "fullmetal","hunter x hunter","fairy tail","boruto","jujutsu",
    "black clover","tokyo ghoul","re:zero","overlord","one punch","mob psycho",
    "cowboy bebop","evangelion","neon genesis","dbz","shingeki","kimetsu",
]

SERIE_PATTERN = re.compile(r'S\d{2}\s*E\d{2}', re.IGNORECASE)

# ── MAPEAMENTO GRUPO → CATEGORIA TV ──────────────────────────────────────────
GROUP_MAP_TV = {
    "ABERTOS":"Canais Abertos","BAND":"Canais Abertos","SBT":"Canais Abertos",
    "RECORD":"Canais Abertos","GLOBO SUDESTE":"Canais Abertos",
    "BRAZIL":"Canais Abertos","BRAZIL ":"Canais Abertos",
    "BBB 26":"BBB 26","BBB 2026":"BBB 26",
    "CANAIS | BBB":"BBB 26","♦️CANAIS | BBB 26":"BBB 26",
    "ESPN":"ESPN",
    "ESPORTES":"Esportes","HORA DO JOGO":"Esportes","PREMIERE":"Esportes",
    "ESPORTES PPV":"Esportes PPV",
    "NOTÍCIAS":"Notícias",
    "HBO ":"Canais de Cinema","HBO":"Canais de Cinema","MAX":"Canais de Cinema",
    "TELECINE":"Canais de Cinema","CINE SKY":"Canais de Cinema",
    "FILMES & SERIES":"Canais de Cinema","DISNEY+":"Canais de Cinema",
    "PRIME VIDEO":"Canais de Cinema","PARAMOUNT+":"Canais de Cinema",
    "LEGENDADOS":"Canais de Cinema",
    "DISCOVERY":"Documentários | Discovery | History",
    "DOCUMENTÁRIOS":"Documentários | Discovery | History",
    "VARIEDADES":"Variedades e Entretenimento",
    "INFANTIS":"Kids — Canais","DESENHOS 24H":"Kids — Canais",
    "ESPECIAIS 24H":"Kids — Canais","KIDS ZONE":"Kids — Canais",
    "CANAIS | DESENHOS":"Kids — Canais",
    "24/7 CHANNELS":"Filmes e Séries","24/7 CHANNELS ":"Filmes e Séries",
}

TV_GROUP_ORDER = [
    "Canais Abertos","BBB 26","Notícias","ESPN","Esportes","Esportes PPV",
    "Canais de Cinema","Documentários | Discovery | History",
    "Variedades e Entretenimento","Kids — Canais","Filmes e Séries",
]

# ── HELPERS ───────────────────────────────────────────────────────────────────
def parse_m3u(fp):
    entries = []
    try:
        with open(fp, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
    except Exception as e:
        print(f"  ERRO ao ler {os.path.basename(fp)}: {e}"); return []
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith('#EXTINF'):
            j = i + 1
            while j < len(lines) and not lines[j].strip(): j += 1
            if j < len(lines):
                url = lines[j].strip()
                if url and not url.startswith('#'):
                    entries.append((line, url)); i = j + 1; continue
        i += 1
    return entries

def ggroup(e):
    m = re.search(r'group-title="([^"]*)"', e); return m.group(1).strip() if m else ""
def gname(e):
    m = re.search(r'#EXTINF[^,]*,(.+)$', e); return m.group(1).strip() if m else ""
def nl(s): return s.lower().strip()

def is_adult(e):   n=nl(gname(e)); g=nl(ggroup(e)); return any(k in n or k in g for k in ADULTO_KW)
def is_anime(e):   n=nl(gname(e)); g=nl(ggroup(e)); return any(k in n or k in g for k in ANIME_KW)
def is_serie(e,u): return bool(SERIE_PATTERN.search(gname(e))) or '/series/' in u
def is_kids_canal(e): n=nl(gname(e)); return any(k in n for k in KIDS_CANAIS_TV)
def is_noticia_intl(e): n=nl(gname(e)); return any(k in n for k in NOTICIAS_INTL)
def is_esporte(e): n=nl(gname(e)); return any(k in n for k in ESPORTES_KW)
def is_discovery(e): n=nl(gname(e)); g=nl(ggroup(e)); return any(k in n or k in g for k in DISC_KW)
def is_variedades(e): n=nl(gname(e)); return any(k in n for k in VAR_KW)

def is_globo_ok(e):
    n = nl(gname(e))
    if any(k in n for k in GLOBO_EXCLUIR_EXPLICIT): return False
    return any(k in n for k in GLOBO_PERMITIDOS)

def is_regional(e): n=nl(gname(e)); return any(k in n for k in REGIONAIS_EXCLUIR)

def quality(e):
    n=nl(gname(e))
    if any(q in n for q in ["fhd","4k","2k","hdr"]): return 0
    if "hd" in n: return 1
    if " sd" in n or n.endswith("sd"): return 2
    if "alternativo" in n or "fonte" in n: return 3
    return 1

def base_name(e):
    n = gname(e)
    return re.sub(
        r'\s*(FHD[²2]?|4K|2K|HDR|UHD|HD[²2]?|SD|Alternativo\s*(HD)?|FONTE\s*\d+|F\d+|\d+k)\s*$',
        '', n, flags=re.IGNORECASE
    ).strip().lower()

def write_m3u(filepath, groups_dict, group_order=None):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write("#EXTM3U\n")
        written = set()
        for grp in (group_order or []):
            if grp not in groups_dict: continue
            written.add(grp)
            for extinf, url in groups_dict[grp]:
                e = re.sub(r'group-title="[^"]*"', f'group-title="{grp}"', extinf)
                f.write(f"{e}\n{url}\n")
        for grp, entries in sorted(groups_dict.items()):
            if grp in written: continue
            for extinf, url in entries:
                e = re.sub(r'group-title="[^"]*"', f'group-title="{grp}"', extinf)
                f.write(f"{e}\n{url}\n")

def dedup_best(canal_map):
    final = defaultdict(list)
    seen_urls = set()
    for grp, canais in canal_map.items():
        for bname, versions in canais.items():
            vs = sorted(versions, key=lambda x: x[0])
            best = vs[0]
            if best[2] not in seen_urls:
                seen_urls.add(best[2])
                final[grp].append((best[1], best[2]))
            if best[0] == 0:
                for v in vs[1:]:
                    if v[0] == 1 and v[2] not in seen_urls:
                        seen_urls.add(v[2])
                        final[grp].append((v[1], v[2]))
                        break
    return final

# ── PRINCIPAL ─────────────────────────────────────────────────────────────────
def main():
    print("🚀 Gerando listas IPTV curadas...\n")

    tv_map = defaultdict(lambda: defaultdict(list))
    filmes_map = defaultdict(lambda: defaultdict(list))
    series_map = defaultdict(lambda: defaultdict(list))
    kids_map = defaultdict(lambda: defaultdict(list))
    animes_map = defaultdict(lambda: defaultdict(list))
    adultos_map = defaultdict(lambda: defaultdict(list))

    total_lidas = excl = 0

    for fp in INPUT_FILES:
        if not os.path.exists(fp):
            print(f"  ⚠ Arquivo não encontrado: {os.path.basename(fp)}")
            continue
        print(f"📂 {os.path.basename(fp)}")
        entries = parse_m3u(fp)
        print(f"   → {len(entries)} entradas")
        total_lidas += len(entries)

        for extinf, url in entries:
            g  = ggroup(extinf)
            gu = g.strip().upper()
            name = gname(extinf)

            adult   = is_adult(extinf)
            anime   = is_anime(extinf) and not adult
            kids_tv = is_kids_canal(extinf) and not adult and not anime
            serie   = is_serie(extinf, url) and not adult and not anime
            is_vod  = url.endswith('.mp4') and not serie and 'cord-cutter' not in url
            notintl = is_noticia_intl(extinf)
            esporte = is_esporte(extinf) and not adult and not anime
            discov  = is_discovery(extinf) and not adult and not anime
            varied  = is_variedades(extinf) and not adult and not anime

            destino = None
            if adult:     destino = "adultos"
            elif anime:   destino = "animes"
            elif serie:   destino = "series"
            elif is_vod:  destino = "filmes"
            elif kids_tv or g.strip() in {"INFANTIS","DESENHOS 24H","ESPECIAIS 24H","KIDS ZONE"}:
                destino = "tv"
            elif g.strip() in GRUPOS_TV or gu in {x.upper() for x in GRUPOS_TV}:
                destino = "tv"
            elif g.strip() in GRUPOS_TV_MUNDIAIS:
                destino = "tv"
            elif g.strip() in GRUPOS_CINEMA or gu in {x.upper() for x in GRUPOS_CINEMA}:
                destino = "tv"
            elif notintl or esporte or discov or varied:
                destino = "tv"
            else:
                excl += 1; continue

            if "GLOBO" in gu or gu in {"ABERTOS","BRAZIL","BRAZIL "}:
                if "GLOBO" in name.upper():
                    if not is_globo_ok(extinf) or is_regional(extinf):
                        excl += 1; continue
                elif is_regional(extinf):
                    excl += 1; continue

            if destino == "tv":
                if kids_tv or g.strip() in {"INFANTIS","DESENHOS 24H","ESPECIAIS 24H","KIDS ZONE","CANAIS | DESENHOS"}:
                    fg = "Kids — Canais"
                elif notintl:  fg = "Notícias"
                elif esporte:  fg = "Esportes"
                elif discov:   fg = "Documentários | Discovery | History"
                elif varied:   fg = "Variedades e Entretenimento"
                else:          fg = GROUP_MAP_TV.get(g.strip(), GROUP_MAP_TV.get(gu, "Outros"))
            elif destino == "series":
                serie_name = re.sub(r'\s*S\d{2}\s*E\d{2}.*$', '', name, flags=re.IGNORECASE).strip()
                fg = serie_name if serie_name else "Séries"
            elif destino == "filmes":  fg = "Filmes"
            elif destino == "animes":  fg = "Animes"
            elif destino == "adultos": fg = "Adultos 18+"
            else:                      fg = "Outros"

            q = quality(extinf); bn = base_name(extinf)
            if destino == "tv":       tv_map[fg][bn].append((q, extinf, url))
            elif destino == "filmes":  filmes_map[fg][bn].append((q, extinf, url))
            elif destino == "series":  series_map[fg][bn].append((q, extinf, url))
            elif destino == "kids":    kids_map["Kids"][bn].append((q, extinf, url))
            elif destino == "animes":  animes_map[fg][bn].append((q, extinf, url))
            elif destino == "adultos": adultos_map[fg][bn].append((q, extinf, url))

    print("\n🔧 Aplicando filtro FHD + HD fallback e deduplicação...")
    tv_f = dedup_best(tv_map); filmes_f = dedup_best(filmes_map)
    series_f = dedup_best(series_map); kids_f = dedup_best(kids_map)
    animes_f = dedup_best(animes_map); adultos_f = dedup_best(adultos_map)

    print(f"\n✍️  Escrevendo 6 arquivos em {LISTAS_DIR}/")
    write_m3u(OUTPUT_TV, tv_f, TV_GROUP_ORDER)
    write_m3u(OUTPUT_FILMES, filmes_f)
    write_m3u(OUTPUT_SERIES, series_f, sorted(series_f.keys()))
    write_m3u(OUTPUT_KIDS, kids_f)
    write_m3u(OUTPUT_ANIMES, animes_f)
    write_m3u(OUTPUT_ADULTOS, adultos_f)

    tv_tot=sum(len(v) for v in tv_f.values())
    fi_tot=sum(len(v) for v in filmes_f.values())
    se_tot=sum(len(v) for v in series_f.values())
    ki_tot=sum(len(v) for v in kids_f.values())
    an_tot=sum(len(v) for v in animes_f.values())
    ad_tot=sum(len(v) for v in adultos_f.values())
    total=tv_tot+fi_tot+se_tot+ki_tot+an_tot+ad_tot

    print(f"\n{'='*60}")
    print(f"📊 RELATÓRIO")
    print(f"{'='*60}")
    print(f"  Entradas lidas:   {total_lidas:>10,}")
    print(f"  Excluídas:        {excl:>10,}")
    print(f"  TOTAL INCLUÍDAS:  {total:>10,}")
    print(f"\n  {'ARQUIVO':<25} {'ENTRADAS':>10}")
    print(f"  {'-'*38}")
    print(f"  lista_tv.m3u8{'':<12} {tv_tot:>10,}")
    for g in TV_GROUP_ORDER:
        if g in tv_f: print(f"    · {g:<28} {len(tv_f[g]):>6}")
    print(f"  lista_filmes.m3u8{'':<8} {fi_tot:>10,}")
    print(f"  lista_series.m3u8{'':<8} {se_tot:>10,}  ({len(series_f)} títulos)")
    print(f"  lista_kids.m3u8{'':<10} {ki_tot:>10,}")
    print(f"  lista_animes.m3u8{'':<8} {an_tot:>10,}")
    print(f"  lista_adultos.m3u8{'':<7} {ad_tot:>10,}")
    print(f"{'='*60}")
    print(f"\n✅ Listas salvas em: {LISTAS_DIR}")

if __name__ == "__main__":
    main()
