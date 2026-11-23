from __future__ import annotations
import math
from pathlib import Path
import networkx as nx
import pandas as pd

NODES_PATH = Path("data/master/station_nodes.csv")
EDGES_PATH = Path("data/master/network_edges.csv")


def calc_walking_minutes_fallback(
    lat1: float, lon1: float, lat2: float, lon2: float, detour_factor: float = 1.3
) -> float:
    """Fallback walking time calculation (80m/min) when explicit transfer data is unavailable."""
    r = 6371000  # Earth radius in meters
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    straight_dist_m = 2 * r * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    walking_dist_m = straight_dist_m * detour_factor
    return round(max(2.0, walking_dist_m / 80.0), 1)


class TransitRouter:
    def __init__(self, edges_path: Path = EDGES_PATH, nodes_path: Path = NODES_PATH):
        self.df_edges = pd.read_csv(edges_path)
        self.df_nodes = pd.read_csv(nodes_path)
        self.graph = self._build_base_graph()

    def _build_base_graph(self) -> nx.DiGraph:
        g = nx.DiGraph()
        for _, row in self.df_edges.iterrows():
            u = (row["from_station"], row["from_line"])
            v = (row["to_station"], row["to_line"])
            minutes = float(row["base_minutes"])
            edge_type = row["edge_type"]
            line_name = row["from_line"] if edge_type == "ride" else "transfer"

            # Add bidirectional edges
            g.add_edge(u, v, base_minutes=minutes, edge_type=edge_type, line=line_name)
            g.add_edge(v, u, base_minutes=minutes, edge_type=edge_type, line=line_name)
        return g

    def find_optimal_route(
        self,
        origin_station: str,
        dest_station: str,
        predicted_delays: dict[str, float] | None = None,
        risk_aversion: float = 1.0,
    ) -> dict:
        """
        Find optimal route considering predicted line delays.
        predicted_delays: mapping of line_name -> expected delay minutes
        risk_aversion: multiplier for delay penalty (1.0 = expected value, >1.0 = conservative)
        """
        delays = predicted_delays or {}
        g_weighted = self.graph.copy()

        # Assign dynamic edge weights: base_minutes + expected delay penalty
        for u, v, data in g_weighted.edges(data=True):
            weight = data["base_minutes"]
            if data["edge_type"] == "ride":
                line_delay = delays.get(data["line"], 0.0)
                weight += line_delay * risk_aversion * 0.5
            g_weighted[u][v]["weight"] = weight

        # Add virtual START and END nodes to handle multi-line origin/destination stations
        start_node = ("__START__", origin_station)
        end_node = ("__END__", dest_station)

        origin_candidates = [n for n in g_weighted.nodes if n[0] == origin_station]
        dest_candidates = [n for n in g_weighted.nodes if n[0] == dest_station]

        if not origin_candidates or not dest_candidates:
            raise ValueError(f"Unknown station: {origin_station} or {dest_station}")

        for node in origin_candidates:
            g_weighted.add_edge(start_node, node, weight=0.0, base_minutes=0.0, edge_type="access", line="start")
        for node in dest_candidates:
            g_weighted.add_edge(node, end_node, weight=0.0, base_minutes=0.0, edge_type="egress", line="end")

        path = nx.dijkstra_path(g_weighted, start_node, end_node, weight="weight")

        total_base_min = 0.0
        total_expected_min = 0.0
        steps = []
        used_lines = set()

        for i in range(1, len(path) - 2):
            u, v = path[i], path[i + 1]
            edge = g_weighted[u][v]
            total_base_min += edge["base_minutes"]
            total_expected_min += edge["weight"]
            if edge["edge_type"] == "ride":
                used_lines.add(edge["line"])
            steps.append(f"{u[0]}({u[1]}) -> {v[0]}({v[1]}) [{edge['edge_type']}: {edge['weight']:.1f}m]")

        return {
            "origin": origin_station,
            "destination": dest_station,
            "base_minutes": round(total_base_min, 1),
            "expected_minutes": round(total_expected_min, 1),
            "used_lines": sorted(used_lines),
            "steps": steps,
        }


if __name__ == "__main__":
    router = TransitRouter()

    print("=== Case 1: Normal Weather (新宿 -> 東京) ===")
    res_normal = router.find_optimal_route("新宿", "東京")
    print(f"所要時間(平常): {res_normal['base_minutes']}分 / 使用路線: {res_normal['used_lines']}")
    for s in res_normal["steps"]:
        print("  ", s)

    print("\n=== Case 2: Strong Wind / Heavy Rain (JR中央線快速が25分遅延予測) ===")
    storm_delays = {"JR中央線快速": 25.0, "JR京葉線": 30.0, "東京メトロ東西線": 20.0}
    res_storm = router.find_optimal_route("新宿", "東京", predicted_delays=storm_delays, risk_aversion=1.2)
    print(f"平常基準: {res_storm['base_minutes']}分 -> 遅延考慮期待時間: {res_storm['expected_minutes']}分 / 使用路線: {res_storm['used_lines']}")
    for s in res_storm["steps"]:
        print("  ", s)
