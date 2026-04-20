
import webbrowser
import urllib.parse


WEATHER_SOURCES = {
    "google":      "https://www.google.com/search?q=weather+{location}",
    "weather.com": "https://weather.com/weather/today/l/{location}",
    "wttr":        "https://wttr.in/{location}",
    "openweather": "https://openweathermap.org/find?q={location}",
    "accuweather": "https://www.accuweather.com/en/search-locations?query={location}",
}


def weather_report(
    parameters:     dict,
    response=None,
    player=None,
    session_memory=None,
) -> str:
    """
    Lumina weather action. Opens weather info in the default browser.

    parameters:
        location : City, country, or zip code (default: 'my location')
        source   : 'google' (default) | 'weather.com' | 'wttr' | 'openweather' | 'accuweather'
    """
    params     = parameters or {}
    location   = params.get("location", "my location").strip()
    source     = params.get("source", "google").lower().strip()

    if source not in WEATHER_SOURCES:
        source = "google"

    encoded  = urllib.parse.quote_plus(location)
    url      = WEATHER_SOURCES[source].format(location=encoded)

    if player:
        player.write_log(f"[Lumina] Checking weather for: {location}")

    print(f"[Weather] 🌤️ Opening weather for: {location!r} via {source}")
    webbrowser.open(url)

    return f"Opening weather for {location} via {source.title()}."
