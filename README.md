# Apex Weather - Motorsport Weather Intelligence

Hyper-local weather intelligence platform for motorsport circuits worldwide. Built for race engineers, strategy teams, and pitwall operations.

## Features (MVP)

- **Circuit Database** — 30 global circuits with coordinates, series, and metadata
- **Live Weather** — Real-time conditions via Tomorrow.io API
- **Track Temperature** — Estimated surface temperature model (air temp + solar + wind)
- **Rain ETA** — Predicted rainfall arrival time from forecast data
- **Weather Alerts** — Automated alerts for rain, wind, temperature drops, grip conditions
- **12-Hour Forecast** — Hourly forecast with precipitation probability visualization
- **Radar Map** — Circuit-centered map with coverage overlay (Leaflet + CARTO dark tiles)
- **Pitwall Dashboard** — High-contrast, glanceable UI designed for garage monitors

## Tech Stack

| Layer    | Technology                        |
| -------- | --------------------------------- |
| Frontend | Next.js 15, React 19, TypeScript, Tailwind CSS |
| Backend  | Python 3.12, FastAPI, SQLAlchemy 2.0 |
| Database | PostgreSQL 16                     |
| Maps     | Leaflet + CARTO dark basemap      |
| Weather  | Tomorrow.io API (v4)              |
| Infra    | Docker, docker-compose            |

## Quick Start

### Prerequisites

- Docker and docker-compose
- A [Tomorrow.io](https://www.tomorrow.io/) API key (free tier works)

### Setup

1. Clone the repository:
   ```bash
   cd "Apex Weather"
   ```

2. Configure environment:
   ```bash
   cp .env.example .env
   # Edit .env and add your TOMORROW_API_KEY
   ```

3. Start the platform:
   ```bash
   docker-compose up --build
   ```

4. Seed the circuit database:
   ```bash
   docker-compose exec backend python scripts/seed_circuits.py
   ```

5. Open the dashboard:
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API docs: http://localhost:8000/docs

### Without Docker

**Backend:**
```bash
cd backend
pip install -r requirements.txt
# Start PostgreSQL separately, update DATABASE_URL in .env
uvicorn app.main:app --reload
python scripts/seed_circuits.py
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

## API Routes

| Method | Path                          | Description              |
| ------ | ----------------------------- | ------------------------ |
| GET    | `/api/v1/circuits/`           | List all circuits        |
| GET    | `/api/v1/circuits/{id}`       | Get circuit by ID        |
| GET    | `/api/v1/weather/{circuit_id}` | Get weather for circuit |
| GET    | `/health`                     | Health check             |

## Project Structure

```
├── backend/
│   ├── app/
│   │   ├── algorithms/      # Rain ETA, track temp, alerts engine
│   │   ├── api/             # FastAPI route handlers
│   │   ├── core/            # Config and settings
│   │   ├── db/              # Database session and base
│   │   ├── models/          # SQLAlchemy models
│   │   ├── schemas/         # Pydantic schemas
│   │   ├── services/        # Weather providers (Tomorrow.io)
│   │   └── workers/         # Background tasks (future)
│   ├── alembic/             # Database migrations
│   └── scripts/             # Seed data scripts
├── frontend/
│   └── src/
│       ├── app/             # Next.js app router
│       ├── components/      # React components
│       ├── hooks/           # Custom React hooks
│       ├── lib/             # API client
│       └── types/           # TypeScript types
├── data/                    # Static data files
├── docs/                    # Documentation
└── docker-compose.yml
```

## Algorithms

### Track Temperature Model
Estimates asphalt surface temperature:
```
track_temp = air_temp + (solar_radiation × 0.03) - (wind_speed × 0.2) - (humidity_factor)
```

### Rain ETA
Scans hourly forecast for first point with >40% precipitation probability. Future versions will use radar storm motion vectors.

### Alerts Engine
Threshold-based alerts:
- **Rain**: >70% probability = warning, active precipitation = critical
- **Wind**: >40 km/h = warning, >60 km/h = critical
- **Temperature**: >5°C drop in 3h = warning
- **Grip**: cold + wet = critical

## Roadmap

- **Phase 2**: Sector-level weather modeling, storm motion tracking from radar frames
- **Phase 3**: Satellite imagery integration, lightning detection
- **Phase 4**: AI prediction models, trackside sensor network integration

## License

Proprietary. All rights reserved.
