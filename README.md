# VERVE — AI-Powered Parametric Income Insurance for Gig Workers

> *"We don't insure events. We insure verified income loss."*

---

## Table of Contents

1. [What is VERVE?](#what-is-verve)
2. [The Problem We're Solving](#the-problem-were-solving)
3. [Persona-Based Scenarios & Workflows](#persona-based-scenarios--workflows)
4. [How the Application Works — End to End](#how-the-application-works--end-to-end)
5. [Weekly Premium Model](#weekly-premium-model)
6. [Parametric Triggers](#parametric-triggers)
7. [Platform Choice — Mobile vs Web](#platform-choice--mobile-vs-web)
8. [AI/ML Integration Plan](#aiml-integration-plan)
9. [Tech Stack](#tech-stack)
10. [Development Plan](#development-plan)
11. [System Architecture](#system-architecture)
12. [Why VERVE is Different](#why-verve-is-different)

---

## What is VERVE?

VERVE is a hyperlocal, AI-powered parametric insurance system built specifically for food delivery partners working on platforms like Swiggy and Zomato. The idea is simple — gig workers earn daily, they have no fixed salary, and when something goes wrong (a storm, heavy traffic, a protest nearby), they lose income with zero safety net.

Traditional insurance doesn't help here. It either doesn't cover these scenarios at all, or it requires the worker to file a manual claim and wait days for a payout. By then, the damage is done.

VERVE solves this by watching the real world in real time — weather, traffic, platform activity, local events — and automatically compensating delivery partners when they actually lose income due to disruptions they couldn't control. No forms. No waiting. No guessing.

**One-line summary:** VERVE converts real-world disruptions into verified financial compensation using AI-driven, hyperlocal, fully automated decision systems.

---

## The Problem We're Solving

Let's be honest about what gig workers face:

- They earn on a per-delivery basis — if they can't deliver, they don't earn
- Environmental conditions (heavy rain, heatwaves, flooding, pollution) directly cut into their ability to work
- Platform order volumes drop during disruptions, so even workers who *want* to work find no orders
- Strikes, local events, and curfews can shut down entire zones without warning
- Current insurance products don't account for any of this — they're designed for salaried employees

The gap isn't just a product gap. It's a systemic failure to recognize how gig work actually functions.

What makes this tricky is that a disruption doesn't *always* mean loss. Sometimes workers adapt — they shift zones, work longer hours, or the disruption passes quickly. So we can't just say "it rained → pay everyone." We need to verify actual income loss before triggering a payout.

That's the core design challenge VERVE is built to solve.

---

## Persona-Based(Food Delivery) Scenarios & Workflows


### Persona 1 — Ravi, a Full-Time Delivery Partner in Bengaluru

Ravi has been delivering for Zomato for 2 years. He works 8–10 hours a day and earns around ₹800–1000 on a good day. He typically covers Koramangala and Indiranagar.

**Scenario: Heavy rain on a Tuesday afternoon**

1. At 2 PM, Bengaluru receives heavy rainfall. IMD data shows 45mm/hr in Ravi's zone.
2. VERVE's Event Intelligence Agent detects the rainfall signal from the weather API.
3. The Risk Engine flags Ravi's H3 zone (hexagonal geospatial cell covering his area) as high-risk.
4. The Digital Twin model checks what Ravi *typically* earns on a Tuesday between 2–6 PM based on his 60-day history — let's say ₹320.
5. Ravi's actual earnings logged by the platform during this window: ₹85 (2 orders instead of usual 9).
6. The Impact Agent confirms a real, significant drop in income.
7. Fraud Detection Agent validates that Ravi was actually in the zone, moving, and not faking inactivity.
8. Decision Engine approves payout: ₹235 (difference between expected and actual).
9. Ravi gets a notification: *"We noticed reduced orders in your area due to heavy rain. ₹235 has been added to your wallet."*
10. Payout hits within minutes. Ravi didn't do anything — it just happened.

---

### Persona 2 — Priya, a Part-Time Delivery Partner in Hyderabad

Priya delivers on weekends and a few evenings. She's not a full-time worker, so her earnings pattern is irregular.

**Scenario: City-wide auto/cab strike**

1. A transport union strike is called on a Saturday morning. Social signals and news APIs detect this.
2. VERVE identifies affected zones in Hyderabad where traffic is abnormally low and order volumes have dropped.
3. Priya typically earns ₹400 on Saturday mornings based on her 3-month history.
4. Her actual earnings: ₹0 — she couldn't even get to her pickup zone due to blocked roads.
5. The Digital Twin accounts for her part-time pattern and confirms the baseline.
6. Impact verified. Fraud check passes (her last GPS ping was near the blocked road area).
7. Payout: ₹400 credited automatically.

---

### Persona 3 — Kiran, a Delivery Partner Who Adapts Well

Kiran is experienced and knows his city well. When rain hits, he immediately shifts to a covered zone with higher demand.

**Scenario: Rain in Zone A, Kiran shifts to Zone B**

1. Heavy rain detected in Kiran's usual zone (Zone A).
2. VERVE flags Zone A as disrupted.
3. Kiran's actual earnings for the day: ₹780 — almost normal.
4. Expected income from Digital Twin: ₹800.
5. Drop is less than the materiality threshold (e.g., <15% loss).
6. Impact Agent marks this as a non-qualifying event.
7. **No payout triggered.** This is correct — Kiran didn't actually lose money.

This scenario illustrates why we don't just pay when events happen. We pay when loss is real.

---

## How the Application Works — End to End

Here's the full workflow from disruption detection to payout:

```
External World (Rain / Traffic / Strike / Heat)
        ↓
  APIs (Weather, Traffic, Platform, Social)
        ↓
  Data Ingestion Layer
        ↓
  H3 Geo-Spatial Mapping (City divided into hexagonal cells)
        ↓
  ┌─────────────────────────────────────────────┐
  │           Multi-Agent AI System             │
  │                                             │
  │  1. Event Intelligence Agent                │
  │     → Detects disruptions, scores them      │
  │                                             │
  │  2. Risk Engine Agent                       │
  │     → Computes live zone-level risk         │
  │                                             │
  │  3. Exposure Agent                          │
  │     → Calculates each user's risk exposure  │
  │                                             │
  │  4. Digital Twin Agent                      │
  │     → Predicts what user *should* earn      │
  │                                             │
  │  5. Impact Agent                            │
  │     → Confirms real, meaningful loss        │
  │                                             │
  │  6. Fraud Detection Agent                   │
  │     → Rules out fake inactivity/GPS spoof   │
  │                                             │
  │  7. Decision Agent                          │
  │     → Final approve/reject + payout amount  │
  └─────────────────────────────────────────────┘
        ↓
  Payout Execution (Auto, no claim required)
        ↓
  User Notification (Mobile App)
```

Every step in this pipeline runs without any action from the delivery partner. They don't file a claim. They don't explain anything. The system does the work.

---

## Weekly Premium Model

The insurance premium is calculated and charged on a weekly basis. This makes it affordable and aligned with how gig workers actually think about money — weekly, not annually.

### Why Weekly?

Gig workers don't think in annual premiums. They think in daily/weekly income. A ₹50/week insurance deduction from their wallet feels manageable. A ₹2600/year number feels enormous even if it's the same thing. Weekly pricing also allows us to adjust premiums dynamically based on the risk in their operating zones.

### Premium Formula

```
Expected Loss = Zone Risk × Exposure Score × Income Loss Rate × Weekly Income

Premium = Expected Loss × Uncertainty Buffer + Operating Margin
```

Breaking this down:

**Zone Risk** — A score between 0 and 1 representing how historically prone the delivery partner's operating zones are to disruptions. Computed from historical weather data, traffic incidents, flood records, and seasonal patterns. A zone that floods every monsoon season has a higher base risk than a dry, high-flyover zone.

**Exposure Score** — How much time the delivery partner actually spends in risky zones. Calculated as:

```
Exposure = Σ (time_in_zone × zone_risk)
```

A worker who only operates in low-risk zones pays less than someone working in flood-prone areas.

**Income Loss Rate** — The historical probability that a disruption actually causes them personal income loss. If a worker has historically adapted well during disruptions, their personal loss rate is lower.

**Weekly Income** — The worker's average weekly earnings over the last 4–8 weeks. This ensures the premium is proportional to what they actually stand to lose.

**Uncertainty Buffer** — A multiplier that accounts for model uncertainty. If we're less confident about a zone's risk (e.g., a new zone, recent urban development), we buffer slightly higher.

**Operating Margin** — A fixed percentage to cover operational costs and maintain reserve funds.

### Example Calculation

Ravi's numbers:
- Zone Risk: 0.35 (moderate monsoon exposure)
- Exposure Score: 0.72 (spends most of his time in medium-risk zones)
- Income Loss Rate: 0.18 (historically loses ~18% of income during disruptions)
- Weekly Income: ₹5600
- Uncertainty Buffer: 1.15
- Operating Margin: ₹20

```
Expected Loss = 0.35 × 0.72 × 0.18 × 5600 = ₹253.5
Premium = 253.5 × 1.15 + 20 = ₹311.5 ≈ ₹312/week
```

For ₹312/week, Ravi is protected from income loss caused by external disruptions — a fair deal for someone who earns ₹5600/week with no sick leave or safety net.

### Key Design Choices in Pricing

- Premiums are **personalized** — not one-size-fits-all
- Premiums **adjust weekly** as risk changes (monsoon months cost more)
- New workers start on **zone-average pricing** until we have 4+ weeks of their personal data
- Workers in **lower-risk zones** are incentivized to operate there (lower premium)

---

## Parametric Triggers

A parametric trigger is a pre-defined condition that, when met, initiates the payout evaluation pipeline. Unlike traditional insurance where you prove a loss after the fact, parametric systems pre-define what conditions qualify.

But here's where VERVE goes further — we use **multi-signal parametric triggers**, not single-signal ones. A single weather reading saying "it rained" isn't enough. We need corroborating evidence.

### Primary Triggers

| Trigger Type | Signal Source | Threshold Example |
|---|---|---|
| Heavy Rainfall | Weather API | > 20mm/hr sustained for 30+ mins |
| Extreme Heat | Weather API + Heat Index | > 42°C heat index |
| Severe Air Quality | AQI API | AQI > 300 (Hazardous) |
| Traffic Gridlock | Traffic API | Zone speed < 5 km/h across >70% of roads |
| Flooding | Flood API + Traffic | Road closures + standing water reports |
| Strike / Curfew | Social/Event API | Verified civic disruption signal |

### Secondary Validation (Multi-Signal)

A primary trigger alone doesn't release a payout. It starts the evaluation. Then:

1. **Platform Activity Signal** — Has order volume actually dropped in the affected zone? If rain is detected but orders are fine, no payout.
2. **Worker Location Signal** — Was the worker actually in or near the affected zone during the event?
3. **Crowd Behaviour Signal** — Are multiple workers in the same zone showing similar income drops? (Prevents individual gaming)
4. **Digital Twin Comparison** — Does the worker's actual income fall meaningfully below their predicted baseline?

Only when all signals align does the system approve a payout. This is what makes VERVE accurate and fraud-resistant.

### What Doesn't Trigger a Payout

- A disruption in Zone A when the worker was in Zone B
- A drop in income smaller than the materiality threshold (< 15% of expected)
- Income drop caused by the worker choosing not to work (not external)
- Suspicious GPS patterns or device anomalies flagged by fraud detection

---

## Platform Choice — Mobile vs Web

We are building **a mobile-first application with a supporting web dashboard**.

### Why Mobile for Delivery Partners

Delivery partners live on their phones. Their workflow is entirely mobile — they receive orders, navigate, and communicate on their smartphones. Any product that requires them to open a laptop is a product they won't use.

The mobile app needs to be:
- Lightweight (works on entry-level Android phones)
- Low data consumption (not everyone has unlimited data)
- Available in regional languages (Hindi, Telugu, Kannada, Tamil)
- Capable of running in the background (real-time alerts without the app being open)

The mobile app handles:
- Onboarding and profile setup
- Real-time zone risk alerts ("Heavy rain expected in your area in 30 mins")
- Earnings dashboard and expected income tracker
- Payout notifications and wallet
- Premium deduction history and insurance coverage summary

### Why Web for Admin/Operations

The backend operations — fraud monitoring, risk map visualization, simulation controls, zone management, and model performance — need a proper dashboard. This is built as a web application for the operations and data science teams.

The admin dashboard handles:
- Real-time H3 risk heat map across the city
- Active disruption monitoring
- Fraud alert queue and investigation tools
- Premium calibration controls
- Payout audit logs
- Model performance metrics (false positives, payout accuracy)

### Technical Reasoning

A hybrid approach (mobile app + web dashboard) gives us the best of both:
- Mobile PWA (Progressive Web App) approach allows us to ship fast without a separate native app initially
- React Native for cross-platform mobile coverage (Android priority, iOS secondary)
- The web dashboard uses the same backend APIs, reducing development duplication

---

## AI/ML Integration Plan

AI/ML isn't a layer on top of VERVE — it's the engine running everything. Here's how each model fits in:

### 1. Risk Scoring Model (Zone-Level)

**Type:** Gradient Boosted Trees (XGBoost/LightGBM)

**What it does:** Computes a real-time risk score for each H3 hexagonal zone in the city.

**Inputs:**
- Current weather readings (rainfall, temperature, humidity, AQI)
- Historical disruption frequency for the zone
- Time of day and day of week
- Neighboring zone risk scores (spatial smoothing)
- Seasonal patterns (monsoon month = higher base risk)

**Output:** `zone_risk_score` (0.0 to 1.0)

**Training:** Supervised on historical disruption-to-loss data. Retrained monthly, updated in inference daily.

---

### 2. Digital Twin Model (Per-User Income Prediction)

**Type:** LSTM (Long Short-Term Memory) Neural Network

**What it does:** For each delivery partner, predicts what they *would have earned* on a given day/time period if no disruption had occurred. This is the counterfactual baseline.

**Inputs:**
- Worker's earning history (60-day rolling window)
- Time features: hour, day of week, week of month
- Zone-level historical demand patterns
- Worker's behavioral patterns (typical working hours, usual zones)

**Output:** `expected_income` (in ₹, for the disruption period)

**Why LSTM:** Income patterns have strong temporal dependencies. What someone earned last Tuesday at 3 PM is a strong signal for this Tuesday at 3 PM. LSTMs capture this sequential dependency better than simple regression.

**Cold Start Handling:** For new workers (< 4 weeks of data), we fall back to zone-average income predictions for workers with similar operating profiles (clustering by zone, hours, platform).

---

### 3. Impact Classification Model

**Type:** Gradient Boosted Classifier

**What it does:** Given the gap between expected and actual income, determines if this constitutes a real, meaningful loss worth compensating. This step exists to filter out noise — small random variations that aren't caused by the disruption.

**Inputs:**
- `expected_income` from Digital Twin
- `actual_income` from platform API
- `zone_risk_score` during the period
- Duration of disruption
- Worker's historical income variance (baseline noise)

**Output:** `impact_score` (0.0 to 1.0) + binary `impact_confirmed` flag

**Key Design Choice:** We use a probabilistic impact score rather than a hard threshold. A score of 0.85 means we're 85% confident this is a real disruption-caused loss. The Decision Engine uses this score, not a binary yes/no.

---

### 4. Fraud Detection Model

**Type:** Isolation Forest + Behavioral Pattern Classifier (ensemble)

**What it does:** Detects fake inactivity, GPS spoofing, and coordinated fraud attempts.

**Signals analyzed:**
- GPS trace consistency (is the device moving realistically?)
- Motion sensor data (is the device actually stationary or moving?)
- Network patterns (is the device connecting from expected cell towers?)
- Activity cross-reference (are app interactions consistent with claimed inactivity?)
- Peer comparison (is the worker's behaviour aligned with others in the same zone?)
- Device fingerprint (sudden device changes are flagged)
- Economic validity (is the claimed loss economically plausible given zone activity?)

**Output:** `fraud_probability` (0.0 to 1.0)

**Threshold:** `fraud_probability > 0.6` → flag for manual review. `> 0.85` → automatic rejection.

**Why Isolation Forest:** It's unsupervised, meaning it learns what "normal" behaviour looks like and flags deviations. Since fraud patterns evolve, this is more resilient than a purely supervised approach.

---

### 5. Premium Calculation Model

**Type:** Actuarial regression with ML-augmented risk inputs

**What it does:** Computes the weekly premium for each worker based on their personal risk profile.

**Inputs:**
- Historical loss events for the worker
- Zone risk scores for their operating areas
- Exposure score (time × zone risk)
- Income volatility (workers with more variance get slightly higher premiums)
- Tenure (longer-tenured workers have better calibrated risk estimates)

**Output:** `weekly_premium` (in ₹)

**Recalculation Frequency:** Every Sunday night for the upcoming week.

---

### 6. Event Intelligence Agent

**Type:** Rule-based + ML classifier hybrid

**What it does:** Detects and classifies disruption events from incoming signals.

**Inputs:** Weather API, Traffic API, Social/News API, Platform activity changes

**Output:** `event_type`, `event_severity`, `event_confidence`, `affected_zones`

**How it works:** Rule-based filters catch known patterns (rainfall threshold, traffic speed collapse). The ML classifier handles ambiguous or novel events by learning from historical event labels.

---

### 7. Decision Engine (Final Layer)

**Type:** Weighted scoring model with business rules overlay

**What it does:** Takes outputs from all agents and makes the final payout decision.

**Formula:**
```
decision_score = (
    w1 × event_confidence +
    w2 × impact_score +
    w3 × (1 - fraud_probability) +
    w4 × trust_score
)
```

Where `trust_score` is a long-term metric built from the worker's history of legitimate claims.

**Output:**
```json
{
  "decision": "APPROVE",
  "payout_amount": 235,
  "confidence": 0.91,
  "reasoning": "Heavy rain confirmed, income drop of 73% vs baseline, fraud check passed"
}
```

---

## Tech Stack

### Backend

| Component | Technology | Reason |
|---|---|---|
| API Layer | FastAPI (Python) | Fast, async, great for ML pipelines |
| ML Models | PyTorch + scikit-learn | LSTM for Digital Twin, XGBoost for classifiers |
| Geo-Spatial Engine | H3-py (Uber's H3 library) | Native hexagonal grid support |
| Message Queue | Apache Kafka | Real-time event streaming across agents |
| Database | PostgreSQL + TimescaleDB | Time-series data for earnings and risk scores |
| Cache | Redis | Real-time zone risk score caching |
| Model Serving | FastAPI endpoints + TorchServe | Low-latency inference |

### Frontend (Mobile App)

| Component | Technology | Reason |
|---|---|---|
| Framework | React Native | Cross-platform, single codebase |
| State Management | Redux Toolkit | Predictable state for real-time updates |
| Maps | Mapbox SDK | H3 hex grid visualization support |
| Notifications | Firebase Cloud Messaging | Real-time push alerts |

### Frontend (Admin Dashboard)

| Component | Technology | Reason |
|---|---|---|
| Framework | React.js | Component-based, fast rendering |
| Maps | Deck.gl + H3 | Built-in H3 hexagon layer for risk visualization |
| Charts | Recharts | Earnings trends, payout analytics |

### Infrastructure

| Component | Technology |
|---|---|
| Cloud | AWS (EC2, RDS, S3, Lambda) |
| Containerization | Docker + Kubernetes |
| CI/CD | GitHub Actions |
| Monitoring | Grafana + Prometheus |
| Simulation Layer | Custom Python simulation scripts |

---

## Development Plan

We're building this in four phases. The hackathon covers Phase 1 and Phase 2 foundations.

### Phase 1 — Core System 

Goal: Prove the core logic works end-to-end with simulated data.

- [ ] Set up simulation APIs (Weather, Traffic, Platform, Social)
- [ ] Implement H3 geo-spatial mapping and zone management
- [ ] Build the Risk Scoring model (XGBoost, trained on simulated historical data)
- [ ] Build the Digital Twin model (LSTM, trained on synthetic earnings data)
- [ ] Build the Impact Classification model
- [ ] Wire up the basic Decision Engine
- [ ] Build a simple REST API exposing the pipeline
- [ ] Build a minimal admin dashboard to visualize zones and risk scores

**Milestone:** Full simulated payout run — disruption detected → income loss verified → payout computed, logged

---

### Phase 2 — Fraud Detection + Premium Model 

Goal: Add fraud prevention and dynamic pricing.

- [ ] Implement Fraud Detection (Isolation Forest + behavioral signals)
- [ ] Build the Premium Calculation Model
- [ ] Integrate trust scoring for repeat users
- [ ] Add multi-signal validation to the Event Intelligence Agent
- [ ] Extend admin dashboard with fraud monitoring and payout audit logs

**Milestone:** Full pipeline run including fraud detection, with premium calculated per simulated user

---

### Phase 3 — Mobile App + Real Data Integration 

Goal: Build the user-facing experience and connect to real data sources.

- [ ] Build React Native mobile app (earnings view, alerts, payout history)
- [ ] Integrate real weather and traffic APIs (OpenWeatherMap, TomTom/HERE)
- [ ] Build onboarding and KYC flow for delivery partners
- [ ] Connect premium deduction to wallet system
- [ ] Push notification system for real-time zone alerts

**Milestone:** Working mobile app demo with live weather data triggering simulated payouts

---

### Phase 4 — Scale + Compliance 

Goal: Production readiness.

- [ ] IRDAI regulatory compliance review (insurance product filing)
- [ ] Performance testing at scale (10,000 simulated users, real-time)
- [ ] Model monitoring and drift detection pipelines
- [ ] Premium backtesting against historical disruption data
- [ ] Security audit (especially fraud detection and payout APIs)
- [ ] Pilot rollout with 50–100 real delivery partners in one city

---

## System Architecture

```
┌────────────────────────────────────────────────────────┐
│                    API LAYER                    │
│   Weather API | Traffic API | Platform API | Social    │
└────────────────────┬───────────────────────────────────┘
                     │
              ┌──────▼──────┐
              │  Data Ingest │  (Kafka Streams)
              └──────┬───────┘
                     │
              ┌──────▼──────┐
              │ H3 Geo-Map  │  (Zone Risk Cache — Redis)
              └──────┬───────┘
                     │
    ┌────────────────▼────────────────────────────┐
    │              MULTI-AGENT SYSTEM              │
    │                                             │
    │  ┌──────────┐  ┌──────────┐  ┌──────────┐  │
    │  │  Event   │  │  Risk    │  │ Exposure │  │
    │  │  Agent   │  │  Engine  │  │  Agent   │  │
    │  └────┬─────┘  └────┬─────┘  └────┬─────┘  │
    │       │             │             │         │
    │  ┌────▼─────┐  ┌────▼─────┐  ┌───▼──────┐  │
    │  │ Digital  │  │  Impact  │  │  Fraud   │  │
    │  │  Twin    │  │  Agent   │  │  Detect  │  │
    │  └────┬─────┘  └────┬─────┘  └────┬─────┘  │
    │       └─────────────┼─────────────┘         │
    │                ┌────▼─────┐                 │
    │                │ Decision │                 │
    │                │  Engine  │                 │
    │                └────┬─────┘                 │
    └─────────────────────┼───────────────────────┘
                          │
              ┌───────────▼────────────┐
              │    Payout Execution    │
              └───────────┬────────────┘
                          │
           ┌──────────────┼──────────────┐
           │                             │
    ┌──────▼───────┐           ┌─────────▼──────┐
    │  Mobile App  │           │  Admin Dashboard│
    │ (Delivery    │           │  (Operations + │
    │  Partner)    │           │   Fraud Team)  │
    └──────────────┘           └────────────────┘
```

---

## Why VERVE is Different

A few things that set this apart from anything existing:

**No claim required.** The system watches. It pays. The worker doesn't fill in anything. This is the biggest UX improvement over any existing gig worker protection product.

**Counterfactual income modeling.** We don't just measure actual income. We measure the *gap* between what you should have earned and what you did earn. Without a Digital Twin, you can't fairly compute loss.

**Hyperlocal precision.** H3 hexagonal grids let us operate at ~1 km² resolution. Two workers 800m apart might have completely different risk profiles, and our system handles that. City-wide weather data is useless for this.

**Multi-signal fraud prevention.** We don't rely on GPS alone — which is trivially spoofable. We cross-reference motion sensors, network data, platform activity, peer comparison, and behavioral history. Gaming this system would require coordinating multiple independent data sources simultaneously.

**Adaptive, not static.** Risk scores, premiums, and baselines update continuously. A zone that floods in July isn't treated the same in December. A worker who changes their operating area gets a recalibrated premium the following week.

---

## What's Next

In the longer run, VERVE's infrastructure has natural extensions:

- **Health micro-insurance** — same parametric logic applied to hospitalization affecting earnings
- **Multi-platform support** — expanding beyond Swiggy/Zomato to Dunzo, Porter, Urban Company
- **Savings and credit products** — using the income history and trust scores built by VERVE as a financial profile for gig workers (who are currently invisible to formal credit systems)
- **B2B licensing** — platforms like Swiggy could white-label VERVE as a benefit for their delivery partners

---

*Built with the belief that the people keeping our cities fed deserve a financial safety net that actually understands how they work.*
