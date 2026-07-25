"""Procedural animation framework for the AI-Avatar-Engine clip library.

Modules:
  rig     — armature/mesh discovery, identity-key guard, bone helpers
  keying  — layered channel buffers -> Blender actions + NLA tracks
  motion  — naturalness generators (breathing, blinks, gaze, noise, ...)
  clips   — clip registry, build/rebuild, NLA/solo/export helpers

See animations/scripts/README.md for the authoring guide.
"""
from . import rig, keying, motion, clips  # noqa: F401
