"""Multilingual Love Heart — generative typographic animation."""

from __future__ import annotations

import math
import random
import turtle
import tkinter.font as tkfont

# --- canvas -----------------------------------------------------------------
WIDTH, HEIGHT = 900, 900
SCALE = 23
ORIGIN_Y = 18
BG = "#050108"
TITLE = "Love You"

# --- timing -----------------------------------------------------------------
DURATION_MS = 11_000
TICK_MS = 16
ANIM_FRAMES = 44
LIFT = 36
SPAWN_JITTER = 10

# --- type -------------------------------------------------------------------
GAP = 8
SIZES = (9, 10, 11, 12)
FONT_CANDIDATES = {
    "ko": ("Malgun Gothic", "AppleGothic", "NanumGothic"),
    "ja": ("Yu Gothic UI", "Yu Gothic", "Meiryo", "Hiragino Sans"),
    "zh": ("Microsoft YaHei UI", "Microsoft YaHei", "PingFang SC", "SimHei"),
    "hi": ("Nirmala UI", "Mangal", "Kohinoor Devanagari"),
    "th": ("Leelawadee UI", "Tahoma", "Thonburi"),
    "ar": ("Segoe UI", "Tahoma", "Arial Unicode MS"),
    "he": ("Segoe UI", "Arial Hebrew", "Tahoma"),
    "el": ("Segoe UI", "Calibri", "Arial"),
    "cyr": ("Segoe UI", "Calibri", "Arial"),
    "lat": ("Segoe UI Semibold", "Segoe UI", "Calibri", "Arial", "Helvetica"),
}

PHRASES = [
    ("I love you", "lat"),
    ("Seni seviyorum", "lat"),
    ("Te amo", "lat"),
    ("Je t'aime", "lat"),
    ("Ich liebe dich", "lat"),
    ("Ti amo", "lat"),
    ("Eu te amo", "lat"),
    ("T'estimo", "lat"),
    ("Te iubesc", "lat"),
    ("Szeretlek", "lat"),
    ("Miluji tě", "lat"),
    ("Kocham cię", "lat"),
    ("Jag älskar dig", "lat"),
    ("Jeg elsker deg", "lat"),
    ("Ik hou van jou", "lat"),
    ("Minä rakastan sinua", "lat"),
    ("Mahal kita", "lat"),
    ("Aku cinta kamu", "lat"),
    ("Anh yêu em", "lat"),
    ("Nakupenda", "lat"),
    ("Я тебя люблю", "cyr"),
    ("Я тебе кохаю", "cyr"),
    ("Σ' αγαπώ", "el"),
    ("사랑해", "ko"),
    ("愛してる", "ja"),
    ("我爱你", "zh"),
    ("मैं तुमसे प्यार करता हूँ", "hi"),
    ("ฉันรักเธอ", "th"),
    ("أحبك", "ar"),
    ("אני אוהב אותך", "he"),
]

WINE = (0.52, 0.0, 0.08)
CRIMSON = (0.88, 0.04, 0.13)
BLOOD = (0.99, 0.16, 0.22)
FLASH = (1.0, 0.82, 0.82)
GLOW = (0.55, 0.02, 0.10)
HINT = "#6a3040"


