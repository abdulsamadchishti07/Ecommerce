# MyStore — Django Ecommerce Platform

A full ecommerce site built with Django, PostgreSQL, Redis, HTMX, and Tailwind CSS,
with a Stripe-powered checkout and a REST API (Django REST Framework) underneath.

## Stack

- **Backend:** Django 5, Django REST Framework
- **Database:** PostgreSQL
- **Cache / Sessions / Cart:** Redis
- **Background jobs:** Celery + Redis broker
- **Frontend:** Django templates + HTMX + Alpine.js + Tailwind CSS
- **Payments:** Stripe
- **Infra:** Docker + Docker Compose

## Project structure

```
ecommerce/
├── config/                # Django project config (settings, urls, celery, wsgi/asgi)
│   └── settings/
│       ├── base.py
│       ├── dev.py
│       └── prod.py
├── apps/
│   ├── core/               # shared abstract models, utils
│   ├── accounts/           # custom User, Profile, Address, auth
│   ├── products/           # Product, Category, Variant, Inventory
│   ├── cart/                # Redis-backed cart
│   ├── orders/              # order creation, status, history
│   ├── payments/            # Stripe checkout + webhooks
│   ├── reviews/              # ratings + comments
│   └── search/                # product search
├── templates/                  # Django templates (base.html + per-app)
├── static/                      # CSS/JS/images
├── docker-compose.yml
├── Dockerfile
└── requirements.txt
```

## Getting started

1. **Clone and configure environment variables**
   ```bash
   cp .env.example .env
   # edit .env — set SECRET_KEY, DB credentials, Stripe test keys, etc.
   ```

2. **Build and start the stack**
   ```bash
   docker-compose up --build
   ```

3. **Run migrations and create a superuser** (in a second terminal)
   ```bash
   docker-compose exec web python manage.py migrate
   docker-compose exec web python manage.py createsuperuser
   ```

4. **Visit the site**
   - Web: http://localhost:8000
   - Admin: http://localhost:8000/admin
   - API: http://localhost:8000/api/v1/

## Roadmap

- [x] Repo skeleton, Docker, split settings, custom User model
- [ ] `accounts`: Profile (avatar/bio), Address, auth views
- [ ] `products`: Category, Product, Variant, Inventory + admin
- [ ] `cart`: Redis-backed cart logic
- [ ] `orders` + `payments`: checkout flow, Stripe integration
- [ ] `reviews`: ratings + comments
- [ ] `search`: Postgres full-text search
- [ ] Deployment (Docker on Railway/Render/Fly.io)
