import discord
from discord import app_commands
import httpx
import os
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

BASE_URL      = "https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/scoreboard"
STANDINGS_URL = "https://site.api.espn.com/apis/v2/sports/soccer/fifa.world/standings"
TEAM_URL      = "https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/teams"
SUMMARY_URL   = "https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/summary"

BRT = timezone(timedelta(hours=-3))

# ─── Bot setup ────────────────────────────────────────────────────────────────

intents = discord.Intents.default()
bot  = discord.Client(intents=intents)
tree = app_commands.CommandTree(bot)

# ─── Helpers ──────────────────────────────────────────────────────────────────

async def espn_get(url: str, params: dict = {}) -> dict:
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(url, params=params)
    return r.json()

async def get_all_events() -> list:
    """Busca todos os jogos da Copa (scoreboard geral sem data)."""
    data = await espn_get(BASE_URL)
    return data.get("events", [])

async def find_next_event(team_name: str):
    """Retorna o próximo evento (pré ou ao vivo) de um time."""
    events = await get_all_events()
    tl = team_name.lower()
    for e in events:
        comp = e["competitions"][0]
        home = comp["competitors"][0]["team"]["displayName"]
        away = comp["competitors"][1]["team"]["displayName"]
        if tl in home.lower() or tl in away.lower():
            if e["status"]["type"]["state"] in ("pre", "in"):
                return e
    return None

FLAGS = {
    "Brazil": "🇧🇷", "Argentina": "🇦🇷", "France": "🇫🇷", "Germany": "🇩🇪",
    "Spain": "🇪🇸", "England": "🏴󠁧󠁢󠁥󠁮󠁧󠁿", "Portugal": "🇵🇹", "Netherlands": "🇳🇱",
    "Italy": "🇮🇹", "Uruguay": "🇺🇾", "Mexico": "🇲🇽", "United States": "🇺🇸",
    "Japan": "🇯🇵", "Morocco": "🇲🇦", "Croatia": "🇭🇷", "Serbia": "🇷🇸",
    "Switzerland": "🇨🇭", "Senegal": "🇸🇳", "Australia": "🇦🇺", "Iran": "🇮🇷",
    "South Korea": "🇰🇷", "Ghana": "🇬🇭", "Cameroon": "🇨🇲", "Canada": "🇨🇦",
    "Ecuador": "🇪🇨", "Qatar": "🇶🇦", "Saudi Arabia": "🇸🇦", "Tunisia": "🇹🇳",
    "Colombia": "🇨🇴", "Chile": "🇨🇱", "Peru": "🇵🇪", "Venezuela": "🇻🇪",
    "Poland": "🇵🇱", "Denmark": "🇩🇰", "Belgium": "🇧🇪", "Wales": "🏴󠁧󠁢󠁷󠁬󠁳󠁿",
    "Costa Rica": "🇨🇷", "New Zealand": "🇳🇿", "South Africa": "🇿🇦",
    "Czech Republic": "🇨🇿", "Czechia": "🇨🇿", "Paraguay": "🇵🇾",
    "Bosnia and Herzegovina": "🇧🇦",
}

POSITIONS_PT = {
    "Goalkeeper": "Goleiro", "Defender": "Zagueiro/Lateral",
    "Midfielder": "Meio-campo", "Forward": "Atacante",
    "GK": "Goleiro", "DF": "Defensor", "MF": "Meio-campo", "FW": "Atacante",
}

def flag(country: str) -> str:
    return FLAGS.get(country, "🏳️")

def fmt_date(date_str: str) -> str:
    try:
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00")).astimezone(BRT)
        return dt.strftime("%d/%m/%Y às %H:%M (Brasília)")
    except:
        return date_str

def pos_pt(pos: str) -> str:
    return POSITIONS_PT.get(pos, pos)

# ─── Decorators reutilizáveis ─────────────────────────────────────────────────

def global_command(name, description):
    def decorator(func):
        func = app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)(func)
        func = app_commands.allowed_installs(guilds=True, users=True)(func)
        func = tree.command(name=name, description=description)(func)
        return func
    return decorator


# ─── /jogoshoje ───────────────────────────────────────────────────────────────

