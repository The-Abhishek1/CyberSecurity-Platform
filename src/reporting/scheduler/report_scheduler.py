
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
import asyncio
import logging
import uuid

logger = logging.getLogger(__name__)


class ReportScheduler:
    """Schedules and manages recurring reports"""
    
    def __init__(self):
        self.scheduled_jobs = {}
        self.execution_history = []
        self.running = False
        logger.info("Report Scheduler initialized")
    
    async def schedule_job(self,
                           job_type: str,
                           schedule: str,
                           func: Callable,
                           args: List = None,
                           kwargs: Dict = None,
                           recipients: List[str] = None) -> str:
        """Schedule a recurring job"""
        
        job_id = f"job_{uuid.uuid4().hex[:12]}"
        
        # Parse schedule (simplified cron format)
        schedule_parts = schedule.split()
        if len(schedule_parts) != 5:
            raise ValueError("Schedule must be in cron format: 'minute hour day month day_of_week'")
        
        job = {
            "job_id": job_id,
            "type": job_type,
            "schedule": schedule,
            "schedule_parts": schedule_parts,
            "func": func,
            "args": args or [],
            "kwargs": kwargs or {},
            "recipients": recipients or [],
            "created_at": datetime.utcnow().isoformat(),
            "last_run": None,
            "next_run": await self._calculate_next_run(schedule_parts),
            "status": "active",
            "run_count": 0
        }
        
        self.scheduled_jobs[job_id] = job
        
        logger.info(f"Scheduled job {job_id} with schedule '{schedule}'")
        
        # Start scheduler if not running
        if not self.running:
            asyncio.create_task(self._scheduler_loop())
            self.running = True
        
        return job_id
    
    async def _scheduler_loop(self):
        """Main scheduler loop"""
        
        while self.running:
            now = datetime.utcnow()
            
            for job_id, job in self.scheduled_jobs.items():
                if job["status"] != "active":
                    continue
                
                if job.get("next_run") and now >= datetime.fromisoformat(job["next_run"]):
                    # Execute job
                    asyncio.create_task(self._execute_job(job_id))
            
            await asyncio.sleep(60)  # Check every minute
    
    async def _execute_job(self, job_id: str):
        """Execute a scheduled job"""
        
        job = self.scheduled_jobs.get(job_id)
        if not job:
            return
        
        logger.info(f"Executing scheduled job {job_id}")
        
        start_time = datetime.utcnow()
        
        try:
            # Execute the function
            if asyncio.iscoroutinefunction(job["func"]):
                result = await job["func"](*job["args"], **job["kwargs"])
            else:
                result = job["func"](*job["args"], **job["kwargs"])
            
            status = "success"
            error = None
            
            # Send to recipients if provided
            if job["recipients"] and result:
                await self._deliver_report(result, job["recipients"])
            
        except Exception as e:
            logger.error(f"Job {job_id} failed: {e}")
            status = "failed"
            error = str(e)
            result = None
        
        end_time = datetime.utcnow()
        
        # Record execution
        execution = {
            "job_id": job_id,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "duration_seconds": (end_time - start_time).total_seconds(),
            "status": status,
            "error": error
        }
        self.execution_history.append(execution)
        
        # Update job
        job["last_run"] = start_time.isoformat()
        job["run_count"] += 1
        job["next_run"] = await self._calculate_next_run(job["schedule_parts"], start_time)
    
    async def _deliver_report(self, report: Dict, recipients: List[str]):
        """Deliver report to recipients"""
        
        logger.info(f"Delivering report {report.get('report_id')} to {len(recipients)} recipients")
        
        for recipient in recipients:
            # In production, would send email, Slack, etc.
            logger.debug(f"Would send report to {recipient}")
    
    async def _calculate_next_run(self, schedule_parts: List[str], from_time: Optional[datetime] = None) -> str:
        """Calculate next run time based on cron expression"""
        
        # Simplified cron calculation - just add 1 day for daily reports
        # In production, use a proper cron library like croniter
        from_time = from_time or datetime.utcnow()
        
        minute, hour, day, month, day_of_week = schedule_parts
        
        # Simple handling for common patterns
        if minute == "0" and hour == "0" and day == "*" and month == "*" and day_of_week == "*":
            # Daily at midnight
            next_run = from_time.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        elif minute == "0" and hour == "9" and day == "*" and month == "*" and day_of_week == "*":
            # Daily at 9 AM
            next_run = from_time.replace(hour=9, minute=0, second=0, microsecond=0)
            if next_run <= from_time:
                next_run += timedelta(days=1)
        elif minute == "0" and hour == "*" and day == "*" and month == "*" and day_of_week == "*":
            # Hourly
            next_run = from_time.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
        elif minute == "*/5" and hour == "*" and day == "*" and month == "*" and day_of_week == "*":
            # Every 5 minutes
            minutes = (from_time.minute // 5 + 1) * 5
            next_run = from_time.replace(minute=minutes % 60, second=0, microsecond=0)
            if minutes >= 60:
                next_run += timedelta(hours=1)
        else:
            # Default: next day
            next_run = from_time + timedelta(days=1)
        
        return next_run.isoformat()
    
    async def get_job(self, job_id: str) -> Optional[Dict]:
        """Get job details"""
        
        job = self.scheduled_jobs.get(job_id)
        if job:
            # Return a copy without the function
            return {k: v for k, v in job.items() if k != "func"}
        
        return None
    
    async def list_jobs(self, status: Optional[str] = None) -> List[Dict]:
        """List scheduled jobs"""
        
        jobs = []
        for job in self.scheduled_jobs.values():
            job_copy = {k: v for k, v in job.items() if k != "func"}
            jobs.append(job_copy)
        
        if status:
            jobs = [j for j in jobs if j["status"] == status]
        
        return jobs
    
    async def pause_job(self, job_id: str) -> bool:
        """Pause a scheduled job"""
        
        if job_id in self.scheduled_jobs:
            self.scheduled_jobs[job_id]["status"] = "paused"
            logger.info(f"Paused job {job_id}")
            return True
        
        return False
    
    async def resume_job(self, job_id: str) -> bool:
        """Resume a paused job"""
        
        if job_id in self.scheduled_jobs:
            self.scheduled_jobs[job_id]["status"] = "active"
            logger.info(f"Resumed job {job_id}")
            return True
        
        return False
    
    async def delete_job(self, job_id: str) -> bool:
        """Delete a scheduled job"""
        
        if job_id in self.scheduled_jobs:
            del self.scheduled_jobs[job_id]
            logger.info(f"Deleted job {job_id}")
            return True
        
        return False
    
    async def get_execution_history(self, job_id: Optional[str] = None, limit: int = 100) -> List[Dict]:
        """Get execution history"""
        
        history = self.execution_history
        
        if job_id:
            history = [h for h in history if h["job_id"] == job_id]
        
        return sorted(history, key=lambda x: x["start_time"], reverse=True)[:limit]