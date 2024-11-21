import time
from typing import Union

class ProgressTracker:
    def __init__(self):
        self.start_time = time.time()
        self.last_update = 0
        self.last_size = 0
        
    def update_progress(self, current: int, total: int, message, action: str):
        now = time.time()
        diff = now - self.last_update
        
        if diff < 1 and current != total:  # Update only after 1 second
            return
            
        self.last_update = now
        
        # Calculate speed
        if self.last_size:
            speed = (current - self.last_size) / diff
        else:
            speed = current / (now - self.start_time)
            
        self.last_size = current
        
        # Calculate progress and ETA
        progress = current * 100 / total
        elapsed_time = now - self.start_time
        if speed > 0:
            eta = (total - current) / speed
        else:
            eta = 0
            
        progress_str = self._get_progress_bar(progress)
        
        status = (
            f"{action}\n"
            f"{progress_str} {progress:.1f}%\n"
            f"Speed: {self._format_speed(speed)}\n"
            f"ETA: {self._format_time(eta)}\n"
        )
        
        return status
    
    @staticmethod
    def _get_progress_bar(percentage: float) -> str:
        filled_length = int(percentage // 10)
        return '█' * filled_length + '░' * (10 - filled_length)
    
    @staticmethod
    def _format_speed(speed: float) -> str:
        units = ['B/s', 'KB/s', 'MB/s', 'GB/s']
        for unit in units:
            if speed < 1024:
                return f"{speed:.2f} {unit}"
            speed /= 1024
            
    @staticmethod
    def _format_time(seconds: float) -> str:
        if seconds <= 0:
            return "0s"
            
        parts = []
        for unit, div in [('h', 3600), ('m', 60), ('s', 1)]:
            amount = int(seconds // div)
            seconds %= div
            if amount > 0:
                parts.append(f'{amount}{unit}')
                
        return ' '.join(parts) 