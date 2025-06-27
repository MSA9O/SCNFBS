# seed_data.py
import json
from pathlib import Path
from werkzeug.security import generate_password_hash
from app import create_app
from app.models import db, User, Building, Room, BookingRule, MapPath

def seed_database(app):
    with app.app_context():
        print("Dropping all tables and re-creating...")
        db.drop_all()
        db.create_all()

        # ───────── 1. Users ─────────
        users = [
            User(name="Admin", email="admin@scnfbs.com", role="Admin", password_hash=generate_password_hash("admin123")),
            User(name="Faculty", email="faculty@scnfbs.com", role="Faculty", password_hash=generate_password_hash("faculty123")),
            User(name="Student", email="student@scnfbs.com", role="Student", password_hash=generate_password_hash("student123")),
        ]
        db.session.bulk_save_objects(users)
        print("✓ Users seeded.")

        # ───────── 2. Buildings + Rooms ─────────
        b_a = Building(name="Building A"); b_b = Building(name="Building B"); b_c = Building(name="Building C"); b_d = Building(name="Building D"); b_e = Building(name="Building E")
        buildings = [b_a, b_b, b_c, b_d, b_e]
        db.session.add_all(buildings)

        bookable_rooms = [
            # Faculty bookable
            Room(name="Faculty Office", type="Room", building=b_a),
            Room(name="Lab 101", type="Lab", building=b_b),
            Room(name="Lecture Hall 102", type="Room", building=b_a),
            Room(name="Auditorium", type="Auditorium", building=b_d),
            Room(name="Student Lounge", type="Room", building=b_a),
            # Student bookable
            Room(name="Quiet Study Room", type="Study", building=b_c),
            Room(name="Group Study Room", type="Study", building=b_d),
            Room(name="Study Room A", type="Study", building=b_a),
            Room(name="Study Room B", type="Study", building=b_b),
            Room(name="Study Room C", type="Study", building=b_c),
            Room(name="Study Room D", type="Study", building=b_d),
            Room(name="Study Room E", type="Study", building=b_e),
        ]
        db.session.add_all(bookable_rooms)
        print("✓ Buildings and Rooms seeded.")
        
        # ───────── 3. Booking Rules ─────────
        rules = [ BookingRule(role="Admin", max_hours=8), BookingRule(role="Faculty", max_hours=4), BookingRule(role="Student", max_hours=2) ]
        db.session.bulk_save_objects(rules)
        print("✓ Booking Rules seeded.")
        
        db.session.commit()

        # ───────── 4. Campus Paths from JSON ─────────
        path_data_to_process = []
        SEPARATOR = " / "
        data_dir = Path(__file__).parent / 'data'
        building_entrances = {}

        with open(data_dir / 'campus_paths.json', 'r', encoding='utf-8') as f:
            for p in json.load(f).get('paths', []):
                path_data_to_process.append({'from': p['from'], 'to': p['to'], 'dist': p['distance'], 'kind': p['kind'], 'access': p.get('accessible', True)})

        for json_file in data_dir.glob("Building_*.json"):
            with open(json_file, 'r', encoding='utf-8') as f:
                b_data = json.load(f)
                b_name = b_data['name'].split('–')[0].strip()
                
                if b_data.get('paths'):
                    entrance_node = b_data['paths'][0]['from']
                    building_entrances[b_name] = f"{b_name}{SEPARATOR}{entrance_node}"

                if "floors" in b_data:
                    for i in range(len(b_data["floors"]) - 1):
                        f1, f2 = b_data["floors"][i], b_data["floors"][i+1]
                        path_data_to_process.append({'from': f"{b_name}{SEPARATOR}Elevator@{f1}", 'to': f"{b_name}{SEPARATOR}Elevator@{f2}", 'dist': 5, 'kind': "elevator", 'access': True})
                        path_data_to_process.append({'from': f"{b_name}{SEPARATOR}Stairs@{f1}", 'to': f"{b_name}{SEPARATOR}Stairs@{f2}", 'dist': 8, 'kind': "stairs", 'access': False})
                for p in b_data.get('paths', []):
                    floor = p["floor"]
                    from_node = p['from'] + (f"@{floor}" if p['from'] in ["Elevator", "Stairs"] else "")
                    to_node = p['to'] + (f"@{floor}" if p['to'] in ["Elevator", "Stairs"] else "")
                    path_data_to_process.append({'from': f"{b_name}{SEPARATOR}{from_node}", 'to': f"{b_name}{SEPARATOR}{to_node}", 'dist': p['distance'], 'kind': "walk", 'access': p['accessible']})

        all_waypoints = {p['from'] for p in path_data_to_process} | {p['to'] for p in path_data_to_process}
        
        room_to_waypoint_map = {
            "Faculty Office": f"Building A{SEPARATOR}Room 101 - Faculty Office",
            "Lab 101": f"Building B{SEPARATOR}Lab 101",
            "Lecture Hall 102": f"Building A{SEPARATOR}Room 102 - Classroom",
            "Auditorium": f"Building D{SEPARATOR}Auditorium",
            "Student Lounge": f"Building A{SEPARATOR}Room 202 - Student Lounge",
            "Quiet Study Room": f"Building C{SEPARATOR}Study Room 201",
            "Group Study Room": f"Building D{SEPARATOR}Conference Room 202",
            "Study Room A": f"Building A{SEPARATOR}Study Room A",
            "Study Room B": f"Building B{SEPARATOR}Study Room B",
            "Study Room C": f"Building C{SEPARATOR}Study Room C",
            "Study Room D": f"Building D{SEPARATOR}Study Room D",
            "Study Room E": f"Building E{SEPARATOR}Study Room E",
        }
        
        print("Connecting bookable rooms to the navigation graph...")
        for room in bookable_rooms:
            room_node_name = f"{room.building.name}{SEPARATOR}{room.name}"
            waypoint = room_to_waypoint_map.get(room.name)
            if waypoint and waypoint in all_waypoints:
                path_data_to_process.append({'from': room_node_name, 'to': waypoint, 'dist': 0, 'kind': "entry", 'access': True})
            else:
                print(f"  - WARNING: No waypoint found for '{room.name}'. It will be unreachable.")

        print("Connecting buildings to their main entrances...")
        for b_name, entrance_waypoint in building_entrances.items():
            if entrance_waypoint in all_waypoints:
                path_data_to_process.append({'from': b_name, 'to': entrance_waypoint, 'dist': 0, 'kind': "entry", 'access': True})
            else:
                print(f"  - WARNING: No entrance waypoint found for '{b_name}'. It may be isolated.")

        final_paths_to_add = []
        path_tracker = set()

        for p_data in path_data_to_process:
            frm, to, kind = p_data['from'], p_data['to'], p_data['kind']
            if frm == to:
                continue
            path_key = (min(frm, to), max(frm, to), kind)
            if path_key not in path_tracker:
                final_paths_to_add.append(MapPath(from_location=frm, to_location=to, distance=p_data['dist'], kind=kind, accessible=p_data['access']))
                final_paths_to_add.append(MapPath(from_location=to, to_location=frm, distance=p_data['dist'], kind=kind, accessible=p_data['access']))
                path_tracker.add(path_key)

        db.session.bulk_save_objects(final_paths_to_add)
        print(f"✓ {len(final_paths_to_add)} total map path segments seeded.")
        
        db.session.commit()
        print("\nDatabase seeded successfully!")


if __name__ == "__main__":
    app = create_app()
    seed_database(app)