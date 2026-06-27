# Wearify — Multi-Vendor Fashion eCommerce Platform

> Production-ready architecture: FastAPI · PostgreSQL · Redis · Celery · React · Vite · Docker

---

## Quick Start (Local Development)

### Prerequisites
- Docker + Docker Compose
- Node.js 20+
- Python 3.12+

### 1. Clone and configure
```bash
git clone https://github.com/yourorg/wearify.git
cd wearify
cp .env.example .env
# Edit .env with your credentials
```

### 2. Start all services
```bash
docker-compose up -d
```

### 3. Run database migrations
```bash
docker-compose exec backend alembic upgrade head
```

### 4. Seed initial data (optional)
```bash
docker-compose exec backend python -m app.scripts.seed
```

### 5. Access the app
| Service     | URL                          |
|-------------|------------------------------|
| Frontend    | http://localhost:3000        |
| API         | http://localhost:8000        |
| API Docs    | http://localhost:8000/api/docs |
| Flower      | http://localhost:5555        |

---

## Project Structure

```
wearify/
├── backend/                    # FastAPI Python backend
│   ├── app/
│   │   ├── api/v1/endpoints/   # Route handlers
│   │   ├── core/               # Config, DB, Redis, Security
│   │   ├── models/             # SQLAlchemy ORM models
│   │   ├── schemas/            # Pydantic schemas
│   │   ├── services/           # Business logic layer
│   │   ├── tasks/              # Celery async tasks
│   │   └── utils/              # Helpers, validators
│   ├── alembic/                # Database migrations
│   ├── tests/                  # Pytest test suite
│   └── requirements.txt
│
├── frontend/                   # React + Vite frontend
│   ├── src/
│   │   ├── api/                # Axios API clients
│   │   ├── app/                # Redux store
│   │   ├── components/         # Reusable UI components
│   │   ├── features/           # Redux slices + feature components
│   │   ├── hooks/              # Custom React hooks
│   │   ├── pages/              # Route-level page components
│   │   ├── routes/             # React Router setup
│   │   └── utils/              # Formatters, storage, constants
│   ├── tailwind.config.js
│   └── vite.config.js
│
├── nginx/                      # Nginx reverse proxy config
├── docker-compose.yml          # Development
├── docker-compose.prod.yml     # Production
└── .env.example
```

---

## Backend Architecture

### Tech Stack
| Layer        | Technology               |
|--------------|--------------------------|
| Framework    | FastAPI (async)          |
| ORM          | SQLAlchemy 2 (asyncpg)   |
| Database     | PostgreSQL 16            |
| Cache        | Redis 7                  |
| Task Queue   | Celery + Redis broker    |
| Auth         | JWT (python-jose)        |
| Passwords    | bcrypt (passlib)         |
| Rate Limit   | slowapi                  |
| Storage      | Cloudinary / AWS S3      |
| Email        | SendGrid                 |
| Payments     | Paystack, Flutterwave, Stripe |
| Monitoring   | Sentry, Flower           |

### Running backend independently
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
alembic upgrade head
uvicorn app.main:app --reload
```

### Run Celery workers
```bash
# Worker (in separate terminal)
celery -A app.tasks worker --loglevel=info -Q default,emails,orders,notifications

# Beat scheduler (in another terminal)
celery -A app.tasks beat --loglevel=info

# Flower monitoring (optional)
celery -A app.tasks flower --port=5555
```

---

## Frontend Architecture

### Tech Stack
| Layer        | Technology                |
|--------------|---------------------------|
| Framework    | React 18 + Vite           |
| Styling      | Tailwind CSS v3           |
| State        | Redux Toolkit             |
| Routing      | React Router v6           |
| HTTP         | Axios (with interceptors) |
| Animations   | Framer Motion             |
| Toast        | react-hot-toast           |
| Forms        | React Hook Form           |

### Running frontend independently
```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

### Environment variables
```env
VITE_API_URL=/api/v1
VITE_WS_URL=ws://localhost:8000
VITE_PAYSTACK_PUBLIC=pk_test_xxxxx
VITE_FLUTTERWAVE_PUBLIC=FLWPUBK_TEST-xxxxx
```

---

## Database

### Running migrations
```bash
# Create new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback one
alembic downgrade -1
```

### Key Design Decisions
- **UUID PKs** everywhere — safe for distributed systems and ID enumeration attacks
- **JSONB** for flexible data (shipping address, KYC docs, notification payloads)
- **GIN indexes** on product tags for fast array filtering
- **Partial indexes** on `orders WHERE status='pending'` for common queries
- **Composite indexes** on `(vendor_id, status)` for vendor product dashboards
- **Audit log** table for compliance — consider table partitioning by month at scale

