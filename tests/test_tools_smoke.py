"""Smoke tests for the geometry, mesh and UI toolchain (versions pinned in pyproject.toml)."""

import pytest


def test_cadquery_box_volume():
    import cadquery as cq

    box = cq.Workplane("XY").box(10.0, 20.0, 30.0)
    assert box.val().Volume() == pytest.approx(6000.0, rel=1e-9)


def test_gmsh_meshes_a_box():
    import gmsh

    gmsh.initialize()
    try:
        gmsh.option.setNumber("General.Terminal", 0)
        gmsh.model.add("box")
        gmsh.model.occ.addBox(0.0, 0.0, 0.0, 1.0, 1.0, 1.0)
        gmsh.model.occ.synchronize()
        gmsh.option.setNumber("Mesh.MeshSizeMax", 0.25)
        gmsh.model.mesh.generate(3)
        _, element_tags, _ = gmsh.model.mesh.getElements(3)
        assert sum(len(tags) for tags in element_tags) > 0
        assert gmsh.model.occ.getMass(3, 1) == pytest.approx(1.0)
    finally:
        gmsh.finalize()


def test_streamlit_imports():
    import streamlit

    assert streamlit.__version__ == "1.65.0"
