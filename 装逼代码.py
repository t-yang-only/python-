# -*- coding: utf-8 -*-
import sys
import tkinter as tk
import random
import threading
import time
import os
import math
from collections import deque

# 隐藏控制台黑框（仅限 Windows）
if os.name == "nt":
    try:
        import ctypes
        ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)
    except Exception:
        pass

# 需要 Pillow：pip install pillow
try:
    from PIL import Image, ImageDraw, ImageFont, ImageOps
except ImportError:
    raise SystemExit("未检测到 Pillow，请先执行：pip install pillow")


# ========= 字体与多脚本 fallback =========
def _first_existing(paths):
    for p in paths:
        if os.path.exists(p):
            return p
    return None

def _load_font(path, size):
    try:
        return ImageFont.truetype(path, size, layout_engine=getattr(ImageFont, "LAYOUT_RAQM", 0))
    except Exception:
        return ImageFont.truetype(path, size)

def pick_font(size: int):
    if os.name == "nt":
        candidates = [
            r"C:/Windows/Fonts/msyh.ttc",
            r"C:/Windows/Fonts/msyh.ttf",
            r"C:/Windows/Fonts/simhei.ttf",
            r"C:/Windows/Fonts/simsun.ttc",
            r"C:/Windows/Fonts/segoeui.ttf",
            r"C:/Windows/Fonts/arial.ttf",
            r"C:/Windows/Fonts/arialuni.ttf",
        ]
    elif sys.platform == "darwin":
        candidates = [
            "/System/Library/Fonts/PingFang.ttc",
            "/System/Library/Fonts/Hiragino Sans GB W3.otf",
            "/Library/Fonts/Arial Unicode.ttf",
            "/Library/Fonts/Arial Unicode MS.ttf",
        ]
    else:
        candidates = [
            "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
        ]
    path = _first_existing(candidates)
    if path:
        return _load_font(path, size)
    return ImageFont.load_default()

FALLBACK_FONT_PATHS = {
    "emoji": [
        r"C:/Windows/Fonts/seguiemj.ttf",
        "/System/Library/Fonts/Apple Color Emoji.ttc",
        "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf",
    ],
    "symbol": [
        r"C:/Windows/Fonts/seguisym.ttf",
        "/System/Library/Fonts/Apple Symbols.ttf",
        "/usr/share/fonts/truetype/noto/NotoSansSymbols2-Regular.ttf",
        "/usr/share/fonts/truetype/noto/NotoSansSymbols-Regular.ttf",
        "/usr/share/fonts/truetype/ancient-scripts/Symbola.ttf",
    ],
    "kannada": [
        r"C:/Windows/Fonts/nirmala.ttf",
        "/System/Library/Fonts/Supplemental/Kannada MN.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansKannada-Regular.ttf",
    ],
    "thai": [
        r"C:/Windows/Fonts/segoeui.ttf",
        r"C:/Windows/Fonts/angsana.ttf",
        "/System/Library/Fonts/Thonburi.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansThai-Regular.ttf",
    ],
    "arabic": [
        r"C:/Windows/Fonts/segoeui.ttf",
        r"C:/Windows/Fonts/trado.ttf",
        "/System/Library/Fonts/Al Nile.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansArabic-Regular.ttf",
    ],
}

def _script_bucket(ch):
    cp = ord(ch)
    if 0x1F000 <= cp <= 0x1FAFF:
        return "emoji"
    if 0x2600 <= cp <= 0x27FF:
        return "symbol"
    if 0x0C80 <= cp <= 0x0CFF:
        return "kannada"
    if 0x0E00 <= cp <= 0x0E7F:
        return "thai"
    if 0x0600 <= cp <= 0x06FF:
        return "arabic"
    return None

_fallback_font_cache = {}
def _get_fallback_font(bucket, size):
    if bucket is None:
        return None
    key = (bucket, size)
    if key in _fallback_font_cache:
        return _fallback_font_cache[key]
    path = _first_existing(FALLBACK_FONT_PATHS.get(bucket, []))
    if path:
        _fallback_font_cache[key] = _load_font(path, size)
        return _fallback_font_cache[key]
    _fallback_font_cache[key] = None
    return None


