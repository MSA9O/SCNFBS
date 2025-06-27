# app/routes/navigation.py
import os
import json
from flask import Blueprint, render_template, request, flash, current_app, jsonify
from flask_login import login_required, current_user
from ..utils.pathfinding import find_shortest_path, all_locations, get_path_directions
from ..models import MapPath
from pathlib import Path

bp_navigation = Blueprint("navigation", __name__)

def load_building_json(building_name):
    filename = building_name.replace(" ", "_") + ".json"
    data_path = Path(current_app.root_path).parent / 'data' / filename
    if data_path.exists():
        with open(data_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None

def load_campus_paths_json():
    data_path = Path(current_app.root_path).parent / 'data' / 'campus_paths.json'
    if data_path.exists():
        with open(data_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None

@bp_navigation.route("/navigation/data/<building_filename>")
@login_required
def building_data(building_filename):
    """Serve the JSON data for a specific building."""
    building_name = building_filename.replace("_", " ")
    data = load_building_json(building_name)
    if data:
        return jsonify(data)
    return jsonify({"error": "Building data not found"}), 404

@bp_navigation.route("/navigation", methods=["GET", "POST"])
@login_required
def navigation():
    locations = all_locations(current_user.role)
    context = {
        "locations": locations, "path": [], "steps": [], "distance": 0,
        "selected_start": request.form.get("start", ""),
        "selected_dest": request.form.get("destination", ""),
        "accessible": bool(request.form.get("accessible")),
        "map_type": "campus", "map_data": load_campus_paths_json(),
    }

    if request.method == "POST":
        start_node = context["selected_start"]
        end_node = context["selected_dest"]
        if not start_node or not end_node:
            flash("Start and destination points are required.", "warning")
            return render_template("navigation.html", **context)
        
        path, distance = find_shortest_path(start_node, end_node, context["accessible"])
        
        context["path"] = path
        context["distance"] = distance
        context["steps"] = get_path_directions(path) 

        if path:
            start_building = path[0].split(' / ')[0]
            end_building = path[-1].split(' / ')[0]
            if start_building == end_building and "Building" in start_building:
                context["map_type"] = "building"
                context["map_data"] = load_building_json(start_building)
            else:
                context["map_type"] = "campus"
                context["map_data"] = load_campus_paths_json()
    
    return render_template("navigation.html", **context)