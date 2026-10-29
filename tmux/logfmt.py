# ═══════════════════════════════════════════════════════════════
#  Makes container log lines readable (used by docker_logs.py)
#
#  parse(line, stamp=None) → (level, pretty line)
#                 level: "error" | "warning" | "info" | "debug" | None
#                 pretty: a coloured level badge, a short dim local time (docker's own
#                 timestamp when given) and the message first. Understands: JSON (Caddy / FrankenPHP, Monolog…),
#                 logfmt (time= level= msg=), Redis, PostgreSQL, RabbitMQ-style
#                 "[info]", Symfony "app.ERROR:" and plain text with a level word.
#                 HTTP access lines become "GET /path → 200 · 12 ms".
# ═══════════════════════════════════════════════════════════════

import datetime
import json
import re

from tui import ANSI, BLUE, DIM, GREEN, RED, RESET, SUB, TEXT, YELLOW, bg, fg

BADGE = {"error": bg("#f38ba8") + fg("#11111b") + "ERR ",
         "warning": bg("#f9e2af") + fg("#11111b") + "WARN",
         "info": fg("#89b4fa") + "INFO",
         "debug": DIM + "DBUG"}
LEVEL_WORDS = {"emergency": "error", "emerg": "error", "alert": "error", "critical": "error", "crit": "error",
               "fatal": "error", "panic": "error", "error": "error", "err": "error", "severe": "error",
               "warning": "warning", "warn": "warning",
               "notice": "info", "info": "info", "information": "info", "log": "info", "statement": "info",
               "detail": "info", "hint": "info", "context": "info",
               "debug": "debug", "trace": "debug", "verbose": "debug", "dbg": "debug"}
REDIS = re.compile(r"^\d+:[A-Z] (\d+ \w{3} \d{4} [\d:.]+) ([.\-*#]) (.*)$")
REDIS_LEVEL = {".": "debug", "-": "debug", "*": "info", "#": "warning"}
POSTGRES = re.compile(r"^(\d{4}-\d\d-\d\d [\d:.]+) \w+ \[\d+\]\S* ?(?:\S*@\S* )?(\w+):\s+(.*)$")
BRACKET = re.compile(r"^(\d{4}-\d\d-\d\d[T ][\d:.]+(?:[+-]\d\d:?\d\d|Z)?)\s+\[(\w+)\]\s+(?:<[\d.]+>\s+)?(.*)$")
SYMFONY = re.compile(r"^\[([^\]]+)\]\s+([\w.-]+)\.([A-Z]+):\s+(.*)$")
LOGFMT_PAIR = re.compile(r'(\w[\w.]*)=("(?:[^"\\]|\\.)*"|\S+)')
LEADING_TIME = re.compile(r"^\[?(\d{4}[-/]\d\d[-/]\d\d[T ]\d\d:\d\d:\d\d(?:[.,]\d+)?(?:Z|[+-]\d\d:?\d\d| UTC)?)\]?\s*")
ISO_TZ = re.compile(r"^(\d{4}-\d\d-\d\d[T ]\d\d:\d\d:\d\d)(?:[.,]\d+)?(Z|[+-]\d\d:\d\d)$")
WORD_LEVEL = re.compile(r"\b(EMERGENCY|ALERT|CRITICAL|FATAL|PANIC|ERROR|ERR|WARNING|WARN|NOTICE|INFO|DEBUG|TRACE)\b",
                        re.I)


def short_time(value):
    """Epoch numbers or ISO-ish strings → HH:MM:SS (local time for epochs)."""
    if isinstance(value, (int, float)) or (isinstance(value, str) and re.fullmatch(r"\d{9,}(\.\d+)?", value)):
        v = float(value)
        if v > 1e12:          # milliseconds
            v /= 1000
        return datetime.datetime.fromtimestamp(v).strftime("%H:%M:%S")
    m = ISO_TZ.match(str(value))
    if m:                 # an exact moment (Z / +02:00, e.g. docker's own timestamps): show it in local time
        try:
            t = datetime.datetime.fromisoformat(m[1].replace(" ", "T") + ("+00:00" if m[2] == "Z" else m[2]))
            return t.astimezone().strftime("%H:%M:%S")
        except ValueError:
            pass
    m = re.search(r"(\d\d:\d\d:\d\d)", str(value))
    return m[1] if m else str(value)[:8]


def badge(lvl):
    return (BADGE.get(lvl, DIM + "    ") + RESET) if lvl else DIM + "    " + RESET


def status_colour(code):
    c = str(code)
    return RED if c.startswith("5") else YELLOW if c.startswith("4") else GREEN if c.startswith("2") else BLUE


def http_line(d):
    """Caddy access log → 'GET /path → 200 · 12 ms · 1.2K'."""
    req = d.get("request") or {}
    method, uri = req.get("method", ""), req.get("uri", "")
    status = d.get("status", "")
    dur = d.get("duration")
    if isinstance(dur, (int, float)):
        ms = f" · {dur * 1000:.0f} ms" if dur < 1 else f" · {dur:.1f} s"
    else:
        ms = ""
    size = f" · {d['size']}B" if d.get("size") else ""
    return f"{TEXT}{method} {uri}{RESET} {DIM}→{RESET} {status_colour(status)}{status}{RESET}{DIM}{ms}{size}{RESET}"