def clamp(v: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return lo if v < lo else hi if v > hi else v


def mix(a, b, k: float):
    k = clamp(k)
    return tuple(p + (q - p) * k for p, q in zip(a, b))


def dim(c, k: float):
    return tuple(v * k for v in c)


def hx(c) -> str:
    return "#%02x%02x%02x" % tuple(int(clamp(v) * 255) for v in c)


def heart(a: float):
    x = 16 * (math.sin(a) ** 3)
    y = (
        13 * math.cos(a)
        - 5 * math.cos(2 * a)
        - 2 * math.cos(3 * a)
        - math.cos(4 * a)
    )
    return x * SCALE, y * SCALE + ORIGIN_Y


def ease_out_cubic(u: float) -> float:
    u = clamp(u)
    return 1 - (1 - u) ** 3


def flash_envelope(u: float) -> float:
    t = clamp((u - 0.52) / 0.48)
    return math.sin(math.pi * t)


class LoveHeart:
    def __init__(self, seed: int | None = None):
        self.rng = random.Random(seed)
        self.seed = seed
        self.screen = turtle.Screen()
        self.screen.setup(WIDTH, HEIGHT)
        self.screen.bgcolor(BG)
        self.screen.title(TITLE)
        self.screen.tracer(0)
        turtle.hideturtle()

        self.cv = self.screen.getcanvas()
        self.root = self.cv.winfo_toplevel()
        self.root.resizable(False, False)
        self._center_window()

        self.bgc = tuple(int(BG[i : i + 2], 16) / 255 for i in (1, 3, 5))
        self._families = self._resolve_fonts()
        self._font_cache: dict[tuple[str, int], tkfont.Font] = {}

        self.poly = [heart(2 * math.pi * i / 720) for i in range(720)]
        self.edges = list(zip(self.poly, self.poly[1:] + self.poly[:1]))
        self.ymax = max(p[1] for p in self.poly)
        self.ymin = min(p[1] for p in self.poly)
        self.cy = (self.ymax + self.ymin) / 2

        self.main_ids: list[tuple[int, tuple]] = []
        self.active: list[dict] = []
        self.sparkles: list[dict] = []
        self.order: list[dict] = []
        self.items = iter(())
        self.acc = 0.0
        self.spawning = True
        self.elapsed = 0
        self.hint_id = None
        self.after_token = None
        self.epoch = 0

        self._bind()
        self._start_scene()

    def _center_window(self):
        self.root.update_idletasks()
        sw, sh = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        x = (sw - WIDTH) // 2
        y = max(0, (sh - HEIGHT) // 2 - 20)
        self.root.geometry(f"{WIDTH}x{HEIGHT}+{x}+{y}")

    def _bind(self):
        self.root.bind("<Escape>", lambda e: self.root.destroy())
        self.root.bind("<space>", lambda e: self.replay(False))
        self.root.bind("<Return>", lambda e: self.replay(False))
        self.root.bind("r", lambda e: self.replay(True))
        self.root.bind("R", lambda e: self.replay(True))
        self.cv.bind("<Button-1>", lambda e: self.replay(False))
        self.cv.focus_set()

    def _available(self) -> set[str]:
        return {name.lower() for name in tkfont.families(self.root)}

    def _resolve_fonts(self) -> dict[str, str]:
        have = self._available()
        resolved = {}
        fallback = "Arial"
        for script, names in FONT_CANDIDATES.items():
            pick = next((n for n in names if n.lower() in have), fallback)
            resolved[script] = pick
        return resolved

    def font(self, script: str, size: int) -> tkfont.Font:
        family = self._families.get(script, self._families["lat"])
        key = (family, size)
        if key not in self._font_cache:
            self._font_cache[key] = tkfont.Font(
                root=self.root, family=family, size=size, weight="bold"
            )
        return self._font_cache[key]

    def font_tuple(self, script: str, size: int, extra: int = 0):
        family = self._families.get(script, self._families["lat"])
        return (family, size + extra, "bold")

    def dist(self, x: float, y: float) -> float:
        return math.hypot(x / (16 * SCALE), (y - self.cy) / (14.5 * SCALE))

    def spans(self, y: float):
        xs = []
        for (x1, y1), (x2, y2) in self.edges:
            if (y1 <= y < y2) or (y2 <= y < y1):
                xs.append(x1 + (y - y1) * (x2 - x1) / (y2 - y1))
        xs.sort()
        return list(zip(xs[0::2], xs[1::2]))

    @staticmethod
    def intersect(a, b):
        out = []
        for p in a:
            for q in b:
                lo, hi = max(p[0], q[0]), min(p[1], q[1])
                if hi - lo > 16:
                    out.append((lo, hi))
        return out

    def phrase_cycle(self):
        while True:
            order = PHRASES[:]
            self.rng.shuffle(order)
            yield from order

    def build(self) -> list[dict]:
        cycle = self.phrase_cycle()
        row_h = (
            max(
                self.font(script, size).metrics("linespace")
                for script, _ in FONT_CANDIDATES.items()
                for size in SIZES
            )
            + 3
        )
        half = row_h / 2
        placed: list[dict] = []

        y = self.ymax - half
        while y > self.ymin + half:
            row = self.intersect(self.spans(y + half), self.spans(y - half))
            for lo, hi in row:
                lo += 5
                hi -= 5
                cur = lo + self.rng.uniform(0, 8)
                line = []
                while True:
                    fit = None
                    for _ in range(12):
                        text, script = next(cycle)
                        size = self.rng.choice(SIZES)
                        w = self.font(script, size).measure(text)
                        if cur + w <= hi:
                            fit = (text, script, size, w)
                            break
                    if not fit:
                        break
                    text, script, size, w = fit
                    line.append([cur + w / 2, text, script, size, w])
                    cur += w + GAP

                if not line:
                    continue
                if len(line) > 1:
                    left = hi - (line[-1][0] + line[-1][4] / 2)
                    for i, it in enumerate(line):
                        it[0] += left * i / (len(line) - 1)
                else:
                    line[0][0] = (lo + hi) / 2

                for i, (x, text, script, size, w) in enumerate(line):
                    placed.append(
                        dict(
                            x=x,
                            y=y,
                            text=text,
                            script=script,
                            size=size,
                            edge=i == 0 or i == len(line) - 1,
                        )
                    )
            y -= row_h

        for p in placed:
            rad = min(1.0, self.dist(p["x"], p["y"]))
            base = mix(WINE, CRIMSON, 0.2 + 0.8 * rad)
            base = mix(
                base,
                BLOOD,
                self.rng.uniform(0, 0.32) + (0.28 if p["edge"] else 0),
            )
            p["color"] = tuple(min(1.0, v) for v in base)
            p["rad"] = rad

        rim = [p for p in placed if p["edge"]]
        inner = [p for p in placed if not p["edge"]]
        rim.sort(key=lambda p: math.atan2(p["x"], p["y"] - self.cy) % (2 * math.pi))
        inner.sort(key=lambda p: -p["rad"] + self.rng.uniform(0, 0.08))
        return rim + inner

    def draw_backdrop(self):
        for i, k in enumerate((0.18, 0.10, 0.05)):
            r = 210 + i * 70
            self.cv.create_oval(
                -r, -r + 30, r, r + 30, fill=hx(mix(self.bgc, GLOW, k)), outline=""
            )
        pts = []
        for x, y in self.poly:
            pts.extend((x, -y))
        for width, color in (
            (28, mix(self.bgc, GLOW, 0.55)),
            (16, mix(self.bgc, CRIMSON, 0.45)),
            (7, mix(WINE, CRIMSON, 0.5)),
        ):
            self.cv.create_line(
                *pts,
                fill=hx(color),
                width=width,
                smooth=True,
                splinesteps=24,
                capstyle="round",
                joinstyle="round",
            )
        self.cv.create_line(
            *pts,
            fill=hx(mix(CRIMSON, FLASH, 0.15)),
            width=2,
            smooth=True,
            splinesteps=24,
        )

    def draw_hint(self, text: str):
        if self.hint_id:
            self.cv.delete(self.hint_id)
        self.hint_id = self.cv.create_text(
            0,
            HEIGHT // 2 - 36,
            text=text,
            fill=HINT,
            font=self.font_tuple("lat", 11),
        )

    def spawn(self, p: dict):
        x, y = p["x"], -p["y"]
        size, text, c = p["size"], p["text"], p["color"]
        script = p["script"]
        font = self.font_tuple(script, size)
        big = self.font_tuple(script, size, 1)

        shadow = self.cv.create_text(x + 2, y + 3, text=text, font=font, fill=BG)
        halo = self.cv.create_text(x, y, text=text, font=big, fill=BG)
        main = self.cv.create_text(x, y - LIFT, text=text, font=font, fill=BG)

        p.update(
            shadow=shadow,
            halo=halo,
            main=main,
            f=0,
            dx=self.rng.uniform(-SPAWN_JITTER, SPAWN_JITTER),
        )
        self.main_ids.append((main, c))
        self.active.append(p)
        if self.rng.random() < 0.12:
            self._sparkle(x, y, c)

    def _sparkle(self, x, y, c):
        jx = x + self.rng.uniform(-18, 18)
        jy = y + self.rng.uniform(-12, 12)
        s = self.rng.uniform(1.6, 3.2)
        item = self.cv.create_oval(
            jx - s, jy - s, jx + s, jy + s, fill=hx(mix(c, FLASH, 0.7)), outline=""
        )
        self.sparkles.append(dict(id=item, f=0, life=18 + self.rng.randint(0, 10)))

    def animate(self, p: dict) -> bool:
        p["f"] += 1
        u = clamp(p["f"] / ANIM_FRAMES)
        e = ease_out_cubic(u)
        c = p["color"]
        x, y = p["x"], -p["y"]
        px = x + p["dx"] * (1 - e)
        py = y - (1 - e) * LIFT

        self.cv.itemconfig(p["shadow"], fill=hx(mix(self.bgc, dim(c, 0.28), e)))
        self.cv.itemconfig(p["halo"], fill=hx(mix(self.bgc, dim(c, 0.22), e * e)))
        self.cv.coords(p["halo"], px, py)

        col = mix(mix(self.bgc, c, e**1.45), FLASH, 0.72 * flash_envelope(u))
        self.cv.itemconfig(p["main"], fill=hx(col))
        self.cv.coords(p["main"], px, py)

        if u >= 1:
            self.cv.coords(p["halo"], x, y)
            self.cv.coords(p["main"], x, y)
            self.cv.itemconfig(p["main"], fill=hx(c))
            return False
        return True

    def animate_sparkles(self):
        keep = []
        for sp in self.sparkles:
            sp["f"] += 1
            t = sp["f"] / sp["life"]
            if t >= 1:
                self.cv.delete(sp["id"])
                continue
            fade = 1 - t
            try:
                self.cv.itemconfig(sp["id"], fill=hx(mix(self.bgc, FLASH, fade)))
            except Exception:
                pass
            keep.append(sp)
        self.sparkles = keep

    def spawn_rate(self) -> float:
        base = len(self.order) / (DURATION_MS / TICK_MS)
        beat = (self.elapsed / 1000) % 0.86
        if beat < 0.11 or 0.20 < beat < 0.30:
            return base * 2.35
        return base * 0.42

    def step(self, epoch: int):
        if epoch != self.epoch:
            return
        self.elapsed += TICK_MS
        if self.spawning:
            self.acc += self.spawn_rate()
            try:
                while self.acc >= 1:
                    self.acc -= 1
                    self.spawn(next(self.items))
            except StopIteration:
                self.spawning = False

        self.active[:] = [p for p in self.active if self.animate(p)]
        self.animate_sparkles()

        if not self.spawning and not self.active:
            self.draw_hint("click or space · again     r · new heart     esc · close")
            self.idle(epoch, 0)
            return
        self.after_token = self.cv.after(TICK_MS, lambda: self.step(epoch))

    def _safe_fill(self, item, color):
        try:
            self.cv.itemconfig(item, fill=hx(color))
        except Exception:
            pass

    def idle(self, epoch: int, frame: int):
        if epoch != self.epoch:
            return
        pulse = 0.055 * (0.5 + 0.5 * math.sin(frame * 0.035))
        flashed = set()
        if self.main_ids and frame % 7 == 0:
            for _ in range(1 if self.rng.random() < 0.7 else 2):
                item, c = self.rng.choice(self.main_ids)
                self._safe_fill(item, mix(c, FLASH, 0.58))
                flashed.add(item)
        for item, c in self.main_ids:
            if item not in flashed:
                self._safe_fill(item, mix(c, FLASH, pulse))
        if self.main_ids and frame % 36 == 0:
            item, c = self.rng.choice(self.main_ids)
            coords = self.cv.coords(item)
            if len(coords) >= 2:
                self._sparkle(coords[0], coords[1], c)
        self.animate_sparkles()
        self.after_token = self.cv.after(48, lambda: self.idle(epoch, frame + 1))

    def _start_scene(self):
        self.epoch += 1
        epoch = self.epoch
        if self.after_token is not None:
            try:
                self.cv.after_cancel(self.after_token)
            except Exception:
                pass
            self.after_token = None
        self.cv.delete("all")
        self._font_cache.clear()
        self.main_ids = []
        self.active = []
        self.sparkles = []
        self.acc = 0.0
        self.spawning = True
        self.elapsed = 0
        self.hint_id = None
        self.draw_backdrop()
        self.order = self.build()
        self.items = iter(self.order)
        self.draw_hint("for you")
        self.after_token = self.cv.after(280, lambda: self.step(epoch))

    def replay(self, reshuffle: bool):
        if reshuffle or self.seed is None:
            self.rng = random.Random()
            self.seed = None
        else:
            self.rng = random.Random(self.seed)
        self._start_scene()

    def run(self):
        try:
            turtle.done()
        except turtle.Terminator:
            pass


def main():
    LoveHeart(seed=11).run()


if __name__ == "__main__":
    main()
