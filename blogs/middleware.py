from django.db import connection
from django.shortcuts import render
from django.urls import resolve, Resolver404
from django.conf import settings

import time
import threading
from collections import defaultdict
from contextlib import contextmanager
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError


request_metrics = defaultdict(list)

# Thread-local storage for query times
_local = threading.local()

@contextmanager
def track_db_time():
    _local.db_time = 0.0
    def execute_wrapper(execute, sql, params, many, context):
        start = time.time()
        try:
            return execute(sql, params, many, context)
        finally:
            _local.db_time += time.time() - start
    
    with connection.execute_wrapper(execute_wrapper):
        yield
        

class RequestPerformanceMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.skip_methods = {'HEAD', 'OPTIONS'}

    def get_pattern_name(self, request):
        if request.method in self.skip_methods:
            return None
            
        try:
            resolver_match = getattr(request, 'resolver_match', None) or resolve(request.path)
            # Normalize all feed endpoints to a single path
            if resolver_match.func.__name__ == 'feed':
                return f"{request.method} feed/"
            return f"{request.method} {resolver_match.route}"
        except Resolver404:
            return None
        
    def __call__(self, request):
        endpoint = self.get_pattern_name(request)
        if endpoint is None:
            return self.get_response(request)

        start_time = time.time()
        
        with track_db_time():
            response = self.get_response(request)
            db_time = getattr(_local, 'db_time', 0.0)

        total_time = time.time() - start_time
        
        # Direct write to shared dictionary without locks
        metrics = request_metrics[endpoint]
        metrics.append({
            'total_time': total_time,
            'db_time': db_time,
            'compute_time': total_time - db_time,
            'timestamp': start_time
        })
        
        # Non-thread-safe list trimming
        if len(metrics) > 50:
            del metrics[:-50]

        return response
    

class TimeoutMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        # Set lower than Gunicorn's timeout to ensure we respond first
        self.timeout = 20
        # Share executor across requests instead of creating per instance
        self._executor = None

    @property
    def executor(self):
        if self._executor is None:
            # Use more workers to handle concurrent requests
            self._executor = ThreadPoolExecutor(max_workers=4)
        return self._executor

    def __call__(self, request):
        try:
            future = self.executor.submit(self.get_response, request)
            response = future.result(timeout=self.timeout)
            return response
        except (TimeoutError, FuturesTimeoutError):
            future.cancel()
            return render(request, '503.html', status=503)
        except Exception:
            return render(request, '503.html', status=503)