@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@app_commands.allowed_installs(guilds=True, users=True)
@tree.command(name="jogoshoje", description="Todos os jogos da Copa do Mundo hoje")
async def jogoshoje(interaction: discord.Interaction):
    await interaction.response.defer()

    today = datetime.now(BRT).strftime("%Y%m%d")
    data   = await espn_get(BASE_URL, {"dates": today})
    events = data.get("events", [])

    if not events:
        await interaction.followup.send("📅 Nenhum jogo da Copa do Mundo hoje.")
        return

    embed = discord.Embed(title="📅 Jogos de Hoje — Copa do Mundo 2026", color=0x1565C0)

    for event in events:
        comp       = event["competitions"][0]
        home       = comp["competitors"][0]["team"]["displayName"]
        away       = comp["competitors"][1]["team"]["displayName"]
        home_score = comp["competitors"][0].get("score", "—")
        away_score = comp["competitors"][1].get("score", "—")
        status     = event["status"]["type"]["description"]
        date       = fmt_date(event["date"])

        if status == "Scheduled":
            placar = f"🕐 {date}"
        elif status in ("Final", "Full Time", "FT"):
            placar = f"**{home_score} — {away_score}**  •  Encerrado"
        else:
            clock  = event["status"].get("displayClock", "")
            placar = f"🔴 **{home_score} — {away_score}**  •  {clock}"

        embed.add_field(
            name=f"{flag(home)} {home} vs {away} {flag(away)}",
            value=placar, inline=False,
        )

    embed.set_footer(text="Copa do Mundo 2026 • Horário de Brasília")
    await interaction.followup.send(embed=embed)


# ─── /proximojogo ─────────────────────────────────────────────────────────────

@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@app_commands.allowed_installs(guilds=True, users=True)
@tree.command(name="proximojogo", description="Próximo jogo de um time na Copa do Mundo 2026")
@app_commands.describe(time="Nome do time em inglês. Ex: Brazil, France, Mexico")
async def proximojogo(interaction: discord.Interaction, time: str):
    await interaction.response.defer()

    event = await find_next_event(time)

    if not event:
        await interaction.followup.send(
            f"❌ Nenhum jogo futuro encontrado para **{time}**.\n"
            f"💡 Use o nome em inglês. Ex: `Brazil`, `France`, `United States`"
        )
        return

    comp    = event["competitions"][0]
    home    = comp["competitors"][0]["team"]["displayName"]
    away    = comp["competitors"][1]["team"]["displayName"]
    date    = fmt_date(event["date"])
    venue   = comp.get("venue", {})
    stadium = venue.get("fullName", "—")
    city    = venue.get("address", {}).get("city", "—")
    note    = (comp.get("notes") or [{}])[0].get("headline", "Fase de Grupos")

    embed = discord.Embed(
        title=f"📅 Próximo Jogo — {flag(home)} {home}",
        color=0x1565C0,
    )
    embed.add_field(
        name="⚽ Confronto",
        value=f"{flag(home)} **{home}** vs **{away}** {flag(away)}",
        inline=False,
    )
    embed.add_field(name="🗓️ Data e Hora", value=date,    inline=True)
    embed.add_field(name="🏆 Fase",        value=note,    inline=True)
    embed.add_field(name="🏟️ Estádio",    value=f"{stadium}, {city}", inline=False)
    embed.set_footer(text="Use /informacoes para ver o elenco • Copa do Mundo 2026")

    await interaction.followup.send(embed=embed)


# ─── /placar ──────────────────────────────────────────────────────────────────

@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@app_commands.allowed_installs(guilds=True, users=True)
@tree.command(name="placar", description="Placares ao vivo ou de um time específico")
@app_commands.describe(time="Nome do time (opcional). Ex: Brazil, France")
async def placar(interaction: discord.Interaction, time: str = None):
    await interaction.response.defer()

    events = await get_all_events()
    live   = [e for e in events if e["status"]["type"]["state"] == "in"]

    if time:
        tl   = time.lower()
        live = [
            e for e in events
            if tl in e["competitions"][0]["competitors"][0]["team"]["displayName"].lower()
            or tl in e["competitions"][0]["competitors"][1]["team"]["displayName"].lower()
        ]

    if not live:
        msg = f"⏸️ **{time}** não está jogando agora." if time else "⏸️ Nenhum jogo ao vivo agora."
        await interaction.followup.send(msg)
        return

    embed = discord.Embed(title="🔴 Ao Vivo — Copa do Mundo 2026", color=0xCC0000)

    for event in live:
        comp       = event["competitions"][0]
        home       = comp["competitors"][0]["team"]["displayName"]
        away       = comp["competitors"][1]["team"]["displayName"]
        home_score = comp["competitors"][0].get("score", "0")
        away_score = comp["competitors"][1].get("score", "0")
        clock      = event["status"].get("displayClock", "")
        status     = event["status"]["type"]["description"]

        embed.add_field(
            name=f"{flag(home)} {home} vs {away} {flag(away)}",
            value=f"**{home_score} — {away_score}**  •  ⏱️ {clock} ({status})",
            inline=False,
        )

    await interaction.followup.send(embed=embed)


