# CoolFix Services — Business Knowledge (reference)

This is the **human-readable mirror** of the AI's source of truth. The live values the
bot uses live in `app/knowledge.py`. To change what the bot knows (prices, services,
hours, areas, FAQs), edit `app/knowledge.py` and redeploy — the change takes effect
everywhere (AI answers, dashboard, demo). Keep this document in sync as your reference.

> The AI is **only** allowed to answer from this knowledge. It never invents prices,
> services, hours or areas, and it politely declines anything out of scope.

---

## Business
- **Name:** CoolFix Services
- **Tagline:** Air-conditioning, electrical & generator specialists in Lagos
- **Phone / WhatsApp:** +234 801 234 5678
- **Email:** hello@coolfixservices.ng
- **Address:** 12 Adeola Odeku Street, Victoria Island, Lagos
- **Since:** 2016

## Opening hours
| Day | Hours |
|-----|-------|
| Mon–Fri | 8:00 AM – 6:00 PM |
| Saturday | 9:00 AM – 4:00 PM |
| Sunday | Closed (emergency line only) |

## Service areas
Ikoyi, Lekki, Victoria Island (VI), Ikeja, Yaba, Surulere, Ajah, Gbagada, Maryland, Magodo, Ogudu.

---

## Services & pricing
| Service | What's included | Price |
|---|---|---|
| **AC Installation** | Mounting, up to 3m piping, drainage, gas top-up & test. Supply or install your unit. | Labour from ₦25,000 (1–1.5HP); larger units more; unit price varies by brand/size |
| **AC Repair** | Diagnose & fix: not cooling, leaking, ice, noise, tripping, low gas, PCB/remote | Diagnosis ₦5,000 (waived if repaired); gas refill from ₦12,000; capacitor from ₦8,000 |
| **AC Servicing** | Filter/coil clean, drainage clear, gas check, outdoor unit clean, test. Every 3–4 months. | ₦7,500 per split unit; discount for 3+ |
| **Electrical Repairs** | Wiring, sockets, lighting, DBs, changeovers, surge protection, new points | Callout ₦5,000; work quoted after inspection |
| **Generator Servicing & Repair** | Oil/filter/plug change, carburettor clean, fault diagnosis (petrol & diesel) | From ₦10,000 by KVA; repairs quoted; parts extra |

## Booking rules
- Slots: **Morning (9am–12pm), Afternoon (12pm–4pm), Evening (4pm–6pm)**
- Same-day possible with **≥3 hours notice**, subject to availability
- Sundays: **emergency-only**
- Reschedule/cancel free up to **2 hours** before

## Payment
- **Bank transfer or cash**, due on completion
- Large installations may need a **50% deposit** for the unit/parts
- We send a **written quote** before any chargeable work

## Policies
- **Callout/diagnosis:** ₦5,000, waived if you proceed with the repair
- **Warranty:** 30 days on repairs · 6 months on installations · 14 days on servicing
- **Emergencies:** sparks/burning smell/smoke/shock → switch off at the mains, call +234 801 234 5678
- **Punctuality:** arrive within the booked slot; we message on WhatsApp if running late

## Common problems the AI can speak to
- AC not cooling → low gas / dirty coils / capacitor → diagnosis
- AC leaking water → blocked drainage / dirty filter → servicing
- AC icing → low gas / airflow → turn off, book diagnosis
- Generator won't start → fuel / plug / battery / carburettor
- Power keeps tripping → overload / faulty wiring → inspection

## Out of scope (politely declined)
Laptops, phones, TVs, fridges/freezers, washing machines, microwaves, plumbing, cars,
solar, CCTV. The bot offers CoolFix's real services instead.

---

## FAQ bank
The bot answers these directly. Full list (question → answer) is maintained in
`app/knowledge.py` under `FAQS`. Covered topics: opening hours, service areas, pricing for
each service, callout fee, warranty, payment methods, AC brands, same-day availability,
servicing frequency, leaking/not-cooling diagnosis, generator won't start, do you sell ACs,
installation duration, reschedule/cancel, location, weekend work.
