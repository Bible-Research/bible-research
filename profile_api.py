#!/usr/bin/env python
"""
Script to profile the Bible API endpoint using cProfile.
Run this script to get detailed profiling information.
"""
import cProfile
import pstats
import io
from django.test import Client
from django.conf import settings
import os
import sys

# Add the project directory to the Python path
sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bible_research.settings')

import django
django.setup()

def profile_api_call():
    """Profile a single API call to the Bible endpoint."""
    client = Client()
    # Profile the API call
    pr = cProfile.Profile()
    pr.enable()

    # Make the API call
    response = client.get('/api/v1/bible/?passage=Luke%2018')

    pr.disable()

    # Print profiling results
    s = io.StringIO()
    ps = pstats.Stats(pr, stream=s).sort_stats('cumulative')
    ps.print_stats(20)  # Top 20 functions by cumulative time
    print("Profiling Results:")
    print(s.getvalue())

    print(f"Response status: {response.status_code}")
    print(f"Response time would be logged in the application logs")

if __name__ == '__main__':
    profile_api_call()