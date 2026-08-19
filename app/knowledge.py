"""CoolFix Services - the complete business knowledge base (source of truth).

This is what the AI is allowed to know and answer from. It is seeded/synced into
the database on startup, and mirrored in the human-editable KNOWLEDGE.md template.
The AI must NEVER invent anything outside this file.

To update your business info: edit this file (or KNOWLEDGE.md) and redeploy.
"""
from __future__ import annotations

BUSINESS = {
    "id": "coolfix",
    "name": "CoolFix Services",
    "tagline": "Air-conditioning, electrical & generator specialists in Lagos",
    "tone": "friendly, professional, concise. Warm but not chatty. Nigerian small business. "
            "Use plain English, a little pidgin is fine if the customer uses it. Never pushy.",
    "phone": "+234 801 234 5678",
    "whatsapp": "+234 801 234 5678",
    "email": "hello@coolfixservices.ng",
    "address": "12 Adeola Odeku Street, Victoria Island, Lagos",
    "established": "2016",
    "opening_hours": {
        "Monday": "8:00 AM - 6:00 PM",
        "Tuesday": "8:00 AM - 6:00 PM",
        "Wednesday": "8:00 AM - 6:00 PM",
        "Thursday": "8:00 AM - 6:00 PM",
        "Friday": "8:00 AM - 6:00 PM",
        "Saturday": "9:00 AM - 4:00 PM",
        "Sunday": "Closed (emergency line only)",
    },
    "service_areas": [
        "Ikoyi", "Lekki", "Victoria Island", "VI", "Ikeja", "Yaba",
        "Surulere", "Ajah", "Gbagada", "Maryland", "Magodo", "Ogudu",
    ],
    "areas_not_covered_note": "Outside these areas we may still help for larger jobs - "
                              "we'll confirm case by case or arrange a callout fee.",
    "booking_rules": {
        "min_notice_hours": 3,
        "slots": ["Morning (9am-12pm)", "Afternoon (12pm-4pm)", "Evening (4pm-6pm)"],
        "same_day": "Same-day booking is possible with at least 3 hours notice, subject to availability.",
        "sunday": "Sundays are emergency-only (sparks, burning smell, total power loss).",
        "reschedule": "You can reschedule or cancel free up to 2 hours before the visit.",
    },
    "payment": {
        "methods": ["Bank transfer", "Cash"],
        "when": "Payment is due on completion of the job.",
        "deposit": "Large installations may require a 50% deposit for parts/units.",
        "invoice": "We send a written quote before starting any chargeable work.",
    },
    "policies": [
        {"title": "Callout & diagnosis fee",
         "body": "A callout/diagnosis visit is 5,000 NGN. It is waived if you proceed with the repair on the same visit."},
        {"title": "Warranty",
         "body": "Repairs carry a 30-day workmanship warranty. New installations carry a 6-month warranty. Serviced units are guaranteed for 14 days."},
        {"title": "Payment terms",
         "body": "Bank transfer or cash, due on completion. Installations may need a 50% deposit for the unit/parts."},
        {"title": "Emergencies",
         "body": "For sparks, burning smells, smoke or electric shocks: switch off at the mains immediately and call +234 801 234 5678. Do not touch the unit."},
        {"title": "Punctuality",
         "body": "Technicians arrive within the booked time slot. If we are running late we message you on WhatsApp."},
        {"title": "Cancellation",
         "body": "Reschedule or cancel free up to 2 hours before the appointment."},
    ],
}

