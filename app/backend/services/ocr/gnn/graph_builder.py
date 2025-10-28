import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

import numpy as np
import torch
from scipy.spatial import Delaunay
from sklearn.neighbors import NearestNeighbors
from torch_geometric.data import Data

logger = logging.getLogger(__name__)


@dataclass
class CharacterNode:
    """文字ノードの情報"""

    char_id: int
    char: str
    confidence: float
    x: float  # 中心座標
    y: float
    width: float
    height: float
    char_code: int
    region_id: int
    char_index_in_region: int
    font_features: Optional[np.ndarray] = None


class ReceiptGraphBuilder:
    """レシート文字認識結果からグラフを構築"""

    def __init__(
        self,
        edge_method: str = "directional",  # 'knn', 'delaunay', 'threshold', 'directional'
        k_neighbors: int = 5,
        distance_threshold: float = 100.0,
        use_char_embedding: bool = True,
        embedding_dim: int = 128,
        normalize_positions: bool = True,
    ):
        """
        Args:
            edge_method: エッジ構築手法
            k_neighbors: k近傍法のk値
            distance_threshold: 距離閾値
            use_char_embedding: 文字埋め込みを使用するか
            embedding_dim: 埋め込み次元数
            normalize_positions: 位置座標を正規化するか
        """
        self.edge_method = edge_method
        self.k_neighbors = k_neighbors
        self.distance_threshold = distance_threshold
        self.use_char_embedding = use_char_embedding
        self.embedding_dim = embedding_dim
        self.normalize_positions = normalize_positions

        logger.info(
            f"GraphBuilder initialized with edge_method={edge_method}, k={k_neighbors}"
        )

    def load_recognition_results(self, json_path: str) -> List[CharacterNode]:
        """
        文字認識結果JSONを読み込み

        Args:
            json_path: recognition_results.json のパス

        Returns:
            CharacterNodeのリスト
        """
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        nodes = []
        for result in data["recognition_results"]:
            # 認識失敗したものはスキップ
            if result["processing_status"] != "success":
                logger.warning(
                    f"Skipping failed recognition: char_id={result['char_id']}"
                )
                continue

            center = result["center"]
            bbox = result["bbox"]
            width = bbox[2] - bbox[0]
            height = bbox[3] - bbox[1]

            # フォント特徴量の読み込み
            font_feat = None
            if "font_features" in result and result["font_features"]:
                font_feat = np.array(result["font_features"], dtype=np.float32)

            node = CharacterNode(
                char_id=result["char_id"],
                char=result["recognized_char"],
                confidence=result["confidence"],
                x=center[0],
                y=center[1],
                width=width,
                height=height,
                char_code=result["char_code"],
                region_id=result.get("region_id", -1),
                char_index_in_region=result.get("char_index_in_region", -1),
                font_features=font_feat,
            )
            nodes.append(node)

        logger.info(f"Loaded {len(nodes)} character nodes")
        return nodes

    def load_from_metadata(self, metadata_path: str) -> List[CharacterNode]:
        """
        metadata.json から直接読み込み（文字認識チームの処理前）

        Args:
            metadata_path: metadata.json のパス

        Returns:
            CharacterNodeのリスト
        """
        with open(metadata_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        nodes = []
        for char_data in data["characters"]:
            center = char_data["center"]
            bbox = char_data["bbox"]
            width = bbox[2] - bbox[0]
            height = bbox[3] - bbox[1]

            # EasyOCRの結果を使用（暫定）
            char = char_data["char"]
            char_code = ord(char) if char else 0

            node = CharacterNode(
                char_id=char_data["char_id"],
                char=char,
                confidence=char_data["confidence"],
                x=center[0],
                y=center[1],
                width=width,
                height=height,
                char_code=char_code,
                region_id=char_data["region_id"],
                char_index_in_region=char_data["char_index_in_region"],
                font_features=None,
            )
            nodes.append(node)

        logger.info(f"Loaded {len(nodes)} character nodes from metadata")
        return nodes

    def build_node_features(self, nodes: List[CharacterNode]) -> torch.Tensor:
        """
        ノード特徴量を構築

        特徴量の構成:
        1. 位置特徴 (x, y) - 正規化済み
        2. サイズ特徴 (width, height)
        3. 信頼度 (confidence)
        4. 文字コード特徴 (char_code正規化)
        5. 領域内インデックス (char_index_in_region)
        6. フォント特徴量 (利用可能な場合)
        """
        features = []

        # 正規化用の統計値
        if self.normalize_positions and len(nodes) > 0:
            x_coords = np.array([n.x for n in nodes])
            y_coords = np.array([n.y for n in nodes])
            x_min, x_max = x_coords.min(), x_coords.max()
            y_min, y_max = y_coords.min(), y_coords.max()
            x_range = x_max - x_min if x_max > x_min else 1.0
            y_range = y_max - y_min if y_max > y_min else 1.0
        else:
            x_min, y_min = 0, 0
            x_range, y_range = 1.0, 1.0

        for node in nodes:
            feat = []

            # 1. 位置特徴（正規化）
            norm_x = (node.x - x_min) / x_range if self.normalize_positions else node.x
            norm_y = (node.y - y_min) / y_range if self.normalize_positions else node.y
            feat.extend([norm_x, norm_y])

            # 2. サイズ特徴
            feat.extend([node.width, node.height])

            # 3. 信頼度
            feat.append(node.confidence)

            # 4. 文字コード特徴（正規化）
            if self.use_char_embedding:
                char_feat = node.char_code / 65536.0  # Unicode範囲で正規化
                feat.append(char_feat)

            # 5. 領域内インデックス（正規化）
            feat.append(node.char_index_in_region / 100.0)  # 通常100文字未満と想定

            # 6. フォント特徴（利用可能な場合）
            if node.font_features is not None:
                feat.extend(node.font_features.tolist())

            features.append(feat)

        features_tensor = torch.FloatTensor(features)
        logger.info(f"Node feature shape: {features_tensor.shape}")
        return features_tensor

    def build_edges_knn(
        self, nodes: List[CharacterNode]
    ) -> Tuple[np.ndarray, np.ndarray]:
        """k近傍法によるエッジ構築"""
        positions = np.array([[n.x, n.y] for n in nodes])

        k = min(self.k_neighbors + 1, len(nodes))
        nbrs = NearestNeighbors(n_neighbors=k, algorithm="ball_tree")
        nbrs.fit(positions)
        distances, indices = nbrs.kneighbors(positions)

        edge_index = []
        edge_attr = []

        for i, (dists, neighbors) in enumerate(zip(distances, indices)):
            for dist, neighbor in zip(dists[1:], neighbors[1:]):  # 自己ループを除外
                edge_index.append([i, neighbor])
                # エッジ特徴: 距離, 角度, 相対位置
                dx = nodes[neighbor].x - nodes[i].x
                dy = nodes[neighbor].y - nodes[i].y
                angle = np.arctan2(dy, dx)
                edge_attr.append([dist, angle, dx, dy])

        return np.array(edge_index).T, np.array(edge_attr)

    def build_edges_delaunay(
        self, nodes: List[CharacterNode]
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Delaunay三角分割によるエッジ構築"""
        positions = np.array([[n.x, n.y] for n in nodes])

        if len(positions) < 3:
            logger.warning(
                "Not enough nodes for Delaunay triangulation, using empty edges"
            )
            return np.array([[], []]), np.array([])

        tri = Delaunay(positions)
        edge_index = set()

        for simplex in tri.simplices:
            for i in range(3):
                v1, v2 = simplex[i], simplex[(i + 1) % 3]
                edge_index.add((min(v1, v2), max(v1, v2)))

        edge_index = list(edge_index)
        edge_attr = []

        for v1, v2 in edge_index:
            dx = nodes[v2].x - nodes[v1].x
            dy = nodes[v2].y - nodes[v1].y
            dist = np.sqrt(dx**2 + dy**2)
            angle = np.arctan2(dy, dx)
            edge_attr.append([dist, angle, dx, dy])

        # 双方向エッジ
        edge_index = np.array(
            [[v1, v2] for v1, v2 in edge_index] + [[v2, v1] for v1, v2 in edge_index]
        ).T
        edge_attr = np.array(edge_attr + edge_attr)

        return edge_index, edge_attr

    def build_edges_directional(
        self, nodes: List[CharacterNode]
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        方向別（上下左右）最近傍によるエッジ構築
        レシートの行構造を考慮
        """
        edge_index = []
        edge_attr = []

        for i, node in enumerate(nodes):
            # 各方向で最も近いノードを探す
            directions = {
                "right": (float("inf"), -1),
                "left": (float("inf"), -1),
                "bottom": (float("inf"), -1),
                "top": (float("inf"), -1),
            }

            for j, other in enumerate(nodes):
                if i == j:
                    continue

                dx = other.x - node.x
                dy = other.y - node.y
                dist = np.sqrt(dx**2 + dy**2)

                # 右方向（同じ行の次の文字）
                if dx > 0 and abs(dy) < node.height * 1.0:  # 高さの範囲内
                    if dist < directions["right"][0]:
                        directions["right"] = (dist, j)

                # 左方向（同じ行の前の文字）
                if dx < 0 and abs(dy) < node.height * 1.0:
                    if dist < directions["left"][0]:
                        directions["left"] = (dist, j)

                # 下方向（次の行）
                if dy > 0 and abs(dx) < node.width * 2.0:  # 幅の範囲内
                    if dist < directions["bottom"][0]:
                        directions["bottom"] = (dist, j)

                # 上方向（前の行）
                if dy < 0 and abs(dx) < node.width * 2.0:
                    if dist < directions["top"][0]:
                        directions["top"] = (dist, j)

            # エッジを追加
            for direction, (dist, j) in directions.items():
                if j != -1:
                    edge_index.append([i, j])
                    dx = nodes[j].x - node.x
                    dy = nodes[j].y - node.y
                    angle = np.arctan2(dy, dx)

                    # 方向エンコーディング (one-hot的に)
                    dir_encoding = [
                        1.0 if direction == "right" else 0.0,
                        1.0 if direction == "left" else 0.0,
                        1.0 if direction == "bottom" else 0.0,
                        1.0 if direction == "top" else 0.0,
                    ]

                    edge_attr.append([dist, angle, dx, dy] + dir_encoding)

        if len(edge_index) == 0:
            return np.array([[], []]), np.array([])

        return np.array(edge_index).T, np.array(edge_attr)

    def build_graph(self, json_path: str, use_metadata: bool = False) -> Data:
        """
        完全なグラフデータを構築

        Args:
            json_path: recognition_results.json または metadata.json のパス
            use_metadata: True の場合 metadata.json として読み込み

        Returns:
            PyTorch Geometric Data オブジェクト
        """
        # ノード読み込み
        if use_metadata:
            nodes = self.load_from_metadata(json_path)
        else:
            nodes = self.load_recognition_results(json_path)

        if len(nodes) == 0:
            raise ValueError("No valid nodes found in input file")

        # ノード特徴量
        x = self.build_node_features(nodes)

        # エッジ構築
        if self.edge_method == "knn":
            edge_index, edge_attr = self.build_edges_knn(nodes)
        elif self.edge_method == "delaunay":
            edge_index, edge_attr = self.build_edges_delaunay(nodes)
        elif self.edge_method == "directional":
            edge_index, edge_attr = self.build_edges_directional(nodes)
        else:
            raise ValueError(f"Unknown edge method: {self.edge_method}")

        edge_index = torch.LongTensor(edge_index)
        edge_attr = torch.FloatTensor(edge_attr)

        # PyTorch Geometric Data オブジェクト作成
        graph_data = Data(
            x=x, edge_index=edge_index, edge_attr=edge_attr, num_nodes=len(nodes)
        )

        # メタデータ保持（デバッグ・可視化用）
        graph_data.chars = [n.char for n in nodes]
        graph_data.char_ids = [n.char_id for n in nodes]
        graph_data.positions = torch.FloatTensor([[n.x, n.y] for n in nodes])
        graph_data.confidences = torch.FloatTensor([n.confidence for n in nodes])
        graph_data.region_ids = torch.LongTensor([n.region_id for n in nodes])

        logger.info(
            f"Graph built: {graph_data.num_nodes} nodes, {edge_index.shape[1]} edges"
        )
        return graph_data

    def save_graph(self, graph: Data, output_path: str):
        """グラフデータを保存"""
        torch.save(graph, output_path)
        logger.info(f"Graph saved to {output_path}")

    def load_graph(self, graph_path: str) -> Data:
        """保存されたグラフを読み込み"""
        graph = torch.load(graph_path)
        logger.info(f"Graph loaded from {graph_path}")
        return graph


if __name__ == "__main__":
    # 使用例
    builder = ReceiptGraphBuilder(
        edge_method="directional",  # レシートの構造を考慮
        k_neighbors=5,
    )

    # メタデータから直接グラフ構築（テスト用）
    metadata_path = "/workspace/data/ocr_output/sample_receipt/metadata.json"
    if Path(metadata_path).exists():
        graph = builder.build_graph(metadata_path, use_metadata=True)

        print(f"ノード数: {graph.num_nodes}")
        print(f"エッジ数: {graph.edge_index.shape[1]}")
        print(f"ノード特徴量次元: {graph.x.shape[1]}")
        print(f"エッジ特徴量次元: {graph.edge_attr.shape[1]}")
        print(f"認識文字列: {''.join(graph.chars)}")

        # グラフ保存
        builder.save_graph(graph, "/workspace/data/graphs/sample_receipt_graph.pt")
