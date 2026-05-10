from util.download.task.info import TaskInfo
from util.common.enum import DownloadStatus
from util.common import config

from typing import List, Optional
import time
import logging

logger = logging.getLogger(__name__)

SMALL_FILE_THRESHOLD = 50 * 1024 * 1024
MEDIUM_FILE_THRESHOLD = 200 * 1024 * 1024
LARGE_FILE_THRESHOLD = 500 * 1024 * 1024

WEIGHT_SIZE = 0.6
WEIGHT_WAIT = 0.4

STARVATION_THRESHOLD = 30.0

BASE_THREADS = 4
MIN_THREADS = 1
MAX_THREADS = 10

SIZE_SCALE_REFERENCE = 1024 * 1024 * 1024


class TaskPriority:
    def __init__(self, task_info: TaskInfo, queue_time: float):
        self.task_id = task_info.Basic.task_id
        self.task_info = task_info
        self.queue_time = queue_time
        self.file_size = max(float(task_info.Download.total_size), 1.0)
        self.priority_score = 0.0

    def calculate(self, max_file_size: float, current_time: float):
        size_ratio = self.file_size / max(max_file_size, 1.0)
        size_score = 1.0 - size_ratio

        wait_time = current_time - self.queue_time
        wait_score = min(wait_time / STARVATION_THRESHOLD, 1.0)

        self.priority_score = WEIGHT_SIZE * size_score + WEIGHT_WAIT * wait_score
        return self.priority_score


class ResourceAllocator:
    def __init__(self):
        self._queue_times: dict[str, float] = {}
        self._speed_history: dict[str, list[float]] = {}

    def register_queue(self, task_info: TaskInfo):
        self._queue_times[task_info.Basic.task_id] = time.time()

    def unregister(self, task_id: str):
        self._queue_times.pop(task_id, None)
        self._speed_history.pop(task_id, None)

    def record_speed(self, task_id: str, speed: int):
        if task_id not in self._speed_history:
            self._speed_history[task_id] = []
        history = self._speed_history[task_id]
        history.append(float(speed))
        if len(history) > 10:
            history.pop(0)

    def get_average_speed(self, task_id: str) -> float:
        history = self._speed_history.get(task_id, [])
        if not history:
            return 0.0
        return sum(history) / len(history)

    def select_next_task(self, queued_tasks: List[TaskInfo], active_tasks: List[TaskInfo]) -> Optional[TaskInfo]:
        if not queued_tasks:
            return None

        current_time = time.time()
        max_file_size = 1.0
        for task in queued_tasks + active_tasks:
            size = max(float(task.Download.total_size), 1.0)
            if size > max_file_size:
                max_file_size = size

        priorities = []
        for task in queued_tasks:
            task_id = task.Basic.task_id
            if task_id not in self._queue_times:
                self._queue_times[task_id] = current_time

            priority = TaskPriority(task, self._queue_times[task_id])
            priority.calculate(max_file_size, current_time)
            priorities.append(priority)

        priorities.sort(key=lambda p: p.priority_score, reverse=True)

        if priorities:
            logger.debug(
                f"任务调度优先级: "
                + ", ".join(
                    f"{p.task_id[:8]}... score={p.priority_score:.3f} size={p.file_size / 1024 / 1024:.1f}MB"
                    for p in priorities[:3]
                )
            )

        best = priorities[0].task_info if priorities else None
        return best

    def calculate_thread_allocation(self, task_info: TaskInfo, active_tasks: List[TaskInfo], base_threads: int = None) -> int:
        if base_threads is None:
            base_threads = config.get(config.download_thread)

        if not active_tasks:
            return base_threads

        total_remaining = 0.0
        task_remaining = 0.0

        for task in active_tasks + [task_info]:
            total_size = max(float(task.Download.total_size), 1.0)
            downloaded = max(float(task.Download.downloaded_size), 0.0)
            remaining = max(total_size - downloaded, 1.0)
            total_remaining += remaining
            if task.Basic.task_id == task_info.Basic.task_id:
                task_remaining = remaining

        if total_remaining <= 0:
            return base_threads

        ratio = task_remaining / total_remaining
        allocation = max(MIN_THREADS, round(base_threads * ratio * len(active_tasks + [task_info])))
        allocation = min(allocation, MAX_THREADS)

        return allocation

    def adjust_parallel_limit(self, active_tasks: List[TaskInfo], base_limit: int = None) -> int:
        if base_limit is None:
            base_limit = config.get(config.download_parallel)

        if not active_tasks:
            return base_limit

        total_size = 0.0
        for task in active_tasks:
            total_size += max(float(task.Download.total_size), 0.0)

        avg_size = total_size / len(active_tasks)

        if avg_size < SMALL_FILE_THRESHOLD:
            adjustment = 2
        elif avg_size < MEDIUM_FILE_THRESHOLD:
            adjustment = 1
        elif avg_size > LARGE_FILE_THRESHOLD:
            adjustment = -1
        else:
            adjustment = 0

        effective_limit = max(1, base_limit + adjustment)
        return effective_limit

    def get_file_size_category(self, size: float) -> str:
        if size < SMALL_FILE_THRESHOLD:
            return "small"
        elif size < MEDIUM_FILE_THRESHOLD:
            return "medium"
        elif size < LARGE_FILE_THRESHOLD:
            return "large"
        else:
            return "xlarge"

    def get_allocation_summary(self, active_tasks: List[TaskInfo], queued_tasks: List[TaskInfo]) -> dict:
        summary = {
            "active_count": len(active_tasks),
            "queued_count": len(queued_tasks),
            "active_sizes": [],
            "queued_sizes": [],
            "total_active_size": 0,
            "total_queued_size": 0,
        }

        for task in active_tasks:
            size = max(float(task.Download.total_size), 0.0)
            summary["active_sizes"].append({
                "task_id": task.Basic.task_id[:8],
                "size_mb": round(size / 1024 / 1024, 1),
                "category": self.get_file_size_category(size),
                "progress": task.Download.progress,
            })
            summary["total_active_size"] += size

        for task in queued_tasks:
            size = max(float(task.Download.total_size), 0.0)
            summary["queued_sizes"].append({
                "task_id": task.Basic.task_id[:8],
                "size_mb": round(size / 1024 / 1024, 1),
                "category": self.get_file_size_category(size),
            })
            summary["total_queued_size"] += size

        return summary


resource_allocator = ResourceAllocator()