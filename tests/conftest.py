import os
import sys
from pathlib import Path

# Ensure root directory is on sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Ensure Java and PySpark Python binaries are set
java_home = r"C:\Program Files\Java\jdk-17"
if os.path.exists(java_home):
    os.environ["JAVA_HOME"] = java_home

os.environ["PYSPARK_PYTHON"] = sys.executable
os.environ["PYSPARK_DRIVER_PYTHON"] = sys.executable
os.environ["TESTING"] = "1"
