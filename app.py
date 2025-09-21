from flask import Flask, render_template, request
import os, requests
from collections import defaultdict
import datetime

def create_app():
    app = Flask(__name__)
    app.secret_key = os.environ.get("SECRET_KEY", "dev-secret")

    API_KEY = os.environ.get("OPENWEATHER_API_KEY", "")
    if not API_KEY:
        # Still allow the app to boot; surface a friendly error on requests
        print("WARNING: OPENWEATHER_API_KEY is not set")

    def get_weather_and_forecast(location, api_key):
        base_url = "https://api.openweathermap.org/data/2.5/weather"
        if location.isdigit():
            params = {"zip": location, "appid": api_key, "units": "imperial"}
        else:
            params = {"q": location, "appid": api_key, "units": "imperial"}
        try:
            response = requests.get(base_url, params=params, timeout=10)
            if response.status_code != 200:
                try:
                    message = response.json().get('message', 'Unknown error')
                except Exception:
                    message = "Unknown error"
                return None, None, f"Error: {response.status_code}, {message}"
            data = response.json()
            weather = {
                "city": data['name'],
                "temp_f": round(data['main']['temp'], 1),
                "description": data['weather'][0]['description'].capitalize(),
                "humidity": data['main']['humidity'],
                "wind": data['wind']['speed']
            }
        except Exception as e:
            return None, None, f"Error fetching current weather: {e}"

        forecast_url = "https://api.openweathermap.org/data/2.5/forecast"
        try:
            params2 = params.copy()
            response2 = requests.get(forecast_url, params=params2, timeout=10)
            if response2.status_code != 200:
                try:
                    message = response2.json().get('message', 'Unknown error')
                except Exception:
                    message = "Unknown error"
                return weather, None, f"Forecast error: {response2.status_code}, {message}"
            data2 = response2.json()

            day_groups = defaultdict(list)
            for item in data2['list']:
                dt = datetime.datetime.fromtimestamp(item['dt'])
                day = dt.date().isoformat()
                day_groups[day].append(item)

            forecast = []
            for day, items in sorted(day_groups.items())[:5]:
                temps_f = [i['main']['temp'] for i in items]
                descs = [i['weather'][0]['description'] for i in items]
                icons = [i['weather'][0]['icon'] for i in items]
                desc = max(set(descs), key=descs.count)
                icon = max(set(icons), key=icons.count)
                forecast.append({
                    "date": day,
                    "min_temp_f": round(min(temps_f), 1),
                    "max_temp_f": round(max(temps_f), 1),
                    "desc": desc.capitalize(),
                    "icon": icon
                })
        except Exception as e:
            return weather, None, f"Error fetching forecast: {e}"

        return weather, forecast, None

    @app.get("/health")
    def health():
        return {"status": "ok"}, 200

    @app.route("/", methods=["GET", "POST"])
    def index():
        weather = None
        forecast = None
        error = None
        location = ""
        if request.method == "POST":
            location = request.form.get("location", "").strip()
            if not API_KEY:
                error = "Server missing OPENWEATHER_API_KEY."
            elif location:
                weather, forecast, error = get_weather_and_forecast(location, API_KEY)
            else:
                error = "Please enter a city name or zip code."
        return render_template("index.html", weather=weather, forecast=forecast, error=error, location=location)

    return app

# Gunicorn entrypoint
app = create_app()