# ─── /informacoes ─────────────────────────────────────────────────────────────

@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@app_commands.allowed_installs(guilds=True, users=True)
@tree.command(name="informacoes", description="Informações detalhadas de um time na Copa 2026")
@app_commands.describe(time="Nome do time em inglês. Ex: Brazil, France, Mexico")
async def informacoes(interaction: discord.Interaction, time: str):
    await interaction.response.defer()

    tl = time.lower()

    # 1. Próximo jogo
    event     = await find_next_event(time)
    team_name = time
    oponente  = "—"
    data_jogo = "—"
    fase      = "—"
    stadium   = "—"
    city      = "—"

    if event:
        comp      = event["competitions"][0]
        home      = comp["competitors"][0]["team"]["displayName"]
        away      = comp["competitors"][1]["team"]["displayName"]
        team_name = home if tl in home.lower() else away
        oponente  = away if tl in home.lower() else home
        data_jogo = fmt_date(event["date"])
        fase      = (comp.get("notes") or [{}])[0].get("headline", "Fase de Grupos")
        venue     = comp.get("venue", {})
        stadium   = venue.get("fullName", "—")
        city      = venue.get("address", {}).get("city", "—")

    # 2. Resultados anteriores na Copa
    all_events  = await get_all_events()
    resultados  = []
    for e in all_events:
        if e["status"]["type"]["state"] != "post":
            continue
        comp = e["competitions"][0]
        h    = comp["competitors"][0]["team"]["displayName"]
        a    = comp["competitors"][1]["team"]["displayName"]
        if tl not in h.lower() and tl not in a.lower():
            continue
        hg   = comp["competitors"][0].get("score", "0")
        ag   = comp["competitors"][1].get("score", "0")
        resultados.append((h, a, hg, ag))

    # 3. Posição no grupo via standings
    standings_data = await espn_get(STANDINGS_URL)
    posicao_grupo  = None
    grupo_nome     = None
    stats_time     = None

    try:
        for group in standings_data.get("standings", []):
            for i, entry in enumerate(group.get("standings", []), 1):
                if tl in entry["team"]["displayName"].lower():
                    posicao_grupo = i
                    grupo_nome    = group.get("name", "—")
                    stats_time    = {s["name"]: s["displayValue"] for s in entry.get("stats", [])}
                    team_name     = entry["team"]["displayName"]
                    break
            if posicao_grupo:
                break
    except Exception:
        pass

    # 4. Monta embed
    embed = discord.Embed(
        title=f"{flag(team_name)} {team_name} — Copa do Mundo 2026",
        color=0x004D40,
    )

    # Próximo jogo
    if event:
        embed.add_field(
            name="📅 Próximo Jogo",
            value=(
                f"{flag(team_name)} **{team_name}** vs {flag(oponente)} **{oponente}**\n"
                f"🗓️ {data_jogo}\n"
                f"🏟️ {stadium}, {city}\n"
                f"🏆 {fase}"
            ),
            inline=False,
        )

    # Posição no grupo
    if posicao_grupo and stats_time:
        pts    = stats_time.get("points", "0")
        played = stats_time.get("gamesPlayed", "0")
        won    = stats_time.get("wins", "0")
        drawn  = stats_time.get("ties", "0")
        lost   = stats_time.get("losses", "0")
        gf     = stats_time.get("pointsFor", stats_time.get("goalsFor", "0"))
        gc     = stats_time.get("pointsAgainst", stats_time.get("goalsAgainst", "0"))
        gd     = stats_time.get("pointDifferential", "0")
        classif = "✅ Classificado" if posicao_grupo <= 2 else "⏳ Em disputa"

        embed.add_field(
            name=f"📊 {grupo_nome} — {classif}",
            value=(
                f"`{posicao_grupo}º lugar`  •  **{pts} pts**\n"
                f"🎮 {played}j  ✅ {won}v  🤝 {drawn}e  ❌ {lost}d\n"
                f"⚽ Gols: {gf} marcados / {gc} sofridos  •  GD {gd}"
            ),
            inline=False,
        )

    # Últimos resultados
    if resultados:
        linhas = []
        for h, a, hg, ag in resultados[-5:]:
            is_home   = tl in h.lower()
            tm_gols   = int(hg) if is_home else int(ag)
            op_gols   = int(ag) if is_home else int(hg)
            oponente_ = a if is_home else h
            if tm_gols > op_gols:
                res = "✅"
            elif tm_gols == op_gols:
                res = "🤝"
            else:
                res = "❌"
            if is_home:
                linhas.append(f"{res} {flag(h)} **{h}** `{hg}—{ag}` {flag(a)} **{a}**")
            else:
                linhas.append(f"{res} {flag(a)} **{a}** `{ag}—{hg}` {flag(h)} **{h}**")

        embed.add_field(
            name="📋 Últimos Resultados na Copa",
            value="\n".join(linhas),
            inline=False,
        )
    else:
        embed.add_field(
            name="📋 Resultados",
            value="Ainda não jogou na Copa.",
            inline=False,
        )

    embed.set_footer(text="Copa do Mundo 2026 • Dados via ESPN")
    await interaction.followup.send(embed=embed)


