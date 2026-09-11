from __future__ import annotations

from typing import Any

from bs4 import BeautifulSoup, NavigableString, Tag

from benchmarks.metrics.ocr_eval import levenshtein_distance


class TableTree:
    """Represents a node in the table tree structure for TEDS computation."""

    def __init__(self, tag: str, text: str | None = None, attributes: dict[str, Any] | None = None):
        self.tag = tag
        self.text = text or ""
        self.attributes = attributes or {}
        self.children: list[TableTree] = []

    def add_child(self, child: TableTree) -> None:
        self.children.append(child)

    def size(self) -> int:
        """Total number of nodes in the subtree rooted at this node."""
        return 1 + sum(child.size() for child in self.children)


class TEDS:
    """Tree-Edit-Distance-based Similarity (TEDS) metric for table structure and content evaluation.

    Formula:
        TEDS(T_pred, T_true) = 1.0 - (TreeEditDistance(T_pred, T_true) / max(size(T_pred), size(T_true)))
    """

    def __init__(self, structure_only: bool = False, ignore_case: bool = True):
        self.structure_only = structure_only
        self.ignore_case = ignore_case

    def html_to_tree(self, html_str: str) -> TableTree:
        """Convert an HTML table string into a TableTree hierarchy."""
        soup = BeautifulSoup(html_str, "html.parser")
        table = soup.find("table")
        if not table:
            # Fallback wrapper if string lacks <table> tag
            table = soup

        def _build_node(elem: Tag | NavigableString) -> TableTree | None:
            if isinstance(elem, NavigableString):
                text = str(elem).strip()
                if not text:
                    return None
                return TableTree(tag="text", text=text)

            tag_name = elem.name
            attrs = {}
            if "colspan" in elem.attrs:
                attrs["colspan"] = elem.attrs["colspan"]
            if "rowspan" in elem.attrs:
                attrs["rowspan"] = elem.attrs["rowspan"]

            node = TableTree(tag=tag_name, attributes=attrs)
            for child in elem.children:
                child_node = _build_node(child)
                if child_node is not None:
                    node.add_child(child_node)
            return node

        root = _build_node(table)
        return root or TableTree(tag="table")

    def _node_distance(self, node_a: TableTree, node_b: TableTree) -> float:
        """Calculate substitution cost between two individual tree nodes."""
        if node_a.tag != node_b.tag:
            return 1.0

        if node_a.attributes != node_b.attributes:
            return 1.0

        if self.structure_only:
            return 0.0

        # For text nodes and table cells, evaluate string similarity
        if node_a.text or node_b.text:
            text_a = node_a.text.lower() if self.ignore_case else node_a.text
            text_b = node_b.text.lower() if self.ignore_case else node_b.text
            max_len = max(len(text_a), len(text_b))
            if max_len == 0:
                return 0.0
            edit_dist = levenshtein_distance(text_a, text_b)
            return float(edit_dist / max_len)

        return 0.0

    def tree_edit_distance(self, tree_a: TableTree, tree_b: TableTree) -> float:
        """Compute recursive tree edit distance between two TableTree instances with rolling DP memory."""
        memo: dict[tuple[int, int], float] = {}

        def _ted(n1: TableTree, n2: TableTree) -> float:
            key = (id(n1), id(n2))
            if key in memo:
                return memo[key]

            cost = self._node_distance(n1, n2)

            # Match children via sequence alignment DP
            m, n = len(n1.children), len(n2.children)
            if m == 0 and n == 0:
                return cost
            if m == 0:
                return cost + sum(c.size() for c in n2.children)
            if n == 0:
                return cost + sum(c.size() for c in n1.children)

            # Match children via 2-row rolling sequence alignment
            prev_dp = [0.0] * (n + 1)
            for j in range(1, n + 1):
                prev_dp[j] = prev_dp[j - 1] + n2.children[j - 1].size()
            curr_dp = [0.0] * (n + 1)
            for i in range(1, m + 1):
                child_a = n1.children[i - 1]
                curr_dp[0] = prev_dp[0] + child_a.size()
                for j in range(1, n + 1):
                    child_b = n2.children[j - 1]
                    sub_cost = _ted(child_a, child_b)
                    curr_dp[j] = min(
                        prev_dp[j] + child_a.size(),  # delete child_a
                        curr_dp[j - 1] + child_b.size(),  # insert child_b
                        prev_dp[j - 1] + sub_cost,  # match/substitute
                    )
                prev_dp, curr_dp = curr_dp, prev_dp

            total_dist = cost + prev_dp[n]
            memo[key] = total_dist
            return total_dist

        return _ted(tree_a, tree_b)

    def evaluate(self, pred_html: str, true_html: str) -> float:
        """Calculate TEDS score between predicted and ground truth HTML tables."""
        tree_pred = self.html_to_tree(pred_html)
        tree_true = self.html_to_tree(true_html)

        size_pred = tree_pred.size()
        size_true = tree_true.size()
        max_size = max(size_pred, size_true)

        if max_size == 0:
            return 1.0

        ted = self.tree_edit_distance(tree_pred, tree_true)
        teds_score = 1.0 - (ted / max_size)
        return max(0.0, min(1.0, float(teds_score)))
