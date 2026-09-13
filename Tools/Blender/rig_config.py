"""Shared paths and names for the fighter rig pipeline."""
import os

TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_DIR = os.path.abspath(os.path.join(TOOLS_DIR, os.pardir, os.pardir))
MODELS_DIR = os.path.join(REPO_DIR, "Resources", "Models")

SOURCE_FBX = os.path.join(MODELS_DIR, "Fighter.fbx")
# Set OPEN_STANCE_RIG_OUTPUT to write somewhere other than Resources/Models (e.g. for a test run).
OUTPUT_DIR = os.environ.get("OPEN_STANCE_RIG_OUTPUT", MODELS_DIR)
OUTPUT_NAME = "Fighter_Rigged"
OUTPUT_BLEND = os.path.join(OUTPUT_DIR, OUTPUT_NAME + ".blend")
OUTPUT_FBX = os.path.join(OUTPUT_DIR, OUTPUT_NAME + ".fbx")

LOG_DIR = os.path.join(TOOLS_DIR, "logs")

ARMATURE_NAME = "Armature"  # UE drops an FBX armature node with this name, leaving "root" as the root bone
MESH_NAME = "SK_Fighter"


def open_log(name):
    """Return a print-like function that writes to logs/<name>.txt (and stdout)."""
    os.makedirs(LOG_DIR, exist_ok=True)
    f = open(os.path.join(LOG_DIR, name + ".txt"), "w", encoding="utf-8")

    def log(*args):
        print(*args, file=f)
        f.flush()
        print(*args)

    log.close = f.close
    return log