---

## Security Checklist

- [x] JWT access tokens (15-min TTL) + refresh tokens (7-day TTL)
- [x] Token blacklist in Redis (logout invalidation)
- [x] Access token stored in sessionStorage (cleared on tab close)
- [x] bcrypt password hashing (cost factor 12)
- [x] Rate limiting on all public endpoints (slowapi)
- [x] CORS restricted to allowed origins
- [x] Payment webhook signature verification (HMAC)
- [x] Idempotent payment processing (reference deduplication)
- [x] SQL injection protection via SQLAlchemy ORM
- [x] Role-based access control (customer / vendor / admin)
- [x] Audit logging for all write operations
- [x] Sentry error tracking (production)
- [x] Non-root Docker user
- [ ] TODO: Add TOTP 2FA for vendor/admin accounts
- [ ] TODO: Add field-level encryption for PII (phone, address)

---

## Payment Integration

### Paystack (Primary — Nigeria/Africa)
1. Get API keys from https://dashboard.paystack.com
2. Set `PAYSTACK_SECRET` and `PAYSTACK_PUBLIC` in `.env`
3. Configure webhook URL: `https://yourdomain.com/api/v1/payments/webhooks/paystack`
4. Webhook events to enable: `charge.success`, `transfer.success`

### Flutterwave (Secondary)
1. Get API keys from https://dashboard.flutterwave.com
2. Set `FLUTTERWAVE_SECRET` and `FLUTTERWAVE_PUBLIC` in `.env`
3. Configure webhook: `https://yourdomain.com/api/v1/payments/webhooks/flutterwave`

### Stripe (International)
1. Get keys from https://dashboard.stripe.com
2. Set `STRIPE_SECRET` and `STRIPE_WEBHOOK_SECRET`
3. Use Stripe CLI to test webhooks locally:
   ```bash
   stripe listen --forward-to localhost:8000/api/v1/payments/webhooks/stripe
   ```

---

## Production Deployment

### VPS Minimum Requirements
| Traffic Level | vCPUs | RAM  | Storage |
|---------------|-------|------|---------|
| Starter       | 4     | 8GB  | 80GB SSD|
| Medium        | 8     | 16GB | 160GB   |
| High          | 16+   | 32GB | 320GB + managed DB |

### Recommended: DigitalOcean or Hetzner
- DigitalOcean Droplet: 4 vCPU / 8GB → ~$48/month
- Hetzner CPX31: 4 vCPU / 8GB → ~€15/month (much cheaper)

### Deploy steps
```bash
# On your VPS
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

git clone https://github.com/yourorg/wearify.git
cd wearify
cp .env.example .env
nano .env  # fill in ALL secrets

# SSL setup
sudo apt install certbot -y
sudo certbot certonly --standalone -d wearify.com -d www.wearify.com
sudo cp /etc/letsencrypt/live/wearify.com/fullchain.pem nginx/ssl/
sudo cp /etc/letsencrypt/live/wearify.com/privkey.pem nginx/ssl/

# Run migrations and start
docker-compose -f docker-compose.prod.yml run --rm backend alembic upgrade head
docker-compose -f docker-compose.prod.yml up -d

# Check health
docker-compose -f docker-compose.prod.yml ps
curl https://wearify.com/health
```

### Auto-renew SSL
```bash
echo "0 0 1 * * certbot renew --quiet && docker-compose -f /path/to/wearify/docker-compose.prod.yml restart nginx" | sudo crontab -
```

---

## Scalability Roadmap

### Phase 1 (0–10K users): Current architecture
- Single VPS with Docker Compose
- PostgreSQL on same server
- Redis on same server

### Phase 2 (10K–100K users): Managed services
- Move to managed PostgreSQL (DO Managed DB / RDS)
- Move to managed Redis (ElastiCache / DO Redis)
- Add CDN for static assets (Cloudflare)
- Separate Celery workers to dedicated server

### Phase 3 (100K+ users): Distributed
- Kubernetes or Docker Swarm
- Read replicas for PostgreSQL
- Redis Cluster
- Extract notification service to dedicated microservice
- Add Elasticsearch for product search
- Implement GraphQL for frontend flexibility

---

## Testing

```bash
# Backend tests
cd backend
pytest tests/ -v --asyncio-mode=auto

# With coverage
pytest tests/ --cov=app --cov-report=html

# Frontend tests
cd frontend
npm test
```

---

## Contributing

1. `git checkout -b feature/your-feature`
2. Make changes with tests
3. `git commit -m "feat: description"`
4. Open PR against `main`

---

## License
MIT — built for the Wearify fashion marketplace project.
