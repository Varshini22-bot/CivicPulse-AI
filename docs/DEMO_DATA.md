# CivicPulse AI — Realistic Demonstration Dataset & Reset Guide

## 1. Dataset Overview

CivicPulse AI includes a curated, realistic municipal civic dataset centered in **Bengaluru (Bangalore), Karnataka**. 

> [!NOTE]
> All demonstration records are explicitly labeled with `[DEMO DATA]` in their titles and descriptions. They represent realistic urban infrastructure scenarios for software evaluation, developer testing, and stakeholder demonstrations.

---

## 2. Municipal Scope & Geographical Coverage

The dataset models civic issues across **12 distinct urban localities and municipal wards**:
1. **Indiranagar**: 100ft Road, CMH Road, Defence Colony (High commercial traffic)
2. **Koramangala**: 80ft Road, Sony World Junction, 4th Block (Drainage & pavement issues)
3. **Whitefield**: ITPL Main Road, Hope Farm Junction (Heavy transit & construction runoff)
4. **HSR Layout**: Sector 1, 27th Main Road (Urban residential & stormwater runoff)
5. **Jayanagar**: 4th Block Complex, 11th Main (Pedestrian walkways & streetlights)
6. **Malleshwaram**: 8th Cross, Margosa Road, Sampige Road (Heritage residential & markets)
7. **Bellandur**: Outer Ring Road, EcoSpace Tech Park (Severe traffic corridors & drainage)
8. **Hebbal**: Airport Flyover ramp, Baptist Hospital service road (High-speed transit)
9. **Rajajinagar**: 1st Block, Industrial Area, Dr. Rajkumar Road (Industrial runoff & asphalt)
10. **Electronic City**: Phase 1 Toll Gate, Velankani Drive (Tech corridor & street fixtures)
11. **Yelahanka**: New Town, Kogilu Cross (Developing infrastructure & waste collection)
12. **CBD / Central**: MG Road, Brigade Road, Residency Road (Dense pedestrian core)

---

## 3. Civic Agencies & Departmental Structure

Reports are routed to five authentic statutory authorities:
- **BBMP-RD**: Bruhat Bengaluru Mahanagara Palike — Road Infrastructure & Engineering
- **BBMP-SWM**: Bruhat Bengaluru Mahanagara Palike — Solid Waste Management
- **BWSSB**: Bangalore Water Supply and Sewerage Board
- **BESCOM**: Bangalore Electricity Supply Company Limited
- **BBMP-SWD**: Bruhat Bengaluru Mahanagara Palike — Stormwater Drains & Lakes

### Active Municipal Field Engineers:
- *Er. Sridhar Murthy* (Senior Executive Engineer, BBMP Roads)
- *Deepa Narayanan* (Assistant Executive Engineer, BBMP Roads)
- *Manjunath K.* (Zonal SWM Coordinator, BBMP Solid Waste)
- *Anand Kumar* (Assistant Engineer, BWSSB Water Supply)
- *Lakshmi Prasad* (Sanitary Inspector, BWSSB Drainage)
- *Venkatesh Babu* (Assistant Executive Engineer, BESCOM Electrical)
- *Praveen Naik* (Sub-Station Supervisor, BESCOM Electrical)
- *Nandini S.* (Assistant Director, BBMP Stormwater Drains)

---

## 4. Duplicate Clusters for Geospatial Evaluation

To demonstrate spherical Haversine duplicate detection and administrative merger workflows, the dataset embeds deliberate duplicate pairs:
1. **Indiranagar**: Duplicate garbage overflow report 18m away submitted 3 hours later.
2. **Whitefield**: Secondary water pipeline rupture report 22m away submitted 2 hours later.
3. **HSR Layout**: Additional blocked culvert report 16m away submitted 4 hours later.
4. **CBD / Central**: Second broken luminaire complaint 12m away submitted 1 hour later.

Each pair generates an active `DuplicateCandidate` record with distance in meters, category match boolean, time delta in hours, and a composite similarity score.

---

## 5. Safe Reset Utility

If reports are edited, resolved, or deleted during a live demonstration or testing session, the original dataset can be restored instantly:

### Method A: Admin Dashboard UI
1. Navigate to the **Municipal Operations Control Center** (`/admin-dashboard`).
2. Click the **"Reset Demo Data"** button in the header action bar.
3. Confirm the modal prompt.
4. A floating toast confirmation will announce the successful restoration of 140+ reports.

### Method B: REST API Endpoint
Send an authenticated `POST` request:
```bash
curl -X POST "http://127.0.0.1:8000/api/admin/reset-demo-data" \
  -H "Authorization: Bearer <ADMIN_JWT_TOKEN>"
```

### Method C: Command-Line Seeding
Run the standalone Python seeder:
```bash
python -c "from app.database.connection import SessionLocal; from app.database.seed_data import seed_database; db = SessionLocal(); seed_database(db, force=True); db.close()"
```
