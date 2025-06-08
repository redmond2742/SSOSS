from ssoss.dynamic_road_object import *
from ssoss.motion_road_object import *
from ssoss.process_road_objects import *
from ssoss.process_video import *
from ssoss.static_road_object import *
import importlib.metadata
try:
    from icecream import install
    install()
except Exception:
    # icecream is an optional dependency used for debugging. Avoid failing
    # if it isn't installed when running in minimal environments such as tests.
    pass

__version__ = importlib.metadata.version("ssoss")

