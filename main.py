from job_processor import JobProcessor

if __name__ == "__main__":
    worker = JobProcessor()
    worker.start_worker()