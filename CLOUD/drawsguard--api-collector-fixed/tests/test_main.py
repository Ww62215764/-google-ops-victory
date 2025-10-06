from unittest.mock import patch, MagicMock
import json
import logging
from fastapi import BackgroundTasks, HTTPException

# 将应用目录添加到sys.path，以便pytest可以找到main模块
import sys
