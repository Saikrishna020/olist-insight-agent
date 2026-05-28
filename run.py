#!/usr/bin/env python
"""Run the olist-insight-agent"""
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(__file__))

from src.app import run_agent

if __name__ == "__main__":
    run_agent("What are the top 5 product categories by number of orders?")
