# School Timetable Generator

A web-based timetable generator for Indian government schools, built for the Indian classroom model where students stay in one room and teachers rotate between classes.

## Features

**Smart Scheduling**
- Uniform distribution of subjects across the week (e.g. 6 periods/week → exactly 1 per day)
- When a subject has more periods than days, extra periods are placed consecutively on the same day (e.g. 8 periods/week → 4 days with 1 period + 2 days with 2 consecutive periods)
- No teacher is double-booked across classes in the same period

**Flexible Constraints**
- Fixed sessions: multiple classes share the exact same slot (e.g. Mass Drill, Assembly, Yoga)
- Period placement rules: force or block a subject from a specific period slot
- Teacher consecutive period limits

**User-Friendly Interface**
- Step-by-step setup wizard
- Visual timetable grid showing subject and teacher in each cell
- Demo data and real school data presets for quick testing

## Installation

### Prerequisites
- Python 3.7+
- pip

### Setup

1. **Clone or download the project**

2. **Create a virtual environment (recommended)**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. **Install dependencies**
   ```bash
   pip install flask flask-cors
   ```

4. **Start the backend server**
   ```bash
   python app.py
   ```
   You should see:
   ```
   Server starting on http://127.0.0.1:5000
   ```

5. **Open the frontend**
   - Double-click `index.html`, or open it in your browser directly

## Usage

### Step 1: Setup Classes, Subjects & Teachers

Enter comma-separated values for each field.

**Example:**
- Classes: `6th, 7th, 8th, 9th, 10th`
- Subjects: `Maths, Science, English, Hindi, SS, ICT, Yoga, MD`
- Teachers: `SNK, HVN, MBL, BSJ, BMR`

Use **Load Demo** for a small example, or **Load Real School Data** for a full 5-class dataset.

### Step 2: Assign Periods & Teachers

For each class × subject cell in the matrix:
- Enter the number of periods per week
- Select the teacher for that subject

Each class has 48 slots per week (6 days × 8 periods). Leave count as 0 to skip a subject for a class.

### Step 3: Define Constraints

#### Teacher Workload Limit
Maximum consecutive periods any one teacher can teach in a day.

#### Fixed Sessions (Classes Together)
Use for activities where multiple classes are in the same place at the same time (Mass Drill, Assembly, etc.). All selected classes will share that exact day and period.

#### Period Placement Rules
- **SHOULD BE in Period X** — the subject will be scheduled in that period slot (at least some occurrences)
- **SHOULD NOT be in Period X** — the subject is blocked from that period for the selected classes

### Step 4: Generate

Click **✨ Generate Timetable**. The solver typically finds a perfect solution in under a second.

## Built-in Scheduling Rules

These are enforced automatically — no configuration needed:

| Rule | Behaviour |
|---|---|
| Uniform distribution | Subjects spread across all 6 days as evenly as possible |
| Consecutive pairs | If a subject needs 2 periods on one day, they are placed back-to-back |
| No class conflicts | A class cannot have two subjects in the same period |
| No teacher conflicts | A teacher cannot be in two classes at the same period (except fixed sessions) |

## How the Solver Works

The algorithm runs in five phases per attempt:

1. **Fixed sessions** — lock the user-defined shared slots first
2. **"Should be" preferences** — place preferred-period subjects early
3. **Teacher-first round-robin** — group all assignments by teacher and schedule the most-loaded teachers first; for each teacher, assign slots across all their classes day by day together, preventing any one class from monopolising the teacher's available slots
4. **MRV cleanup** — for any remaining unplaced periods, always place the one with the fewest valid slots remaining (Minimum Remaining Values heuristic), so constrained periods don't get squeezed out by easier ones
5. **Local repair** — for any period that still cannot fit, find a slot where the teacher is free but occupied by another subject, relocate that subject to a different valid slot, and place the stuck period in the freed slot

**Performance on a 5-class, 10-teacher, 240-period dataset:** perfect solution on the first attempt, under 1 second, 10/10 runs.

## Troubleshooting

### "Failed to generate timetable"
- Total periods for a class exceed 48 — reduce some counts
- A teacher's total load exceeds 48 — check workload summary in the terminal
- Fixed session conflicts — ensure no two fixed sessions overlap for the same class or teacher

### "Could not connect to backend"
- Make sure `python app.py` is running before clicking Generate
- Check that port 5000 is free: `lsof -i :5000`

### Server errors
Check the terminal running `app.py` for the full traceback.

## Project Structure

```
school-timetable-generator/
├── index.html   # Frontend (single-page, no build step)
├── app.py       # Flask API server
└── solver.py    # Constraint solver
```

## License

Free to use for educational purposes.

---

Built for Indian government schools where students stay in one classroom and teachers rotate.
