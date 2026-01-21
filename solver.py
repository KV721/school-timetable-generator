import random

class TimetableSolver:
    def __init__(self, classes, teachers, subjects_demand):
        """
        classes: List of class names ['6th', '7th'...]
        teachers: Dict mapping Subject -> Teacher Name
        subjects_demand: Dict mapping Class -> {Subject: Count}
        """
        self.classes = classes
        self.teachers = teachers
        self.demand = subjects_demand
        
        # The Schedule Grid: schedule[class][day][period] = Subject
        self.schedule = {c: {d: [None]*8 for d in range(6)} for c in classes}
        
        # Track teacher availability: teacher_schedule[teacher][day][period] = Class
        self.teacher_grid = {} 

    def solve(self):
        """The main backtracking function."""
        # We process slot by slot: Day 0 Period 0, then Day 0 Period 1...
        for day in range(6): # 6 Days (Mon-Sat)
            for period in range(8): # 8 Periods
                
                # SPECIAL RULE: YOGA (Period 8 is fixed)
                if period == 7: 
                    if not self._assign_yoga(day): return False
                    continue

                for class_name in self.classes:
                    # Try to fill this slot for this class
                    if not self._fill_slot(class_name, day, period):
                        # If we can't fill a slot, we need to backtrack (simplified here)
                        # For a simple version, we might just restart or return False
                        return False 
        return True

    def _fill_slot(self, class_name, day, period):
        """Try to find a valid subject for a specific slot."""
        
        # 1. Get list of subjects still needed for this class
        needed = [sub for sub, count in self.demand[class_name].items() if count > 0]
        
        # HEURISTIC: Uniform Distribution
        # Sort subjects by: "Have I already taught this today?"
        # If I taught Math today, put it at the end of the list.
        daily_subjects = [self.schedule[class_name][day][p] for p in range(period) if self.schedule[class_name][day][p]]
        needed.sort(key=lambda s: 1 if s in daily_subjects else 0)

        for subject in needed:
            # 2. Check Constraints
            teacher = self.teachers[class_name].get(subject) # Get teacher for this subject & class
            
            # Constraint: Social Studies (No Afternoon Nap)
            if subject == "Social" and period == 4: # Period 4 is 5th slot (0-index)
                continue

            # Constraint: Teacher Busy?
            if self._is_teacher_busy(teacher, day, period):
                continue
            
            # 3. Assign
            self.schedule[class_name][day][period] = subject
            self._mark_teacher(teacher, day, period, class_name)
            self.demand[class_name][subject] -= 1 # Decrease demand
            return True
            
        return False # No subject worked!

    def _assign_yoga(self, day):
        """Force assign Yoga to everyone in last period"""
        for c in self.classes:
            self.schedule[c][day][7] = "Yoga"
            # We don't mark the teacher busy because it's a mass class
        return True

    def _is_teacher_busy(self, teacher, day, period):
        # Check if teacher is already booked in our tracking grid
        key = f"{teacher}_{day}_{period}"
        return key in self.teacher_grid

    def _mark_teacher(self, teacher, day, period, class_name):
        key = f"{teacher}_{day}_{period}"
        self.teacher_grid[key] = class_name

# --- Test Data Setup (Based on your Prompt) ---
classes = ["6th", "7th", "8th", "9th", "10th"]

# Simplified Teacher Mapping (Subject -> Teacher)
# In reality, this might differ per class, but for structure:
teacher_map = {
    "6th": {"Maths": "SNK", "Social": "MBL", "Science": "HVN", "Tel": "MNR", "Hin": "MKV", "Eng": "BSJ"},
    "7th": {"Maths": "SNK", "Social": "MBL", "Science": "HVN", "Tel": "MNR", "Hin": "MKV", "Eng": "BSJ"},
    # ... add others
}

# Demand (How many periods per week)
demand_matrix = {
    "6th": {"Maths": 8, "Social": 6, "Science": 7, "Tel": 6, "Hin": 5, "Eng": 6},
    "7th": {"Maths": 8, "Social": 6, "Science": 7, "Tel": 6, "Hin": 5, "Eng": 6},
    # ... add others
}

# Run
solver = TimetableSolver(classes, teacher_map, demand_matrix)
if solver.solve():
    print("Schedule Generated Successfully!")
    print(solver.schedule["6th"]) # Print 6th class schedule to check
else:
    print("Could not generate schedule. Constraints too tight!")