# app.py — Flask + OpenWeather (Render-ready) with /health and /diag
from flask import Flask, render_template, request
import os, requests
from collections import defaultdict
from datetime import datetime

def create_app():
    app = Flask(__name__)
    app.secret_key = os.environ.get("SECRET_KEY", "dev-secret")
    API_KEY = (os.environ.get("OPENWEATHER_API_KEY", "") or "").strip()

    def build_params(location: str):
        loc = (location or "").strip()
        if loc.isdigit():
            # Force country for ZIP lookups unless user typed one
            zip_param = loc if "," in loc else f"{loc},US"
            return {"zip": zip_param, "appid": API_KEY, "units": "imperial"}
        return {"q": loc, "appid": API_KEY, "units": "imperial"}

    def get_weather_and_forecast(location: str):
        if not API_KEY:
            return None, None, "Server missing OPENWEATHER_API_KEY."

        params = build_params(location)

        # ---- Current weather
        r = requests.get("https://api.openweathermap.org/data/2.5/weather",
                         params=params, timeout=10)
        if r.status_code != 200:
            msg = r.json().get("message") if "application/json" in r.headers.get("content-type","") else r.text
            return None, None, f"Error: {r.status_code}, {msg or 'Unknown error'}"
        cur = r.json()
        weather = {
            "city": cur["name"],
            "temp_f": round(cur["main"]["temp"], 1),
            "description": cur["weather"][0]["description"].capitalize(),
            "humidity": cur["main"]["humidity"],
            "wind": cur["wind"]["speed"],
        }

        # ---- 5-day / 3-hour forecast
        r2 = requests.get("https://api.openweathermap.org/data/2.5/forecast",
                          params=params, timeout=10)
        if r2.status_code != 200:
            msg = r2.json().get("message") if "application/json" in r2.headers.get("content-type","") else r2.text
            return weather, None, f"Forecast error: {r2.status_code}, {msg or 'Unknown error'}"
        fc = r2.json()

        day_groups = defaultdict(list)
        for item in fc.get("list", []):
            dt = datetime.fromtimestamp(item["dt"])
            day_groups[dt.date().isoformat()].append(item)

        forecast = []
        for day, items in sorted(day_groups.items())[:5]:
            temps = [i["main"]["temp"] for i in items]
            descs = [i["weather"][0]["description"] for i in items]
            icons = [i["weather"][0]["icon"] for i in items]
            forecast.append({
                "date": day,
                "min_temp_f": round(min(temps), 1),
                "max_temp_f": round(max(temps), 1),
                "desc": max(set(descs), key=descs.count).capitalize(),
                "icon": max(set(icons), key=icons.count),
            })
        return weather, forecast, None

    @app.get("/health")
    def health():
        return {"ok": True, "has_key": bool(API_KEY), "key_len": len(API_KEY)}, 200

    @app.get("/diag")
    def diag():
        """Calls OpenWeather with a known ZIP to help debug 401s."""
        test_loc = "75040"  # change if you want
        params = build_params(test_loc)
        # Mask appid before echoing
        masked_key = f"{API_KEY[:4]}...{API_KEY[-4:]}" if API_KEY else ""
        safe_params = {**params, "appid": masked_key}
        try:
            resp = requests.get("https://api.openweathermap.org/data/2.5/weather",
                                params=params, timeout=10)
            ct = resp.headers.get("content-type", "")
            body = resp.json() if "application/json" in ct else {"text": resp.text[:300]}
            return {
                "request_params_sanitized": safe_params,
                "status_code": resp.status_code,
                "ok": resp.ok,
                "body_excerpt": body
            }, resp.status_code
        except Exception as e:
            return {"error": str(e), "request_params_sanitized": safe_params}, 500

    @app.route("/", methods=["GET", "POST"])
    def index():
        weather = forecast = None
        error = None
        location = ""
        if request.method == "POST":
            location = (request.form.get("location") or "").strip()
            if location:
                weather, forecast, error = get_weather_and_forecast(location)
            else:
                error = "Please enter a city name or zip code."
        return render_template("index.html", weather=weather, forecast=forecast, error=error, location=location)

    return app

# Gunicorn entrypoint
app = create_app()

if __name__ == "__main__":
    app.run(debug=True, port=int(os.environ.get("PORT", "5000")))
