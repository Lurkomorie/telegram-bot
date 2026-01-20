#!/usr/bin/env python3
"""
Detailed refresh analysis
"""
import os
from datetime import datetime, timedelta
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker
from app.db.models import TgAnalyt