# slug -> full service definition
SERVICES = [
    {
        "slug": "ac_installation",
        "name": "Air-Conditioner Installation",
        "short": "Supply and/or install split-unit and window ACs.",
        "description": "We install split-unit and window air-conditioners: mounting the indoor and "
                       "outdoor units, copper piping, drainage, bracket, electrical connection, gas "
                       "check and a full test. We can supply the unit or install one you already bought.",
        "price": "Installation labour from 25,000 NGN (1-1.5HP). Larger units cost more. "
                 "Unit price depends on brand/size if you want us to supply it.",
        "duration": "2-4 hours per unit.",
        "includes": ["Wall bracket & mounting", "Up to 3m copper piping", "Drainage", "Gas top-up & test"],
        "notes": "Extra piping beyond 3m is charged per metre. We install LG, Samsung, Midea, Hisense, Panasonic, Gree and more.",
        "keywords": ["install", "installation", "new ac", "buy ac", "fix new ac", "mount", "set up ac",
                     "fit ac", "supply and install", "new air conditioner"],
    },
    {
        "slug": "ac_repair",
        "name": "Air-Conditioner Repair",
        "short": "Diagnose and fix AC faults.",
        "description": "We diagnose and repair AC faults: not cooling, blowing warm air, water leaking, "
                       "ice on the pipes, strange noise, bad smell, tripping the breaker, remote/PCB "
                       "issues and low gas. Diagnosis first, then a quote before any repair.",
        "price": "Diagnosis 5,000 NGN (waived if you proceed). Common repairs: gas refill from 12,000 NGN, "
                 "capacitor from 8,000 NGN, PCB/board repairs quoted after diagnosis.",
        "duration": "1-3 hours depending on the fault.",
        "common_problems": {
            "not cooling / blowing warm air": "Usually low gas, dirty coils or a faulty compressor/capacitor. Needs diagnosis.",
            "water leaking indoors": "Usually a blocked drainage pipe or dirty filter - a service/clean often fixes it.",
            "ice / frost on pipes": "Often low gas or restricted airflow. Turn it off and book a diagnosis.",
            "tripping the breaker": "Possible electrical fault or compressor issue - stop using it and book us.",
            "noisy / vibrating": "Loose fan, debris, or worn bearing.",
            "bad smell": "Mould in the unit - a deep service usually clears it.",
        },
        "keywords": ["repair", "not cooling", "not working", "leak", "leaking", "noise", "noisy",
                     "broken", "fault", "faulty", "fix my ac", "tripping", "gas", "blowing hot",
                     "blowing warm", "ice", "frost", "smell", "remote not working", "not blowing"],
    },
    {
        "slug": "ac_maintenance",
        "name": "Air-Conditioner Maintenance / Servicing",
        "short": "Full service to keep an AC running efficiently.",
        "description": "A full service: wash and clean the filters and coils, clear the drainage, check "
                       "and top up gas if needed, clean the outdoor unit, and a performance test. Keeps "
                       "the AC cooling well and cuts electricity use. Recommended every 3-4 months.",
        "price": "7,500 NGN per split unit. Discounts for 3+ units (call for a quote). Gas top-up if needed is extra.",
        "duration": "45-60 minutes per unit.",
        "includes": ["Filter & coil cleaning", "Drainage clearing", "Gas level check", "Outdoor unit clean", "Performance test"],
        "notes": "Regular servicing every 3-4 months keeps warranties valid and prevents leaks/breakdowns.",
        "keywords": ["service", "servicing", "maintenance", "clean", "cleaning", "wash", "tune up",
                     "general check", "servicing cost", "maintain", "deep clean"],
    },
    {
        "slug": "electrical_repair",
        "name": "Electrical Repairs & Installation",
        "short": "Home electrical faults, wiring, sockets, DBs, changeovers.",
        "description": "General home electrical work: wiring faults, tripping, dead sockets, lighting, "
                       "distribution boards (DB), changeover switches, surge protection and new points. "
                       "Safety-first diagnosis, then a clear quote.",
        "price": "Callout/inspection 5,000 NGN. Work quoted after inspection.",
        "duration": "Varies by job.",
        "common_problems": {
            "power keeps tripping": "Overload or a faulty appliance/wiring - needs inspection.",
            "sockets not working": "Loose wiring or a tripped circuit.",
            "changeover / inverter": "We install and repair manual and automatic changeovers.",
        },
        "keywords": ["electrical", "wiring", "socket", "light", "lights", "power", "changeover",
                     "electric", "spark", "shock", "db", "distribution board", "breaker", "surge",
                     "no power", "point"],
    },
    {
        "slug": "generator_service",
        "name": "Generator Servicing & Repair",
        "short": "Service and repair home/office generators.",
        "description": "Generator servicing and repair: oil and filter change, spark plug check, air "
                       "filter, carburettor cleaning, fault diagnosis (won't start, cuts off, smoking), "
                       "and general servicing for petrol and diesel home/office generators.",
        "price": "Servicing from 10,000 NGN depending on generator size (KVA). Repairs quoted after diagnosis. Parts extra.",
        "duration": "1-2 hours.",
        "common_problems": {
            "won't start": "Could be fuel, plug, battery or carburettor - needs a look.",
            "starts then cuts off": "Often fuel/carburettor or a choke issue.",
            "smoking": "Oil or fuel mix problem - stop using it and book us.",
        },
        "keywords": ["generator", "gen", "genset", "kva", "servicing gen", "won't start", "wont start",
                     "not starting", "generator repair", "gen service", "smoking", "cuts off"],
    },
]

