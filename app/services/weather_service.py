import httpx

# 常用城市经纬度映射（避免每次都查）
CITY_COORDS = {
    "北京": (39.90, 116.40),
    "上海": (31.23, 121.47),
    "成都": (30.57, 104.07),
    "杭州": (30.29, 120.15),
    "重庆": (29.56, 106.55),
    "西安": (34.26, 108.94),
    "南京": (32.06, 118.80),
    "广州": (23.13, 113.26),
    "深圳": (22.54, 114.06),
    "武汉": (30.59, 114.30),
    "长沙": (28.23, 112.94),
    "厦门": (24.48, 118.09),
    "青岛": (36.07, 120.38),
    "三亚": (18.25, 109.51),
    "昆明": (25.04, 102.68),
    "大理": (25.59, 100.23),
    "拉萨": (29.65, 91.12),
    "苏州": (31.30, 120.62),
    "桂林": (25.27, 110.28),
    "哈尔滨": (45.80, 126.53),
}

# 天气代码 → 中文描述
WEATHER_CODES = {
    0: "晴天", 1: "大部晴", 2: "多云", 3: "阴天",
    45: "雾", 48: "霜雾",
    51: "小毛毛雨", 53: "毛毛雨", 55: "大毛毛雨",
    61: "小雨", 63: "中雨", 65: "大雨",
    71: "小雪", 73: "中雪", 75: "大雪",
    80: "阵雨", 81: "中等阵雨", 82: "大阵雨",
    95: "雷暴", 96: "冰雹雷暴", 99: "强冰雹雷暴",
}


async def get_weather(city: str, days: int = 3) -> str:
    """获取城市未来几天天气，返回中文描述"""

    coords = CITY_COORDS.get(city)
    if not coords:
        return f"（未找到{city}的天气数据）"

    lat, lon = coords

    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "daily": ["weather_code", "temperature_2m_max", "temperature_2m_min"],
        "forecast_days": min(days, 7),  # 最多 7 天
        "timezone": "Asia/Shanghai",
    }

    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.get(url, params=params)
        data = response.json()

    daily = data["daily"]
    lines = [f"【{city}未来{days}天天气】"]

    for i in range(min(days, len(daily["time"]))):
        date = daily["time"][i]
        code = daily["weather_code"][i]
        t_max = daily["temperature_2m_max"][i]
        t_min = daily["temperature_2m_min"][i]
        weather_desc = WEATHER_CODES.get(code, f"未知({code})")
        lines.append(f"{date}: {weather_desc}，{t_min}°C ~ {t_max}°C")

    return "\n".join(lines)
