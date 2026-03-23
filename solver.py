import random
import copy
from collections import defaultdict


class TimetableSolver:
    DAYS = 6
    PERIODS = 8

    def __init__(self, data):
        self.classes = data["classes"]
        self.teachers = data["teachers"]
        self.demand = data["demand"]
        self.original_demand = copy.deepcopy(data["demand"])
        self.constraints = data.get("constraints", {})

        self.max_consecutive = self.constraints.get("max_consecutive", 8)
        self.fixed_sessions = self.constraints.get("fixed_sessions", [])
        self.placement_rules = self.constraints.get("placement_rules", [])

        self.schedule = None
        self.teacher_slots = None
        self._reset()

    # ------------------------------------------------------------------ #
    # Infra                                                                #
    # ------------------------------------------------------------------ #

    def _reset(self):
        self.schedule = {
            cls: [[None] * self.PERIODS for _ in range(self.DAYS)]
            for cls in self.classes
        }
        self.teacher_slots = defaultdict(
            lambda: [[None] * self.PERIODS for _ in range(self.DAYS)]
        )

    def _place(self, cls, subject, teacher, day, period):
        self.schedule[cls][day][period] = subject
        self.teacher_slots[teacher][day][period] = cls

    # ------------------------------------------------------------------ #
    # Main solve loop                                                      #
    # ------------------------------------------------------------------ #

    def solve(self, max_attempts=300):
        print(f"\nStarting solver with {len(self.classes)} classes...")
        total = sum(sum(d.values()) for d in self.demand.values())
        print(f"Total periods to schedule: {total}")

        best_schedule = None
        best_teacher_slots = None
        best_unfilled = float("inf")

        for attempt in range(max_attempts):
            self._reset()
            unfilled = self._attempt_solve()

            if unfilled == 0:
                print(f"\n✓ Perfect solution found on attempt {attempt + 1}!")
                return True

            if unfilled < best_unfilled:
                best_unfilled = unfilled
                best_schedule = copy.deepcopy(self.schedule)
                best_teacher_slots = {
                    t: copy.deepcopy(slots)
                    for t, slots in self.teacher_slots.items()
                }
                if attempt % 20 == 0 or attempt < 5:
                    print(f"  Attempt {attempt + 1}: {unfilled} periods unfilled")

        if best_unfilled <= 2:
            print(f"\n⚠ Using best solution: {best_unfilled} periods unfilled")
            self.schedule = best_schedule
            self.teacher_slots = defaultdict(
                lambda: [[None] * self.PERIODS for _ in range(self.DAYS)]
            )
            for t, slots in best_teacher_slots.items():
                self.teacher_slots[t] = slots
            return True

        print(f"\n✗ Best attempt: {best_unfilled} periods unfilled")
        return False

    def _attempt_solve(self):
        remaining = copy.deepcopy(self.demand)

        # Phase 1: Fixed sessions (multiple classes at the same slot)
        if not self._place_fixed_sessions(remaining):
            return 9999

        # Phase 2: "Should be in period X" soft preferences
        self._place_should_be_rules(remaining)

        # Phase 3: Teacher-first round-robin scheduling
        #   Group all (cls, subject) by teacher. Process the most-loaded
        #   teachers first. For each teacher schedule all their classes
        #   together, day by day, so their slots are coordinated and never
        #   conflict with each other.
        self._schedule_by_teacher(remaining)

        # Phase 4: MRV (Minimum Remaining Values) cleanup
        #   For anything still unplaced, always place the period that has
        #   the fewest valid slots remaining — prevents getting squeezed out.
        unfilled = sum(sum(d.values()) for d in remaining.values())
        if unfilled > 0:
            self._mrv_cleanup(remaining)

        # Phase 5: Local repair
        #   For stubborn periods that still can't fit, try evicting an
        #   already-placed subject to a different slot, then drop ours in.
        unfilled = sum(sum(d.values()) for d in remaining.values())
        if 0 < unfilled <= 6:
            self._local_repair(remaining)

        return sum(sum(d.values()) for d in remaining.values())

    # ------------------------------------------------------------------ #
    # Distribution helper                                                  #
    # ------------------------------------------------------------------ #

    def _day_distribution(self, total):
        """
        Return a shuffled list of DAYS values summing to *total*,
        spread as evenly as possible.
          total=6 → [1,1,1,1,1,1]
          total=8 → [2,2,1,1,1,1]  (shuffled)
          total=5 → [1,1,1,1,1,0]  (shuffled)
        """
        base = total // self.DAYS
        extra = total % self.DAYS
        dist = [base + (1 if i < extra else 0) for i in range(self.DAYS)]
        random.shuffle(dist)
        return dist

    # ------------------------------------------------------------------ #
    # Slot validation helpers                                              #
    # ------------------------------------------------------------------ #

    def _can_place(self, cls, teacher, day, period, subject):
        if self.schedule[cls][day][period] is not None:
            return False
        if self.teacher_slots[teacher][day][period] is not None:
            return False
        if not self._ok_consecutive(teacher, day, period):
            return False
        for rule in self.placement_rules:
            if rule["type"] == "should_not":
                if subject in rule["subjects"] and cls in rule["classes"]:
                    if period == rule["period"]:
                        return False
        return True

    def _ok_consecutive(self, teacher, day, period):
        """Bidirectional consecutive-periods check."""
        if self.max_consecutive >= self.PERIODS:
            return True
        run = 1
        for p in range(period - 1, -1, -1):
            if self.teacher_slots[teacher][day][p] is not None:
                run += 1
            else:
                break
        for p in range(period + 1, self.PERIODS):
            if self.teacher_slots[teacher][day][p] is not None:
                run += 1
            else:
                break
        return run <= self.max_consecutive

    def _find_slot(self, cls, teacher, day, subject):
        periods = list(range(self.PERIODS))
        random.shuffle(periods)
        for p in periods:
            if self._can_place(cls, teacher, day, p, subject):
                return p
        return None

    def _find_consecutive_block(self, cls, teacher, day, count, subject):
        """Find *count* adjacent valid slots on *day*, or return None."""
        starts = list(range(self.PERIODS - count + 1))
        random.shuffle(starts)
        for start in starts:
            block = list(range(start, start + count))
            if all(self._can_place(cls, teacher, day, p, subject) for p in block):
                return block
        return None

    def _score_placement(self, cls, subject, day, period):
        """
        Higher score = better placement.
        Rewards spreading to new days; penalises piling up on one day.
        """
        score = 100
        periods_today = sum(
            1 for p in range(self.PERIODS)
            if self.schedule[cls][day][p] == subject
        )
        if periods_today == 0:
            score += 25   # spreading bonus
        else:
            score -= periods_today * 35   # pile-up penalty
        score -= period   # slight preference for earlier in the day
        return score

    # ------------------------------------------------------------------ #
    # Phase 3 – Teacher-first round-robin scheduling                      #
    # ------------------------------------------------------------------ #

    def _schedule_by_teacher(self, remaining):
        """
        Build a teacher → [(cls, subject)] map and process teachers
        in order of total load (most periods first).
        For each teacher, schedule all their classes together using
        a day-by-day round-robin so that their slots are coordinated
        and cannot collide between classes.
        """
        teacher_jobs = defaultdict(list)
        for cls in self.classes:
            for subject, count in remaining[cls].items():
                if count > 0:
                    teacher = self.teachers[cls].get(subject)
                    if teacher:
                        teacher_jobs[teacher].append((cls, subject))

        # Most-loaded teacher first — their constraints are tightest
        for teacher in sorted(
            teacher_jobs,
            key=lambda t: sum(remaining[c].get(s, 0) for c, s in teacher_jobs[t]),
            reverse=True,
        ):
            self._schedule_teacher_roundrobin(teacher, teacher_jobs[teacher], remaining)

    def _schedule_teacher_roundrobin(self, teacher, jobs, remaining):
        """
        For each day (in shuffled order):
          - Compute target periods per class on that day (from distribution).
          - Place 2-period consecutive blocks first (they're harder to fit).
          - Then place single periods.
        Any leftover periods are scattered as overflow at the end.

        Interleaving day-by-day across classes means all classes get their
        share of each day before we move on — preventing one class from
        monopolising all of the teacher's available slots.
        """
        # Pre-compute per-job day distributions (based on original demand)
        job_dist = {
            (cls, subj): self._day_distribution(self.original_demand[cls][subj])
            for cls, subj in jobs
        }

        days = list(range(self.DAYS))
        random.shuffle(days)

        for day_idx, day in enumerate(days):
            # Collect (needed, cls, subject) for this day — 2-blocks first
            day_work = []
            for cls, subj in jobs:
                count = remaining[cls].get(subj, 0)
                if count <= 0:
                    continue
                needed = min(job_dist[(cls, subj)][day_idx], count)
                if needed > 0:
                    day_work.append((needed, cls, subj))

            day_work.sort(reverse=True)  # larger blocks before singles

            for needed, cls, subj in day_work:
                count = remaining[cls].get(subj, 0)
                if count <= 0:
                    continue
                actual = min(needed, count)

                if actual >= 2:
                    block = self._find_consecutive_block(cls, teacher, day, actual, subj)
                    if block:
                        for slot in block:
                            self._place(cls, subj, teacher, day, slot)
                            remaining[cls][subj] -= 1
                        continue
                    # Could not find a consecutive block — fall through to singles

                for _ in range(actual):
                    if remaining[cls].get(subj, 0) <= 0:
                        break
                    slot = self._find_slot(cls, teacher, day, subj)
                    if slot is not None:
                        self._place(cls, subj, teacher, day, slot)
                        remaining[cls][subj] -= 1

        # Overflow: anything still unplaced goes wherever a valid slot exists
        for cls, subj in jobs:
            if remaining[cls].get(subj, 0) > 0:
                self._place_overflow(cls, subj, teacher, remaining)

    def _place_overflow(self, cls, subject, teacher, remaining):
        days = list(range(self.DAYS))
        random.shuffle(days)
        for day in days:
            if remaining[cls].get(subject, 0) <= 0:
                break
            slot = self._find_slot(cls, teacher, day, subject)
            if slot is not None:
                self._place(cls, subject, teacher, day, slot)
                remaining[cls][subject] -= 1

    # ------------------------------------------------------------------ #
    # Phase 4 – MRV cleanup                                               #
    # ------------------------------------------------------------------ #

    def _mrv_cleanup(self, remaining):
        """
        Minimum Remaining Values: at each step, place whichever unscheduled
        period has the *fewest* valid slots left.  This prevents easy periods
        from consuming slots that only the hard periods can use.
        """
        for _ in range(600):
            best_cls = best_subj = best_teacher = None
            best_count = float("inf")
            best_placements = []

            for cls in self.classes:
                for subj, count in remaining[cls].items():
                    if count <= 0:
                        continue
                    teacher = self.teachers[cls].get(subj)
                    if not teacher:
                        continue

                    valid = [
                        (self._score_placement(cls, subj, d, p), d, p)
                        for d in range(self.DAYS)
                        for p in range(self.PERIODS)
                        if self._can_place(cls, teacher, d, p, subj)
                    ]

                    if len(valid) < best_count:
                        best_count = len(valid)
                        best_cls, best_subj, best_teacher = cls, subj, teacher
                        best_placements = valid

            if best_cls is None or not best_placements:
                break  # nothing more can be placed

            best_placements.sort(reverse=True)
            _, day, period = best_placements[0]
            self._place(best_cls, best_subj, best_teacher, day, period)
            remaining[best_cls][best_subj] -= 1

    # ------------------------------------------------------------------ #
    # Phase 5 – Local repair                                              #
    # ------------------------------------------------------------------ #

    def _local_repair(self, remaining):
        """
        For each period that still can't be placed, find a slot where
        the teacher is free but the class slot is occupied by a different
        subject, then try to relocate that blocker to another valid slot
        and place our stuck period in the freed slot.
        Runs up to 3 passes so a chain of swaps can propagate.
        """
        for _ in range(3):
            made_progress = False
            for cls in self.classes:
                for subj in list(remaining[cls].keys()):
                    if remaining[cls].get(subj, 0) <= 0:
                        continue
                    teacher = self.teachers[cls].get(subj)
                    if not teacher:
                        continue
                    if self._try_repair_one(cls, subj, teacher, remaining):
                        made_progress = True
            if not made_progress:
                break

    def _try_repair_one(self, cls, subject, teacher, remaining):
        """
        Try to free exactly one slot for *subject* by relocating a blocker.
        Returns True if a placement was made.
        """
        for day in range(self.DAYS):
            for period in range(self.PERIODS):
                # Teacher must be free at this slot
                if self.teacher_slots[teacher][day][period] is not None:
                    continue
                # Class slot must be occupied (otherwise MRV would have placed here)
                blocker = self.schedule[cls][day][period]
                if blocker is None:
                    continue

                block_teacher = self.teachers[cls].get(blocker)
                if not block_teacher:
                    continue

                # Tentatively free the slot
                self.schedule[cls][day][period] = None
                self.teacher_slots[block_teacher][day][period] = None

                placed = False
                if self._can_place(cls, teacher, day, period, subject):
                    # Find the best alternative home for the blocker
                    alt = self._find_best_alt_slot(cls, blocker, block_teacher, day, period)
                    if alt is not None:
                        alt_day, alt_period = alt
                        self._place(cls, blocker, block_teacher, alt_day, alt_period)
                        self._place(cls, subject, teacher, day, period)
                        remaining[cls][subject] -= 1
                        placed = True

                if not placed:
                    # Restore the original placement
                    self.schedule[cls][day][period] = blocker
                    self.teacher_slots[block_teacher][day][period] = cls
                else:
                    return True

        return False

    def _find_best_alt_slot(self, cls, subject, teacher, avoid_day, avoid_period):
        """
        Find the highest-scored valid slot for *subject* that isn't
        (avoid_day, avoid_period).  Returns (day, period) or None.
        """
        candidates = [
            (self._score_placement(cls, subject, d, p), d, p)
            for d in range(self.DAYS)
            for p in range(self.PERIODS)
            if not (d == avoid_day and p == avoid_period)
            and self._can_place(cls, teacher, d, p, subject)
        ]
        if not candidates:
            return None
        candidates.sort(reverse=True)
        _, day, period = candidates[0]
        return (day, period)

    # ------------------------------------------------------------------ #
    # Phase 1 – Fixed sessions                                            #
    # ------------------------------------------------------------------ #

    def _place_fixed_sessions(self, remaining):
        for rule in self.fixed_sessions:
            subject = rule["subject"]
            day = rule["day"]
            period = rule["period"]
            rule_classes = rule["classes"]

            for cls in rule_classes:
                if self.schedule[cls][day][period] is not None:
                    print(f"  ✗ Fixed session conflict: {cls} slot {day}/{period} occupied")
                    return False

            teacher_map = {}
            for cls in rule_classes:
                teacher = self.teachers[cls].get(subject)
                if not teacher:
                    continue
                if self.teacher_slots[teacher][day][period] is not None:
                    print(f"  ✗ Fixed session conflict: teacher {teacher} busy at {day}/{period}")
                    return False
                teacher_map[cls] = teacher

            for cls, teacher in teacher_map.items():
                self._place(cls, subject, teacher, day, period)
                if remaining[cls].get(subject, 0) > 0:
                    remaining[cls][subject] -= 1

        return True

    # ------------------------------------------------------------------ #
    # Phase 2 – "Should be" preferences                                   #
    # ------------------------------------------------------------------ #

    def _place_should_be_rules(self, remaining):
        for rule in self.placement_rules:
            if rule["type"] != "should_be":
                continue
            subjects = rule["subjects"]
            target_period = rule["period"]
            rule_classes = rule["classes"]

            for cls in rule_classes:
                days = list(range(self.DAYS))
                random.shuffle(days)
                for day in days:
                    if self.schedule[cls][day][target_period] is not None:
                        continue
                    for subj in subjects:
                        if remaining[cls].get(subj, 0) <= 0:
                            continue
                        teacher = self.teachers[cls].get(subj)
                        if teacher and self._can_place(cls, teacher, day, target_period, subj):
                            self._place(cls, subj, teacher, day, target_period)
                            remaining[cls][subj] -= 1
                            break

    # ------------------------------------------------------------------ #
    # Output                                                               #
    # ------------------------------------------------------------------ #

    def get_schedule(self):
        return {
            cls: {day: list(self.schedule[cls][day]) for day in range(self.DAYS)}
            for cls in self.classes
        }
