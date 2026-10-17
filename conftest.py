import os
import tempfile

# Must run before `main` is imported, so test errors never touch the real log.
os.environ["SHOP_LOG_PATH"] = os.path.join(tempfile.mkdtemp(), "app.log")