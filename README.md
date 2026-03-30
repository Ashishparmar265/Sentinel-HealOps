# Sentinel-HealOps

> **Autonomous SRE agent that detects latency anomalies in a C++ Order Matching Engine and triggers self-healing rollbacks — without human intervention.**

[![Build](https://img.shields.io/badge/status-in--development-orange)]()
[![License](https://img.shields.io/badge/license-MIT-blue)]()
[![Demo](https://img.shields.io/badge/live--demo-coming--soon-lightgrey)]()

---

## What It Does

HealOps is a self-healing infrastructure layer built alongside a high-frequency C++ Order Matching Engine. It:

1. **Ingests** logs at high throughput using `io_uring` (zero-copy kernel I/O)
2. **Detects** latency anomalies via Z-score statistical analysis
3. **Classifies** fault types using a scikit-learn Random Forest model
4. **Remediates** automatically via GitHub Actions webhooks (container restart / rollback)

---

## Architecture

```
┌─────────────────────┐      logs      ┌───────────────────────┐
│  C++ Matching Engine │ ─────────────► │  C++ Ingestor Sidecar │
│  (FIX Protocol LOB)  │                │  (io_uring + Z-score) │
└─────────────────────┘                └────────────┬──────────┘
                                                     │ anomaly events
                                                     ▼
                                       ┌───────────────────────┐
                                       │  Python Control Plane │
                                       │  (FastAPI + RF Model) │
                                       └────────────┬──────────┘
                                                     │ webhook
                                                     ▼
                                       ┌───────────────────────┐
                                       │  GitHub Actions       │
                                       │  (Rollback / Restart) │
                                       └───────────────────────┘
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Matching Engine | C++20, Boost.Asio |
| Telemetry Ingestor | C++, `io_uring`, lock-free ring buffers |
| Control Plane | Python 3.11, FastAPI, scikit-learn |
| Orchestration | Docker, Docker Compose, Kubernetes (kind/minikube) |
| CI/CD & Remediation | GitHub Actions |
| Dashboard | Streamlit (MVP) |

---

## MVP Roadmap (6 Weeks)

| Phase | Timeline | Goal |
|---|---|---|
| **Phase 1** | Week 1–2 | C++ ingestor + `io_uring` log harvester + Z-score anomaly detection |
| **Phase 2** | Week 3 | Python/FastAPI control plane + scikit-learn Random Forest classifier |
| **Phase 3** | Week 4–5 | GitHub Actions webhook for auto-rollback on local Kubernetes (kind) |
| **Phase 4** | Week 6 | Streamlit health dashboard + live public demo |

> **Out of scope for MVP**: Kafka, Redis, pgvector, eBPF, full OIDC, gRPC, WebSockets

---

## Target Performance Metrics

| Metric | Target |
|---|---|
| Log ingestion throughput | 20,000–40,000 logs/sec |
| Anomaly detection latency | < 30ms (Random Forest) |
| Mean Time To Recovery (MTTR) | < 60 seconds (automated rollback) |
| Engine throughput | > 10,000 orders/sec |

---

## How to Run (Coming Soon)

```bash
# 1. Start the matching engine + ingestor
docker compose up --build engine interceptor

# 2. Start the control plane
docker compose up brain
```

---

## Live Demo

🎥 Demo video will be linked here after MVP completion.

---

## Project Structure

```
Sentinel-HealOps/
├── engine/         # C++20 Order Matching Engine (FIX protocol LOB)
├── interceptor/    # C++ io_uring log ingestor sidecar
├── brain/          # Python FastAPI + scikit-learn anomaly classifier
├── governor/       # GitHub Actions + Kubernetes configs
├── scripts/        # Load generator + synthetic fault injection
├── docs/           # Architecture diagrams and design notes
├── CMakeLists.txt
└── README.md
```

---

**Author**: Ashish Parmar | IIIT Lucknow | M.Tech AI & ML | March 2026