# ======== 点阵生成 ========
def text_to_grid_points(text: str, grid_w: int, grid_h: int, margin_cells: int = 2, scale: int = 4):
    target_w = max(1, grid_w - margin_cells * 2)
    target_h = max(1, grid_h - margin_cells * 2)
    canvas_w = target_w * scale
    canvas_h = target_h * scale

    font_size = int(min(canvas_h * 1, canvas_w * 1))
    if font_size <= 0:
        return []
    while font_size > 5:
        font = pick_font(font_size)
        tmp_img = Image.new("L", (canvas_w, canvas_h), 255)
        d = ImageDraw.Draw(tmp_img)
        bbox = d.textbbox((0, 0), text, font=font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
        if text_w <= canvas_w and text_h <= canvas_h:
            break
        font_size -= 2
    else:
        font = pick_font(12)

    img = Image.new("L", (canvas_w, canvas_h), 255)
    draw = ImageDraw.Draw(img)
    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    ox = (canvas_w - text_w) // 2 - bbox[0]
    oy = (canvas_h - text_h) // 2 - bbox[1]
    draw.text((ox, oy), text, fill=0, font=font)

    # fallback 覆盖（逐字修正）
    try:
        ascent, descent = font.getmetrics()
        line_h = ascent + descent
    except Exception:
        line_h = int(font.size * 1.2)

    def adv_width(ch):
        if hasattr(font, "getlength"):
            return int(font.getlength(ch))
        bb = font.getbbox(ch)
        if bb:
            return bb[2] - bb[0]
        return max(1, font.size // 2)

    y = oy
    for line in text.splitlines():
        x = ox
        for ch in line:
            bucket = _script_bucket(ch)
            fb = _get_fallback_font(bucket, font.size)
            if fb is not None:
                draw.text((x, y), ch, fill=0, font=fb)
            x += adv_width(ch)
        y += line_h

    bw = img.point(lambda p: 0 if p < 200 else 255, mode="1")
    reduced = bw.resize((target_w, target_h), Image.NEAREST)

    points = []
    px = reduced.load()
    for gy in range(target_h):
        for gx in range(target_w):
            v = px[gx, gy]
            if (v == 0) or (v is False):
                points.append((gx, gy))

    offset_x = (grid_w - target_w) // 2
    offset_y = (grid_h - target_h) // 2
    centered = [(gx + offset_x, gy + offset_y) for gx, gy in points]
    return centered


# ======== 公共工具 ========
def grid_to_screen(points, cell_size, kuan_size, dot_size):
    res = []
    for gx, gy in points:
        px = gx * cell_size + (cell_size - kuan_size) // 2
        py = gy * cell_size + (cell_size - dot_size) // 2
        res.append((px, py))
    return res

def screen_center_from_grid(gx, gy):
    return (gx * CELL_SIZE + CELL_SIZE // 2, gy * CELL_SIZE + CELL_SIZE // 2)

def show_warn_tip(x, y):
    if not SHOW_WINDOWS:
        return
    window = tk.Toplevel()
    window.geometry(f"{Kuan_SIZE}x{DOT_SIZE}+{x}+{y}")
    if SHOW_BORDER:
        window.overrideredirect(False)
    else:
        window.overrideredirect(True)
    window.attributes("-topmost", True)
    tip = random.choice(tips)
    bg = random.choice(bg_colors)
    label = tk.Label(window, text=tip, bg=bg, font=('仿宋', 18), width=15, height=2)
    label.pack()
    window.update()
    return window

def sort_points(points, display_order):
    if not points:
        return points
    if display_order == 0:
        return sorted(points, key=lambda p: (p[0], p[1]))
    elif display_order == 1:
        return sorted(points, key=lambda p: (p[0], p[1]), reverse=True)
    elif display_order == 2:
        return sorted(points, key=lambda p: (p[1], p[0]))
    elif display_order == 3:
        return sorted(points, key=lambda p: (p[1], p[0]), reverse=True)
    elif display_order == 4:
        cx = sum(p[0] for p in points) / len(points)
        cy = sum(p[1] for p in points) / len(points)
        return sorted(points, key=lambda p: (p[0]-cx)**2 + (p[1]-cy)**2)
    else:
        return points

def _rects_overlap(ax, ay, bx, by, w, h, pad):
    pad = max(0, int(pad))
    w_pad = w + pad
    h_pad = h + pad
    if ax >= bx + w_pad: return False
    if bx >= ax + w_pad: return False
    if ay >= by + h_pad: return False
    if by >= ay + h_pad: return False
    return True

def filter_points_non_overlap(points, w, h, pad, limit):
    kept = []
    for x, y in points:
        conflict = False
        for kx, ky in kept:
            if _rects_overlap(x, y, kx, ky, w, h, pad):
                conflict = True
                break
        if not conflict:
            kept.append((x, y))
            if len(kept) >= limit:
                break
    return kept

def filter_points_non_overlap_with_base(points, base_points, w, h, pad, limit):
    kept = []
    for x, y in points:
        conflict = False
        for bx, by in base_points:
            if _rects_overlap(x, y, bx, by, w, h, pad):
                conflict = True
                break
        if conflict:
            continue
        for kx, ky in kept:
            if _rects_overlap(x, y, kx, ky, w, h, pad):
                conflict = True
                break
        if not conflict:
            kept.append((x, y))
            if len(kept) >= limit:
                break
    return kept

def split_points_into_lines(points):
    if not points:
        return [points]
    ys = sorted(set(p[1] for p in points))
    clusters, cur, prev = [], [], None
    for y in ys:
        if prev is None or y == prev + 1:
            cur.append(y)
        else:
            clusters.append(cur); cur = [y]
        prev = y
    if cur: clusters.append(cur)
    if len(clusters) == 2:
        top_rows = set(clusters[0]); bottom_rows = set(clusters[1])
        top_points = [p for p in points if p[1] in top_rows]
        bottom_points = [p for p in points if p[1] in bottom_rows]
        return [top_points, bottom_points]
    return [points]

NEIGHBORS_8 = [(-1,-1), (0,-1), (1,-1),
               (-1, 0),          (1, 0),
               (-1, 1), (0, 1),  (1, 1)]

def build_components(points):
    s = set(points)
    comp_id = {}; comps = []
    for p in points:
        if p in comp_id: continue
        cid = len(comps)
        queue = deque([p])
        comp_id[p] = cid
        comp_pts = [p]
        while queue:
            x, y = queue.popleft()
            for dx, dy in NEIGHBORS_8:
                q = (x+dx, y+dy)
                if q in s and q not in comp_id:
                    comp_id[q] = cid
                    queue.append(q)
                    comp_pts.append(q)
        comps.append(comp_pts)
    return comp_id, comps, s

def bfs_path(a, b, allowed_set):
    if a == b: return [a]
    if a not in allowed_set or b not in allowed_set: return None
    queue = deque([a]); parent = {a: None}
    while queue:
        x, y = queue.popleft()
        for dx, dy in NEIGHBORS_8:
            q = (x+dx, y+dy)
            if q not in allowed_set or q in parent: continue
            parent[q] = (x, y)
            if q == b:
                path = [q]
                while parent[path[-1]] is not None:
                    path.append(parent[path[-1]])
                path.reverse()
                return path
            queue.append(q)
    return None


# ======== 统一延时（由配置控制） ========
def _next_delay_ms():
    if GEN_INTERVAL_MS <= 0:
        return 0
    jitter = random.randint(0, max(0, int(GEN_JITTER_MS)))
    return max(0, int(GEN_INTERVAL_MS + jitter))


# ======== 粒子模式（支持 on_done 回调） ========
def run_particle_mode(root, sw, sh, grid_points, on_done=None):
    stage = tk.Toplevel(root)
    stage.attributes("-topmost", True)
    stage.overrideredirect(True)
    stage.geometry(f"{sw}x{sh}+0+0")

    # Windows 透明色；其他平台回退
    if 'TRANSPARENT_CANVAS' in globals() and TRANSPARENT_CANVAS and os.name == "nt":
        canvas_bg = TRANSPARENT_COLOR
        try:
            stage.configure(bg=TRANSPARENT_COLOR)
            stage.wm_attributes("-transparentcolor", TRANSPARENT_COLOR)
        except tk.TclError:
            canvas_bg = PARTICLE_BG
    else:
        canvas_bg = PARTICLE_BG

    canvas = tk.Canvas(stage, width=sw, height=sh, highlightthickness=0, bg=canvas_bg)
    canvas.pack(fill="both", expand=True)

    current_color = {"val": random.choice(bg_colors)}
    def tick_color():
        current_color["val"] = random.choice(bg_colors)
        canvas.after(PARTICLE_COLOR_CHANGE_MS, tick_color)
    tick_color()

    line_groups = split_points_into_lines(grid_points)

    def prep_batches_for_grid():
        batches = []
        def order_grid(points_group):
            sp = grid_to_screen(points_group, CELL_SIZE, Kuan_SIZE, DOT_SIZE)
            mapping = {sp[i]: points_group[i] for i in range(len(points_group))}
            sp_sorted = sort_points(sp, DISPLAY_ORDER)
            return [mapping[p] for p in sp_sorted]
        if TWO_LINES_TOGETHER or len(line_groups) != 2:
            batches.append(order_grid(grid_points))
        else:
            batches.extend([order_grid(line_groups[0]), order_grid(line_groups[1])])
        return batches

    batches = prep_batches_for_grid()
    comp_id_map, comps, allowed_set = build_components(grid_points)

    def spawn_sparks(cx, cy):
        if not PARTICLE_SPARKS or PARTICLE_SPARK_COUNT <= 0:
            return
        for _ in range(PARTICLE_SPARK_COUNT):
            angle = random.uniform(0, 2*math.pi)
            vx = PARTICLE_SPARK_SPEED_PX * random.uniform(0.6, 1.2) * math.cos(angle)
            vy = PARTICLE_SPARK_SPEED_PX * random.uniform(0.6, 1.2) * math.sin(angle)
            radius = PARTICLE_SPARK_RADIUS
            item = canvas.create_oval(cx-radius, cy-radius, cx+radius, cy+radius,
                                      fill=current_color["val"], outline="")
            def step(i=0, x=cx, y=cy, r=radius, it=item, vx=vx, vy=vy):
                if i >= PARTICLE_SPARK_STEPS:
                    try: canvas.delete(it)
                    except Exception: pass
                    return
                x += vx; y += vy
                nr = max(0.5, r * 0.85)
                try:
                    canvas.coords(it, x-nr, y-nr, x+nr, y+nr)
                    canvas.itemconfig(it, fill=current_color["val"])
                except Exception:
                    return
                canvas.after(16, step, i+1, x, y, nr, it, vx, vy)
            step()

    def draw_segment(p, q):
        cx1, cy1 = screen_center_from_grid(*p)
        cx2, cy2 = screen_center_from_grid(*q)
        c_now = current_color["val"]
        if comp_id_map.get(p) == comp_id_map.get(q):
            path = bfs_path(p, q, allowed_set)
            if path and len(path) >= 2:
                coords = []
                for gx, gy in path:
                    x, y = screen_center_from_grid(gx, gy)
                    coords.extend([x, y])
                canvas.create_line(*coords, fill=c_now, width=PARTICLE_LINE_WIDTH, capstyle=tk.ROUND)
        else:
            if SHOW_PARTICLE_BRIDGE:
                kwargs = dict(fill=c_now, width=PARTICLE_BRIDGE_WIDTH, capstyle=tk.ROUND)
                if PARTICLE_BRIDGE_DASH is not None:
                    kwargs["dash"] = PARTICLE_BRIDGE_DASH
                canvas.create_line(cx1, cy1, cx2, cy2, **kwargs)
        r = PARTICLE_DOT_RADIUS
        canvas.create_oval(cx2-r, cy2-r, cx2+r, cy2+r, fill=c_now, outline=c_now, width=0)
        spawn_sparks(cx2, cy2)

    def finish():
        try:
            stage.destroy()
        except Exception:
            pass
        if callable(on_done):
            root.after(10, on_done)

    def draw_batches(batch_idx=0, idx=0, last_grid=None):
        if batch_idx >= len(batches):
            stage.after(HOLD_AFTER_DONE_MS, finish)
            return
        seq = batches[batch_idx]
        if idx >= len(seq):
            stage.after(_next_delay_ms(), draw_batches, batch_idx+1, 0, None)
            return
        step = 1 if PARTICLE_SINGLE_STEP else max(1, int(PARTICLE_BATCH_SIZE))
        end = min(idx + step, len(seq))
        part = seq[idx:end]
        if last_grid is None and part:
            gx, gy = part[0]
            x, y = screen_center_from_grid(gx, gy)
            c_now = current_color["val"]
            r = PARTICLE_DOT_RADIUS
            canvas.create_oval(x-r, y-r, x+r, y+r, fill=c_now, outline=c_now, width=0)
            spawn_sparks(x, y)
            last_point = part[0]; items = part[1:]
        else:
            last_point = last_grid; items = part
        for g in items:
            if last_point is not None:
                draw_segment(last_point, g)
            last_point = g
        canvas.after(_next_delay_ms(), draw_batches, batch_idx, end, last_point)

    stage.after(_next_delay_ms(), draw_batches)


# ======== 窗口模式（支持 on_done 回调） ========
def run_window_mode(root, sw, sh, grid_points, on_done=None):
    """
    窗口模式：
    - 如果 RANDOM_WINDOW_COUNT > 0：本段改为随机位置弹出 X 个窗口，使用本段大小/颜色/时间配置；
      全部出现后等待 HOLD_AFTER_DONE_MS 并销毁，再进入下一段。
    - 否则：按原点阵/排序/两行顺序逻辑生成。
    """
    windows = []

    def finish():
        # 等待 -> 销毁所有窗口 -> 调用下一段
        def _destroy_all():
            for w in windows:
                try:
                    w.destroy()
                except Exception:
                    pass
            if callable(on_done):
                root.after(10, on_done)
        root.after(HOLD_AFTER_DONE_MS, _destroy_all)

    # ===== 分支 A：随机位置弹出 X 个 =====
    if isinstance(globals().get("RANDOM_WINDOW_COUNT", 0), int) and RANDOM_WINDOW_COUNT > 0:
        count = min(int(RANDOM_WINDOW_COUNT), MAX_WINDOWS)

        # 预先随机出不重叠的位置（若开启 FORBID_OVERLAP/MIN_GAP_PX）
        chosen = []
        tries = 0
        max_tries = max(2000, count * 50)
        while len(chosen) < count and tries < max_tries:
            tries += 1
            x = random.randint(0, max(0, sw - Kuan_SIZE))
            y = random.randint(0, max(0, sh - DOT_SIZE))
            if SHOW_BORDER and FORBID_OVERLAP:
                conflict = False
                for (px, py) in chosen:
                    if _rects_overlap(x, y, px, py, Kuan_SIZE, DOT_SIZE, MIN_GAP_PX):
                        conflict = True
                        break
                if conflict:
                    continue
            chosen.append((x, y))

        # 如果太难找不重叠，就允许少量重叠：把还缺的随便拼上去
        while len(chosen) < count:
            x = random.randint(0, max(0, sw - Kuan_SIZE))
            y = random.randint(0, max(0, sh - DOT_SIZE))
            chosen.append((x, y))

        random.shuffle(chosen)

        def spawn_random(i=0):
            if i >= len(chosen):
                finish()
                return
            x, y = chosen[i]
            w = show_warn_tip(x, y)
            if w is not None:
                windows.append(w)
            root.after(_next_delay_ms(), spawn_random, i + 1)

        root.after(_next_delay_ms(), spawn_random)
        return  # 这一分支直接返回，等待 finish()

    # ===== 分支 B：按点阵/两行顺序生成（你原来的逻辑） =====
    line_groups = split_points_into_lines(grid_points)

    def prepare_batches_for_windows():
        batches = []

        def prep_one(points_group):
            sp = grid_to_screen(points_group, CELL_SIZE, Kuan_SIZE, DOT_SIZE)
            sp = sort_points(sp, DISPLAY_ORDER)
            return sp

        if TWO_LINES_TOGETHER or len(line_groups) != 2:
            all_sp = prep_one(grid_points)
            if SHOW_BORDER and FORBID_OVERLAP:
                all_sp = filter_points_non_overlap(
                    all_sp, Kuan_SIZE, DOT_SIZE, MIN_GAP_PX, min(MAX_WINDOWS, len(all_sp))
                )
            else:
                all_sp = all_sp[:MAX_WINDOWS]
            batches.append(all_sp)
        else:
            top_sp = prep_one(line_groups[0])
            bot_sp = prep_one(line_groups[1])
            remaining = MAX_WINDOWS
            if SHOW_BORDER and FORBID_OVERLAP:
                top_kept = filter_points_non_overlap(
                    top_sp, Kuan_SIZE, DOT_SIZE, MIN_GAP_PX, min(remaining, len(top_sp))
                )
                remaining -= len(top_kept)
                bot_kept = filter_points_non_overlap_with_base(
                    bot_sp, top_kept, Kuan_SIZE, DOT_SIZE, MIN_GAP_PX, min(remaining, len(bot_sp))
                )
            else:
                top_kept = top_sp[:remaining]
                remaining -= len(top_kept)
                bot_kept = bot_sp[:remaining]
            batches.extend([top_kept, bot_kept])
        return batches

    batches = prepare_batches_for_windows()

    def spawn_batches(batch_idx=0, i=0):
        if batch_idx >= len(batches):
            finish()
            return
        current = batches[batch_idx]
        if i >= len(current):
            root.after(_next_delay_ms(), spawn_batches, batch_idx + 1, 0)
            return
        x, y = current[i]
        w = show_warn_tip(x, y)
        if w is not None:
            windows.append(w)
        root.after(_next_delay_ms(), spawn_batches, batch_idx, i + 1)

    root.after(_next_delay_ms(), spawn_batches)



# ======== 配置：序列与应用 ========
def default_base_config():
    """提供全量键的默认值，便于每段只覆盖差异。"""
    return dict(
        CELL_SIZE=20, Kuan_SIZE=100, DOT_SIZE=30, GRID_MARGIN=1, MAX_WINDOWS=20000,
        SHOW_WINDOWS=True, SHOW_BORDER=False, Display_text=True, Custom_colors=False,
        FORBID_OVERLAP=True, MIN_GAP_PX=0,
        DISPLAY_ORDER=0, TWO_LINES_TOGETHER=False,

        # 生成速度 & 完成后等待
        GEN_INTERVAL_MS=1, GEN_JITTER_MS=0, HOLD_AFTER_DONE_MS=10000,

        # ✅ 新增：随机弹窗数量（>0 时，本段忽略点阵，随机位置弹出这么多个窗）
        RANDOM_WINDOW_COUNT=0,

        # 粒子模式
        PARTICLE=False, PARTICLE_SINGLE_STEP=True, PARTICLE_BATCH_SIZE=8,
        PARTICLE_DOT_RADIUS=2, PARTICLE_LINE_WIDTH=2, PARTICLE_COLOR_CHANGE_MS=10,
        PARTICLE_BG="#000000", TRANSPARENT_CANVAS=True, TRANSPARENT_COLOR="#00FF00",

        # 跨“无坐标区”桥接（粒子）
        SHOW_PARTICLE_BRIDGE=False, PARTICLE_BRIDGE_DASH=(6,4), PARTICLE_BRIDGE_WIDTH=1,

        # 扩散火花（粒子）
        PARTICLE_SPARKS=True, PARTICLE_SPARK_COUNT=3, PARTICLE_SPARK_STEPS=10,
        PARTICLE_SPARK_SPEED_PX=2.0, PARTICLE_SPARK_RADIUS=3,

        # 文本与配色
        text="",
        tips=[
            '好好吃饭','好好休息','早点休息','天天开心','记得喝水','按时吃饭','别熬夜了','照顾好自己',
            '注意身体','记得运动','放松一下','保持微笑','劳逸结合','别太劳累','记得午休','多吃水果',
            '出去走走','呼吸新鲜空气','保持好心情','别久坐','记得早餐','保护眼睛','注意保暖','别着凉',
            '保持健康','平安喜乐','开心每一天','一切顺利','万事如意','心想事成'
        ],
        bg_colors=['#ffffff'],

        # 兼容保留
        BG_COLOR="#111111", DOT_COLORS=["#ffffff"]
    )


def apply_config(cfg):
    """把一段 cfg 应用到全局，并处理联动。"""
    base = default_base_config()
    base.update(cfg or {})
    # 联动：Display_text / Custom_colors
    if not base["Display_text"]:
        base["tips"] = ['']
    if not base["Custom_colors"]:
        base["bg_colors"] = [
            'lightpink','skyblue','lightgreen','lavender','lightyellow','plum','coral','bisque',
            'aquamarine','mistyrose','honeydew','peachpuff','paleturquoise','lavenderblush',
            'oldlace','lemonchiffon','lightcyan','lightgray','lightpink','lightsalmon',
            'lightseagreen','lightskyblue','lightslategray','lightsteelblue','lightyellow'
        ]
    globals().update(base)

def get_config_sequence():
    global CELL_SIZE,SHOW_BORDER,Kuan_SIZE,SHOW_WINDOWS,bg_colors,tips,DOT_SIZE,PARTICLE,HOLD_AFTER_DONE_MS,MAX_WINDOWS,FORBID_OVERLAP,MIN_GAP_PX,TWO_LINES_TOGETHER,DISPLAY_ORDER
    global PARTICLE_COLOR_CHANGE_MS,PARTICLE_DOT_RADIUS,PARTICLE_SPARK_RADIUS,PARTICLE_SPARK_SPEED_PX,PARTICLE_BRIDGE_DASH,SHOW_PARTICLE_BRIDGE,PARTICLE_LINE_WIDTH
    global PARTICLE_BATCH_SIZE,PARTICLE_SINGLE_STEP,PARTICLE_BRIDGE_WIDTH,PARTICLE_SPARK_STEPS,PARTICLE_SPARK_COUNT,PARTICLE_SPARKS,TRANSPARENT_CANVAS,TRANSPARENT_COLOR
    global PARTICLE_BG,GEN_INTERVAL_MS,text,GRID_MARGIN,GEN_JITTER_MS,RANDOM_WINDOW_COUNT
    """PARTICLE
    在这里定义出现的窗口内容和样式
            # ======== 可调参数 ========
        CELL_SIZE=20,            # 网格单元像素（越小越细腻，但点/窗口数↑、更吃性能）
        Kuan_SIZE=100,           # 小窗口宽（像素）——窗口模式用
        DOT_SIZE=30,             # 小窗口高（像素）——窗口模式用
        GRID_MARGIN=1,           # 网格留白（单位：网格单元），四周空出这么多格
        MAX_WINDOWS=20000,       # 窗口数量上限（防卡顿）
        
        SHOW_WINDOWS=True,       # 是否显示提示窗口（窗口模式是否真的弹窗）
        SHOW_BORDER=False,       # 窗口是否带边框（True=正常窗口；False=无边框气泡）
        Display_text=True,       # 窗口内是否显示文字（从 tips 随机抽）
        Custom_colors=False,     # 是否使用自定义 bg_colors（False=用内置彩色）

        # 仅在 SHOW_BORDER=True 时生效（窗口模式）
        FORBID_OVERLAP=True,     # 禁止窗口重叠/“相碰”
        MIN_GAP_PX=0,            # 窗口之间最小间距（像素），FORBID_OVERLAP=True 时有效

        DISPLAY_ORDER=1,         # 生成顺序：0左→右 1右→左 2上→下 3下→上 4中心→外
        TWO_LINES_TOGETHER=False,# 两行是否一起生成：True一起；False先上行后下行

        # ======== 生成速度 & 完成后等待（两种模式通用） ========
        GEN_INTERVAL_MS=1,       # 基础生成间隔（毫秒），越小越快；0≈几乎瞬间
        GEN_JITTER_MS=0,         # 生成间隔的随机抖动范围 0~JITTER（毫秒）；0=不抖动
        HOLD_AFTER_DONE_MS=10000,# 整段完全生成后保留多久再消失（毫秒）

        # ======== 粒子模式与特效 ========
        PARTICLE=False,          # True=使用粒子替代窗口；False=窗口模式
        PARTICLE_SINGLE_STEP=True,# 粒子每tick生成策略：True=1个；False=一批
        PARTICLE_BATCH_SIZE=8,   # 批量模式每tick粒子数（SINGLE_STEP=False 时生效）
        PARTICLE_DOT_RADIUS=2,   # 粒子半径（像素）
        PARTICLE_LINE_WIDTH=2,   # 同连通块路径线宽（像素）
        PARTICLE_COLOR_CHANGE_MS=10, # 粒子颜色随机切换周期（毫秒），颜色来自 bg_colors
        PARTICLE_BG="#000000",   # 画布背景色（不用透明时）

        # —— 透明画布（仅 Windows 真正透明，其它平台自动回退不透明）——
        TRANSPARENT_CANVAS=True, # True=启用色键透明；False=用 PARTICLE_BG
        TRANSPARENT_COLOR="#00FF00", # 色键（不要与粒子颜色重复，否则会被“抠掉”）

        # 跨“无坐标区”桥接（不同连通块之间的连接线）
        SHOW_PARTICLE_BRIDGE=False,   # 是否绘制连通块之间的桥接线（跨空白）
        PARTICLE_BRIDGE_DASH=(6, 4),  # 虚线样式 (线段长度, 空段长度)；None=实线
        PARTICLE_BRIDGE_WIDTH=1,      # 桥接线宽（像素）

        # 扩散火花特效
        PARTICLE_SPARKS=True,     # 是否启用粒子扩散火花
        PARTICLE_SPARK_COUNT=3,   # 每个粒子喷射的火花数量
        PARTICLE_SPARK_STEPS=10,  # 火花寿命（步数/帧数）
        PARTICLE_SPARK_SPEED_PX=2.0,# 火花每步外扩像素
        PARTICLE_SPARK_RADIUS=3,  # 火花初始半径（逐帧衰减）

        # ======== 文本与配色 ========
        text="文字",            # 要渲染的文本（支持换行、符号、emoji 等）
        tips=[
            '好好吃饭','好好休息','早点休息','天天开心','记得喝水','按时吃饭','别熬夜了','照顾好自己',
            '注意身体','记得运动','放松一下','保持微笑','劳逸结合','别太劳累','记得午休','多吃水果',
            '出去走走','呼吸新鲜空气','保持好心情','别久坐','记得早餐','保护眼睛','注意保暖','别着凉',
            '保持健康','平安喜乐','开心每一天','一切顺利','万事如意','心想事成'
        ],                         # 窗口模式 Label 文案池（Display_text=True 时使用）
        bg_colors=['#ffffff'],     # 颜色池：窗口背景色/粒子颜色随机从此选择
        # ======== 兼容保留（当前实现不使用，可忽略） ========
        BG_COLOR="#111111",       # 旧版根背景色（兼容）
        DOT_COLORS=["#ffffff"],   # 旧版点颜色（兼容）
        
        
        ### RANDOM_WINDOW_COUNT  =  X  X是随机窗口数
    """
    seq = []
    # 其它参数按你贴的第二段可选覆盖；未写的使用默认
    # 段1：
    seq.append(dict(
        PARTICLE=False,
        CELL_SIZE=50,  # 网格单元像素（越小越细腻，但点/窗口数↑、更吃性能）
        Kuan_SIZE=50,  # 小窗口宽（像素）——窗口模式用
        DOT_SIZE=50,  # 小窗口高（像素）——窗口模式用
        text="二货",
        DISPLAY_ORDER=0,
        TWO_LINES_TOGETHER=False,
        GEN_INTERVAL_MS=0,  # 基础生成间隔（毫秒），越小越快；0≈几乎瞬间
        GEN_JITTER_MS=0,  # 生成间隔的随机抖动范围 0~JITTER（毫秒）；0=不抖动
        HOLD_AFTER_DONE_MS=1000,
        Display_text=False,  # 窗口内是否显示文字（从 tips 随机抽）
        Custom_colors=True,  # 是否使用自定义 bg_colors（False=用内置彩色）
        bg_colors=['#000000'],  # 颜色池：窗口背景色/粒子颜色随机从此选择
    ))
    #
    # # 段2：
    seq.append(dict(
        PARTICLE=True,
        text="欠我一个锤子",
        PARTICLE_SINGLE_STEP=True,
        DISPLAY_ORDER=0,
        GEN_INTERVAL_MS=1,
        GEN_JITTER_MS=0,
        HOLD_AFTER_DONE_MS=1000,   # 第二段停留更久
        TRANSPARENT_CANVAS=False,
    ))
    # # 段3：
    seq.append(dict(
        PARTICLE=False,
        CELL_SIZE=50,  # 网格单元像素（越小越细腻，但点/窗口数↑、更吃性能）
        Kuan_SIZE=40,  # 小窗口宽（像素）——窗口模式用
        DOT_SIZE=40,  # 小窗口高（像素）——窗口模式用
        text="你说你",
        DISPLAY_ORDER=0,
        TWO_LINES_TOGETHER=False,
        GEN_INTERVAL_MS=0,  # 基础生成间隔（毫秒），越小越快；0≈几乎瞬间
        GEN_JITTER_MS=0,  # 生成间隔的随机抖动范围 0~JITTER（毫秒）；0=不抖动
        HOLD_AFTER_DONE_MS=1000,
        Display_text=False,  # 窗口内是否显示文字（从 tips 随机抽）
    ))
    # # 段4
    seq.append(dict(
        PARTICLE=False,
        CELL_SIZE=40,  # 网格单元像素（越小越细腻，但点/窗口数↑、更吃性能）
        Kuan_SIZE=10,  # 小窗口宽（像素）——窗口模式用
        DOT_SIZE=10,  # 小窗口高（像素）——窗口模式用
        text="开窍了",
        DISPLAY_ORDER=0,
        SHOW_BORDER=True,
        TWO_LINES_TOGETHER=False,
        GEN_INTERVAL_MS=0,  # 基础生成间隔（毫秒），越小越快；0≈几乎瞬间
        GEN_JITTER_MS=0,  # 生成间隔的随机抖动范围 0~JITTER（毫秒）；0=不抖动
        HOLD_AFTER_DONE_MS=1000,
        Display_text=False,  # 窗口内是否显示文字（从 tips 随机抽）
    ))
    #段5
    seq.append(dict(
        PARTICLE=True,
        CELL_SIZE=15,  # 网格单元像素（越小越细腻，但点/窗口数↑、更吃性能）
        Kuan_SIZE=10,  # 小窗口宽（像素）——窗口模式用
        DOT_SIZE=10,  # 小窗口高（像素）——窗口模式用
        text="还要给我\n100个锤子",
        DISPLAY_ORDER=0,
        SHOW_BORDER=True,
        TWO_LINES_TOGETHER=False,
        GEN_INTERVAL_MS=1,  # 基础生成间隔（毫秒），越小越快；0≈几乎瞬间
        GEN_JITTER_MS=0,  # 生成间隔的随机抖动范围 0~JITTER（毫秒）；0=不抖动
        HOLD_AFTER_DONE_MS=1000,
        Display_text=False,  # 窗口内是否显示文字（从 tips 随机抽）
        PARTICLE_SPARK_COUNT=8,
        Custom_colors=True,  # 是否使用自定义 bg_colors（False=用内置彩色）
        bg_colors=['#000000'],  # 颜色池：窗口背景色/粒子颜色随机从此选择
        PARTICLE_BG="#ffffff",
        TRANSPARENT_CANVAS=False,
    ))
    # 段6
    seq.append(dict(
        PARTICLE=True,
        text="那我先",
        CELL_SIZE=15,
        PARTICLE_SINGLE_STEP=True,
        DISPLAY_ORDER=0,
        GEN_INTERVAL_MS=1,
        GEN_JITTER_MS=0,
        HOLD_AFTER_DONE_MS=1000,   # 第二段停留更久
        TRANSPARENT_CANVAS=False,
        SHOW_PARTICLE_BRIDGE=True,

    ))
    # 段7
    seq.append(dict(
        PARTICLE=False,
        text="谢谢你",
        CELL_SIZE=30,
        Kuan_SIZE=1,  # 小窗口宽（像素）——窗口模式用
        DOT_SIZE=10,  # 小窗口高（像素）——窗口模式用
        PARTICLE_SINGLE_STEP=True,
        DISPLAY_ORDER=0,
        GEN_INTERVAL_MS=0,
        GEN_JITTER_MS=0,
        HOLD_AFTER_DONE_MS=1000,   # 第二段停留更久
        TRANSPARENT_CANVAS=False,
        SHOW_PARTICLE_BRIDGE=True,
        Custom_colors=True,  # 是否使用自定义 bg_colors（False=用内置彩色）
        bg_colors=['#000000'],  # 颜色池：窗口背景色/粒子颜色随机从此选择
        SHOW_BORDER=True,  # 窗口是否带边框（True=正常窗口；False=无边框气泡）
        Display_text=False,  # 窗口内是否显示文字（从 tips 随机抽）
        MIN_GAP_PX=5,
    ))
    #段8
    seq.append(dict(
        PARTICLE=False,
        RANDOM_WINDOW_COUNT=250,  # 本段随机弹出 250 个窗口
        Kuan_SIZE=120, DOT_SIZE=40,  # 随机窗也用本段的大小
        GEN_INTERVAL_MS=20,  # 本段的出现节奏
        HOLD_AFTER_DONE_MS=1500,  # 本段全部出现后停留 1.5s
        Display_text=True,
        Custom_colors=False,  # False=内置多彩；True=用你自定义 bg_colors
    ))
    # 段9
    seq.append(dict(
        PARTICLE=True,
        text="你会了这么多",
        CELL_SIZE=10,
        PARTICLE_SINGLE_STEP=True,
        DISPLAY_ORDER=0,
        GEN_INTERVAL_MS=1,
        GEN_JITTER_MS=0,
        HOLD_AFTER_DONE_MS=1000,
        TRANSPARENT_CANVAS=False,
        PARTICLE_SPARK_COUNT=8,  # 每个粒子喷射的火花数量
        PARTICLE_SPARK_STEPS=15,  # 火花寿命（步数/帧数）
        PARTICLE_SPARK_SPEED_PX=5.0,  # 火花每步外扩像素
        PARTICLE_SPARK_RADIUS=5,  # 火花初始半径（逐帧衰减）
        Custom_colors=True,
        bg_colors=['#ffffff'],
    ))
    # #段10
    seq.append(dict(
        PARTICLE=True,
        text="快V我50表示表示",
        CELL_SIZE=10,
        PARTICLE_SINGLE_STEP=True,
        DISPLAY_ORDER=0,
        GEN_INTERVAL_MS=1,
        GEN_JITTER_MS=0,
        HOLD_AFTER_DONE_MS=1000,
        TRANSPARENT_CANVAS=False,
        PARTICLE_SPARK_COUNT=8,  # 每个粒子喷射的火花数量
        PARTICLE_SPARK_STEPS=15,  # 火花寿命（步数/帧数）
        PARTICLE_SPARK_SPEED_PX=5.0,  # 火花每步外扩像素
        PARTICLE_SPARK_RADIUS=5,  # 火花初始半径（逐帧衰减）
        Custom_colors=True,
        bg_colors=['#000000'],
        PARTICLE_BG="#ffffff",
        SHOW_PARTICLE_BRIDGE=True,
    ))
    #段11
    seq.append(dict(
        PARTICLE=False,
        RANDOM_WINDOW_COUNT=250,  # 本段随机弹出 250 个窗口
        Kuan_SIZE=120, DOT_SIZE=40,  # 随机窗也用本段的大小
        GEN_INTERVAL_MS=20,  # 本段的出现节奏
        HOLD_AFTER_DONE_MS=1500,  # 本段全部出现后停留 1.5s
        Display_text=True,
        tips=[
            'V我50'
        ],
        Custom_colors=False,  # False=内置多彩；True=用你自定义 bg_colors
    ))
    # 段7
    seq.append(dict(
        PARTICLE=False,
        text="谢谢",
        CELL_SIZE=30,
        Kuan_SIZE=1,  # 小窗口宽（像素）——窗口模式用
        DOT_SIZE=30,  # 小窗口高（像素）——窗口模式用
        PARTICLE_SINGLE_STEP=True,
        DISPLAY_ORDER=0,
        GEN_INTERVAL_MS=0,
        GEN_JITTER_MS=0,
        HOLD_AFTER_DONE_MS=1000,   # 第二段停留更久
        TRANSPARENT_CANVAS=False,
        SHOW_PARTICLE_BRIDGE=True,
        SHOW_BORDER=True,  # 窗口是否带边框（True=正常窗口；False=无边框气泡）
        tips=[
                    'V我50','谢谢'
                ],
        MIN_GAP_PX=5,
    ))
    return seq


# ========== 主流程：依次播放多段 ==========
def main():
    root = tk.Tk()
    root.withdraw()
    sw = root.winfo_screenwidth()
    sh = root.winfo_screenheight()

    sequence = get_config_sequence()

    def run_step(idx=0):
        if idx >= len(sequence):
            try:
                root.destroy()
            except Exception:
                pass
            return

        # 应用当前段配置
        apply_config(sequence[idx])

        # === 是否需要点阵 ===
        # 1) 粒子模式一定需要点阵
        # 2) 窗口模式但 RANDOM_WINDOW_COUNT <= 0 也需要点阵
        # 3) 窗口模式且 RANDOM_WINDOW_COUNT > 0 则不需要点阵（走随机弹窗分支）
        need_grid = PARTICLE or (globals().get("RANDOM_WINDOW_COUNT", 0) <= 0)

        pts = []
        if need_grid:
            grid_w = max(1, sw // CELL_SIZE)
            grid_h = max(1, sh // CELL_SIZE)
            pts = text_to_grid_points(text, grid_w, grid_h, margin_cells=GRID_MARGIN, scale=4)
            if not pts:
                print(f"[段{idx}] 网格过小或渲染失败，未生成点阵。跳过。")
                root.after(10, run_step, idx + 1)
                return

        # === 根据模式运行 ===
        if PARTICLE:
            run_particle_mode(root, sw, sh, pts, on_done=lambda: run_step(idx + 1))
        else:
            # run_window_mode 内部已支持 RANDOM_WINDOW_COUNT>0 的随机弹窗逻辑
            run_window_mode(root, sw, sh, pts, on_done=lambda: run_step(idx + 1))

    run_step(0)
    root.mainloop()



if __name__ == "__main__":
    main()
