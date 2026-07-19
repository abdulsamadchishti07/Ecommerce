# EvoCart — Django Ecommerce Platform

A Django-based ecommerce site with product browsing, Redis-backed cart, and
custom email-based authentication (with social login via django-allauth).
Built as a Summer Internship 2026 project.

## Stack

- **Backend:** Django 5
- **Database:** PostgreSQL
- **Cache / Sessions / Cart:** Redis
- **Auth:** Custom email-based User model + django-allauth (social login)
- **Frontend:** Django templates + Tailwind CSS
- **Infra:** Docker + Docker Compose

Planned but not yet wired in: Django REST Framework, Celery, Stripe, HTMX.
They're in `requirements.txt` ahead of use — don't assume they're active.

## What's working

- **Accounts** — custom email-based user model, signup/login/logout,
  password change/reset, profile editing, address management, social auth
  (allauth) routes.
- **Products** — category and brand models, product listing (home page),
  category detail pages, product detail pages.
- **Cart** — Redis-backed cart (add / update / remove / view), tied to the
  session so it persists pre-login.

## What's not built yet

- **Orders** — app scaffolded, no models, no views, no URLs.
- **Payments** — app scaffolded, no models, no views, no URLs. Stripe not
  integrated yet.
- **Reviews** — app scaffolded, empty.
- **Search** — app scaffolded, empty.
- **Tests** — coverage is partial and growing alongside features, not
  comprehensive yet.
- **REST API** — not built. DRF is a dependency but unused so far.

## Project structure

```
ecommerce/
├── config/                # Django project config (settings, urls, wsgi/asgi)
│   └── settings/
│       ├── base.py
│       ├── dev.py
│       └── prod.py
├── apps/
│   ├── core/               # shared abstract models (e.g. TimeStampField)
│   ├── accounts/           # custom User, Profile, Address, auth
│   ├── products/           # Product, Category, Brand, Variant
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
   # edit .env — set SECRET_KEY, DB credentials, etc.
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

## Roadmap

1. Order model + cart-to-order conversion, with a deliberate decision on
   when stock is decremented (order creation vs. payment confirmation).
2. Stripe checkout session tied to Order totals, plus webhook handling.
3. Product reviews and ratings.
4. Basic product search.
5. Test coverage for cart → order → payment flow, including edge cases
   (empty cart, out-of-stock, concurrent checkout).
