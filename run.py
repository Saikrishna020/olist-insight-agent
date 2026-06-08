#!/usr/bin/env python
"""Run the olist-insight-agent"""

from src.app import run_agent

if __name__ == "__main__":
    run_agent("What are the top 5 product categories by number of orders?")
