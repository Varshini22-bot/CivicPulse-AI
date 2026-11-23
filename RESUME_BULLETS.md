# CivicPulse AI — Resume Bullets & Interview Portfolio Highlights

These resume bullet points and portfolio descriptions are strictly verified against reproducible repository benchmarks (`EVIDENCE.md`, `ml/eval/priority_sensitivity_results.json`, `ml/eval/duplicate_benchmark_results.json`, and `ml/eval/ood_benchmark_results.json`). Every quantitative metric cited here is backed by unit tests and deterministic scripts.

---

## 🚀 Resume Bullet Points (Copy & Paste for AI / ML / Full-Stack Roles)

### Track 1: AI / Machine Learning Engineer
- **Multi-Modal Civic Infrastructure Diagnostics**: Designed an explainable multi-model vision pipeline combining OpenCLIP (ViT-B/32, 512-d zero-shot embeddings) and custom heuristics across 8 municipal defect categories, enforcing strict `BaseAnalyzer` abstention contracts when images or trained weights are unavailable.
- **Geospatial & Semantic Duplicate Detection**: Built an automated municipal duplicate detection service integrating Haversine distance, temporal exponential decay ($t_{1/2}=48\text{h}$), bitwise perceptual hashing (Hamming distance on 64-bit dHash), and OpenCLIP cosine similarity, with dynamic weight renormalization for missing photographic evidence.
- **Empirical Validation & Uncertainty Reporting**: Evaluated duplicate detection on a held-out test split ($N=40$) with hard negatives (same category within 200m, different defect), achieving 0.776 F1 (95% CI: [0.622, 0.889]) with OpenCLIP and 0.706 F1 (95% CI: [0.542, 0.830]) with bitwise pHash; documented overlapping confidence intervals to honestly avoid ungrounded superiority claims.
- **Fine-Tuned YOLOv8n Object Detection**: Architected sequence-grouped dataset pipelines for RDD2022 (India subset) to prevent dashcam consecutive-frame test leakage; verified sub-millisecond ONNX Runtime CPU export parity ($\text{MAE} < 10^{-4}$) against PyTorch. `[FILL AFTER COLAB/REAL PHOTOS: Test mAP50 = X.XX, mAP50-95 = X.XX across D00/D10/D20/D40 defect classes]`.
- **Field Generalization on Bengaluru Photos**: `[FILL AFTER COLAB/REAL PHOTOS: Benchmarked Zero-Shot CLIP and YOLOv8n detector on N=XX authentic smartphone photos across Bengaluru neighborhoods, measuring real-world domain transfer and viewpoint robustness]`.

### Track 2: Data Engineer & Geospatial Systems
- **Priority Scoring Engine & Sensitivity Analysis**: Engineered an explainable civic urgency algorithm combining physical severity (35%), public safety hazard (25%), OpenStreetMap POI vulnerability (+35% near hospitals/schools) (15%), community upvotes (15%), and continuous saturating age escalation ($1 - e^{-t/72}$, 10%).
- **Monte Carlo Rank Stability Verification**: Demonstrated rank preservation across all 140 seeded database records via 200 Monte Carlo perturbation trials, proving Kendall's $\tau \ge 0.962$ (95% CI: [0.934, 0.981]) under $\pm 20\%$ feature jitter.
- **Geospatial Hotspot Clustering & Routing Optimization**: Deployed DBSCAN and HDBSCAN density clustering on PostGIS spatial coordinates to identify recurring systemic infrastructure failure corridors, integrating Google OR-Tools Vehicle Routing Problem (VRP) algorithms to generate cost-minimized municipal dispatch routes.
- **Two-Tier Spatial Gating Architecture**: Designed an optimized two-tier spatial gating pipeline pairing a coarse database query bounding box pre-filter ($\sim 275\text{m}$) with category-specific physical matching radii (25m–80m base $+ 10\text{m}$ urban GPS accuracy margin), cutting full-table spatial scan overhead.

### Track 3: Full-Stack / Software Engineer
- **Production-Style Municipal Platform**: Developed an enterprise-grade civic management portal using FastAPI, PostgreSQL/PostGIS, SQLAlchemy, Alembic, and React 19 + TypeScript + Vite + Tailwind CSS, featuring role-based access control (RBAC), audit logging, and automated worker assignment.
- **Privacy-by-Design Photographic Ingestion**: Implemented automatic in-memory EXIF/GPS metadata stripping and bundled OpenCV Haar Cascade frontal face anonymization ($30\sigma$ Gaussian blur), overwriting unredacted images in-place to guarantee raw unblurred citizen photos are never retained or served.
- **Defensive Engineering & Test Automation**: Built a comprehensive 72-test automated backend test suite (pytest) and frontend test suite (Vitest + JSDOM) covering negative RBAC authorization, SQL injection boundaries, rate limiting, and automated doc-metric synchronization.

---

## 🎯 Portfolio Project Summary (for Cover Letters & GitHub Profile)

> **CivicPulse AI** is an intelligent civic infrastructure detection, geospatial prioritization, and municipal resolution platform tailored for high-density metropolitan environments like Bengaluru.
>
> Unlike typical hackathon mockups, CivicPulse AI was built with rigorous engineering standards:
> - **Scientific Honesty**: Deployed an honest BaseAnalyzer contract that cleanly abstains (`status="abstain"`) when data or weights are absent, rejecting fabricated benchmark metrics.
> - **Statistical Rigor**: All cited model metrics report sample size $N$ and 95% bootstrap confidence intervals, explicitly discussing where confidence intervals overlap.
> - **Data Provenance**: Every seeded record is tagged `is_synthetic=True` with permanent UI demonstration banners.
> - **Privacy First**: EXIF GPS coordinates are stripped before storage, and detected faces are blurred in-place with raw originals never archived.
> - **Scalability**: Designed for horizontal scaling with PostGIS spatial indexing, Docker containerization, and pgvector migration pathways.
