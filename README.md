# Sentinel-HealOps

## Autonomous SRE and Self-Healing Infrastructure for a High-Frequency C++ Order Matching Engine

### Project Overview
HealOps is a fully autonomous Site Reliability Engineering (SRE) layer integrated with a high-frequency C++ Order Matching Engine. It utilizes non-blocking I/O for telemetry ingestion and a Hybrid AI Classifier (Random Forest + LLM fallback) to identify latency anomalies in real-time and trigger automated failovers via CI/CD webhooks.

### Key Components
- **C++ Matching Engine (`/engine`)**: A Level 3 (L3) order matching engine capable of sub-millisecond execution.
- **Telemetry Interceptor (`/interceptor`)**: A zero-overhead sidecar for log and metric ingestion utilizing `io_uring`.
- **AI Brain (`/brain`)**: A Python FastAPI-based decision engine for anomaly detection and remediation.
- **Governor (`/governor`)**: CI/CD and infrastructure configuration for automated recovery.

### Development Status
- [x] Repository Initialized
- [ ] Phase 1: Engine and baseline metrics
- [ ] Phase 2: HealOps Integration
- [ ] Phase 3: Chaos Engineering and Verification

### Implementation Strategy
1. **Engine Development**: High-performance C++ matching logic.
2. **Telemetry Ingestion**: Low-latency interception.
3. **AI Triage**: Statistical and machine learning-based anomaly classification.
4. **Autonomous Remediation**: Webhook-driven failover.

---
**Author**: Ashish Parmar  
**Institution**: IIIT Lucknow (IIITL)  
**Specialization**: Artificial Intelligence & Machine Learning  
**Date**: March 2026
