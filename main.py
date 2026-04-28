from job_processor import JobProcessor
from dotenv import load_dotenv

load_dotenv()


if __name__ == "__main__":
    worker = JobProcessor()
    worker.start_worker()
    
