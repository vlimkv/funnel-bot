#!/bin/bash

# Скрипт быстрого старта Telegram-бота
# Использование: ./quick-start.sh

set -e

echo "🤖 Telegram Bot Quick Start"
echo "============================="
echo ""

# Проверка Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker не установлен. Установите Docker: https://docs.docker.com/get-docker/"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose не установлен. Установите Docker Compose."
    exit 1
fi

echo "✓ Docker и Docker Compose установлены"
echo ""

# Проверка .env файла
if [ ! -f .env ]; then
    echo "📝 Создаем .env файл..."
    cp .env.example .env
    echo ""
    echo "⚠️  ВАЖНО: Отредактируйте .env файл и добавьте ваш BOT_TOKEN"
    echo ""
    read -p "Введите ваш Telegram Bot Token: " BOT_TOKEN
    
    if [ -z "$BOT_TOKEN" ]; then
        echo "❌ Token не может быть пустым"
        exit 1
    fi
    
    # Обновляем .env
    sed -i "s/BOT_TOKEN=.*/BOT_TOKEN=$BOT_TOKEN/" .env
    echo "✓ Token сохранен"
else
    echo "✓ Файл .env уже существует"
fi

echo ""
echo "🐳 Запускаем Docker контейнеры..."
docker-compose up -d

echo ""
echo "⏳ Ожидаем запуска базы данных..."
sleep 5

echo ""
echo "📊 Проверяем статус..."
docker-compose ps

echo ""
echo "📋 Логи бота (Ctrl+C для выхода):"
echo ""
docker-compose logs -f bot