# The FAQ bank - covers what customers actually ask.
FAQS = [
    {"question": "What time are you open?",
     "answer": "We're open Monday to Friday 8am-6pm, and Saturday 9am-4pm. Sundays are emergency-only.",
     "keywords": ["open", "hours", "time", "closing", "when", "close", "opening"]},
    {"question": "Do you service my area?",
     "answer": "We cover Ikoyi, Lekki, VI, Ikeja, Yaba, Surulere, Ajah, Gbagada, Maryland, Magodo and Ogudu. "
               "Tell me your area and I'll confirm.",
     "keywords": ["area", "areas", "my area", "location", "cover", "come to", "reach", "do you serve"]},
    {"question": "How much is AC servicing?",
     "answer": "AC servicing is 7,500 NGN per split unit, with a discount for 3 or more units.",
     "keywords": ["servicing cost", "how much service", "price servicing", "cost of service", "service price"]},
    {"question": "How much is AC repair?",
     "answer": "Diagnosis is 5,000 NGN (waived if you go ahead with the repair). The repair itself is quoted "
               "after we find the fault - e.g. a gas refill starts from 12,000 NGN.",
     "keywords": ["repair cost", "how much repair", "fix cost", "price repair", "cost to fix"]},
    {"question": "How much to install an AC?",
     "answer": "Installation labour starts from 25,000 NGN for a 1-1.5HP unit; bigger units cost more. "
               "If you want us to supply the unit too, the price depends on brand and size.",
     "keywords": ["install cost", "installation cost", "how much install", "price install", "fix new"]},
    {"question": "How much is generator servicing?",
     "answer": "Generator servicing starts from 10,000 NGN depending on the size (KVA). Repairs are quoted after diagnosis.",
     "keywords": ["generator cost", "gen service cost", "kva", "generator price"]},
    {"question": "Is there a callout fee?",
     "answer": "Yes - a callout/diagnosis visit is 5,000 NGN, and it's waived if you proceed with the repair on the same visit.",
     "keywords": ["callout", "call out", "inspection fee", "come and check", "assessment", "diagnosis fee"]},
    {"question": "Do you offer a warranty?",
     "answer": "Yes - 30 days on repairs, 6 months on new installations, and 14 days on servicing.",
     "keywords": ["warranty", "guarantee", "guaranteed", "warranties"]},
    {"question": "How do I pay?",
     "answer": "Bank transfer or cash, due on completion of the job. Large installations may need a 50% deposit for the unit/parts.",
     "keywords": ["pay", "payment", "transfer", "cash", "card", "deposit", "how to pay"]},
    {"question": "Which AC brands do you work on?",
     "answer": "All major brands - LG, Samsung, Midea, Hisense, Panasonic, Gree and more, split or window units.",
     "keywords": ["brand", "brands", "lg", "samsung", "midea", "hisense", "which ac", "type of ac"]},
    {"question": "Can you come today / same day?",
     "answer": "Often yes - same-day is possible with at least 3 hours notice, subject to availability. Tell me your area and preferred time.",
     "keywords": ["today", "same day", "now", "urgent", "asap", "come now", "immediately"]},
    {"question": "How often should I service my AC?",
     "answer": "Every 3-4 months keeps it cooling well, lowers your electricity bill and prevents leaks and breakdowns.",
     "keywords": ["how often", "frequency", "how many times", "regular service"]},
    {"question": "My AC is leaking water - what's wrong?",
     "answer": "Usually a blocked drainage pipe or a dirty filter. A servicing/clean normally fixes it - want me to book one?",
     "keywords": ["leaking water", "water dripping", "dripping", "leak water", "water coming"]},
    {"question": "My AC is not cooling - what's wrong?",
     "answer": "Common causes are low gas, dirty coils or a faulty capacitor/compressor. It needs a quick diagnosis - shall I book a technician?",
     "keywords": ["not cooling", "no cold", "blowing warm", "blowing hot", "not cold", "not blowing cold"]},
    {"question": "My generator won't start - can you help?",
     "answer": "Yes. It's often fuel, spark plug, battery or the carburettor. We diagnose and repair on-site - want me to arrange a visit?",
     "keywords": ["generator won't start", "gen not starting", "generator not starting", "gen won't"]},
    {"question": "Do you sell air conditioners?",
     "answer": "Yes - we can supply and install a new AC. Tell me the room size or HP you need and I'll help you choose.",
     "keywords": ["sell", "buy", "purchase", "supply", "sell ac", "buy ac", "do you sell"]},
    {"question": "How long does an installation take?",
     "answer": "Usually 2-4 hours per unit, including piping, mounting and testing.",
     "keywords": ["how long install", "installation time", "duration install", "take to install"]},
    {"question": "Can I reschedule or cancel?",
     "answer": "Of course - you can reschedule or cancel free up to 2 hours before the appointment.",
     "keywords": ["reschedule", "cancel", "change time", "change appointment", "postpone"]},
    {"question": "Where are you located?",
     "answer": "Our office is at 12 Adeola Odeku Street, Victoria Island, Lagos - but we come to you across Lagos.",
     "keywords": ["located", "office", "address", "where are you", "your location"]},
    {"question": "Do you work on weekends?",
     "answer": "Saturdays 9am-4pm, yes. Sundays are emergency-only (sparks, burning smell, total power loss).",
     "keywords": ["weekend", "saturday", "sunday", "weekends"]},
]

# Topics the business does NOT handle - so the AI politely declines instead of guessing.
OUT_OF_SCOPE = {
    "note": "CoolFix only handles air-conditioning, home electrical work, and generators. "
            "We do NOT repair laptops, phones, TVs, fridges, washing machines, microwaves, "
            "plumbing, or cars. If asked, politely say it's outside what we do and offer our actual services.",
    "examples": ["laptop", "computer", "phone", "tv", "television", "fridge", "refrigerator",
                 "freezer", "washing machine", "microwave", "plumbing", "car", "inverter battery only",
                 "solar", "cctv"],
}
