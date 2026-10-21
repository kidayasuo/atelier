"""本館の (u, v) 座標（m）と世界座標（mm）の変換（infant200.py と同じ定数）"""
import math, numpy as np
CX, CY, RW = 194662.93237, -41348.26335, 205017.7
TH_S = math.atan2(-65173.47495 - CY, -8965.4788 - CX) % (2 * math.pi)
def uv(x, y):
    th = math.atan2(y - CY, x - CX) % (2 * math.pi)
    return (TH_S - th) * RW / 1000, (RW - math.hypot(x - CX, y - CY)) / 1000
def xy(u, v):
    th = TH_S - u * 1000 / RW; r = RW - v * 1000
    return np.array([CX + r * math.cos(th), CY + r * math.sin(th)])
