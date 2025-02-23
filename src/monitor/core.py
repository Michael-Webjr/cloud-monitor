import psutil
import time
from datetime import datetime
import logging
from pathlib import Path
import subprocess
from typing import Dict, Any, Optional

class DevEnvironmentMonitor:
    """
    Development Environment Monitor for Raspberry Pi.
    
    This class monitors various aspects of a development environment:
    - System resources (CPU, memory, disk)
    - Pi-specific metrics (temperature, throttling)
    - Development tools and services
    - Network connectivity
    """
    
    def __init__(self, config_path: Optional[Path] = None):
        # Set up logging with detailed formatting
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('dev_monitor.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger('DevMonitor')
        self.logger.info("Initializing Development Environment Monitor")
        
        # Initialize monitoring paths
        self.temp_path = Path('/sys/class/thermal/thermal_zone0/temp')
        self.throttle_path = Path('/sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq')
        
        # Track monitored services
        self.dev_services = [
            'ssh',          # Remote access
            'docker',       # Container service
            'nginx',        # Web server
            'postgresql'    # Database
        ]
        
        self.logger.info("Monitor initialized successfully")

    def get_cpu_metrics(self) -> Dict[str, float]:
        """
        Get comprehensive CPU metrics specific to development work.
        Includes load averages which are crucial for development tasks.
        """
        try:
            # Get CPU load averages (1, 5, 15 minutes)
            load1, load5, load15 = psutil.getloadavg()
            cpu_count = psutil.cpu_count()
            
            return {
                'cpu_percent': psutil.cpu_percent(interval=1),
                'load_1min': round(load1/cpu_count * 100, 2),
                'load_5min': round(load5/cpu_count * 100, 2),
                'load_15min': round(load15/cpu_count * 100, 2),
                'cpu_freq': psutil.cpu_freq().current if psutil.cpu_freq() else 0
            }
        except Exception as e:
            self.logger.error(f"Error getting CPU metrics: {e}")
            return {}

    def get_temperature(self) -> Optional[float]:
        """
        Get Raspberry Pi CPU temperature.
        This is crucial for monitoring Pi's health in development environment.
        """
        try:
            with open(self.temp_path, 'r') as f:
                # Convert millidegrees to degrees Celsius
                return round(float(f.read().strip()) / 1000.0, 2)
        except Exception as e:
            self.logger.error(f"Error reading temperature: {e}")
            return None

    def get_memory_metrics(self) -> Dict[str, float]:
        """
        Get memory metrics focused on development needs.
        Includes swap usage which is important for development tools.
        """
        try:
            mem = psutil.virtual_memory()
            swap = psutil.swap_memory()
            
            return {
                'memory_used_percent': mem.percent,
                'memory_available_gb': round(mem.available / (1024**3), 2),
                'swap_used_percent': swap.percent,
                'swap_free_gb': round(swap.free / (1024**3), 2)
            }
        except Exception as e:
            self.logger.error(f"Error getting memory metrics: {e}")
            return {}

    def check_dev_services(self) -> Dict[str, bool]:
        """
        Check status of development-related services.
        """
        service_status = {}
        for service in self.dev_services:
            try:
                # Use systemctl to check service status
                result = subprocess.run(
                    ['systemctl', 'is-active', service],
                    capture_output=True,
                    text=True
                )
                service_status[service] = result.stdout.strip() == 'active'
            except Exception as e:
                self.logger.error(f"Error checking {service} status: {e}")
                service_status[service] = False
        return service_status

    def get_all_metrics(self) -> Dict[str, Any]:
        """
        Get comprehensive development environment metrics.
        """
        metrics = {
            'timestamp': datetime.now().isoformat(),
            'cpu': self.get_cpu_metrics(),
            'memory': self.get_memory_metrics(),
            'temperature': self.get_temperature(),
            'services': self.check_dev_services()
        }
        
        return metrics

    def start_monitoring(self, interval: int = 60):
        """
        Start continuous monitoring of the development environment.
        Default interval is 60 seconds to avoid excessive logging.
        """
        self.logger.info("Starting development environment monitoring")
        try:
            while True:
                metrics = self.get_all_metrics()
                self.logger.info(f"Current metrics: {metrics}")
                
                # Alert on high temperature
                if metrics['temperature'] and metrics['temperature'] > 80:
                    self.logger.warning(f"High temperature detected: {metrics['temperature']}°C")
                
                # Alert on high memory usage
                if metrics['memory']['memory_used_percent'] > 90:
                    self.logger.warning("High memory usage detected!")
                
                # Alert on service issues
                for service, status in metrics['services'].items():
                    if not status:
                        self.logger.warning(f"Service {service} is not running!")
                
                time.sleep(interval)
                
        except KeyboardInterrupt:
            self.logger.info("Monitoring stopped by user")
        except Exception as e:
            self.logger.error(f"Monitoring error: {e}")

if __name__ == "__main__":
    # Create and start the monitor
    monitor = DevEnvironmentMonitor()
    monitor.start_monitoring()
