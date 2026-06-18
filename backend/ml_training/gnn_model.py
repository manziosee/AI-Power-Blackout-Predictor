"""GNN cascade prediction model — GraphSAGE architecture scaffold."""
import json


class CascadeGNN:
    """
    GraphSAGE-based model for predicting transformer-level cascade failures.
    Nodes = H3 cells; edges = adjacency (k-ring 1) + transformer coverage overlap.
    """

    def __init__(self, node_features: int = 16, hidden_dim: int = 64, output_dim: int = 1, num_layers: int = 2):
        self.node_features = node_features
        self.hidden_dim = hidden_dim
        self.output_dim = output_dim
        self.num_layers = num_layers
        self._model = None

    def _build(self):
        try:
            import torch
            import torch.nn as nn
            from torch_geometric.nn import SAGEConv

            class _SAGEModel(nn.Module):
                def __init__(self, in_ch, hidden, out, layers):
                    super().__init__()
                    self.convs = nn.ModuleList()
                    self.convs.append(SAGEConv(in_ch, hidden))
                    for _ in range(layers - 2):
                        self.convs.append(SAGEConv(hidden, hidden))
                    self.convs.append(SAGEConv(hidden, out))
                    self.relu = nn.ReLU()
                    self.sigmoid = nn.Sigmoid()

                def forward(self, x, edge_index):
                    for conv in self.convs[:-1]:
                        x = self.relu(conv(x, edge_index))
                    x = self.sigmoid(self.convs[-1](x, edge_index))
                    return x

            self._model = _SAGEModel(self.node_features, self.hidden_dim, self.output_dim, self.num_layers)
            return True
        except ImportError:
            return False

    def build_graph(self, h3_cells: list[str], outage_history: dict[str, list[float]]):
        """Build node feature matrix and adjacency edge list from H3 cell data."""
        try:
            import h3
            import torch

            node_idx = {cell: i for i, cell in enumerate(h3_cells)}
            edges_src, edges_dst = [], []

            for cell in h3_cells:
                neighbors = h3.k_ring(cell, 1) - {cell}
                for nb in neighbors:
                    if nb in node_idx:
                        edges_src.append(node_idx[cell])
                        edges_dst.append(node_idx[nb])

            import numpy as np
            features = np.zeros((len(h3_cells), self.node_features), dtype=np.float32)
            for i, cell in enumerate(h3_cells):
                history = outage_history.get(cell, [])
                if history:
                    features[i, 0] = np.mean(history[-7:]) if len(history) >= 7 else np.mean(history)
                    features[i, 1] = np.std(history) if len(history) > 1 else 0.0
                    features[i, 2] = float(len(history))

            x = torch.tensor(features)
            edge_index = torch.tensor([edges_src, edges_dst], dtype=torch.long)
            return x, edge_index
        except ImportError:
            return None, None

    def predict(self, h3_cells: list[str], outage_history: dict[str, list[float]]) -> list[dict]:
        """Return cascade risk per cell. Falls back to heuristic if torch not available."""
        x, edge_index = self.build_graph(h3_cells, outage_history)

        if x is None or not self._build():
            # Heuristic fallback — no torch/pyg dependency in CI
            results = []
            for cell in h3_cells:
                history = outage_history.get(cell, [])
                prob = min(1.0, sum(history[-7:]) / 7.0) if history else 0.0
                results.append({"h3_index": cell, "probability": round(prob, 4), "source": "heuristic"})
            return results

        import torch
        self._model.eval()
        with torch.no_grad():
            out = self._model(x, edge_index).squeeze(-1)
        probs = out.numpy().tolist()
        return [
            {"h3_index": cell, "probability": round(float(p), 4), "source": "gnn"}
            for cell, p in zip(h3_cells, probs)
        ]

    def train(self, h3_cells, outage_history, labels, epochs: int = 100, lr: float = 0.01):
        if not self._build():
            print("torch-geometric not available — skipping GNN training")
            return None
        import torch
        import torch.nn as nn

        x, edge_index = self.build_graph(h3_cells, outage_history)
        y = torch.tensor(labels, dtype=torch.float32)
        optimizer = torch.optim.Adam(self._model.parameters(), lr=lr)
        criterion = nn.BCELoss()

        self._model.train()
        for epoch in range(epochs):
            optimizer.zero_grad()
            out = self._model(x, edge_index).squeeze(-1)
            loss = criterion(out, y)
            loss.backward()
            optimizer.step()
            if (epoch + 1) % 20 == 0:
                print(f"Epoch {epoch+1}/{epochs} — Loss: {loss.item():.4f}")
        return self._model

    def save(self, path: str) -> None:
        if self._model is None:
            return
        import torch
        torch.save(self._model.state_dict(), path)
        meta_path = path.replace(".pt", "_meta.json")
        with open(meta_path, "w") as f:
            json.dump({
                "node_features": self.node_features,
                "hidden_dim": self.hidden_dim,
                "output_dim": self.output_dim,
                "num_layers": self.num_layers,
            }, f, indent=2)

    def load(self, path: str) -> None:
        if not self._build():
            return
        import torch
        self._model.load_state_dict(torch.load(path, map_location="cpu"))
        self._model.eval()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--db-url", required=True)
    parser.add_argument("--output", default="models/gnn_cascade.pt")
    parser.add_argument("--epochs", type=int, default=100)
    args = parser.parse_args()

    print("GNN training scaffold — connect to DB to load real cell history")
    model = CascadeGNN()
    print(f"Model architecture: GraphSAGE {model.num_layers}L hidden={model.hidden_dim}")
