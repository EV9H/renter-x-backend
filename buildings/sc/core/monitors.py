from datetime import datetime
import logging
from typing import Optional, Dict, Any
import json
from dataclasses import dataclass, asdict
import statistics
from django.core.mail import send_mail
from django.conf import settings
import asyncio
from collections import defaultdict
from django.utils import timezone
from colorama import init, Fore, Style
import sys
init()
logger = logging.getLogger(__name__)

@dataclass
class ScraperMetrics:
    start_time: datetime
    end_time: Optional[datetime] = None
    items_scraped: int = 0
    errors: list = None
    response_times: list = None
    status: str = "running"

    def __post_init__(self):
        self.errors = self.errors or []
        self.response_times = self.response_times or []

    def to_dict(self):
        return asdict(self)

class ScraperMonitor:
    def __init__(self):
        self._metrics = {}
        self._setup_logging()

    def _setup_logging(self):
        """Setup logging configuration"""
        self.logger = logging.getLogger('scraper_monitor')
        
        # Clear any existing handlers
        self.logger.handlers = []
        
        # Only add handler if none exists
        if not self.logger.handlers:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(logging.INFO)
            
            formatter = logging.Formatter(
                f'{Fore.CYAN}%(asctime)s{Style.RESET_ALL} - '
                f'%(levelname)s - %(message)s'
            )
            console_handler.setFormatter(formatter)
            
        self.logger.addHandler(console_handler)

    def _log_scraper_status(self, scraper_name: str, status: str, **kwargs):
        """Log scraper status with visual formatting"""
        if status == 'start':
            self.logger.info(f"{'='*80}")
            self.logger.info(f"Starting scraper: {scraper_name}")
            self.logger.info(f"{'='*80}")
        elif status == 'end':
            items = kwargs.get('items', 0)
            duration = kwargs.get('duration', 0)
            self.logger.info(f"{'-'*80}")
            self.logger.info(f"Completed scraper: {scraper_name}")
            self.logger.info(f"Items scraped: {items}")
            self.logger.info(f"Duration: {duration:.2f} seconds")
            self.logger.info(f"{'='*80}\n")
        elif status == 'error':
            error = kwargs.get('error', 'Unknown error')
            self.logger.error(f"Error in {scraper_name}: {error}")
            self.logger.error(f"{'='*80}\n")

    def start_scrape(self, scraper_name: str) -> None:
        self.logger.info(f"{Fore.GREEN}Starting scrape for {scraper_name}{Style.RESET_ALL}")
        self._metrics[scraper_name] = {
            'start_time': timezone.now(),
            'items_scraped': 0,
            'errors': []
        }

    def end_scrape(self, scraper_name: str, items_count: int) -> None:
        if scraper_name in self._metrics:
            duration = (timezone.now() - self._metrics[scraper_name]['start_time']).total_seconds()
            self.logger.info(
                f"{Fore.GREEN}Completed scrape for {scraper_name}:{Style.RESET_ALL}\n"
                f"Items scraped: {items_count}\n"
                f"Duration: {duration:.2f} seconds"
            )
    def record_error(self, scraper_name: str, error: str) -> None:
        self.logger.error(f"{Fore.RED}Error in {scraper_name}: {error}{Style.RESET_ALL}")
        if scraper_name in self._metrics:
            self._metrics[scraper_name]['errors'].append(error)

    def record_response_time(self, scraper_name: str, response_time: float) -> None:
        """Record response time for performance monitoring"""
        latest_metric = self._get_latest_metric(scraper_name)
        if latest_metric:
            latest_metric.response_times.append(response_time)
            self._check_performance(scraper_name, response_time)

    def get_scraper_stats(self, scraper_name: str, days: int = 7) -> Dict[str, Any]:
        """Get statistics for a scraper over the specified number of days"""
        cutoff_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        metrics = [
            metric for timestamp, metric in self._metrics[scraper_name].items()
            if timestamp >= cutoff_date
        ]

        if not metrics:
            return {}

        success_rate = len([m for m in metrics if m.status == "completed"]) / len(metrics)
        response_times = [rt for m in metrics for rt in m.response_times]
        
        return {
            'success_rate': success_rate,
            'avg_items_scraped': statistics.mean([m.items_scraped for m in metrics]),
            'avg_response_time': statistics.mean(response_times) if response_times else 0,
            'error_count': sum(len(m.errors) for m in metrics),
            'total_runs': len(metrics)
        }

    def _get_latest_metric(self, scraper_name: str) -> Optional[ScraperMetrics]:
        """Get the most recent metrics for a scraper"""
        if not self._metrics[scraper_name]:
            return None
        latest_time = max(self._metrics[scraper_name].keys())
        return self._metrics[scraper_name][latest_time]

    def _check_metrics(self, scraper_name: str, metrics: ScraperMetrics) -> None:
        """Check various metrics and trigger alerts if necessary"""
        if metrics.end_time:
            duration = (metrics.end_time - metrics.start_time).total_seconds() / 60
            if duration > self.alert_thresholds['max_duration_minutes']:
                self._send_alert(
                    scraper_name,
                    f"Scraper taking too long: {duration:.1f} minutes"
                )

        if metrics.items_scraped < self.alert_thresholds['min_items']:
            self._send_alert(
                scraper_name,
                f"Low item count: {metrics.items_scraped} items"
            )

    def _check_consecutive_failures(self, scraper_name: str) -> None:
        """Check for consecutive failures and alert if threshold is exceeded"""
        recent_metrics = sorted(
            self._metrics[scraper_name].items(),
            key=lambda x: x[0],
            reverse=True
        )[:self.alert_thresholds['consecutive_failures']]

        if len(recent_metrics) == self.alert_thresholds['consecutive_failures']:
            if all(m.status == "failed" for _, m in recent_metrics):
                self._send_alert(
                    scraper_name,
                    f"Consecutive failures: {self.alert_thresholds['consecutive_failures']}"
                )

    def _check_performance(self, scraper_name: str, response_time: float) -> None:
        """Check performance metrics and alert if necessary"""
        latest_metric = self._get_latest_metric(scraper_name)
        if latest_metric and len(latest_metric.response_times) > 10:
            avg_time = statistics.mean(latest_metric.response_times[-10:])
            if avg_time > 5.0:  # Alert if average response time > 5 seconds
                self._send_alert(
                    scraper_name,
                    f"High response time: {avg_time:.1f} seconds"
                )

    def _send_alert(self, scraper_name: str, message: str) -> None:
        """Send alert email for scraper issues"""
        alert_key = f"{scraper_name}:{message}"
        if alert_key in self._alerts_sent:
            return

        try:
            if settings.EMAIL_BACKEND == 'django.core.mail.backends.console.EmailBackend':
                # For development, just log the alert
                logger.info(f"ALERT - {scraper_name}: {message}")
                self._alerts_sent.add(alert_key)
            else:
                # For production, send email
                send_mail(
                    subject=f"Scraper Alert: {scraper_name}",
                    message=message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[settings.ADMIN_EMAIL],
                    fail_silently=True,  # Changed to True to prevent exceptions
                )
                self._alerts_sent.add(alert_key)
                logger.info(f"Alert sent for {scraper_name}: {message}")
        except Exception as e:
            logger.error(f"Failed to send alert: {str(e)}")

    async def cleanup_old_metrics(self, days_to_keep: int = 30) -> None:
        """Clean up old metrics data"""
        cutoff_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        for scraper_name in self._metrics:
            self._metrics[scraper_name] = {
                timestamp: metric
                for timestamp, metric in self._metrics[scraper_name].items()
                if timestamp >= cutoff_date
            }

    def save_metrics(self, filename: str = 'scraper_metrics.json') -> None:
        """Save metrics to file"""
        try:
            metrics_dict = {
                scraper: {
                    timestamp.isoformat(): metric.to_dict()
                    for timestamp, metric in scraper_metrics.items()
                }
                for scraper, scraper_metrics in self._metrics.items()
            }
            
            with open(filename, 'w') as f:
                json.dump(metrics_dict, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save metrics: {str(e)}")

    def load_metrics(self, filename: str = 'scraper_metrics.json') -> None:
        """Load metrics from file"""
        try:
            with open(filename, 'r') as f:
                metrics_dict = json.load(f)
                
            self._metrics = defaultdict(dict)
            for scraper, scraper_metrics in metrics_dict.items():
                for timestamp_str, metric_dict in scraper_metrics.items():
                    timestamp = datetime.fromisoformat(timestamp_str)
                    self._metrics[scraper][timestamp] = ScraperMetrics(**metric_dict)
        except Exception as e:
            logger.error(f"Failed to load metrics: {str(e)}")

logger.info("Loaded monitor module")