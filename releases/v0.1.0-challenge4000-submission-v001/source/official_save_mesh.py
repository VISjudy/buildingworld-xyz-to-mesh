"""Organizer-recommended function, transcribed from Submission information.

Source: https://huggingface.co/spaces/BuildingWorld/10thLiDARConference
Retrieved 2026-09-22. Imports added; function behavior unchanged.
"""
import numpy as np
import trimesh


def save_mesh(path, vertices=None, faces=None, face_normals=None):
    if vertices is None or len(vertices) == 0:
        with open(path, "w"):
            pass
        return
    else:
        vertices = np.asarray(vertices)
    if faces is None or len(faces) == 0:
        with open(path, "w"):
            pass
        return
    else:
        faces = np.asarray(faces)
    mesh = trimesh.Trimesh(vertices=vertices, faces=faces, process=False)
    if face_normals is not None and len(face_normals) == len(faces):
        mesh.face_normals = np.asarray(face_normals, dtype=np.float64)
    mesh.export(path)
