"""Tests for WorldGrid, Tile, Resource, Building."""

import sys
sys.path.insert(0, "..")

from engine.world import WorldGrid, Tile, Resource, Building, BuildingType, Terrain


def test_world_creation():
    world = WorldGrid(10, 10, seed=1)
    assert world.width == 10
    assert world.height == 10
    assert len(world.tiles) == 100


def test_tile_passability():
    tile_ground = Tile(0, 0, terrain=Terrain.GROUND)
    tile_water = Tile(0, 0, terrain=Terrain.WATER)
    tile_mountain = Tile(0, 0, terrain=Terrain.MOUNTAIN)
    assert tile_ground.is_passable
    assert not tile_water.is_passable
    assert not tile_mountain.is_passable


def test_resource_take():
    r = Resource("food", 5)
    taken = r.take(3)
    assert taken == 3
    assert r.quantity == 2
    taken2 = r.take(10)
    assert taken2 == 2
    assert r.quantity == 0


def test_tile_get_resource():
    tile = Tile(0, 0)
    tile.resources.append(Resource("food", 3))
    tile.resources.append(Resource("wood", 0))
    assert tile.get_resource("food") is not None
    assert tile.get_resource("wood") is None  # quantity 0
    assert tile.get_resource("stone") is None


def test_neighbors():
    world = WorldGrid(10, 10, seed=1)
    neighbors = world.get_neighbors(5, 5, radius=1)
    assert len(neighbors) == 8  # 3x3 minus center
    neighbors_r2 = world.get_neighbors(5, 5, radius=2)
    assert len(neighbors_r2) == 24  # 5x5 minus center


def test_corner_neighbors():
    world = WorldGrid(10, 10, seed=1)
    neighbors = world.get_neighbors(0, 0, radius=1)
    assert len(neighbors) == 3  # only 3 valid neighbors at corner


def test_passable_neighbors():
    world = WorldGrid(50, 50, seed=42)
    passable = world.get_passable_neighbors(25, 25)
    for tile in passable:
        assert tile.is_passable


def test_find_random_passable():
    world = WorldGrid(10, 10, seed=1)
    for _ in range(20):
        tile = world.find_random_passable_tile()
        assert tile.is_passable


def test_place_building():
    world = WorldGrid(10, 10, seed=1)
    bt = BuildingType("farm", {"wood": 5}, 3, "food")
    building = Building(type=bt, owner_id="agent1")
    tile = world.find_random_passable_tile()
    assert world.place_building(tile.x, tile.y, building)
    assert world.get_tile(tile.x, tile.y).building is not None
    # Can't place on same tile
    assert not world.place_building(tile.x, tile.y, Building(type=bt))


def test_world_stats():
    world = WorldGrid(10, 10, seed=1)
    stats = world.stats()
    assert "total_resources" in stats
    assert "buildings" in stats
    assert "terrain" in stats
    assert stats["buildings"] == 0


def test_resource_regen():
    world = WorldGrid(10, 10, seed=1)
    initial = world.stats()["total_resources"]
    config = [{"name": "food", "regen_rate": 1.0, "max_per_tile": 5}]
    world.regenerate_resources(config)
    after = world.stats()["total_resources"]
    assert after >= initial
