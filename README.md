# Monitoring Stack Demo

Локальный observability-стенд, собранный вокруг небольшого Flask-приложения с пользователями и тикетами.

Проект показывает, как из маленького сервиса собрать воспроизводимый стенд для метрик, алертов, synthetic checks и dashboard provisioning. Репозиторий одновременно играет роль demo-сервиса и локального SRE/observability lab.

## Portfolio Role

Это основной observability / SRE flagship в портфолио.

Открывать этот репозиторий лучше, когда разговор идет про:

- Prometheus, Grafana и Alertmanager как единый operator flow
- synthetic checks и alerting
- dashboard provisioning и читаемую rule model
- CI, который валидирует monitoring-репозиторий, а не только Python-код

В общей структуре портфолио этот репозиторий дополняет `enterprise-onprem-platform-lab`: platform lab показывает более широкую инфраструктурную оболочку, а этот репозиторий идет глубже в сигналы, alerts и расследование инцидентов.

## Что показывает проект

- Prometheus-метрики на уровне приложения
- Бизнес-метрики, экспортируемые в InfluxDB
- Synthetic HTTP checks через Telegraf
- Автоматический provisioning datasource и dashboard в Grafana
- Alert rules для типовых operational-сценариев
- Воспроизводимый локальный стек через Docker Compose
- Тесты, линтинг, ignore-файлы и CI

## Review Path

Для быстрого технического ревью полезнее всего идти в таком порядке:

1. этот README для scope и demo flow
2. `docker-compose.yml` для общей топологии стенда
3. `prometheus.yml` и `alerts.yml` для scrape и alerting model
4. `grafana/provisioning/` и `grafana/dashboards/app-overview.json` для datasource/dashboard story
5. `monitoring_demo/app.py` и `monitoring_demo/metrics.py` для того, что именно экспортирует приложение
6. `.github/workflows/ci.yml` и `tests/test_app.py` для validation story

## Стек

- Python 3.12
- Flask
- SQLite
- Prometheus
- Grafana
- InfluxDB 2
- Telegraf
- Alertmanager
- Docker Compose
- pytest
- Ruff

## Как устроен поток данных

```text
Flask app
  |- /metrics ----------------------> Prometheus
  |- POST events -> Influx writer --> InfluxDB
  |- /health -----------------------> Telegraf HTTP check -> InfluxDB

Prometheus
  |- scrape app metrics
  |- evaluate alert rules
  |- send alerts -------------------> Alertmanager

Grafana
  |- Prometheus datasource
  |- InfluxDB datasource
  |- provisioned dashboard
```

## Структура репозитория

```text
.
├── monitoring_demo/
│   ├── app.py
│   ├── config.py
│   ├── db.py
│   ├── influx.py
│   └── metrics.py
├── tests/
├── grafana/
│   ├── dashboards/
│   └── provisioning/
├── docker-compose.yml
├── prometheus.yml
├── alerts.yml
├── alertmanager.yml
├── telegraf.conf
├── main.py
└── README.md
```

## Какие метрики есть

Проект публикует как технические, так и прикладные метрики. Среди них:

- `app_http_requests_total`
- `app_http_errors_total`
- `app_http_request_duration_seconds`
- `app_users_total`
- `app_tickets_total`
- `app_tickets_open`
- `app_tickets_closed_current`
- `app_tickets_overdue`
- `app_users_created_total`
- `app_tickets_created_total`
- `app_tickets_closed_total`
- `app_tickets_reopened_total`
- `app_demo_seed_runs_total`
- `app_influx_write_failures_total`

Это важно для самого стенда: сервис считает не только uptime и latency, но и состояние домена, из которого потом строятся operational dashboards и alerts.

## Demo API

- `GET /health` - статус приложения, базы и бизнес-статистика
- `GET /metrics` - endpoint для Prometheus
- `GET /users` - список пользователей
- `POST /users` - создать пользователя
- `GET /tickets` - список тикетов
- `POST /tickets` - создать тикет
- `POST /tickets/{id}/close` - закрыть тикет
- `POST /tickets/{id}/reopen` - переоткрыть тикет
- `POST /demo/seed` - наполнить приложение демо-данными
- `GET /demo/error` - принудительный `503` для проверки алертов

Примеры:

```bash
curl -X POST http://localhost:8000/demo/seed
curl -X POST http://localhost:8000/users -H "Content-Type: application/json" -d "{\"name\": \"alice\"}"
curl -X POST http://localhost:8000/tickets -H "Content-Type: application/json" -d "{\"title\": \"High latency alert\", \"age_hours\": 30}"
curl -X POST http://localhost:8000/tickets/1/close
curl http://localhost:8000/health
```

## Быстрый старт

```bash
cp .env.example .env
docker compose up --build
```

После старта доступны:

- App: `http://localhost:8000`
- Prometheus: `http://localhost:9090`
- Alertmanager: `http://localhost:9093`
- Grafana: `http://localhost:3000`
- InfluxDB: `http://localhost:8086`

Чтобы быстро увидеть стенд в действии:

```bash
curl -X POST http://localhost:8000/demo/seed
```

## Grafana и alerting

Автоматически создаются datasource:

- `Prometheus`
- `InfluxDB`

Автоматически создается dashboard:

- `Monitoring Demo - App Overview`

Alert rules описаны в [alerts.yml](alerts.yml):

- `MonitoringDemoAppDown`
- `MonitoringDemoErrorResponses`
- `MonitoringDemoOverdueTickets`
- `MonitoringDemoInfluxWriteFailures`

## Локальная разработка

```bash
python -m venv .venv
. .venv/bin/activate
# Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
python main.py
```

Линтинг:

```bash
ruff check .
```

Тесты:

```bash
pytest -q
```

## Заметки

- Приложение маленькое намеренно: основная ценность репозитория в observability-стеке, а не в бизнес-логике API.
- SQLite и синхронный экспорт в InfluxDB делают локальный стенд проще. Для production-варианта это стоило бы вынести в отдельный воркер или очередь.
- Стек собран так, чтобы локально воспроизводить типовой цикл: метрики, synthetic checks, alerts и dashboard provisioning.

## Что можно развивать дальше

- Loki + Grafana logs pipeline
- receiver для Alertmanager в Telegram или Slack
- load generator для воспроизводимых traffic spikes
- дополнительный Grafana dashboard под InfluxDB-представления
