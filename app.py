from flask import Flask, render_template_string, request
import requests
from collections import defaultdict
import datetime

API_KEY = "e57242c38fdbd6931001326954c62896"  # Replace with your OpenWeatherMap API key

HTML = '''
<!DOCTYPE html>
<html>
<head>
    <title>Weather App-Eric Holt</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body { background: #f2f6fc; }
        .weather-card { max-width: 1100px; margin: 30px auto; }
        .chart-container { position: relative; height:350px; width:100%; }
        .error { color: #c00; font-weight: bold; }
        @media (max-width: 767px) {
            .chart-container { height:250px; }
        }
    </style>
</head>
<body>
    <div class="container weather-card p-4 bg-white rounded shadow">
        <h2 class="mb-4">Weather Look-Up App</h2>
        <form method="post" class="mb-3">
            <div class="input-group">
                <input type="text" name="location" id="location" class="form-control" placeholder="City or ZIP" value="{{ location|default('') }}" required autofocus>
                <button class="btn btn-primary" type="submit">Fetch Weather</button>
            </div>
        </form>
        {% if weather %}
        <div class="row">
            <!-- LEFT COLUMN: Weather & Forecast -->
            <div class="col-md-6 col-12 mb-4">
                <h4>Current Weather in {{ weather['city'] }}</h4>
                <ul class="list-group mb-3">
                    <li class="list-group-item">Temperature: {{ weather['temp_f'] }}°F</li>
                    <li class="list-group-item">Description: {{ weather['description'] }}</li>
                    <li class="list-group-item">Humidity: {{ weather['humidity'] }}%</li>
                    <li class="list-group-item">Wind Speed: {{ weather['wind'] }} m/s</li>
                </ul>
                <h4>5-Day Forecast</h4>
                <div class="table-responsive">
                    <table class="table table-bordered align-middle text-center">
                        <thead class="table-light">
                            <tr>
                                <th>Date</th>
                                <th>Min (°F)</th>
                                <th>Max (°F)</th>
                                <th>Description</th>
                                <th>Icon</th>
                            </tr>
                        </thead>
                        <tbody>
                        {% for day in forecast %}
                            <tr>
                                <td>{{ day['date'] }}</td>
                                <td>{{ day['min_temp_f'] }}</td>
                                <td>{{ day['max_temp_f'] }}</td>
                                <td>{{ day['desc'] }}</td>
                                <td><img src="https://openweathermap.org/img/wn/{{ day['icon'] }}.png" alt="icon"></td>
                            </tr>
                        {% endfor %}
                        </tbody>
                    </table>
                </div>
            </div>
            <!-- RIGHT COLUMN: Chart -->
            <div class="col-md-6 col-12 d-flex align-items-center justify-content-center">
                <div class="chart-container w-100">
                    <canvas id="tempChart"></canvas>
                </div>
            </div>
        </div>
        {% elif error %}
            <div class="error">{{ error }}</div>
        {% endif %}
    </div>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script>
    {% if forecast %}
        const ctx = document.getElementById('tempChart').getContext('2d');
        const data = {
            labels: {{ forecast|map(attribute='date')|list|tojson }},
            datasets: [
                {
                    label: "Min Temp (°F)",
                    data: {{ forecast|map(attribute='min_temp_f')|list|tojson }},
                    borderColor: '#3498db', backgroundColor: 'rgba(52,152,219,0.2)', tension:0.2
                },
                {
                    label: "Max Temp (°F)",
                    data: {{ forecast|map(attribute='max_temp_f')|list|tojson }},
                    borderColor: '#e67e22', backgroundColor: 'rgba(230,126,34,0.2)', tension:0.2
                }
            ]
        };
        new Chart(ctx, {
            type: 'line',
            data: data,
            options: {
                responsive: true,
                plugins: { legend: { position: 'top' }, title: { display:true, text:'5-Day Temperature Trend' } }
            }
        });
    {% endif %}
    document.getElementById("location").focus();
    </script>
</body>
</html>
'''

def celsius_to_fahrenheit(celsius):
    return (celsius * 9/5) + 32

def get_weather_and_forecast(location, api_key):
    # Use imperial units to get °F directly from API
    base_url = "https://api.openweathermap.org/data/2.5/weather"
    if location.isdigit():
        params = {"zip": location, "appid": api_key, "units": "imperial"}
    else:
        params = {"q": location, "appid": api_key, "units": "imperial"}
    try:
        response = requests.get(base_url, params=params, timeout=5)
        if response.status_code != 200:
            try:
                message = response.json().get('message', 'Unknown error')
            except Exception:
                message = "Unknown error"
            return None, None, f"Error: {response.status_code}, {message}"
        data = response.json()
        weather = {
            "city": data['name'],
            "temp_f": round(data['main']['temp'],1),
            "description": data['weather'][0]['description'].capitalize(),
            "humidity": data['main']['humidity'],
            "wind": data['wind']['speed']
        }
    except Exception as e:
        return None, None, f"Error fetching current weather: {e}"

    # 5-day forecast
    forecast_url = "https://api.openweathermap.org/data/2.5/forecast"
    try:
        params2 = params.copy()
        response2 = requests.get(forecast_url, params=params2, timeout=5)
        if response2.status_code != 200:
            try:
                message = response2.json().get('message', 'Unknown error')
            except Exception:
                message = "Unknown error"
            return weather, None, f"Forecast error: {response2.status_code}, {message}"
        data2 = response2.json()
        # Group by day, get min/max/desc/icon for each day
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
            # Pick most common desc/icon for the day
            desc = max(set(descs), key=descs.count)
            icon = max(set(icons), key=icons.count)
            forecast.append({
                "date": day,
                "min_temp_f": round(min(temps_f),1),
                "max_temp_f": round(max(temps_f),1),
                "desc": desc.capitalize(),
                "icon": icon
            })
    except Exception as e:
        return weather, None, f"Error fetching forecast: {e}"

    return weather, forecast, None

app = Flask(__name__)

@app.route("/", methods=["GET", "POST"])
def index():
    weather = None
    forecast = None
    error = None
    location = ""
    if request.method == "POST":
        location = request.form.get("location", "").strip()
        if location:
            weather, forecast, error = get_weather_and_forecast(location, API_KEY)
        else:
            error = "Please enter a city name or zip code."
    return render_template_string(HTML, weather=weather, forecast=forecast, error=error, location=location)

if __name__ == "__main__":
    app.run(debug=True, port=5001)
