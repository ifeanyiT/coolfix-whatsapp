"""CoolFix Services - the demo business knowledge base.

This is the single source of truth that gets seeded into the database.
The AI is only allowed to answer from this information; it must never
invent prices, services, hours or areas.
"""
from __future__ import annotations

BUSINESS = {
    "id": "coolfix",
    "name": "CoolFix Services",
    "tagline": "Air-conditioning, electrical & generator specialists",
    "tone": "friendly, professional, concise. Warm but not chatty. Nigerian small-business.",
    "phone": "+234 801 234 5678",
    "email": "hello@coolfixservices.ng",
    "opening_hours": {
        "Monday": "8:00 AM - 6:00 PM",
        "Tuesday": "8:00 AM - 6:00 PM",
        "Wednesday": "8:00 AM - 6:00 PM",
        "Thursday": "8:00 AM - 6:00 PM",
        "Friday": "8:00 AM - 6:00 PM",
        "Saturday": "9:00 AM - 4:00 PM",
        "Sunday": "Closed (emergency line only)",
    },
    # Areas we serve. Used to qualify leads by location.
    "service_areas": [
        "Ikoyi", "Lekki", "Victoria Island", "VI", "Ikeja",
        "Yaba", "Surulere", "Ajah", "Gbagada", "Maryland",
    ],
    "booking_rules": {
        "min_notice_hours": 3,
        "slots": ["Morning (9am-12pm)", "Afternoon (12pm-4pm)", "Evening (4pm-6pm)"],
        "note": "Same-day booking needs at least 3 hours notice. Sunday is emergency-only.",
    },
    "policies": [
        {
            "title": "Callout & diagnosis",
            "body": "A callout/diagnosis visit is 5,000 NGN, waived if you proceed with the repair.",
        },
        {
            "title": "Warranty",
            "body": "All repairs carry a 30-day workmanship warranty. Installations carry a 6-month warranty.",
        },
        {
            "title": "Payment",
            "body": "We accept bank transfer and cash. Payment is due on completion of the job.",
        },
        {
            "title": "Emergencies",
            "body": "For sparks, burning smells or electrical shocks, switch off at the mains and call us immediately on +234 801 234 5678.",
        },
    ],
}

# slug -> service definition
SERVICES = [
    {
        "slug": "ac_installation",
        "name": "Air-Conditioner Installation",
        "description": "Supply and/or install split-unit and window ACs, including piping, bracket and testing.",
        "price": "From 25,000 NGN (labour). Unit price depends on brand/size.",
        "keywords": ["install", "installation", "new ac", "buy ac", "fix new", "mount", "set up ac"],
    },
    {
        "slug": "ac_repair",
        "name": "Air-Conditioner Repair",
        "description": "Fault diagnosis and repair: not cooling, water leaks, noise, tripping, gas top-up.",
        "price": "Diagnosis 5,000 NGN. Repairs quoted after diagnosis. Gas refill from 12,000 NGN.",
        "keywords": ["repair", "not cooling", "not working", "leak", "leaking", "noise", "broken",
                     "fault", "faulty", "fix my ac", "tripping", "gas", "blowing hot"],
    },
    {
        "slug": "ac_maintenance",
        "name": "Air-Conditioner Maintenance / Servicing",
        "description": "Full service: filter & coil cleaning, gas check, drainage clearing, performance test.",
        "price": "7,500 NGN per split unit. Discounts for 3+ units.",
        "keywords": ["service", "servicing", "maintenance", "clean", "cleaning", "wash", "tune up", "general check"],
    },
    {
        "slug": "electrical_repair",
        "name": "Electrical Repairs",
        "description": "Wiring faults, sockets, DBs, lighting, changeovers and general electrical work.",
        "price": "Callout 5,000 NGN. Work quoted after inspection.",
        "keywords": ["electrical", "wiring", "socket", "light", "power", "changeover", "electric", "spark", "shock"],
    },
    {
        "slug": "generator_service",
        "name": "Generator Servicing",
        "description": "Oil & filter change, plug check, general servicing and fault diagnosis for home generators.",
        "price": "From 10,000 NGN depending on generator size (KVA).",
        "keywords": ["generator", "gen", "genset", "kva", "servicing gen", "won't start", "not starting"],
    },
]

FAQS = [
    {
        "question": "What time are you open?",
        "answer": "We're open Monday to Friday 8am-6pm, Saturday 9am-4pm. Sundays are emergency-only.",
        "keywords": ["open", "hours", "time", "closing", "when"],
    },
    {
        "question": "Do you service my area?",
        "answer": "We cover Ikoyi, Lekki, VI, Ikeja, Yaba, Surulere, Ajah, Gbagada and Maryland. Tell me your area and I'll confirm.",
        "keywords": ["area", "location", "cover", "come to", "reach", "where"],
    },
    {
        "question": "How much is AC servicing?",
        "answer": "AC servicing is 7,500 NGN per split unit, with a discount for 3 or more units.",
        "keywords": ["servicing cost", "how much service", "price servicing", "cost of service"],
    },
    {
        "question": "Do you offer warranty?",
        "answer": "Yes - 30 days on repairs and 6 months on installations.",
        "keywords": ["warranty", "guarantee", "guaranteed"],
    },
    {
        "question": "How do I pay?",
        "answer": "Bank transfer or cash, due on completion of the job.",
        "keywords": ["pay", "payment", "transfer", "cash", "card"],
    },
]