# ─── /classificacao ───────────────────────────────────────────────────────────

@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@app_commands.allowed_installs(guilds=True, users=True)
@tree.command(name="classificacao", description="Tabela de classificação da Copa do Mundo 2026")
@app_commands.describe(grupo="Letra do grupo (opcional). Ex: A, B, C")
async def classificacao(interaction: discord.Interaction, grupo: str = None):
    await interaction.response.defer()

    data = await espn_get(STANDINGS_URL)

    try:
        groups = data["standings"]
    except (KeyError, TypeError):
        await interaction.followup.send("❌ Classificação não disponível ainda. Começa dia 11/06!")
        return

    embed = discord.Embed(title="🏆 Classificação — Copa do Mundo 2026", color=0x6A1B9A)

    for group in groups:
        group_name = group.get("name", "Grupo")

        if grupo and not group_name.upper().endswith(grupo.upper()):
            continue

        lines = []
        for i, entry in enumerate(group.get("standings", []), 1):
            name  = entry["team"]["displayName"]
            stats = {s["name"]: s["displayValue"] for s in entry.get("stats", [])}
            pts   = stats.get("points", "0")
            played = stats.get("gamesPlayed", "0")
            won   = stats.get("wins", "0")
            drawn = stats.get("ties", "0")
            lost  = stats.get("losses", "0")
            gd    = stats.get("pointDifferential", "0")
            prefix = "✅" if i <= 2 else "   "
            lines.append(
                f"{prefix}`{i}.` {flag(name)} **{name}**\n"
                f"       {pts}pts  |  {played}j  {won}v {drawn}e {lost}d  |  GD {gd}"
            )

        if lines:
            embed.add_field(name=f"📌 {group_name}", value="\n".join(lines), inline=True)

    if not embed.fields:
        embed.description = "Grupos ainda não disponíveis. A Copa começa dia 11/06!"

    await interaction.followup.send(embed=embed)


# ─── /proximosjogos ──────────────────────────────────────────────────────────

@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@app_commands.allowed_installs(guilds=True, users=True)
@tree.command(name="proximosjogos", description="Jogos da Copa do Mundo amanhã")
async def proximosjogos(interaction: discord.Interaction):
    await interaction.response.defer()

    amanha = (datetime.now(BRT) + timedelta(days=1)).strftime("%Y%m%d")
    data   = await espn_get(BASE_URL, {"dates": amanha})
    events = data.get("events", [])

    if not events:
        await interaction.followup.send("📅 Nenhum jogo da Copa do Mundo amanhã.")
        return

    data_fmt = (datetime.now(BRT) + timedelta(days=1)).strftime("%d/%m/%Y")
    embed = discord.Embed(
        title=f"📅 Jogos de Amanhã ({data_fmt}) — Copa do Mundo 2026",
        color=0x0D47A1,
    )

    for event in events:
        comp  = event["competitions"][0]
        home  = comp["competitors"][0]["team"]["displayName"]
        away  = comp["competitors"][1]["team"]["displayName"]
        date  = fmt_date(event["date"])
        note  = (comp.get("notes") or [{}])[0].get("headline", "Fase de Grupos")

        embed.add_field(
            name=f"{flag(home)} {home} vs {away} {flag(away)}",
            value=f"🕐 {date}  •  {note}",
            inline=False,
        )

    embed.set_footer(text="Copa do Mundo 2026 • Horário de Brasília")
    await interaction.followup.send(embed=embed)


