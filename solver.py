import random
import copy
from collections import defaultdict

class TimetableSolver:
    def __init__(self, data):
        self.classes = data["classes"]
        self.teachers = data["teachers"]
        self.demand = data["demand"]
        self.original_demand = copy.deepcopy(data["demand"])
        self.constraints = data.get("constraints", {})
        
        # Initialize empty schedule
        self.schedule = {cls: {day: [None]*8 for day in range(6)} for cls in self.classes}
        
        # Teacher availability tracking: {teacher: {day: {period: class_name}}}
        self.teacher_slots = defaultdict(lambda: defaultdict(dict))
        
        # Extract constraints
        self.max_consecutive = self.constraints.get("max_consecutive", 8)
        self.fixed_sessions = self.constraints.get("fixed_sessions", [])
        self.placement_rules = self.constraints.get("placement_rules", [])
        
        # Statistics
        self.stats = {'attempts': 0, 'best_unfilled': float('inf')}
    
    def solve(self, max_attempts=500):
        """Main solve method with multiple strategies"""
        print(f"\nStarting solver with {len(self.classes)} classes...")
        print(f"Total periods to schedule: {sum(sum(d.values()) for d in self.demand.values())}")
        
        best_schedule = None
        best_teacher_slots = None
        
        for attempt in range(max_attempts):
            self.stats['attempts'] = attempt + 1
            
            # Try to solve
            unfilled = self._attempt_solve()
            
            if unfilled == 0:
                print(f"\n✓ PERFECT solution found on attempt {attempt + 1}!")
                return True
            
            # Track best attempt
            if unfilled < self.stats['best_unfilled']:
                self.stats['best_unfilled'] = unfilled
                best_schedule = copy.deepcopy(self.schedule)
                best_teacher_slots = copy.deepcopy(self.teacher_slots)
                
                if attempt < 10 or attempt % 50 == 0:
                    print(f"  Attempt {attempt + 1}: {unfilled} periods unfilled (best so far)")
            
            # Reset for next attempt
            self.schedule = {cls: {day: [None]*8 for day in range(6)} for cls in self.classes}
            self.teacher_slots = defaultdict(lambda: defaultdict(dict))
        
        # Use best partial solution if reasonably good
        if self.stats['best_unfilled'] <= 5:
            print(f"\n⚠ Using best partial solution: {self.stats['best_unfilled']} periods unfilled")
            self.schedule = best_schedule
            self.teacher_slots = best_teacher_slots
            return True
        
        print(f"\n✗ Could not find solution. Best attempt left {self.stats['best_unfilled']} periods unfilled")
        return False
    
    def _attempt_solve(self):
        """Single solving attempt"""
        remaining = copy.deepcopy(self.demand)
        
        # Phase 1: Fixed sessions (highest priority)
        if not self._place_fixed_sessions(remaining):
            return 9999
        
        # Phase 2: Apply "should be" placement rules
        self._place_should_be_rules(remaining)
        
        # Phase 3: Main scheduling loop
        return self._greedy_schedule(remaining)
    
    def _place_fixed_sessions(self, remaining):
        """Place fixed sessions where multiple classes meet together"""
        for rule in self.fixed_sessions:
            subject = rule["subject"]
            day = rule["day"]
            period = rule["period"]
            classes = rule["classes"]
            
            # Verify all classes can accommodate this
            for cls in classes:
                if self.schedule[cls][day][period] is not None:
                    return False
                if remaining[cls].get(subject, 0) <= 0:
                    return False
            
            # Place for all classes
            teachers_used = set()
            for cls in classes:
                teacher = self.teachers[cls].get(subject)
                if not teacher:
                    return False
                teachers_used.add(teacher)
                
                self.schedule[cls][day][period] = subject
                remaining[cls][subject] -= 1
            
            # Mark teachers as busy (teaching multiple classes)
            for teacher in teachers_used:
                self.teacher_slots[teacher][day][period] = f"Fixed:{','.join(classes)}"
        
        return True
    
    def _place_should_be_rules(self, remaining):
        """Try to place 'should be' rules (not mandatory if impossible)"""
        should_be = [r for r in self.placement_rules if r["type"] == "should_be"]
        
        for rule in should_be:
            subjects = rule["subjects"]
            target_period = rule["period"]
            classes = rule["classes"]
            
            for cls in classes:
                available_subjects = [s for s in subjects if remaining[cls].get(s, 0) > 0]
                if not available_subjects:
                    continue
                
                # Try to place in target period on any day
                for day in random.sample(range(6), 6):
                    if self.schedule[cls][day][target_period] is not None:
                        continue
                    
                    for subject in available_subjects:
                        teacher = self.teachers[cls].get(subject)
                        if not teacher:
                            continue
                        
                        if self._is_teacher_available(teacher, day, target_period):
                            self._assign_period(cls, subject, teacher, day, target_period, remaining)
                            break
                    else:
                        continue
                    break
    
    def _greedy_schedule(self, remaining):
        """Main greedy scheduling algorithm"""
        max_iterations = 2000
        stuck_count = 0
        
        for iteration in range(max_iterations):
            # Build priority list of assignments needed
            tasks = self._build_task_list(remaining)
            
            if not tasks:
                # Success - all periods assigned!
                return 0
            
            # Try to place highest priority task
            placed = False
            for cls, subject, priority in tasks[:20]:  # Try top 20 tasks
                if self._try_place_subject(cls, subject, remaining):
                    placed = True
                    stuck_count = 0
                    break
            
            if not placed:
                stuck_count += 1
                if stuck_count > 50:
                    # Can't make progress - return unfilled count
                    return sum(sum(d.values()) for d in remaining.values())
        
        # Timeout - return unfilled count
        return sum(sum(d.values()) for d in remaining.values())
    
    def _build_task_list(self, remaining):
        """Build prioritized list of (class, subject, priority) tasks"""
        tasks = []
        
        for cls in self.classes:
            for subject, count in remaining[cls].items():
                if count <= 0:
                    continue
                
                # Calculate priority score (higher = more urgent)
                priority = count * 100  # Base priority on remaining count
                
                # Bonus for subjects with few periods (harder to place)
                if count <= 2:
                    priority += 50
                
                # Bonus if teacher is heavily used (schedule early)
                teacher = self.teachers[cls].get(subject)
                if teacher:
                    teacher_load = sum(1 for d in range(6) for p in range(8) 
                                     if teacher in str(self.teacher_slots.get(teacher, {}).get(d, {}).get(p, '')))
                    if teacher_load > 20:
                        priority += 30
                
                tasks.append((cls, subject, priority))
        
        tasks.sort(key=lambda x: x[2], reverse=True)
        return tasks
    
    def _try_place_subject(self, cls, subject, remaining):
        """Try to place a subject somewhere in the schedule"""
        teacher = self.teachers[cls].get(subject)
        if not teacher:
            return False
        
        # Find all valid slots and score them
        candidates = []
        
        for day in range(6):
            for period in range(8):
                if self.schedule[cls][day][period] is not None:
                    continue
                
                score = self._score_placement(cls, subject, teacher, day, period, remaining)
                if score > 0:
                    candidates.append((score, day, period))
        
        if not candidates:
            return False
        
        # Choose best slot (with some randomness for diversity)
        candidates.sort(reverse=True)
        
        # Pick from top candidates with weighted randomness
        if len(candidates) > 5:
            choice_idx = random.choices(range(min(5, len(candidates))), 
                                       weights=[5, 3, 2, 1, 1][:min(5, len(candidates))])[0]
        else:
            choice_idx = 0
        
        _, day, period = candidates[choice_idx]
        self._assign_period(cls, subject, teacher, day, period, remaining)
        return True
    
    def _score_placement(self, cls, subject, teacher, day, period, remaining):
        """Score a potential placement (0 = invalid, higher = better)"""
        score = 100
        
        # HARD CONSTRAINTS (return 0 if violated)
        
        # 1. Teacher must be available
        if not self._is_teacher_available(teacher, day, period):
            return 0
        
        # 2. Check "should not" placement rules
        for rule in self.placement_rules:
            if rule["type"] == "should_not":
                if subject in rule["subjects"] and cls in rule["classes"]:
                    if period == rule["period"]:
                        return 0
        
        # 3. Teacher consecutive limit
        if not self._check_consecutive_limit(teacher, day, period):
            return 0
        
        # SOFT CONSTRAINTS (adjust score)
        
        # 4. Distribution across days
        total_periods = self.original_demand[cls].get(subject, 0)
        current_day_count = sum(1 for p in range(8) if self.schedule[cls][day][p] == subject)
        
        if total_periods <= 6:
            # Prefer max 1 per day for subjects with ≤6 periods
            if current_day_count >= 1:
                score -= 30
            if current_day_count >= 2:
                score -= 100
        elif total_periods <= 8:
            # For 7-8 periods, allow 2 per day but prefer spreading
            if current_day_count >= 2:
                score -= 40
        else:
            # For 9+ periods, be more flexible
            if current_day_count >= 3:
                score -= 50
        
        # 5. Continuity bonus
        prev_same = (period > 0 and self.schedule[cls][day][period - 1] == subject)
        next_same = (period < 7 and self.schedule[cls][day][period + 1] == subject)
        
        if prev_same or next_same:
            score += 40  # Encourage consecutive periods
        
        # 6. Avoid triple periods
        if period >= 2 and self.schedule[cls][day][period-1] == subject and self.schedule[cls][day][period-2] == subject:
            score -= 200  # Heavy penalty for 3 in a row
        
        # 7. Balance across week
        days_with_subject = sum(1 for d in range(6) 
                               if any(self.schedule[cls][d][p] == subject for p in range(8)))
        
        if days_with_subject < remaining[cls][subject] and current_day_count == 0:
            score += 20  # Bonus for using a new day when needed
        
        return max(0, score)
    
    def _is_teacher_available(self, teacher, day, period):
        """Check if teacher is free at this time"""
        return period not in self.teacher_slots[teacher][day]
    
    def _check_consecutive_limit(self, teacher, day, period):
        """Check if placing here would violate consecutive limit"""
        consecutive = 0
        
        # Count consecutive periods before this one
        for p in range(period - 1, -1, -1):
            if p in self.teacher_slots[teacher][day]:
                consecutive += 1
            else:
                break
        
        return consecutive < self.max_consecutive
    
    def _assign_period(self, cls, subject, teacher, day, period, remaining):
        """Assign a period to the schedule"""
        self.schedule[cls][day][period] = subject
        self.teacher_slots[teacher][day][period] = cls
        remaining[cls][subject] -= 1
    
    def get_schedule(self):
        """Return the generated schedule"""
        return self.schedule