def from_json(d, stamp=None):
    lvl_raw = str(d.get("level") or d.get("lvl") or d.get("severity") or d.get("level_name") or "").lower()
    lvl = LEVEL_WORDS.get(lvl_raw)
    when = next((d[k] for k in ("ts", "time", "timestamp", "@timestamp", "datetime") if k in d), None)
    logger = d.get("logger") or d.get("channel") or d.get("name") or ""
    msg = d.get("msg") or d.get("message") or ""
    if str(logger).startswith("http.log.access") and isinstance(d.get("request"), dict):
        body, logger = http_line(d), "http"
    else:
        skip = {"level", "lvl", "severity", "level_name", "ts", "time", "timestamp", "@timestamp", "datetime",
                "logger", "channel", "name", "msg", "message"}
        extra = []
        for k, v in d.items():
            if k in skip:
                continue
            if isinstance(v, (dict, list)):
                v = json.dumps(v, separators=(",", ":"))
            v = str(v)
            extra.append(f"{k}={v[:80] + '…' if len(v) > 80 else v}")
        body = f"{TEXT}{msg}{RESET}" + (f" {DIM}{' '.join(extra)}{RESET}" if extra else "")
    head = f"{DIM}{short_time(stamp or when)}{RESET} " if stamp or when is not None else ""
    log = f"{SUB}{logger}{RESET} " if logger else ""
    return lvl, f"{badge(lvl)} {head}{log}{body}"


def parse(line, stamp=None):
    """→ (level, pretty line). `stamp`: docker's own time for the line (`docker logs --timestamps`),
    shown in local time instead of whatever time the program wrote."""
    plain = ANSI.sub("", line).rstrip()
    s = plain.lstrip()
    if s.startswith("{") and s.endswith("}"):
        try:
            d = json.loads(s)
            if isinstance(d, dict):
                return from_json(d, stamp)
        except ValueError:
            pass
    m = REDIS.match(s)
    if m:
        lvl = REDIS_LEVEL.get(m[2])
        return lvl, f"{badge(lvl)} {DIM}{short_time(stamp or m[1])}{RESET} {TEXT}{m[3]}{RESET}"
    m = POSTGRES.match(s)
    if m:
        lvl = LEVEL_WORDS.get(m[2].lower(), "info")
        return lvl, f"{badge(lvl)} {DIM}{short_time(stamp or m[1])}{RESET} {TEXT}{m[3]}{RESET}"
    m = SYMFONY.match(s)
    if m:
        lvl = LEVEL_WORDS.get(m[3].lower())
        return lvl, f"{badge(lvl)} {DIM}{short_time(stamp or m[1])}{RESET} {SUB}{m[2]}{RESET} {TEXT}{m[4]}{RESET}"
    m = BRACKET.match(s)
    if m and m[2].lower() in LEVEL_WORDS:
        lvl = LEVEL_WORDS[m[2].lower()]
        return lvl, f"{badge(lvl)} {DIM}{short_time(stamp or m[1])}{RESET} {TEXT}{m[3]}{RESET}"
    if "level=" in s or "msg=" in s:                       # logfmt
        pairs = dict((k, v.strip('"')) for k, v in LOGFMT_PAIR.findall(s))
        if pairs.get("msg") or pairs.get("level"):
            lvl = LEVEL_WORDS.get(pairs.get("level", "").lower())
            when = pairs.get("time") or pairs.get("ts")
            extra = " ".join(f"{k}={v}" for k, v in pairs.items() if k not in ("time", "ts", "level", "msg"))
            return lvl, (f"{badge(lvl)} " + (f"{DIM}{short_time(stamp or when)}{RESET} " if stamp or when else "")
                         + f"{TEXT}{pairs.get('msg', '')}{RESET}" + (f" {DIM}{extra}{RESET}" if extra else ""))
    # plain text: a leading timestamp goes dim, a level word gives the badge
    m = LEADING_TIME.match(s)
    when, rest = (m[1], s[m.end():]) if m else (None, s)
    w = WORD_LEVEL.search(rest[:60])
    lvl = LEVEL_WORDS.get(w[1].lower()) if w else None
    colour = RED if lvl == "error" else YELLOW if lvl == "warning" else TEXT
    return lvl, (f"{badge(lvl)} " + (f"{DIM}{short_time(stamp or when)}{RESET} " if stamp or when else "") + f"{colour}{rest}{RESET}")


def mark(line, terms):
    """Highlight every term (case-insensitive) in a coloured line, keeping its colours."""
    if not terms:
        return line
    plain = ANSI.sub("", line)
    low = plain.lower()
    spans = []
    for t in terms:
        start = low.find(t)
        while t and start >= 0:
            spans.append((start, start + len(t)))
            start = low.find(t, start + len(t))
    if not spans:
        return line
    hit = [False] * len(plain)
    for a, b in spans:
        for i in range(a, b):
            hit[i] = True
    out, vis, i, last_sgr, on = [], 0, 0, "", False
    MARK = bg("#f9e2af") + fg("#11111b")
    while i < len(line):
        m = ANSI.match(line, i)
        if m:
            last_sgr = m.group()
            if not on:
                out.append(last_sgr)
            i = m.end()
            continue
        want = hit[vis] if vis < len(hit) else False
        if want and not on:
            out.append(MARK)
            on = True
        elif not want and on:
            out.append(RESET + last_sgr)
            on = False
        out.append(line[i])
        vis += 1
        i += 1
    if on:
        out.append(RESET)
    return "".join(out)