# ─── /noticias ───────────────────────────────────────────────────────────────

@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@app_commands.allowed_installs(guilds=True, users=True)
@tree.command(name="noticias", description="Últimas notícias da Copa do Mundo 2026")
async def noticias(interaction: discord.Interaction):
    await interaction.response.defer()

    data = await espn_get("https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/news")
    articles = data.get("articles", [])

    if not articles:
        await interaction.followup.send("📰 Nenhuma notícia disponível no momento.")
        return

    embed = discord.Embed(
        title="📰 Últimas Notícias — Copa do Mundo 2026",
        color=0x1565C0,
    )

    for article in articles[:8]:
        title    = article.get("headline", "Sem título")
        desc     = article.get("description", "")
        link     = article.get("links", {}).get("web", {}).get("href", "")
        published = article.get("published", "")

        # Formata data
        try:
            dt = datetime.fromisoformat(published.replace("Z", "+00:00")).astimezone(BRT)
            data_fmt = dt.strftime("%d/%m %H:%M")
        except:
            data_fmt = ""

        value = ""
        if desc:
            value += f"{desc[:100]}{'...' if len(desc) > 100 else ''}\n"
        if data_fmt:
            value += f"🕐 {data_fmt}"
        if link:
            value += f"  •  [Ler mais]({link})"

        embed.add_field(name=f"📌 {title}", value=value or "—", inline=False)

    embed.set_footer(text="Copa do Mundo 2026 • Fonte: ESPN")
    await interaction.followup.send(embed=embed)


# ─── /comandos ───────────────────────────────────────────────────────────────

@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@app_commands.allowed_installs(guilds=True, users=True)
@tree.command(name="comandos", description="Lista todos os comandos do bot")
async def comandos(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🌍  HallowsWorldCup — Comandos",
        description="*Todos os comandos da Copa do Mundo 2026*",
        color=0x1a1a2e,
    )

    comandos_lista = [
        (
            "📅  /jogoshoje",
            "Mostra todos os jogos da Copa do Mundo no dia de hoje.",
            "`/jogoshoje`",
        ),
        (
            "🗓️  /proximosjogos",
            "Mostra todos os jogos da Copa do Mundo amanhã.",
            "`/proximosjogos`",
        ),
        (
            "🔴  /placar",
            "Placares ao vivo. Filtre por time ou veja todos de uma vez.",
            "`/placar` — todos ao vivo\n`/placar time:Brazil` — só o Brasil",
        ),
        (
            "⏭️  /proximojogo",
            "Próximo jogo de um time específico na Copa.",
            "`/proximojogo time:Brazil`",
        ),
        (
            "🧬  /informacoes",
            "Informações detalhadas do time: próximo jogo e elenco convocado.",
            "`/informacoes time:Mexico`",
        ),
        (
            "🏆  /classificacao",
            "Tabela de classificação por grupos. Filtre por grupo se quiser.",
            "`/classificacao` — todos os grupos\n`/classificacao grupo:A` — só o Grupo A",
        ),
        (
            "📰  /noticias",
            "Últimas notícias da Copa do Mundo 2026.",
            "`/noticias`",
        ),
        (
            "📖  /comandos",
            "Exibe esta lista de comandos.",
            "`/comandos`",
        ),
    ]

    for nome, desc, exemplo in comandos_lista:
        embed.add_field(
            name=nome,
            value=f"{desc}\n> {exemplo}",
            inline=False,
        )

    embed.set_footer(text="Copa do Mundo 2026  •  Dados via ESPN  •  Horário de Brasília")
    await interaction.response.send_message(embed=embed)


# ─── Events ───────────────────────────────────────────────────────────────────

@bot.event
async def on_ready():
    for guild in bot.guilds:
        tree.clear_commands(guild=guild)
        await tree.sync(guild=guild)

    synced = await tree.sync()
    print(f"✅ Bot conectado como {bot.user}")
    print(f"📡 Slash commands globais: {[c.name for c in synced]}")


bot.run(DISCORD_TOKEN)
