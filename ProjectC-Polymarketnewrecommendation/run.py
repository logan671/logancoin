#!/usr/bin/env python3
"""
Polymarket Alpha Scanner - Quick Run Script
"""
import sys
import os

# 프로젝트 루트를 path에 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.main import main

if __name__ == "__main__":
    main()
