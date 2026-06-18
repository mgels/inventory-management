"""
Tests for restocking API endpoints (recommendations and order submission).
"""
import pytest


class TestRestockingRecommendations:
    """Test suite for GET /api/restocking/recommendations."""

    def test_recommendations_structure(self, client):
        """Test that the recommendations response has the expected structure."""
        response = client.get("/api/restocking/recommendations?budget=5000")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, dict)
        assert "recommendations" in data
        assert "total_cost" in data
        assert "max_budget" in data
        assert isinstance(data["recommendations"], list)
        assert isinstance(data["total_cost"], (int, float))
        assert isinstance(data["max_budget"], (int, float))

    def test_recommendation_item_fields(self, client):
        """Test that each recommendation has the required fields."""
        response = client.get("/api/restocking/recommendations?budget=10000")
        data = response.json()

        assert len(data["recommendations"]) > 0
        for rec in data["recommendations"]:
            assert "sku" in rec
            assert "name" in rec
            assert "trend" in rec
            assert "quantity" in rec
            assert "unit_cost" in rec
            assert "line_total" in rec
            assert "lead_time_days" in rec
            assert rec["quantity"] > 0

    def test_recommendations_respect_budget(self, client):
        """Test that total cost never exceeds the requested budget."""
        for budget in [0, 500, 2000, 5000, 100000]:
            response = client.get(f"/api/restocking/recommendations?budget={budget}")
            data = response.json()
            assert data["total_cost"] <= budget + 0.01, f"budget={budget}"

    def test_zero_gap_items_excluded(self, client):
        """Items with no demand gap (e.g. decreasing trend) must never be recommended."""
        # MTR-304 has forecasted < current (decreasing) -> gap 0 -> excluded
        response = client.get("/api/restocking/recommendations?budget=1000000")
        data = response.json()
        skus = [rec["sku"] for rec in data["recommendations"]]
        assert "MTR-304" not in skus

    def test_increasing_trend_prioritized(self, client):
        """With a tight budget, increasing-trend items are recommended before stable ones."""
        # Small budget should be consumed by increasing-trend (priority) items first.
        response = client.get("/api/restocking/recommendations?budget=1500")
        data = response.json()
        recs = data["recommendations"]
        assert len(recs) > 0
        # The first recommendation should be an increasing-trend item.
        assert recs[0]["trend"] == "increasing"

    def test_line_total_matches_quantity_times_cost(self, client):
        """Each line total should equal quantity * unit_cost."""
        response = client.get("/api/restocking/recommendations?budget=10000")
        data = response.json()
        for rec in data["recommendations"]:
            assert abs(rec["line_total"] - rec["quantity"] * rec["unit_cost"]) < 0.01

    def test_total_cost_matches_sum_of_lines(self, client):
        """total_cost should equal the sum of all recommendation line totals."""
        response = client.get("/api/restocking/recommendations?budget=8000")
        data = response.json()
        line_sum = sum(rec["line_total"] for rec in data["recommendations"])
        assert abs(data["total_cost"] - line_sum) < 0.01

    def test_zero_budget_returns_no_recommendations(self, client):
        """A zero budget should yield no recommendations and zero cost."""
        response = client.get("/api/restocking/recommendations?budget=0")
        data = response.json()
        assert data["recommendations"] == []
        assert data["total_cost"] == 0

    def test_max_budget_is_positive(self, client):
        """max_budget reflects the cost to restock every gap and should be positive."""
        response = client.get("/api/restocking/recommendations?budget=0")
        data = response.json()
        assert data["max_budget"] > 0


class TestRestockingOrderSubmission:
    """Test suite for POST /api/restocking/orders."""

    def _sample_payload(self):
        return {
            "items": [
                {
                    "sku": "WDG-001",
                    "name": "Industrial Widget Type A",
                    "quantity": 10,
                    "unit_cost": 45.0,
                    "lead_time_days": 14,
                },
                {
                    "sku": "FLT-405",
                    "name": "Oil Filter Cartridge",
                    "quantity": 20,
                    "unit_cost": 8.0,
                    "lead_time_days": 5,
                },
            ]
        }

    def test_submit_order_returns_created(self, client):
        """Test that submitting a restocking order returns 201 with a valid order."""
        response = client.post("/api/restocking/orders", json=self._sample_payload())
        assert response.status_code == 201

        order = response.json()
        assert order["status"] == "Submitted"
        assert order["customer"] == "Internal Restock"
        assert order["order_number"].startswith("RST-")
        assert len(order["items"]) == 2

    def test_submit_order_total_value(self, client):
        """Test that the order total_value equals the sum of line totals."""
        response = client.post("/api/restocking/orders", json=self._sample_payload())
        order = response.json()
        expected = 10 * 45.0 + 20 * 8.0
        assert abs(order["total_value"] - expected) < 0.01

    def test_submit_order_lead_time_is_max(self, client):
        """Order-level lead time should be the maximum item lead time."""
        response = client.post("/api/restocking/orders", json=self._sample_payload())
        order = response.json()
        assert order["lead_time_days"] == 14

    def test_submitted_order_appears_in_orders(self, client):
        """Test that a submitted order then appears in GET /api/orders."""
        post_response = client.post("/api/restocking/orders", json=self._sample_payload())
        created = post_response.json()

        list_response = client.get("/api/orders")
        assert list_response.status_code == 200
        orders = list_response.json()

        matching = [o for o in orders if o["order_number"] == created["order_number"]]
        assert len(matching) == 1
        assert matching[0]["status"] == "Submitted"

    def test_submitted_order_filterable_by_status(self, client):
        """Submitted orders should be retrievable via the status filter."""
        client.post("/api/restocking/orders", json=self._sample_payload())
        response = client.get("/api/orders?status=Submitted")
        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0
        for order in data:
            assert order["status"].lower() == "submitted"

    def test_order_items_use_unit_price_key(self, client):
        """Submitted order items must use unit_price to match the Orders table contract."""
        response = client.post("/api/restocking/orders", json=self._sample_payload())
        order = response.json()
        for item in order["items"]:
            assert "unit_price" in item
            assert "quantity" in item
            assert "lead_time_days" in item

    def test_submit_empty_items_rejected(self, client):
        """Submitting with no items should return a 400 error."""
        response = client.post("/api/restocking/orders", json={"items": []})
        assert response.status_code == 400
        assert "detail" in response.json()

    def test_submit_invalid_payload_rejected(self, client):
        """A payload missing required item fields should fail validation (422)."""
        bad_payload = {"items": [{"sku": "WDG-001"}]}
        response = client.post("/api/restocking/orders", json=bad_payload)
        assert response.status_code == 422
