# API Call Stack for `http://0.0.0.0:8000/api/v1/bible/?passage=Luke%2018`

## Overview
This document outlines the call stack for the API call to retrieve Bible verses for the specified passage. The API call takes more than 1.5 seconds, while the internal call to dbt takes only 0.3 seconds.

## Call Stack
1. **API Endpoint**: `/api/v1/bible/`
   - **Parameters**: `passage=Luke 18`
   - **Total Time**: 1.5 seconds

2. **View Function**: `views.py` - `get_bible_passage()`
   - **Description**: Handles the incoming request and processes the passage.
   - **Time Taken**: TBD (now profiled with timing logs)

3. **Serializer**: `serializers.py` - `BiblePassageSerializer.to_representation()`
   - **Description**: Serializes the data for the response, calls DBT API.
   - **Time Taken**: TBD (now profiled with timing logs)

4. **DBT Call**: `dbt_integration_test.py` - `call_dbt()`
   - **Description**: Calls the dbt service to fetch additional data.
   - **Time Taken**: 0.3 seconds (now profiled)

5. **Response Construction**: `views.py` - `construct_response()`
   - **Description**: Constructs the final response to be sent back to the client.
   - **Time Taken**: TBD

## Profiling Methods Added
- Added timing logs to `BiblePassageView.get()` method
- Added timing logs to `BiblePassageSerializer.to_representation()` method
- Added timing logs for the DBT API call within the serializer

## Additional Profiling Options
1. **Django Debug Toolbar**: Install and configure for detailed request profiling
   ```bash
   pip install django-debug-toolbar
   # Add to INSTALLED_APPS and configure in settings.py
   ```

2. **cProfile Script**: Use the provided `profile_api.py` script
   ```bash
   python profile_api.py
   ```

3. **Line Profiler**: For line-by-line profiling of specific functions
   ```bash
   pip install line-profiler
   # Add @profile decorator to functions and run:
   kernprof -l -v your_script.py
   ```

4. **Django Profiling Middleware**: Custom middleware to profile all requests

## How to Run Profiling
1. **Basic Timing Logs**: The code now includes timing logs. Run the server and make API calls to see logs in the console/logs.

2. **cProfile**: Run `python profile_api.py` to get detailed function-level profiling.

3. **Django Debug Toolbar**: Install and access the toolbar in your browser for visual profiling.

## Expected Output
After running a profiled API call, you should see logs like:
```
INFO - DBT call time: 0.300s
INFO - Serializer to_representation time: 0.350s
INFO - API call timing - Total: 1.520s, Serializer: 0.350s
```

This will help identify where the remaining ~1.2 seconds are being spent.

## Profiling Results
After running the profiling script, here are the actual timings:

- **DBT API Call**: 1.126 seconds
- **Serializer to_representation**: 1.127 seconds  
- **Total API Call**: 1.131 seconds
- **Middleware overhead**: ~0.3 seconds (from cProfile)

### Key Findings
1. The DBT API call is taking **1.126 seconds**, not 0.3 seconds as initially stated
2. The serializer processing adds minimal overhead (~0.001 seconds)
3. The total request time is **1.131 seconds**
4. Django middleware and framework overhead account for the remaining time

### cProfile Top Functions
```
bible/services/dbt/client.py:203(get_verses) - 1.126s
bible/serializers.py:29(to_representation) - 1.127s  
bible/views.py:27(get) - 1.131s
bible_research/middleware.py:16(__call__) - 1.425s
```

## Root Cause Analysis
The bottleneck is the **DBT API call** itself, which is taking over 1 second. This suggests:
- Network latency to DBT servers
- DBT API processing time
- Potential rate limiting or API performance issues
- No local caching of Bible verses

## Recommendations
1. **Implement caching**: Cache DBT responses locally to avoid repeated API calls
2. **Async processing**: Consider making DBT calls asynchronous
3. **Local database**: Store frequently accessed verses in local database
4. **CDN**: Use a CDN for static Bible content
5. **API optimization**: Check if DBT offers faster endpoints or bulk operations