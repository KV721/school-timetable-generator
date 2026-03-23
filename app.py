from flask import Flask, request, jsonify
from flask_cors import CORS
from solver import TimetableSolver
import traceback

app = Flask(__name__)
CORS(app)  # Enable CORS for frontend

@app.route('/generate', methods=['POST'])
def generate_timetable():
    """
    Generate timetable based on input constraints
    
    Expected JSON format:
    {
        "classes": ["6th", "7th", "8th"],
        "teachers": {
            "6th": {"Maths": "SNK", "Science": "HVN", ...},
            "7th": {...},
            ...
        },
        "demand": {
            "6th": {"Maths": 8, "Science": 7, ...},
            "7th": {...},
            ...
        },
        "constraints": {
            "max_consecutive": 8,
            "fixed_sessions": [
                {
                    "subject": "MD",
                    "day": 5,  # Saturday (0=Mon, 5=Sat)
                    "period": 7,  # Period 8 (0-indexed, so 7)
                    "classes": ["6th", "7th", "8th"]
                }
            ],
            "placement_rules": [
                {
                    "subjects": ["ICT"],
                    "type": "should_be",  # or "should_not"
                    "period": 2,  # Period 3 (0-indexed)
                    "classes": ["6th", "7th"]
                }
            ]
        }
    }
    """
    try:
        data = request.json
        
        # Validate input
        if not data:
            return jsonify({
                "status": "error",
                "message": "No data provided"
            }), 400
        
        required_fields = ["classes", "teachers", "demand"]
        for field in required_fields:
            if field not in data:
                return jsonify({
                    "status": "error",
                    "message": f"Missing required field: {field}"
                }), 400
        
        print(f"\n{'='*60}")
        print(f"Generating timetable for classes: {data['classes']}")
        print(f"{'='*60}")
        
        # Print summary of what needs to be scheduled
        total_periods = sum(sum(d.values()) for d in data['demand'].values())
        print(f"Total periods to schedule: {total_periods}")
        
        # Teacher workload analysis
        teacher_load = {}
        for cls in data['classes']:
            for subject, teacher in data['teachers'][cls].items():
                if teacher not in teacher_load:
                    teacher_load[teacher] = 0
                periods = data['demand'][cls].get(subject, 0)
                teacher_load[teacher] += periods
        
        print(f"\nTeacher workload:")
        for teacher, load in sorted(teacher_load.items(), key=lambda x: x[1], reverse=True):
            print(f"  {teacher}: {load} periods")
        print()
        
        # Validate total periods
        total_periods_check = validate_periods(data)
        if not total_periods_check['valid']:
            return jsonify({
                "status": "failed",
                "message": total_periods_check['message']
            })
        
        # Create solver and attempt to solve
        solver = TimetableSolver(data)
        
        if solver.solve(max_attempts=300):
            schedule = solver.get_schedule()
            
            print("\n✓ Timetable generated successfully!")
            print_summary(schedule, data['classes'])
            
            # Verify the schedule
            verification = verify_schedule(schedule, data)
            
            return jsonify({
                "status": "success",
                "schedule": schedule,
                "message": "Timetable generated successfully",
                "stats": verification
            })
        else:
            print("\n✗ Failed to generate timetable")
            
            # Analyze why it failed
            analysis = analyze_failure(data)
            
            return jsonify({
                "status": "failed",
                "message": f"Could not generate a complete timetable. {analysis}"
            })
    
    except Exception as e:
        print(f"\n✗ Server error occurred:")
        print(traceback.format_exc())
        
        return jsonify({
            "status": "error",
            "message": f"Server error: {str(e)}"
        }), 500

def print_summary(schedule, classes):
    """Print a summary of the generated timetable"""
    days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
    
    for cls in classes:
        print(f"\nClass {cls}:")
        print(f"{'-'*80}")
        print(f"{'Day':<10} ", end="")
        for p in range(1, 9):
            print(f"P{p:<7} ", end="")
        print()
        print(f"{'-'*80}")
        
        for day in range(6):
            print(f"{days[day]:<10} ", end="")
            for period in range(8):
                subject = schedule[cls][day][period]
                print(f"{subject if subject else '-':<8} ", end="")
            print()

def validate_periods(data):
    """Validate that period counts are reasonable"""
    for cls in data['classes']:
        total = sum(data['demand'][cls].values())
        if total > 48:
            return {
                'valid': False,
                'message': f"Class {cls} has {total} periods assigned but only 48 are available per week (6 days × 8 periods)"
            }
    return {'valid': True}

def verify_schedule(schedule, data):
    """Verify the generated schedule and return statistics"""
    stats = {
        'total_periods': 0,
        'empty_periods': 0,
        'classes': {}
    }
    
    for cls in data['classes']:
        cls_stats = {'total': 0, 'empty': 0}
        for day in range(6):
            for period in range(8):
                if schedule[cls][day][period]:
                    cls_stats['total'] += 1
                    stats['total_periods'] += 1
                else:
                    cls_stats['empty'] += 1
                    stats['empty_periods'] += 1
        stats['classes'][cls] = cls_stats
    
    return stats

def analyze_failure(data):
    """Analyze why timetable generation failed"""
    messages = []
    
    # Check teacher workload
    teacher_load = {}
    for cls in data['classes']:
        for subject, teacher in data['teachers'][cls].items():
            if teacher not in teacher_load:
                teacher_load[teacher] = 0
            periods = data['demand'][cls].get(subject, 0)
            teacher_load[teacher] += periods
    
    overloaded = [(t, load) for t, load in teacher_load.items() if load > 40]
    if overloaded:
        messages.append(f"Teachers with heavy load: {', '.join([f'{t}({l} periods)' for t, l in overloaded[:3]])}. ")
    
    # Check if any class is overfilled
    for cls in data['classes']:
        total = sum(data['demand'][cls].values())
        if total > 45:
            messages.append(f"Class {cls} has {total} periods (very tight). ")
    
    if not messages:
        messages.append("Try increasing max consecutive periods limit or removing some constraints.")
    
    return "".join(messages)

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({"status": "healthy", "message": "Server is running"})

if __name__ == '__main__':
    print("\n" + "="*60)
    print("  School Timetable Generator - Backend Server")
    print("="*60)
    print("\nServer starting on http://127.0.0.1:5000")
    print("Press CTRL+C to stop\n")
    
    app.run(debug=True, port=5000, host='127.0.0.1')