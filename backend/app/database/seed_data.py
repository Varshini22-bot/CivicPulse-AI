import random
import uuid
import hashlib
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from app.models import (
    User, Department, Staff, Category, Report, AIPrediction, PriorityScore,
    DuplicateCandidate, Assignment, AuditLog, Notification
)
from app.core.security import get_password_hash
from app.services.priority_service import PriorityService
from app.services.duplicate_service import DuplicateService
from app.core.logging import logger

def seed_database(db: Session, force: bool = False):
    """
    Populates realistic Bengaluru municipal civic dataset.
    Clearly annotated as [DEMO DATA] for development and evaluation.
    """
    random.seed(42)
    # Check if already seeded
    existing_reports = db.query(Report).count()
    if existing_reports > 10 and not force:
        logger.info(f"Database already contains {existing_reports} reports. Skipping seed.")
        return

    if force:
        logger.info("Force flag set. Resetting transactional records for fresh demo seed...")
        try:
            db.query(DuplicateCandidate).delete()
            db.query(AuditLog).delete()
            db.query(Notification).delete()
            db.query(Assignment).delete()
            db.query(PriorityScore).delete()
            db.query(AIPrediction).delete()
            db.query(Report).delete()
            db.commit()
            logger.info("Transactional records cleared successfully.")
        except Exception as e:
            db.rollback()
            logger.warning(f"Error clearing existing records during force reset: {e}")

    logger.info("Initializing database seed data with realistic Bengaluru civic reports...")

    # 1. Seed Departments
    departments_data = [
        {
            "name": "BBMP Road Infrastructure & Engineering",
            "code": "BBMP-RD",
            "contact_email": "roads.bbmp@karnataka.gov.in",
            "phone": "+91-80-2222-1188",
            "description": "Responsible for arterial roads, asphalt resurfacing, pothole remediation, and pedestrian footpaths across Greater Bengaluru."
        },
        {
            "name": "BBMP Solid Waste Management (SWM)",
            "code": "BBMP-SWM",
            "contact_email": "swm.bbmp@karnataka.gov.in",
            "phone": "+91-80-2266-0000",
            "description": "Oversees municipal waste collection, secondary transfer stations, and clearing unauthorized roadside debris dumping."
        },
        {
            "name": "Bangalore Water Supply and Sewerage Board (BWSSB)",
            "code": "BWSSB",
            "contact_email": "helpdesk@bwssb.gov.in",
            "phone": "+91-80-2294-5100",
            "description": "Maintains Cauvery drinking water supply conduits, underground drainage pipelines, and stormwater drain desilting."
        },
        {
            "name": "Bangalore Electricity Supply Company (BESCOM)",
            "code": "BESCOM",
            "contact_email": "helpline@bescom.co.in",
            "phone": "+91-80-1912-0000",
            "description": "Powers municipal street lighting grids, maintenance of utility poles, and public electrical hazard mitigation."
        },
        {
            "name": "BBMP Stormwater Drains (SWD)",
            "code": "BBMP-SWD",
            "contact_email": "swd.bbmp@karnataka.gov.in",
            "phone": "+91-80-2297-5555",
            "description": "Primary and secondary stormwater rajakaluve networks, culverts, and urban flood prevention."
        }
    ]

    dept_map = {}
    for d_data in departments_data:
        existing = db.query(Department).filter(Department.code == d_data["code"]).first()
        if not existing:
            dept = Department(id=str(uuid.uuid4()), **d_data)
            db.add(dept)
            db.flush()
            dept_map[d_data["code"]] = dept
        else:
            dept_map[d_data["code"]] = existing

    # 2. Seed Staff Members
    staff_data = [
        {"name": "Ramesh Kumar", "email": "ramesh.kumar@bbmp.gov.in", "dept": "BBMP-RD", "desig": "Assistant Executive Engineer (Roads)"},
        {"name": "Priya Nair", "email": "priya.nair@bbmp.gov.in", "dept": "BBMP-RD", "desig": "Ward Infrastructure Inspector"},
        {"name": "Anil Deshmukh", "email": "anil.deshmukh@bbmp.gov.in", "dept": "BBMP-SWM", "desig": "Senior Sanitation Supervisor"},
        {"name": "Lakshmi Sundaram", "email": "lakshmi.s@bbmp.gov.in", "dept": "BBMP-SWM", "desig": "SWM Quality Officer"},
        {"name": "Karthik Venkatesh", "email": "karthik.v@bwssb.gov.in", "dept": "BWSSB", "desig": "Assistant Engineer (Water Supply)"},
        {"name": "Divya Murthy", "email": "divya.m@bwssb.gov.in", "dept": "BWSSB", "desig": "Sanitary Inspector"},
        {"name": "Suresh Gowda", "email": "suresh.gowda@bescom.co.in", "dept": "BESCOM", "desig": "Junior Engineer (Distribution)"},
        {"name": "Farhan Ahmed", "email": "farhan.a@bbmp.gov.in", "dept": "BBMP-SWD", "desig": "Drainage Maintenance Superintendent"}
    ]

    staff_map = {}
    for s_info in staff_data:
        existing = db.query(Staff).filter(Staff.email == s_info["email"]).first()
        if not existing:
            dept = dept_map[s_info["dept"]]
            stf = Staff(
                id=str(uuid.uuid4()),
                department_id=dept.id,
                name=s_info["name"],
                email=s_info["email"],
                designation=s_info["desig"],
                phone="+91-98800" + str(random.randint(10000, 99999))
            )
            db.add(stf)
            db.flush()
            staff_map[s_info["email"]] = stf
        else:
            staff_map[s_info["email"]] = existing

    # 3. Seed Categories
    categories_data = [
        {
            "code": "pothole",
            "name": "Pothole",
            "description": "Depression, rim fracture, or crater in asphalt roadway endangering vehicular or two-wheeler traffic.",
            "default_dept": "BBMP-RD",
            "icon": "circle-dot",
            "safety_weight": 0.85,
            "base_severity": 6,
            "keywords": ["pothole", "crater", "hole", "cavity", "asphalt", "bump", "tyre", "tire", "bike fell"]
        },
        {
            "code": "road_damage",
            "name": "Road Damage",
            "description": "Surface cracking, uneven tarmac, shoulder disintegration, or unfinished trench cuts.",
            "default_dept": "BBMP-RD",
            "icon": "git-commit",
            "safety_weight": 0.70,
            "base_severity": 5,
            "keywords": ["crack", "road damage", "tar", "uneven road", "broken road", "tarmac", "crumbling"]
        },
        {
            "code": "garbage_overflow",
            "name": "Garbage Overflow",
            "description": "Uncollected public bins overflowing with municipal solid waste posing hygiene and odor risks.",
            "default_dept": "BBMP-SWM",
            "icon": "trash-2",
            "safety_weight": 0.50,
            "base_severity": 4,
            "keywords": ["garbage", "trash", "waste", "bin", "overflowing", "rubbish", "litter", "smell", "rotting"]
        },
        {
            "code": "illegal_dumping",
            "name": "Illegal Dumping",
            "description": "Unauthorized large-scale construction debris, commercial waste, or vacant plot disposal.",
            "default_dept": "BBMP-SWM",
            "icon": "alert-triangle",
            "safety_weight": 0.65,
            "base_severity": 6,
            "keywords": ["dumping", "debris", "construction waste", "rubble", "discarded", "lorry dumped", "pile"]
        },
        {
            "code": "water_leakage",
            "name": "Water Leakage",
            "description": "Drinking water pipeline breach, leaking municipal valve, or continuous localized pooling.",
            "default_dept": "BWSSB",
            "icon": "droplet",
            "safety_weight": 0.60,
            "base_severity": 5,
            "keywords": ["water", "leak", "pipeline", "pipe burst", "drinking water", "flowing water", "puddle"]
        },
        {
            "code": "blocked_drain",
            "name": "Blocked Drain",
            "description": "Stormwater drain, roadside culvert, or gutter obstructed by silt or refuse leading to street waterlogging.",
            "default_dept": "BBMP-SWD",
            "icon": "layers",
            "safety_weight": 0.75,
            "base_severity": 6,
            "keywords": ["drain", "blocked", "gutter", "clogged", "sewage", "stormwater", "overflowing drain", "stagnant"]
        },
        {
            "code": "broken_streetlight",
            "name": "Broken Streetlight",
            "description": "Defective luminaire fixture, blackout along arterial stretch, or damaged streetlight pole.",
            "default_dept": "BESCOM",
            "icon": "lightbulb-off",
            "safety_weight": 0.65,
            "base_severity": 4,
            "keywords": ["streetlight", "lamp", "dark", "wire", "pole", "light not working", "bulb", "illumination"]
        },
        {
            "code": "damaged_infrastructure",
            "name": "Damaged Public Infrastructure",
            "description": "Broken sidewalk slabs, missing manhole covers, compromised pedestrian barriers, or shattered bus stops.",
            "default_dept": "BBMP-RD",
            "icon": "construction",
            "safety_weight": 0.80,
            "base_severity": 6,
            "keywords": ["footpath", "sidewalk", "railing", "bus stop", "manhole cover", "signboard", "divider", "pavement"]
        },
        {
            "code": "other",
            "name": "Other Civic Issue",
            "description": "General civic grievance requiring municipal assessment and departmental routing.",
            "default_dept": "BBMP-RD",
            "icon": "help-circle",
            "safety_weight": 0.40,
            "base_severity": 4,
            "keywords": ["general", "civic", "issue", "problem"]
        }
    ]

    cat_map = {}
    for c_data in categories_data:
        existing = db.query(Category).filter(Category.code == c_data["code"]).first()
        if not existing:
            dept = dept_map[c_data["default_dept"]]
            cat = Category(
                id=str(uuid.uuid4()),
                code=c_data["code"],
                name=c_data["name"],
                description=c_data["description"],
                default_department_id=dept.id,
                icon=c_data["icon"],
                safety_weight=c_data["safety_weight"],
                base_severity=c_data.get("base_severity", 5),
                keywords=c_data.get("keywords", [])
            )
            db.add(cat)
            db.flush()
            cat_map[c_data["code"]] = cat
        else:
            existing.base_severity = c_data.get("base_severity", 5)
            existing.keywords = c_data.get("keywords", [])
            cat_map[c_data["code"]] = existing

    # 4. Seed Standard Users
    # Admin User
    admin = db.query(User).filter(User.email == "admin@civicpulse.gov.in").first()
    if not admin:
        admin = User(
            id=str(uuid.uuid4()),
            email="admin@civicpulse.gov.in",
            password_hash=get_password_hash("Admin@12345"),
            full_name="Municipal Operations Officer",
            role="admin",
            phone="+91-80-2222-9999"
        )
        db.add(admin)
        db.flush()

    # Citizen User
    citizen = db.query(User).filter(User.email == "citizen@example.com").first()
    if not citizen:
        citizen = User(
            id=str(uuid.uuid4()),
            email="citizen@example.com",
            password_hash=get_password_hash("Citizen@12345"),
            full_name="Rahul Sharma",
            role="citizen",
            phone="+91-98450-12345"
        )
        db.add(citizen)
        db.flush()

    # Secondary Citizen User
    citizen2 = db.query(User).filter(User.email == "ananya.r@example.com").first()
    if not citizen2:
        citizen2 = User(
            id=str(uuid.uuid4()),
            email="ananya.r@example.com",
            password_hash=get_password_hash("Citizen@12345"),
            full_name="Ananya Rao",
            role="citizen",
            phone="+91-99801-67890"
        )
        db.add(citizen2)
        db.flush()

    # 5. Bengaluru Locality Hubs (Realistic Lat/Lng Anchors)
    LOCALITIES = [
        {"name": "Koramangala 4th Block", "area": "Koramangala", "lat": 12.9344, "lng": 77.6256},
        {"name": "Indiranagar 100ft Road", "area": "Indiranagar", "lat": 12.9784, "lng": 77.6408},
        {"name": "HSR Layout Sector 1", "area": "HSR Layout", "lat": 12.9121, "lng": 77.6446},
        {"name": "Whitefield Main Road", "area": "Whitefield", "lat": 12.9698, "lng": 77.7500},
        {"name": "MG Road Metro Junction", "area": "CBD / Central", "lat": 12.9756, "lng": 77.6066},
        {"name": "Jayanagar 4th Block", "area": "Jayanagar", "lat": 12.9308, "lng": 77.5838},
        {"name": "Malleshwaram 8th Cross", "area": "Malleshwaram", "lat": 13.0031, "lng": 77.5702},
        {"name": "Electronic City Phase 1", "area": "Electronic City", "lat": 12.8452, "lng": 77.6602},
        {"name": "Hebbal Flyover Junction", "area": "Hebbal", "lat": 13.0358, "lng": 77.5970},
        {"name": "Marathahalli Outer Ring Road", "area": "Marathahalli", "lat": 12.9591, "lng": 77.6974},
        {"name": "BTM Layout 2nd Stage", "area": "BTM Layout", "lat": 12.9166, "lng": 77.6101},
        {"name": "Rajajinagar 1st Block", "area": "Rajajinagar", "lat": 12.9915, "lng": 77.5524}
    ]

    # Pre-crafted realistic issue templates
    ISSUE_TEMPLATES = [
        # Potholes
        {
            "cat": "pothole",
            "title": "[DEMO DATA] Hazardous crater pothole near intersection",
            "desc": "Severe asphalt depression over 8 inches deep causing vehicles to brake abruptly. Two-wheelers skidding frequently during evening traffic.",
            "sev": 8,
            "weights": {"ed": 0.14, "dp": 0.38, "sat": 0.12}
        },
        {
            "cat": "pothole",
            "title": "[DEMO DATA] Continuous cluster of potholes on bus route",
            "desc": "Series of deep potholes developing after recent rainfall. Water has accumulated inside, obscuring depth.",
            "sev": 7,
            "weights": {"ed": 0.11, "dp": 0.28, "sat": 0.15}
        },
        # Road Damage
        {
            "cat": "road_damage",
            "title": "[DEMO DATA] Extensive alligator cracking and sunken tarmac",
            "desc": "Road surface severely disintegrated across a 30-meter stretch following underground utility work. Unpaved gravel exposed.",
            "sev": 6,
            "weights": {"ed": 0.09, "dp": 0.18, "sat": 0.14}
        },
        # Garbage Overflow
        {
            "cat": "garbage_overflow",
            "title": "[DEMO DATA] Overflowing municipal waste bin blocking footpath",
            "desc": "Large black bin completely full; secondary plastic and food waste spilling over 15 feet across the pedestrian walkway, causing heavy foul odor.",
            "sev": 5,
            "weights": {"ed": 0.07, "dp": 0.15, "sat": 0.36}
        },
        {
            "cat": "garbage_overflow",
            "title": "[DEMO DATA] Waste accumulation near residential apartment gate",
            "desc": "Community garbage bin has not been cleared for four days. Stray animals scattering refuse across roadway.",
            "sev": 5,
            "weights": {"ed": 0.06, "dp": 0.12, "sat": 0.34}
        },
        # Illegal Dumping
        {
            "cat": "illegal_dumping",
            "title": "[DEMO DATA] Construction demolition debris dumped on roadside",
            "desc": "Truckloads of concrete rubble, broken brick masonry, and discarded tile scrap dumped overnight on the service road.",
            "sev": 7,
            "weights": {"ed": 0.10, "dp": 0.22, "sat": 0.22}
        },
        # Water Leakage
        {
            "cat": "water_leakage",
            "title": "[DEMO DATA] Major potable water pipeline rupture",
            "desc": "High pressure drinking water pipe burst under tarmac. Potable water continuously gushing and flooding the street for over 18 hours.",
            "sev": 9,
            "weights": {"ed": 0.08, "dp": 0.26, "sat": 0.18}
        },
        {
            "cat": "water_leakage",
            "title": "[DEMO DATA] Continuous pipeline valve leak near water tank",
            "desc": "Municipal distribution valve is leaking steadily, creating an extensive muddy puddle near the market entrance.",
            "sev": 5,
            "weights": {"ed": 0.05, "dp": 0.19, "sat": 0.16}
        },
        # Blocked Drain
        {
            "cat": "blocked_drain",
            "title": "[DEMO DATA] Severely clogged stormwater drain causing street flood",
            "desc": "Culvert blocked completely with silt and construction waste. Monsoon runoff unable to flow, causing 1-foot waterlogging.",
            "sev": 8,
            "weights": {"ed": 0.09, "dp": 0.30, "sat": 0.19}
        },
        # Broken Streetlight
        {
            "cat": "broken_streetlight",
            "title": "[DEMO DATA] Dark street section with damaged luminaire",
            "desc": "Entire row of three streetlights non-operational for over a week. Zone is pitch dark, creating serious safety concern for night commuters.",
            "sev": 6,
            "weights": {"ed": 0.04, "dp": 0.45, "sat": 0.08}
        },
        {
            "cat": "broken_streetlight",
            "title": "[DEMO DATA] Bent utility pole with exposed electrical wiring",
            "desc": "Streetlight pole hit by vehicle, tilted precariously with hanging wires near pedestrian footpath.",
            "sev": 9,
            "weights": {"ed": 0.12, "dp": 0.25, "sat": 0.12}
        },
        # Damaged Infrastructure
        {
            "cat": "damaged_infrastructure",
            "title": "[DEMO DATA] Broken pedestrian footpath concrete slabs",
            "desc": "Multiple walking slabs missing or collapsed directly over open drain. Extremely dangerous for elderly and children.",
            "sev": 8,
            "weights": {"ed": 0.13, "dp": 0.32, "sat": 0.11}
        }
    ]

    STATUS_CHOICES = ["Submitted", "Under Review", "Verified", "Assigned", "In Progress", "Resolved", "Resolved", "Resolved"]

    created_reports = []
    now = datetime.now(timezone.utc)

    # 6. Generate 130+ distinct, realistic reports
    total_target = 135
    for i in range(total_target):
        locality = random.choice(LOCALITIES)
        template = random.choice(ISSUE_TEMPLATES)
        cat = cat_map[template["cat"]]
        
        # Slight jitter within ~200-500 meters of locality center
        lat_jitter = random.uniform(-0.0035, 0.0035)
        lng_jitter = random.uniform(-0.0035, 0.0035)
        lat = round(locality["lat"] + lat_jitter, 6)
        lng = round(locality["lng"] + lng_jitter, 6)
        
        # Age between 1 and 30 days
        days_ago = random.randint(0, 30)
        hours_ago = random.randint(0, 23)
        created_time = now - timedelta(days=days_ago, hours=hours_ago)
        
        # Status distribution
        if days_ago > 14:
            # Older reports more likely to be resolved
            status_choice = random.choice(["Resolved", "Resolved", "In Progress", "Assigned"])
        elif days_ago > 5:
            status_choice = random.choice(["Verified", "Assigned", "In Progress", "Resolved"])
        else:
            status_choice = random.choice(["Submitted", "Under Review", "Verified", "Assigned"])

        resolved_time = None
        res_notes = None
        if status_choice == "Resolved":
            resolved_delta_hours = random.randint(12, 72)
            resolved_time = created_time + timedelta(hours=resolved_delta_hours)
            if resolved_time > now:
                resolved_time = now - timedelta(hours=2)
            res_notes = f"Municipal remediation team deployed. Defect verified, repaired, and inspected according to ward civic standards."

        # Compute priority score
        prio_result = PriorityService.calculate_priority(
            severity_score=template["sev"],
            category_safety_weight=cat.safety_weight,
            location_text=f"{locality['name']} {locality['area']}",
            supporting_reports_count=random.choice([1, 1, 1, 2, 3]),
            created_at=created_time
        )

        tracking_num = f"CP-2026-{i + 1:04d}"
        citizen_user = citizen if i % 2 == 0 else citizen2

        report = Report(
            id=str(uuid.uuid4()),
            tracking_number=tracking_num,
            citizen_id=citizen_user.id,
            title=f"{template['title']} ({locality['area']})",
            description=f"{template['desc']} Exact landmark: Near {locality['name']}, {locality['area']}.",
            category_id=cat.id,
            verified_category_id=cat.id if status_choice in ["Verified", "Assigned", "In Progress", "Resolved"] else None,
            latitude=lat,
            longitude=lng,
            address=f"{locality['name']}, Ward 142, Bengaluru",
            area=locality["area"],
            status=status_choice,
            image_url=None,  # Handled via simulated visual features
            resolution_notes=res_notes,
            ai_severity=template["sev"],
            human_severity=template["sev"] if status_choice in ["Verified", "Resolved"] else None,
            priority_score=prio_result["final_score"],
            priority_level=prio_result["priority_level"],
            is_duplicate=False,
            is_synthetic=True,
            location=f"POINT({lng} {lat})",
            created_at=created_time,
            updated_at=created_time + timedelta(hours=4),
            resolved_at=resolved_time
        )
        db.add(report)
        db.flush()

        # AI Prediction Record
        features = {
            "edge_density": template["weights"]["ed"] + round(random.uniform(-0.01, 0.01), 3),
            "dark_pixel_ratio": template["weights"]["dp"] + round(random.uniform(-0.02, 0.02), 3),
            "saturation": template["weights"]["sat"] + round(random.uniform(-0.02, 0.02), 3),
            "contrast": round(random.uniform(0.35, 0.65), 3),
            "perceptual_hash": hashlib.md5(f"{template['cat']}-{i}".encode()).hexdigest()
        }
        
        pred = AIPrediction(
            report_id=report.id,
            predicted_category_id=cat.id,
            confidence=round(random.uniform(0.82, 0.96), 2),
            detected_features=features,
            raw_predictions={cat.code: 0.88, "road_damage": 0.06, "other": 0.06},
            model_name="CivicPulse-Vision-Ensemble-v1",
            model_version="1.2.0",
            inference_time_ms=round(random.uniform(38.0, 52.0), 1),
            processing_status="completed",
            created_at=created_time
        )
        db.add(pred)

        # Priority Record
        comps = prio_result["components"]
        prio_rec = PriorityScore(
            report_id=report.id,
            severity_component=comps["severity"],
            safety_component=comps["safety"],
            location_risk_component=comps["location_risk"],
            community_impact_component=comps["community_impact"],
            age_component=comps["issue_age"],
            final_score=prio_result["final_score"],
            priority_level=prio_result["priority_level"],
            explanation_json={
                "reasons": prio_result["reasons"],
                "weights": prio_result["weights"]
            },
            scoring_version="2.1.0",
            created_at=created_time
        )
        db.add(prio_rec)

        # Department assignment if assigned or in progress
        if status_choice in ["Assigned", "In Progress", "Resolved"]:
            dept = cat.default_department or dept_map["BBMP-RD"]
            staff_list = [s for s in staff_map.values() if s.department_id == dept.id]
            assigned_staff = random.choice(staff_list) if staff_list else None
            
            assignment = Assignment(
                report_id=report.id,
                department_id=dept.id,
                staff_id=assigned_staff.id if assigned_staff else None,
                assigned_by_user_id=admin.id,
                notes=f"Dispatched field repair work order to {dept.name} ward response division.",
                status="completed" if status_choice == "Resolved" else "active",
                created_at=created_time + timedelta(hours=2)
            )
            db.add(assignment)

        # Audit log
        audit = AuditLog(
            report_id=report.id,
            user_id=citizen_user.id,
            action="report_submitted",
            previous_state=None,
            new_state={"status": "Submitted", "priority": prio_result["priority_level"]},
            notes="Report logged by citizen and evaluated by CivicPulse AI pipeline.",
            created_at=created_time
        )
        db.add(audit)
        
        created_reports.append(report)

    db.commit()

    # 7. Create intentional Duplicate Clusters (e.g. 5 duplicate pairs near same location)
    logger.info("Generating intentional duplicate candidate pairings...")
    duplicate_hubs = [
        ("Koramangala", "pothole", 12.9345, 77.6258),
        ("Indiranagar", "garbage_overflow", 12.9785, 77.6409),
        ("Whitefield", "water_leakage", 12.9699, 77.7501),
        ("HSR Layout", "blocked_drain", 12.9122, 77.6447),
        ("CBD / Central", "broken_streetlight", 12.9757, 77.6067)
    ]

    for area_name, cat_code, base_lat, base_lng in duplicate_hubs:
        cat = cat_map[cat_code]
        # Find an existing report in this area & category (or fallback to category)
        anchor_report = db.query(Report).filter(
            Report.area == area_name,
            Report.category_id == cat.id
        ).first() or db.query(Report).filter(Report.category_id == cat.id).first()

        if anchor_report:
            # Create a duplicate citizen report 18 meters away
            dup_report = Report(
                id=str(uuid.uuid4()),
                tracking_number=f"CP-2026-DUP-{random.randint(100, 999)}",
                citizen_id=citizen2.id,
                title=f"[DEMO DATA] Additional citizen report: {anchor_report.title}",
                description=f"Second citizen notice: The {cat.name.lower()} problem at this spot is worsening rapidly. Vehicles are getting stuck.",
                category_id=cat.id,
                latitude=anchor_report.latitude + 0.00015,  # ~16 meters
                longitude=anchor_report.longitude + 0.00010,
                address=anchor_report.address,
                area=anchor_report.area,
                status="Submitted",
                ai_severity=anchor_report.ai_severity,
                priority_score=anchor_report.priority_score,
                priority_level=anchor_report.priority_level,
                is_duplicate=True,
                canonical_report_id=anchor_report.id,
                is_synthetic=True,
                location=f"POINT({anchor_report.longitude + 0.00010} {anchor_report.latitude + 0.00015})",
                created_at=anchor_report.created_at + timedelta(hours=3),
                updated_at=anchor_report.created_at + timedelta(hours=3)
            )
            db.add(dup_report)
            db.flush()

            # Record duplicate candidate link
            dup_link = DuplicateCandidate(
                source_report_id=dup_report.id,
                target_report_id=anchor_report.id,
                distance_meters=18.4,
                category_match=True,
                time_diff_hours=3.0,
                visual_similarity=0.91,
                composite_score=0.91,
                status="suggested",
                notes="High-confidence duplicate: within 18.4m of canonical issue #1042, matching category, submitted 3 hours apart."
            )
            db.add(dup_link)

            # Record duplicate priority score
            if anchor_report.priority_record:
                apr = anchor_report.priority_record
                dup_prio = PriorityScore(
                    report_id=dup_report.id,
                    severity_component=apr.severity_component,
                    safety_component=apr.safety_component,
                    location_risk_component=apr.location_risk_component,
                    community_impact_component=apr.community_impact_component,
                    age_component=apr.age_component,
                    final_score=apr.final_score,
                    priority_level=apr.priority_level,
                    explanation_json=apr.explanation_json,
                    scoring_version=apr.scoring_version,
                    created_at=dup_report.created_at
                )
                db.add(dup_prio)

    db.commit()
    total_final = db.query(Report).count()
    logger.info(f"Successfully seeded database with {total_final} realistic civic reports and duplicate clusters.")
