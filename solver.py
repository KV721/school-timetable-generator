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
        
        self.schedule = {cls: {day: [None]*8 for day in range(6)} for cls in self.classes}
        self.teacher_slots = defaultdict(lambda: defaultdict(dict))
        
        self.max_consecutive = self.constraints.get("max_consecutive", 8)
        self.fixed_sessions = self.constraints.get("fixed_sessions", [])
        self.placement_rules = self.constraints.get("placement_rules", [])
    
    def solve(self, max_attempts=500):
        """Solve with progressive relaxation strategy"""
        print(f"\nStarting solver with {len(self.classes)} classes...")
        total = sum(sum(d.values()) for d in self.demand.values())
        print(f"Total periods to schedule: {total}")
        
        best_schedule = None
        best_teacher_slots = None
        best_unfilled = float('inf')
        
        # Try with strict rules first (attempts 0-200)
        for attempt in range(200):
            unfilled = self._attempt_solve(strict_mode=True)
            
            if unfilled == 0:
                print(f"\n✓ PERFECT solution found on attempt {attempt + 1} (strict mode)!")
                return True
            
            if unfilled < best_unfilled:
                best_unfilled = unfilled
                best_schedule = copy.deepcopy(self.schedule)
                best_teacher_slots = copy.deepcopy(self.teacher_slots)
                if attempt % 50 == 0:
                    print(f"  Attempt {attempt + 1}: {unfilled} periods unfilled (strict mode)")
            
            self._reset()
        
        # If strict mode didn't work, try relaxed mode (attempts 201-500)
        print(f"\n  Switching to relaxed mode after {best_unfilled} unfilled...")
        
        for attempt in range(200, max_attempts):
            unfilled = self._attempt_solve(strict_mode=False)
            
            if unfilled == 0:
                print(f"\n✓ Solution found on attempt {attempt + 1} (relaxed mode)!")
                return True
            
            if unfilled < best_unfilled:
                best_unfilled = unfilled
                best_schedule = copy.deepcopy(self.schedule)
                best_teacher_slots = copy.deepcopy(self.teacher_slots)
                if attempt % 50 == 0:
                    print(f"  Attempt {attempt + 1}: {unfilled} periods unfilled (relaxed mode)")
            
            self._reset()
        
        if best_unfilled <= 2:
            print(f"\n⚠ Using best solution: {best_unfilled} periods unfilled")
            self.schedule = best_schedule
            self.teacher_slots = best_teacher_slots
            return True
        
        print(f"\n✗ Best attempt: {best_unfilled} periods unfilled")
        return False
    
    def _reset(self):
        """Reset schedule for new attempt"""
        self.schedule = {cls: {day: [None]*8 for day in range(6)} for cls in self.classes}
        self.teacher_slots = defaultdict(lambda: defaultdict(dict))
    
    def _attempt_solve(self, strict_mode=True):
        """Single solving attempt"""
        remaining = copy.deepcopy(self.demand)
        
        # Phase 1: Fixed sessions
        if not self._place_fixed_sessions(remaining):
            return 9999
        
        # Phase 2: Should be rules
        self._place_should_be_rules(remaining)
        
        # Phase 3: Main scheduling with chosen strategy
        if strict_mode:
            return self._schedule_strict(remaining)
        else:
            return self._schedule_relaxed(remaining)
    
    def _schedule_strict(self, remaining):
        """Strict scheduling: enforce perfect distribution"""
        # Process by priority: subjects with fewer periods first (harder to place)
        tasks = []
        for cls in self.classes:
            for subject, count in remaining[cls].items():
                if count > 0:
                    tasks.append((count, cls, subject))
        
        tasks.sort()  # Sort by count (ascending - harder subjects first)
        
        for _, cls, subject in tasks:
            count = remaining[cls][subject]
            if count <= 0:
                continue
            
            if not self._place_subject_strict(cls, subject, remaining):
                # Failed to place this subject
                return sum(sum(d.values()) for d in remaining.values())
        
        return sum(sum(d.values()) for d in remaining.values())
    
    def _place_subject_strict(self, cls, subject, remaining):
        """Place all periods of a subject following strict distribution"""
        total = self.original_demand[cls][subject]
        count = remaining[cls][subject]
        teacher = self.teachers[cls].get(subject)
        
        if not teacher:
            return False
        
        placements = []
        
        # Strategy based on total periods
        if total <= 6:
            # Must use different days (1 per day)
            days = list(range(6))
            random.shuffle(days)
            
            for day in days:
                if count <= 0:
                    break
                
                slot = self._find_free_slot(cls, teacher, day, subject)
                if slot is not None:
                    placements.append((day, slot))
                    count -= 1
        
        elif total <= 8:
            # First 6: one per day, then 2 more can be consecutive
            days = list(range(6))
            random.shuffle(days)
            
            # Place first one on each day
            for day in days:
                if count <= 0:
                    break
                
                slot = self._find_free_slot(cls, teacher, day, subject)
                if slot is not None:
                    placements.append((day, slot))
                    count -= 1
            
            # Place remaining (should be 1-2) consecutively on days that already have one
            days_with_subject = [d for d, p in placements]
            random.shuffle(days_with_subject)
            
            for day in days_with_subject:
                if count <= 0:
                    break
                
                # Find the existing period on this day
                existing = next((p for d, p in placements if d == day), None)
                if existing is not None:
                    # Try to place adjacent
                    for adj_period in [existing - 1, existing + 1]:
                        if 0 <= adj_period < 8:
                            if self._can_place(cls, teacher, day, adj_period, subject):
                                placements.append((day, adj_period))
                                count -= 1
                                break
        
        else:
            # 9+ periods: distribute as evenly as possible
            base_per_day = total // 6
            extra = total % 6
            
            days = list(range(6))
            random.shuffle(days)
            
            for i, day in enumerate(days):
                target = base_per_day + (1 if i < extra else 0)
                
                placed_today = 0
                for _ in range(target):
                    if count <= 0:
                        break
                    
                    slot = self._find_free_slot(cls, teacher, day, subject)
                    if slot is not None:
                        placements.append((day, slot))
                        count -= 1
                        placed_today += 1
        
        # Apply all placements
        for day, period in placements:
            self.schedule[cls][day][period] = subject
            self.teacher_slots[teacher][day][period] = cls
            remaining[cls][subject] -= 1
        
        return remaining[cls][subject] == 0
    
    def _find_free_slot(self, cls, teacher, day, subject):
        """Find a free slot for subject on given day"""
        periods = list(range(8))
        random.shuffle(periods)
        
        for period in periods:
            if self._can_place(cls, teacher, day, period, subject):
                return period
        
        return None
    
    def _can_place(self, cls, teacher, day, period, subject):
        """Check if subject can be placed at this slot"""
        # Slot occupied
        if self.schedule[cls][day][period] is not None:
            return False
        
        # Teacher busy
        if period in self.teacher_slots[teacher][day]:
            return False
        
        # Teacher consecutive limit
        consecutive = 0
        for p in range(period - 1, -1, -1):
            if p in self.teacher_slots[teacher][day]:
                consecutive += 1
            else:
                break
        if consecutive >= self.max_consecutive:
            return False
        
        # Placement rules
        for rule in self.placement_rules:
            if rule["type"] == "should_not":
                if subject in rule["subjects"] and cls in rule["classes"]:
                    if period == rule["period"]:
                        return False
        
        # Avoid triple consecutive
        if period >= 2:
            if (self.schedule[cls][day][period-1] == subject and 
                self.schedule[cls][day][period-2] == subject):
                return False
        
        return True
    
    def _schedule_relaxed(self, remaining):
        """Relaxed scheduling: allow some distribution flexibility"""
        max_iterations = 3000
        
        for iteration in range(max_iterations):
            # Get remaining tasks
            tasks = []
            for cls in self.classes:
                for subject, count in remaining[cls].items():
                    if count > 0:
                        # Priority: fewer remaining = higher priority
                        priority = 1000 - count * 10
                        # Bonus for subjects with few total periods (harder to place)
                        total = self.original_demand[cls][subject]
                        if total <= 3:
                            priority += 100
                        tasks.append((priority, cls, subject))
            
            if not tasks:
                return 0  # Success!
            
            tasks.sort(reverse=True)
            
            # Try to place top task
            placed = False
            for _, cls, subject in tasks[:10]:  # Try top 10
                if self._try_place_anywhere(cls, subject, remaining):
                    placed = True
                    break
            
            if not placed:
                # Stuck - return unfilled count
                return sum(sum(d.values()) for d in remaining.values())
        
        return sum(sum(d.values()) for d in remaining.values())
    
    def _try_place_anywhere(self, cls, subject, remaining):
        """Try to place subject anywhere valid"""
        teacher = self.teachers[cls].get(subject)
        if not teacher:
            return False
        
        # Try all slots
        candidates = []
        for day in range(6):
            for period in range(8):
                if self._can_place(cls, teacher, day, period, subject):
                    # Score this placement
                    score = self._score_relaxed(cls, subject, day, period)
                    candidates.append((score, day, period))
        
        if not candidates:
            return False
        
        # Pick best
        candidates.sort(reverse=True)
        _, day, period = candidates[0]
        
        self.schedule[cls][day][period] = subject
        self.teacher_slots[teacher][day][period] = cls
        remaining[cls][subject] -= 1
        return True
    
    def _score_relaxed(self, cls, subject, day, period):
        """Score a placement in relaxed mode"""
        score = 100
        
        # Prefer consecutive if already have one today
        periods_today = sum(1 for p in range(8) if self.schedule[cls][day][p] == subject)
        if periods_today == 1:
            existing = next(p for p in range(8) if self.schedule[cls][day][p] == subject)
            if abs(period - existing) == 1:
                score += 50
        
        # Prefer spreading across days
        days_used = sum(1 for d in range(6) if any(self.schedule[cls][d][p] == subject for p in range(8)))
        if periods_today == 0 and days_used < 6:
            score += 30
        
        # Slight penalty for having too many on one day
        if periods_today >= 2:
            score -= 20
        
        return score
    
    def _place_fixed_sessions(self, remaining):
        """Place fixed sessions"""
        for rule in self.fixed_sessions:
            subject = rule["subject"]
            day = rule["day"]
            period = rule["period"]
            classes = rule["classes"]
            
            for cls in classes:
                if self.schedule[cls][day][period] is not None:
                    return False
                if remaining[cls].get(subject, 0) <= 0:
                    return False
            
            teachers_used = set()
            for cls in classes:
                teacher = self.teachers[cls].get(subject)
                if not teacher:
                    return False
                teachers_used.add(teacher)
                
                self.schedule[cls][day][period] = subject
                remaining[cls][subject] -= 1
            
            for teacher in teachers_used:
                self.teacher_slots[teacher][day][period] = "Fixed"
        
        return True
    
    def _place_should_be_rules(self, remaining):
        """Place should be rules"""
        should_be = [r for r in self.placement_rules if r["type"] == "should_be"]
        
        for rule in should_be:
            subjects = rule["subjects"]
            target_period = rule["period"]
            classes = rule["classes"]
            
            for cls in classes:
                available = [s for s in subjects if remaining[cls].get(s, 0) > 0]
                if not available:
                    continue
                
                for day in random.sample(range(6), 6):
                    if self.schedule[cls][day][target_period] is not None:
                        continue
                    
                    for subject in available:
                        teacher = self.teachers[cls].get(subject)
                        if teacher and self._can_place(cls, teacher, day, target_period, subject):
                            self.schedule[cls][day][target_period] = subject
                            self.teacher_slots[teacher][day][target_period] = cls
                            remaining[cls][subject] -= 1
                            break
                    else:
                        continue
                    break
    
    def get_schedule(self):
        return self.schedule