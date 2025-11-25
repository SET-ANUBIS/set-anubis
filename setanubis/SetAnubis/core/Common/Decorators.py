import time
from functools import wraps

def timing_decorator(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        elapsed_time = end_time - start_time
        print(f"Function {func.__name__} took {elapsed_time:.4f} seconds to complete.")
        return result
    return wrapper


import logging
from functools import wraps

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

def log_decorator(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        logging.debug(f"Calling function {func.__name__} with args: {args}, kwargs: {kwargs}")
        result = func(*args, **kwargs)
        logging.debug(f"Function {func.__name__} returned {result}")
        return result
    return wrapper


def validate_inputs(expected_types):
    """
    Validate the input types of a function.
    
    :param expected_types: A tuple of expected types for each argument.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for arg, expected_type in zip(args, expected_types):
                if not isinstance(arg, expected_type):
                    raise TypeError(f"Expected type {expected_type} but got {type(arg)}")
            return func(*args, **kwargs)
        return wrapper
    return decorator

def memoize(func):
    cache = {}
    
    @wraps(func)
    def wrapper(*args):
        if args in cache:
            return cache[args]
        result = func(*args)
        cache[args] = result
        return result
    
    return wrapper


def exception_handler_decorator(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            print(f"An error occurred in function {func.__name__}: {e}")
            raise
    return wrapper

def tracing_decorator(func):
    """
    Trace the function call, including its arguments and return value.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        print(f"Entering {func.__name__} with arguments: {args} and keyword arguments: {kwargs}")
        result = func(*args, **kwargs)
        print(f"Exiting {func.__name__} with result: {result}")
        return result
    return wrapper


def retry_decorator(max_retries=3, delay=1):
    """
    Retry the function execution in case of failure.
    
    :param max_retries: Maximum number of retries.
    :param delay: Delay between retries in seconds.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            attempts = 0
            while attempts < max_retries:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    print(f"Attempt {attempts+1} failed: {e}")
                    attempts += 1
                    time.sleep(delay)
            raise Exception(f"Function {func.__name__} failed after {max_retries} attempts.")
        return wrapper
    return decorator


def time_based_cache(expiration_time=60):
    """
    Cache the function result for a specified amount of time.
    
    :param expiration_time: Time in seconds before the cache expires.
    """
    def decorator(func):
        cache = {}
        cache_time = {}

        @wraps(func)
        def wrapper(*args):
            current_time = time.time()
            if args in cache and current_time - cache_time[args] < expiration_time:
                return cache[args]
            result = func(*args)
            cache[args] = result
            cache_time[args] = current_time
            return result
        return wrapper
    return decorator


def return_type_checker(expected_type):
    """
    Check that the return type of the function matches the expected type.
    
    :param expected_type: The expected return type.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            if not isinstance(result, expected_type):
                raise TypeError(f"Expected return type {expected_type}, but got {type(result)}")
            return result
        return wrapper
    return decorator
