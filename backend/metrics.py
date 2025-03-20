from prometheus_client import Counter, Gauge, Histogram, Summary, Info
import time

# Define metrics
api_requests_total = Counter(
    'api_requests_total',
    'Total count of API requests',
    ['endpoint', 'method', 'status']
)

api_request_duration = Histogram(
    'api_request_duration_seconds',
    'API request duration in seconds',
    ['endpoint', 'method'],
    buckets=(0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0, float("inf"))
)

openai_api_tokens_total = Counter(
    'openai_api_tokens_total',
    'Total tokens used in OpenAI API calls',
    ['model', 'type']  # type can be 'input' or 'output'
)

openai_api_cost_total = Counter(
    'openai_api_cost_total',
    'Estimated cost in USD for OpenAI API usage',
    ['model']
)

openai_api_calls_total = Counter(
    'openai_api_calls_total',
    'Total number of OpenAI API calls',
    ['model', 'endpoint']
)

backend_info = Info('backend_info', 'Information about the backend service')

# Define pricing for OpenAI models (per 1000000 tokens as of March 2025)
# Update these values as pricing changes
MODEL_PRICING = {
    'gpt-4o-mini': {
        'input': 0.15,  # $0.15 per 1000000 input tokens
        'output': 0.60,  # $0.60 per 1000000 output tokens
    },
    'gpt-3.5-turbo': {
        'input': 0.50,  # $0.01 per 1000000 input tokens
        'output': 1.50,  # $0.02 per 1000000 output tokens
    },
    'gpt-4o': {
        'input': 2.50,  # $0.50 per 1000000 input tokens
        'output': 10.00,  # $1.50 per 1000000 output tokens
    },
    # Add other models as needed
}

# Default values for unknown models
DEFAULT_PRICING = {
    'input': 2.50,
    'output': 10.00,
}


def track_openai_usage(model_name, input_tokens, output_tokens):
    """
    Track OpenAI API usage and estimated cost

    Args:
        model_name: Name of the OpenAI model used
        input_tokens: Number of tokens in the input
        output_tokens: Number of tokens in the output
    """
    # Get pricing for the model or use default
    pricing = MODEL_PRICING.get(model_name, DEFAULT_PRICING)

    # Calculate costs
    input_cost = (input_tokens / 1000000) * pricing['input']
    output_cost = (output_tokens / 1000000) * pricing['output']
    total_cost = input_cost + output_cost

    # Update metrics
    openai_api_tokens_total.labels(model=model_name, type='input').inc(input_tokens)
    openai_api_tokens_total.labels(model=model_name, type='output').inc(output_tokens)
    openai_api_cost_total.labels(model=model_name).inc(total_cost)
    openai_api_calls_total.labels(model=model_name, endpoint='output').inc()


def init_metrics():
    """Initialize metrics with static information"""
    backend_info.info({
        'version': '1.0.0',
        'start_time': str(time.time())
    })


class MetricsMiddleware:
    """Middleware to track API request metrics"""

    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        path = environ.get('PATH_INFO', '')
        method = environ.get('REQUEST_METHOD', '')

        # Skip metrics endpoint to avoid recursion
        if path == '/metrics':
            return self.app(environ, start_response)

        start_time = time.time()

        def custom_start_response(status, headers, exc_info=None):
            status_code = status.split(' ')[0]
            api_requests_total.labels(
                endpoint=path,
                method=method,
                status=status_code
            ).inc()

            duration = time.time() - start_time
            api_request_duration.labels(
                endpoint=path,
                method=method
            ).observe(duration)

            return start_response(status, headers, exc_info)

        return self.app(environ, custom_start_response)