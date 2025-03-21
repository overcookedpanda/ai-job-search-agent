import socket
import time
import logging
import threading
import traceback
from prometheus_client import REGISTRY
from prometheus_remote_writer import RemoteWriter

logger = logging.getLogger(__name__)


class RemoteWriteManager:
    """Handles pushing Prometheus metrics to a Grafana Cloud remote write endpoint."""

    def __init__(self, remote_url=None, username=None, password=None, job_name='ai_interview_prep',
                 push_interval=15, instance_name=None):
        """
        Initialize the remote write manager.

        Args:
            remote_url: URL for the Prometheus remote write endpoint
            username: Username for basic auth (typically Grafana Cloud instance ID)
            password: Password for basic auth (typically Grafana Cloud API key)
            job_name: Job name for metrics (default: ai_interview_prep)
            push_interval: How often to push metrics in seconds (default: 15)
            instance_name: Unique identifier for this instance (default: hostname)
        """
        self.remote_url = remote_url
        self.username = username
        self.password = password
        self.job_name = job_name
        self.push_interval = push_interval
        self.instance_name = instance_name or socket.gethostname()
        self.running = False
        self.thread = None

        # Log configuration
        if self.remote_url:
            logger.info(f"Configured Prometheus remote write to {self.remote_url} as job {self.job_name}")
        else:
            logger.info("Prometheus remote write not configured")

    def start(self):
        """Start the background thread to push metrics periodically."""
        if not self.remote_url:
            logger.warning("No remote_url configured, not starting remote write thread")
            return

        if self.running:
            logger.warning("Remote write thread already running")
            return

        self.running = True
        self.thread = threading.Thread(target=self._push_metrics_loop, daemon=True)
        self.thread.start()
        logger.info(f"Started Prometheus metrics push thread (interval: {self.push_interval}s)")

    def stop(self):
        """Stop the background thread."""
        if not self.running:
            return

        self.running = False
        if self.thread:
            self.thread.join(timeout=5.0)
            logger.info("Stopped Prometheus metrics push thread")

    def _push_metrics_loop(self):
        """Background thread that periodically pushes metrics."""
        while self.running:
            try:
                self._push_metrics()
            except Exception as e:
                logger.error(f"Error pushing metrics: {str(e)}")
                logger.error(f"Traceback: {traceback.format_exc()}")

            # Sleep until next interval
            time.sleep(self.push_interval)

    def _push_metrics(self):
        """Push metrics to the remote endpoint using prometheus-remote-writer."""
        try:
            logger.info(f"Pushing metrics to {self.remote_url} using remote write protocol")

            # Set up auth headers if credentials are provided
            headers = {}
            if self.username and self.password:
                import base64
                auth_string = f"{self.username}:{self.password}"
                encoded_auth = base64.b64encode(auth_string.encode()).decode()
                headers['Authorization'] = f'Basic {encoded_auth}'
                logger.info(f"Added authentication header for user {self.username}")

            # Create a RemoteWriter instance
            writer = RemoteWriter(
                url=self.remote_url,
                headers=headers
            )

            # Extract and convert metrics from the Prometheus registry
            current_time_ms = int(time.time() * 1000)
            data = []

            # Collect and convert all metrics from the registry
            for metric_family in REGISTRY.collect():
                for metric in metric_family.samples:
                    # Create a metadata object with labels
                    metadata = {'__name__': metric.name}

                    # Add all labels from the metric
                    for label_name, label_value in metric.labels.items():
                        metadata[label_name] = label_value

                    # Add job and instance labels if not present
                    if 'job' not in metadata:
                        metadata['job'] = self.job_name
                    if 'instance' not in metadata:
                        metadata['instance'] = self.instance_name

                    # Create the metric entry
                    entry = {
                        'metric': metadata,
                        'values': [float(metric.value)],
                        'timestamps': [current_time_ms]
                    }

                    data.append(entry)

            # Log the number of metrics being sent
            logger.info(f"Sending {len(data)} metrics to remote write endpoint")

            # Send the data
            if data:
                writer.send(data)
                logger.info("Successfully pushed metrics to remote write endpoint")
            else:
                logger.warning("No metrics found to send")

        except Exception as e:
            logger.error(f"Failed to push metrics: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise