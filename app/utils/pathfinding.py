from .. models import Building, Room, MapPath
from .. import db
import heapq
from typing import List, Dict, Tuple


def _load_graph(accessible_only: bool = False) -> Dict[str, List[Tuple[str, int]]]:
    """Builds a graph ONLY from the MapPath table."""
    graph: Dict[str, List[Tuple[str, int]]] = {}
    query = MapPath.query
    if accessible_only:
        query = query.filter_by(accessible=True)
    
    for path in query.all():
        graph.setdefault(path.from_location, []).append((path.to_location, path.distance))
    return graph

def find_shortest_path(start: str, end: str, accessible_only: bool = False) -> Tuple[List[str], int]:
    """Finds the shortest path using Dijkstra's algorithm."""
    if start == end:
        return [start], 0

    graph = _load_graph(accessible_only)
    queue = [(0, start, [])]
    seen = set()

    while queue:
        (cost, node, path) = heapq.heappop(queue)
        if node in seen:
            continue
        path = path + [node]
        seen.add(node)
        if node == end:
            return path, cost
        for next_node, weight in graph.get(node, []):
            if next_node not in seen:
                heapq.heappush(queue, (cost + weight, next_node, path))
    return [], 0


def all_locations(role: str) -> List[str]:
    SEPARATOR = " / "
    locations = set()

    for b in Building.query.all():
        locations.add(b.name)
        
    for r in Room.query.join(Building).all():
        locations.add(f"{r.building.name}{SEPARATOR}{r.name}")
        
    return sorted(list(locations))

def get_path_directions(path: List[str]) -> List[Dict]:
    """Generates human-readable directions from a path list."""
    if not path or len(path) < 2:
        return [{"text": "No path found or destination is the same as start."}]

    steps_raw = []
    for i in range(len(path) - 1):
        a, b = path[i], path[i+1]
        edge = MapPath.query.filter_by(from_location=a, to_location=b).first()
        if not edge:
            steps_raw.append({"text": f"Proceed from {a} to {b}", "node": a})
            continue
        
        if edge.kind == "entry": continue
        elif edge.kind == "elevator":
            start_floor = a.split('@')[-1]; end_floor = b.split('@')[-1]
            steps_raw.append({"text": f"Take elevator from {start_floor} to {end_floor}.", "node": a})
        elif edge.kind == "stairs":
            start_floor = a.split('@')[-1]; end_floor = b.split('@')[-1]
            steps_raw.append({"text": f"Take stairs from {start_floor} to {end_floor}.", "node": a})
        else:
            start_simple = a.split(' / ')[-1]; end_simple = b.split(' / ')[-1]
            steps_raw.append({"text": f"From '{start_simple}', go to '{end_simple}' ({edge.distance}m).", "node": a})

    if not steps_raw: return [{"text": "You are already at your destination.", "node": path[0]}]
        
    cleaned_steps = []
    i = 0
    while i < len(steps_raw):
        current_step = steps_raw[i]
        is_elevator = current_step["text"].startswith("Take elevator")
        is_stairs = current_step["text"].startswith("Take stairs")

        if is_elevator or is_stairs:
            transit_type = "elevator" if is_elevator else "stairs"
            start_floor = current_step["text"].split('from ')[-1].split(' to')[0]
            j = i
            while j + 1 < len(steps_raw) and steps_raw[j+1]["text"].startswith(f"Take {transit_type}"):
                j += 1
            end_floor = steps_raw[j]["text"].split('to ')[-1].replace('.', '')
            cleaned_steps.append({"text": f"Take {transit_type} from {start_floor} to {end_floor}.", "node": current_step["node"]})
            i = j + 1
        else:
            cleaned_steps.append(current_step)
            i += 1

    final_dest_text = f"You have arrived at {path[-1].split(' / ')[-1]}."
    cleaned_steps.append({"text": final_dest_text, "node": path[-1]})
    return cleaned_steps