# School Timetable Generator (In-Progress)

A web-based application for generating optimized school timetables with intelligent constraint handling.

## Features

 **Smart Scheduling**
- Uniform distribution of subjects across the week
- Prevents subject clustering (max 2 consecutive periods)
- Teacher workload management

 **Flexible Constraints**
- Fixed sessions for multiple classes (Mass Drill, Yoga, Assembly)
- Period placement rules (e.g., "ICT should be in Period 3")
- Teacher consecutive period limits

 **User-Friendly Interface**
- Step-by-step setup wizard
- Visual timetable display
- Demo data for quick testing

## Installation

### Prerequisites
- Python 3.7 or higher
- pip (Python package manager)

### Setup Steps

1. **Create project folder and save files**
   ```bash
   mkdir timetable-generator
   cd timetable-generator
   ```

2. **Save the three Python files:**
   - `app.py` - Flask backend server
   - `solver.py` - Timetable generation logic
   - `index.html` - Frontend interface

3. **Install required Python packages**
   ```bash
   pip install flask flask-cors
   ```

4. **Run the backend server**
   ```bash
   python app.py
   ```
   
   You should see:
   ```
   Server starting on http://127.0.0.1:5000
   ```

5. **Open the frontend**
   - Double-click `index.html` to open it in your browser
   - Or open it using a local server for better performance

## Usage Guide

### Step 1: Setup Classes, Subjects & Teachers

Enter your data as comma-separated values:

**Example:**
- **Classes:** `6th, 7th, 8th, 9th, 10th`
- **Subjects:** `Maths, Science, Social, English, Hindi, MD, ICT`
- **Teachers:** `SNK, HVN, MBL, PET, LAB`

Click "Load Demo Data" to see an example.

### Step 2: Assign Periods & Teachers

For each class-subject combination:
1. Enter the number of periods per week (0-48)
2. Select the teacher who teaches that subject

**Important Rules:**
- Each class has 48 periods per week (6 days × 8 periods)
- If you assign periods, you must select a teacher
- Leave count as 0 to skip that subject for that class

### Step 3: Define Constraints

#### 1. Teacher Workload Limit
Set maximum consecutive periods a teacher can teach (default: 8)

#### 2. Fixed Sessions (Multiple Classes Together)
Use for activities where classes meet together:
- **Example:** Mass Drill on Saturday Period 8 for all classes together
- Select subject, day, period, and check classes

#### 3. Period Placement Rules
Control where subjects can be placed:
- **"SHOULD BE in"** - Forces subject into specific period
  - Example: ICT should be in Period 3
- **"SHOULD NOT be in"** - Blocks subject from specific period
  - Example: Maths should not be in Period 8

### Step 4: Generate Timetable

Click "Generate Timetable" and wait for the algorithm to find a solution.

## Built-in Rules

The system automatically enforces these rules:

1. **Uniform Distribution**
   - 6 periods/week → 1 per day
   - 8 periods/week → mostly 1 per day, with 2 days having 2 consecutive periods

2. **No Triple Periods**
   - Maximum 2 consecutive periods of the same subject

3. **No Conflicts**
   - One class = one subject per period
   - One teacher = one class per period (except fixed sessions)

4. **Consecutive Placement**
   - If a subject appears twice in one day, periods must be consecutive

## Troubleshooting

### "Failed to generate timetable"

**Possible causes:**
- Total periods exceed 48 for a class
- Constraints are too restrictive
- Teacher availability conflicts

**Solutions:**
1. Reduce period counts for some subjects
2. Remove or modify some placement rules
3. Increase max consecutive periods for teachers
4. Check that fixed sessions don't conflict

### "Could not connect to backend"

**Solutions:**
1. Make sure `python app.py` is running
2. Check that port 5000 is not being used by another application
3. Look for error messages in the terminal where you ran `app.py`

### Server shows errors

Check the terminal running `app.py` for detailed error messages. Common issues:
- Missing dependencies: Run `pip install flask flask-cors`
- Port already in use: Stop other apps using port 5000

## Example Demo Data

The "Load Demo Data" button fills in:

**Classes:** 6th, 7th, 8th  
**Subjects:** Maths, Science, Social, Tel, Eng, MD, ICT  
**Teachers:** SNK, HVN, MBL, PET, LAB

**Sample Period Assignment:**
- 6th: Maths(8/SNK), Science(7/HVN), Tel(6/MBL), MD(1/PET), ICT(1/LAB)
- 7th: Maths(8/SNK), MD(1/PET), ICT(1/LAB)

**Sample Constraints:**
1. Fixed: MD on Saturday Period 8 for all classes together
2. Placement: ICT should be in Period 3 for 6th and 7th

## Technical Details

### Algorithm
The solver uses a constraint satisfaction approach with backtracking:
1. Apply fixed sessions first (highest priority)
2. Apply "should be" placement rules
3. Fill remaining slots with intelligent heuristics
4. Retry with randomization if constraints fail

### Performance
- Typical solve time: 1-5 seconds
- Maximum attempts: 100
- Success rate: >95% for reasonable constraints

## License

Free to use for educational purposes.

## Support

For issues or questions:
1. Check the troubleshooting section
2. Review console output in browser (F12)
3. Check terminal output where `app.py` is running

---

**Made for Indian Government Schools** 🏫
