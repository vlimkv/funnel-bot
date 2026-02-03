# Savoa Automated Wellness Bot 🤖

**A production-grade Telegram bot for automated content delivery, subscription management, and user onboarding.**

This bot serves as the primary engagement channel for the Savoa platform. It handles the entire user lifecycle: from the initial "warmup" marketing funnel to paid subscription management and daily content distribution.

![Python](https://img.shields.io/badge/Python-3.11+-blue?style=flat&logo=python&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Containerized-2496ED?style=flat&logo=docker&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Database-316192?style=flat&logo=postgresql&logoColor=white)

## ⚙️ Architecture

The bot is built with a modular architecture to ensure scalability and ease of maintenance.



## 🚀 Key Features

* **Marketing Funnels (`/routers/warmup.py`):** Automated sequences of messages and media to engage new users.
* **Subscription System (`/routers/subscription.py`):** Logic for handling paid access, expirations, and renewals.
* **Admin Dashboard (`/routers/admin.py`):** extensive commands for content managers to broadcast messages and view stats.
* **Background Tasks (`scheduler.py`):** Async scheduling for daily reminders and timed content delivery.
* **Containerization:** Fully dockerized setup for one-command deployment.

## 🛠 Tech Stack

* **Core:** Python (AsyncIO)
* **Framework:** Aiogram 3.x
* **Database:** PostgreSQL (Schema in `/sql`)
* **Deployment:** Docker & Docker Compose
* **Media:** Local asset management and cloud integration

## 📂 Project Structure

```bash
├── assets/             # Static media for funnels
├── sql/                # Database schemas and init scripts
├── src/
│   ├── routers/        # Logic handlers (Admin, User, Subscription)
│   ├── db.py           # Database connection & methods
│   ├── scheduler.py    # Cron-jobs and timed tasks
│   ├── main.py         # Entry point
│   └── ...utils
├── Dockerfile          # Image configuration
└── docker-compose.yml  # Orchestration
```

**Deployment**

Clone & Env:

```bash
cp .env.example .env
# Fill in BOT_TOKEN and DB_CREDENTIALS
```

Run with Docker:

```bash
docker-compose up -d --build
```
