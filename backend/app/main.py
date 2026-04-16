from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api.circuits import router as circuits_router
from app.api.weather import router as weather_router
from app.api.sessions import router as sessions_router
from app.api.export import router as export_router

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Hyper-local weather intelligence for motorsport circuits — Market-leading pitwall decision support",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(circuits_router, prefix=settings.API_V1_PREFIX)
app.include_router(weather_router, prefix=settings.API_V1_PREFIX)
app.include_router(sessions_router, prefix=settings.API_V1_PREFIX)
app.include_router(export_router, prefix=settings.API_V1_PREFIX)


@app.on_event("startup")
def on_startup():
    """Create tables and seed data on first run."""
    from app.db.base import Base
    from app.db.session import engine, SessionLocal
    from app.models.circuit import Circuit

    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        if db.query(Circuit).count() == 0:
            _seed_circuits(db)
    finally:
        db.close()


def _seed_circuits(db):
    from app.models.circuit import Circuit

    circuits = [
        # --- Original 20 circuits (unchanged) ---
        {"name": "Spa-Francorchamps", "country": "Belgium", "latitude": 50.4372, "longitude": 5.9714, "length_km": 7.004, "timezone": "Europe/Brussels", "altitude_m": 401, "series": "F1,WEC,GT3", "sector_count": 3, "surface_type": "standard_asphalt"},
        {"name": "Silverstone", "country": "United Kingdom", "latitude": 52.0786, "longitude": -1.0169, "length_km": 5.891, "timezone": "Europe/London", "altitude_m": 153, "series": "F1,WEC,GT3,BTCC", "sector_count": 3, "surface_type": "standard_asphalt"},
        {"name": "Suzuka", "country": "Japan", "latitude": 34.8431, "longitude": 136.5407, "length_km": 5.807, "timezone": "Asia/Tokyo", "altitude_m": 45, "series": "F1,Super GT", "sector_count": 3, "surface_type": "standard_asphalt"},
        {"name": "Monza", "country": "Italy", "latitude": 45.6156, "longitude": 9.2811, "length_km": 5.793, "timezone": "Europe/Rome", "altitude_m": 162, "series": "F1,GT3", "sector_count": 3, "surface_type": "standard_asphalt"},
        {"name": "Imola", "country": "Italy", "latitude": 44.3439, "longitude": 11.7167, "length_km": 4.909, "timezone": "Europe/Rome", "altitude_m": 47, "series": "F1,WEC", "sector_count": 3, "surface_type": "standard_asphalt"},
        {"name": "Barcelona-Catalunya", "country": "Spain", "latitude": 41.5700, "longitude": 2.2611, "length_km": 4.675, "timezone": "Europe/Madrid", "altitude_m": 109, "series": "F1,GT3", "sector_count": 3, "surface_type": "high_grip_asphalt"},
        {"name": "Red Bull Ring", "country": "Austria", "latitude": 47.2197, "longitude": 14.7647, "length_km": 4.318, "timezone": "Europe/Vienna", "altitude_m": 678, "series": "F1,GT3,DTM", "sector_count": 3, "surface_type": "standard_asphalt"},
        {"name": "Monaco", "country": "Monaco", "latitude": 43.7347, "longitude": 7.4206, "length_km": 3.337, "timezone": "Europe/Monaco", "altitude_m": 30, "series": "F1,Formula E", "sector_count": 3, "surface_type": "low_grip_street"},
        {"name": "Circuit of the Americas", "country": "USA", "latitude": 30.1328, "longitude": -97.6411, "length_km": 5.513, "timezone": "America/Chicago", "altitude_m": 163, "series": "F1,WEC,IMSA", "sector_count": 3, "surface_type": "high_grip_asphalt"},
        {"name": "Interlagos", "country": "Brazil", "latitude": -23.7036, "longitude": -46.6997, "length_km": 4.309, "timezone": "America/Sao_Paulo", "altitude_m": 750, "series": "F1,WEC", "sector_count": 3, "surface_type": "standard_asphalt"},
        {"name": "Bahrain International Circuit", "country": "Bahrain", "latitude": 26.0325, "longitude": 50.5106, "length_km": 5.412, "timezone": "Asia/Bahrain", "altitude_m": 7, "series": "F1,WEC", "sector_count": 3, "surface_type": "abrasive"},
        {"name": "Yas Marina", "country": "UAE", "latitude": 24.4672, "longitude": 54.6031, "length_km": 5.281, "timezone": "Asia/Dubai", "altitude_m": 5, "series": "F1,GT3", "sector_count": 3, "surface_type": "abrasive"},
        {"name": "Singapore Marina Bay", "country": "Singapore", "latitude": 1.2914, "longitude": 103.8640, "length_km": 4.940, "timezone": "Asia/Singapore", "altitude_m": 5, "series": "F1", "sector_count": 3, "surface_type": "low_grip_street"},
        {"name": "Le Mans", "country": "France", "latitude": 47.9560, "longitude": 0.2075, "length_km": 13.626, "timezone": "Europe/Paris", "altitude_m": 60, "series": "WEC", "sector_count": 3, "surface_type": "concrete_mix"},
        {"name": "Daytona", "country": "USA", "latitude": 29.1853, "longitude": -81.0712, "length_km": 5.729, "timezone": "America/New_York", "altitude_m": 5, "series": "IMSA", "sector_count": 3, "surface_type": "standard_asphalt"},
        {"name": "Bathurst Mount Panorama", "country": "Australia", "latitude": -33.4474, "longitude": 149.5578, "length_km": 6.213, "timezone": "Australia/Sydney", "altitude_m": 672, "series": "Supercars,GT3", "sector_count": 3, "surface_type": "standard_asphalt"},
        {"name": "Nurburgring GP", "country": "Germany", "latitude": 50.3356, "longitude": 6.9475, "length_km": 5.148, "timezone": "Europe/Berlin", "altitude_m": 617, "series": "F1,WEC,GT3,DTM", "sector_count": 3, "surface_type": "standard_asphalt"},
        {"name": "Brands Hatch", "country": "United Kingdom", "latitude": 51.3569, "longitude": 0.2631, "length_km": 3.908, "timezone": "Europe/London", "altitude_m": 100, "series": "BTCC,GT3", "sector_count": 3, "surface_type": "standard_asphalt"},
        {"name": "Portimao Algarve", "country": "Portugal", "latitude": 37.2272, "longitude": -8.6267, "length_km": 4.684, "timezone": "Europe/Lisbon", "altitude_m": 100, "series": "F1,WEC,GT3", "sector_count": 3, "surface_type": "high_grip_asphalt"},
        {"name": "Laguna Seca", "country": "USA", "latitude": 36.5842, "longitude": -121.7533, "length_km": 3.602, "timezone": "America/Los_Angeles", "altitude_m": 300, "series": "IMSA,IndyCar", "sector_count": 3, "surface_type": "standard_asphalt"},
        # --- Europe additions ---
        {"name": "Hungaroring", "country": "Hungary", "latitude": 47.5789, "longitude": 19.2486, "length_km": 4.381, "timezone": "Europe/Budapest", "altitude_m": 264, "series": "F1", "sector_count": 3, "surface_type": "standard_asphalt"},
        {"name": "Zandvoort", "country": "Netherlands", "latitude": 52.3888, "longitude": 4.5409, "length_km": 4.259, "timezone": "Europe/Amsterdam", "altitude_m": 5, "series": "F1,DTM", "sector_count": 3, "surface_type": "standard_asphalt"},
        {"name": "Jeddah Corniche Circuit", "country": "Saudi Arabia", "latitude": 21.6319, "longitude": 39.1044, "length_km": 6.174, "timezone": "Asia/Riyadh", "altitude_m": 10, "series": "F1", "sector_count": 3, "surface_type": "low_grip_street"},
        {"name": "Lusail Circuit", "country": "Qatar", "latitude": 25.4900, "longitude": 51.4542, "length_km": 5.419, "timezone": "Asia/Qatar", "altitude_m": 10, "series": "F1", "sector_count": 3, "surface_type": "abrasive"},
        {"name": "Hockenheimring", "country": "Germany", "latitude": 49.3278, "longitude": 8.5656, "length_km": 4.574, "timezone": "Europe/Berlin", "altitude_m": 103, "series": "DTM,GT3", "sector_count": 3, "surface_type": "standard_asphalt"},
        {"name": "Lausitzring", "country": "Germany", "latitude": 51.5294, "longitude": 13.9267, "length_km": 3.478, "timezone": "Europe/Berlin", "altitude_m": 120, "series": "DTM,ADAC GT", "sector_count": 3, "surface_type": "standard_asphalt"},
        {"name": "Norisring", "country": "Germany", "latitude": 49.4308, "longitude": 11.1125, "length_km": 2.300, "timezone": "Europe/Berlin", "altitude_m": 310, "series": "DTM", "sector_count": 3, "surface_type": "low_grip_street"},
        {"name": "Donington Park", "country": "United Kingdom", "latitude": 52.8306, "longitude": -1.3750, "length_km": 4.020, "timezone": "Europe/London", "altitude_m": 80, "series": "BTCC,GT3", "sector_count": 3, "surface_type": "standard_asphalt"},
        {"name": "Oulton Park", "country": "United Kingdom", "latitude": 53.1772, "longitude": -2.6119, "length_km": 4.307, "timezone": "Europe/London", "altitude_m": 75, "series": "BTCC,GT3", "sector_count": 3, "surface_type": "standard_asphalt"},
        {"name": "Snetterton", "country": "United Kingdom", "latitude": 52.4636, "longitude": 0.9439, "length_km": 4.779, "timezone": "Europe/London", "altitude_m": 40, "series": "BTCC,GT3", "sector_count": 3, "surface_type": "standard_asphalt"},
        {"name": "Thruxton", "country": "United Kingdom", "latitude": 51.2086, "longitude": -1.6028, "length_km": 3.792, "timezone": "Europe/London", "altitude_m": 115, "series": "BTCC", "sector_count": 3, "surface_type": "standard_asphalt"},
        {"name": "Croft", "country": "United Kingdom", "latitude": 54.4508, "longitude": -1.5572, "length_km": 3.429, "timezone": "Europe/London", "altitude_m": 60, "series": "BTCC", "sector_count": 3, "surface_type": "standard_asphalt"},
        {"name": "Knockhill", "country": "United Kingdom", "latitude": 56.1231, "longitude": -3.5064, "length_km": 2.065, "timezone": "Europe/London", "altitude_m": 150, "series": "BTCC", "sector_count": 3, "surface_type": "standard_asphalt"},
        {"name": "Mugello", "country": "Italy", "latitude": 43.9975, "longitude": 11.3719, "length_km": 5.245, "timezone": "Europe/Rome", "altitude_m": 255, "series": "GT3,Ferrari Challenge", "sector_count": 3, "surface_type": "standard_asphalt"},
        {"name": "Vallelunga", "country": "Italy", "latitude": 42.1400, "longitude": 12.2944, "length_km": 4.085, "timezone": "Europe/Rome", "altitude_m": 180, "series": "GT3", "sector_count": 3, "surface_type": "standard_asphalt"},
        {"name": "Misano", "country": "Italy", "latitude": 43.9633, "longitude": 12.6847, "length_km": 4.226, "timezone": "Europe/Rome", "altitude_m": 10, "series": "MotoGP,GT3", "sector_count": 3, "surface_type": "standard_asphalt"},
        {"name": "Magny-Cours", "country": "France", "latitude": 46.8642, "longitude": 3.1636, "length_km": 4.411, "timezone": "Europe/Paris", "altitude_m": 250, "series": "GT3,FFSA", "sector_count": 3, "surface_type": "standard_asphalt"},
        {"name": "Paul Ricard", "country": "France", "latitude": 43.2506, "longitude": 5.7917, "length_km": 5.842, "timezone": "Europe/Paris", "altitude_m": 410, "series": "F1,GT3,WEC", "sector_count": 3, "surface_type": "high_grip_asphalt"},
        {"name": "Estoril", "country": "Portugal", "latitude": 38.7506, "longitude": -9.3933, "length_km": 4.182, "timezone": "Europe/Lisbon", "altitude_m": 80, "series": "GT3", "sector_count": 3, "surface_type": "standard_asphalt"},
        {"name": "Motorland Aragon", "country": "Spain", "latitude": 41.0819, "longitude": -0.3350, "length_km": 5.345, "timezone": "Europe/Madrid", "altitude_m": 350, "series": "MotoGP,GT3", "sector_count": 3, "surface_type": "standard_asphalt"},
        {"name": "Circuito de Navarra", "country": "Spain", "latitude": 42.5025, "longitude": -1.8381, "length_km": 3.933, "timezone": "Europe/Madrid", "altitude_m": 400, "series": "GT3", "sector_count": 3, "surface_type": "standard_asphalt"},
        {"name": "Valencia Ricardo Tormo", "country": "Spain", "latitude": 39.4878, "longitude": -0.6317, "length_km": 4.005, "timezone": "Europe/Madrid", "altitude_m": 55, "series": "MotoGP,Formula E", "sector_count": 3, "surface_type": "standard_asphalt"},
        # --- Japan additions ---
        {"name": "Fuji Speedway", "country": "Japan", "latitude": 35.3719, "longitude": 138.9272, "length_km": 4.563, "timezone": "Asia/Tokyo", "altitude_m": 560, "series": "WEC,Super GT", "sector_count": 3, "surface_type": "standard_asphalt"},
        {"name": "Autopolis", "country": "Japan", "latitude": 33.1736, "longitude": 131.1508, "length_km": 4.674, "timezone": "Asia/Tokyo", "altitude_m": 700, "series": "Super GT,Super Formula", "sector_count": 3, "surface_type": "standard_asphalt"},
        {"name": "Sportsland Sugo", "country": "Japan", "latitude": 38.1886, "longitude": 140.2733, "length_km": 3.704, "timezone": "Asia/Tokyo", "altitude_m": 180, "series": "Super GT,Super Formula", "sector_count": 3, "surface_type": "standard_asphalt"},
        {"name": "Motegi", "country": "Japan", "latitude": 36.5311, "longitude": 140.2281, "length_km": 4.801, "timezone": "Asia/Tokyo", "altitude_m": 200, "series": "MotoGP,Super GT", "sector_count": 3, "surface_type": "standard_asphalt"},
        {"name": "Okayama", "country": "Japan", "latitude": 34.9164, "longitude": 134.2222, "length_km": 3.703, "timezone": "Asia/Tokyo", "altitude_m": 270, "series": "Super GT", "sector_count": 3, "surface_type": "standard_asphalt"},
        # --- Asia additions ---
        {"name": "Shanghai International Circuit", "country": "China", "latitude": 31.3389, "longitude": 121.2197, "length_km": 5.451, "timezone": "Asia/Shanghai", "altitude_m": 5, "series": "F1,WEC", "sector_count": 3, "surface_type": "standard_asphalt"},
        {"name": "Sepang", "country": "Malaysia", "latitude": 2.7614, "longitude": 101.7381, "length_km": 5.543, "timezone": "Asia/Kuala_Lumpur", "altitude_m": 40, "series": "MotoGP,GT3", "sector_count": 3, "surface_type": "high_grip_asphalt"},
        {"name": "Buriram Chang Circuit", "country": "Thailand", "latitude": 14.9472, "longitude": 103.0856, "length_km": 4.554, "timezone": "Asia/Bangkok", "altitude_m": 170, "series": "MotoGP,Super GT", "sector_count": 3, "surface_type": "standard_asphalt"},
        {"name": "Korea International Circuit", "country": "South Korea", "latitude": 34.7331, "longitude": 126.4172, "length_km": 5.621, "timezone": "Asia/Seoul", "altitude_m": 10, "series": "F1", "sector_count": 3, "surface_type": "standard_asphalt"},
        # --- Australia additions ---
        {"name": "Albert Park", "country": "Australia", "latitude": -37.8497, "longitude": 144.9686, "length_km": 5.278, "timezone": "Australia/Melbourne", "altitude_m": 5, "series": "F1", "sector_count": 3, "surface_type": "low_grip_street"},
        {"name": "Sandown Raceway", "country": "Australia", "latitude": -37.9233, "longitude": 145.1700, "length_km": 3.100, "timezone": "Australia/Melbourne", "altitude_m": 40, "series": "Supercars", "sector_count": 3, "surface_type": "standard_asphalt"},
        {"name": "Symmons Plains", "country": "Australia", "latitude": -41.5331, "longitude": 147.2569, "length_km": 2.410, "timezone": "Australia/Hobart", "altitude_m": 160, "series": "Supercars", "sector_count": 3, "surface_type": "standard_asphalt"},
        {"name": "Hidden Valley", "country": "Australia", "latitude": -12.4381, "longitude": 130.8756, "length_km": 2.870, "timezone": "Australia/Darwin", "altitude_m": 30, "series": "Supercars", "sector_count": 3, "surface_type": "standard_asphalt"},
        {"name": "The Bend Motorsport Park", "country": "Australia", "latitude": -35.4450, "longitude": 139.2819, "length_km": 7.770, "timezone": "Australia/Adelaide", "altitude_m": 60, "series": "Supercars,GT3", "sector_count": 3, "surface_type": "standard_asphalt"},
        {"name": "Surfers Paradise Street Circuit", "country": "Australia", "latitude": -28.0039, "longitude": 153.4281, "length_km": 4.470, "timezone": "Australia/Brisbane", "altitude_m": 5, "series": "Supercars", "sector_count": 3, "surface_type": "low_grip_street"},
        # --- Americas additions ---
        {"name": "Road America", "country": "USA", "latitude": 43.8011, "longitude": -87.9892, "length_km": 6.515, "timezone": "America/Chicago", "altitude_m": 260, "series": "IMSA,IndyCar", "sector_count": 3, "surface_type": "standard_asphalt"},
        {"name": "Watkins Glen", "country": "USA", "latitude": 42.3369, "longitude": -76.9272, "length_km": 5.430, "timezone": "America/New_York", "altitude_m": 480, "series": "IMSA,NASCAR", "sector_count": 3, "surface_type": "standard_asphalt"},
        {"name": "Sebring Raceway", "country": "USA", "latitude": 27.4545, "longitude": -81.3483, "length_km": 6.019, "timezone": "America/New_York", "altitude_m": 20, "series": "IMSA,WEC", "sector_count": 3, "surface_type": "concrete_mix"},
        {"name": "Road Atlanta", "country": "USA", "latitude": 34.1469, "longitude": -83.8117, "length_km": 4.088, "timezone": "America/New_York", "altitude_m": 345, "series": "IMSA,Petit Le Mans", "sector_count": 3, "surface_type": "standard_asphalt"},
        {"name": "Indianapolis Road Course", "country": "USA", "latitude": 39.7953, "longitude": -86.2353, "length_km": 3.925, "timezone": "America/Indiana/Indianapolis", "altitude_m": 218, "series": "IndyCar,IMSA", "sector_count": 3, "surface_type": "standard_asphalt"},
        {"name": "Long Beach Street Circuit", "country": "USA", "latitude": 33.7636, "longitude": -118.1886, "length_km": 3.167, "timezone": "America/Los_Angeles", "altitude_m": 5, "series": "IndyCar,IMSA", "sector_count": 3, "surface_type": "low_grip_street"},
        {"name": "Detroit Street Circuit", "country": "USA", "latitude": 42.3289, "longitude": -83.0458, "length_km": 2.350, "timezone": "America/Detroit", "altitude_m": 180, "series": "IndyCar", "sector_count": 3, "surface_type": "low_grip_street"},
        {"name": "VIRginia International Raceway", "country": "USA", "latitude": 36.5711, "longitude": -79.2097, "length_km": 5.263, "timezone": "America/New_York", "altitude_m": 250, "series": "IMSA,GT3", "sector_count": 3, "surface_type": "standard_asphalt"},
        {"name": "Canadian Tire Motorsport Park", "country": "Canada", "latitude": 44.0481, "longitude": -79.3606, "length_km": 3.957, "timezone": "America/Toronto", "altitude_m": 280, "series": "IMSA", "sector_count": 3, "surface_type": "standard_asphalt"},
        {"name": "Miami International Autodrome", "country": "USA", "latitude": 25.9581, "longitude": -80.2389, "length_km": 5.412, "timezone": "America/New_York", "altitude_m": 3, "series": "F1", "sector_count": 3, "surface_type": "standard_asphalt"},
        {"name": "Las Vegas Strip Circuit", "country": "USA", "latitude": 36.1147, "longitude": -115.1728, "length_km": 6.201, "timezone": "America/Los_Angeles", "altitude_m": 620, "series": "F1", "sector_count": 3, "surface_type": "low_grip_street"},
        {"name": "Mexico City Autodromo", "country": "Mexico", "latitude": 19.4042, "longitude": -99.0907, "length_km": 4.304, "timezone": "America/Mexico_City", "altitude_m": 2240, "series": "F1,WEC", "sector_count": 3, "surface_type": "standard_asphalt"},
        # --- Middle East additions ---
        {"name": "Baku City Circuit", "country": "Azerbaijan", "latitude": 40.3725, "longitude": 49.8533, "length_km": 6.003, "timezone": "Asia/Baku", "altitude_m": -10, "series": "F1,Formula 2", "sector_count": 3, "surface_type": "low_grip_street"},
        # --- Spain additions ---
        {"name": "Circuito del Jarama", "country": "Spain", "latitude": 40.6169, "longitude": -3.5847, "length_km": 3.850, "timezone": "Europe/Madrid", "altitude_m": 609, "series": "F1,GT3,Touring Cars", "sector_count": 3, "surface_type": "standard_asphalt"},
    ]
    for data in circuits:
        db.add(Circuit(**data))
    db.commit()


@app.get("/")
def root():
    return {"status": "ok", "service": settings.PROJECT_NAME}


@app.get("/health")
def health():
    from app.db.session import SessionLocal
    from app.models.circuit import Circuit
    from app.services.weather_service import WeatherService, cache_stats

    svc = WeatherService()
    try:
        db = SessionLocal()
        circuit_count = db.query(Circuit).count()
        db.close()
        db_status = "connected"
    except Exception as e:
        circuit_count = 0
        db_status = f"error: {e}"

    return {
        "status": "healthy",
        "database": db_status,
        "mode": "demo" if svc.is_demo_mode else "live",
        "circuit_count": circuit_count,
        "cache": cache_stats(),
    }
